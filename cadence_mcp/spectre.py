"""Orchestrate a headless Spectre run on the VM and parse the results.

A "netlist" is a complete standalone Spectre deck (simulator lang=spectre, model
include, devices, options, and one or more analysis statements). We:
  1. push the netlist into a guest run directory,
  2. run `spectre <deck> -format psfascii -raw ./psf`,
  3. stream every PSF result file back inside the run log (one round-trip),
  4. parse each into numeric arrays.

Result files are named after the analysis statement, e.g. an analysis named
`acs` of type `ac` produces `psf/acs.ac`.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import config, vm
from .psf import parse_psf_text
from .opparse import parse_opinfo

_FILE_MARK = "@@@PSFFILE::"
_END_MARK = "@@@ENDFILE"
_OP_MARK = "@@@OPINFO"
_OP_END = "@@@ENDOP"


@dataclass
class SpectreResult:
    ok: bool
    run_name: str
    log: str
    errors: int = 0
    warnings: int = 0
    # analysis name -> parsed dict (see psf.parse_psf_text)
    analyses: dict[str, dict] = field(default_factory=dict)
    # analysis name -> spectre file extension (dc/ac/tran/...)
    kinds: dict[str, str] = field(default_factory=dict)
    # parsed operating-point info (from `info what=oppoint`), if present
    opinfo: dict = field(default_factory=dict)


def _count(log: str, word: str) -> int:
    m = re.search(r"spectre completes with (\d+) errors?, (\d+) warnings?", log)
    if not m:
        return 0
    return int(m.group(1)) if word == "errors" else int(m.group(2))


def run_netlist(netlist: str, run_name: str | None = None, timeout: int = 400) -> SpectreResult:
    run_name = run_name or f"run_{uuid.uuid4().hex[:8]}"
    guest_dir = f"{config.GUEST_RUNS_ROOT}/{run_name}"

    # push netlist to /tmp then move into run dir inside the script
    jid = uuid.uuid4().hex[:8]
    local_scs = config.WORK_DIR / f"{jid}.scs"
    local_scs.write_text(netlist.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    guest_tmp_scs = f"/tmp/{jid}.scs"
    vm.push(local_scs, guest_tmp_scs)

    body = f"""
rm -rf {guest_dir}
mkdir -p {guest_dir}
cp {guest_tmp_scs} {guest_dir}/input.scs
cd {guest_dir}
spectre input.scs -format psfascii -raw ./psf +log ./spectre.log
SPRC=$?
echo "@@@SPECTRE_RC=$SPRC"
if [ -d ./psf ]; then
  for f in ./psf/*; do
    case "$f" in
      *.dc|*.ac|*.tran|*.noise|*.pz|*.sp|*.stb|*.xf|*.dcmatch|*.pss|*.pac|*.pnoise)
        echo "{_FILE_MARK}$(basename $f)"
        cat "$f"
        echo "{_END_MARK}"
        ;;
    esac
  done
fi
if [ -f ./op.info ]; then
  echo "{_OP_MARK}"
  cat ./op.info
  echo "{_OP_END}"
fi
echo "@@@DONE"
"""
    res = vm.run_script(body, with_env=True, timeout=timeout, tag=f"spectre_{run_name}")
    log = res.log

    errors = _count(log, "errors")
    warnings = _count(log, "warnings")
    ok = "spectre completes with 0 errors" in log

    analyses: dict[str, dict] = {}
    kinds: dict[str, str] = {}
    # split embedded psf files
    idx = 0
    while True:
        start = log.find(_FILE_MARK, idx)
        if start == -1:
            break
        nl = log.find("\n", start)
        fname = log[start + len(_FILE_MARK):nl].strip()
        end = log.find(_END_MARK, nl)
        if end == -1:
            break
        block = log[nl + 1:end]
        idx = end + len(_END_MARK)
        # files may be "idvgs.dc" or "trans.tran.tran"; analysis name is the
        # part before the first dot, kind is the last extension.
        parts = fname.split(".")
        name = parts[0]
        ext = parts[-1]
        try:
            parsed = parse_psf_text(block)
            analyses[name] = parsed
            kinds[name] = ext
        except Exception as e:  # keep going, record nothing for this file
            analyses[name] = {"error": str(e)}
            kinds[name] = ext

    opinfo: dict = {}
    op_s = log.find(_OP_MARK)
    if op_s != -1:
        op_nl = log.find("\n", op_s)
        op_e = log.find(_OP_END, op_nl)
        if op_e != -1:
            try:
                opinfo = parse_opinfo(log[op_nl + 1:op_e])
            except Exception as e:
                opinfo = {"error": str(e)}

    return SpectreResult(ok=ok, run_name=run_name, log=log, errors=errors,
                         warnings=warnings, analyses=analyses, kinds=kinds, opinfo=opinfo)


def trimmed_log(log: str, max_chars: int = 4000) -> str:
    """Return the informative tail of a spectre log (skip the big embedded PSF dumps)."""
    cut = log.find(_FILE_MARK)
    head = log[:cut] if cut != -1 else log
    if len(head) > max_chars:
        head = head[:1500] + "\n...\n" + head[-max_chars:]
    return head
