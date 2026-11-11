"""Headless SKILL / OpenAccess bridge to Virtuoso.

Runs `virtuoso -nograph -replay <script>` under a virtual X display (Xvfb) so the
full Virtuoso database / pcell / Diva engine is scriptable with no GUI. This is
the foundation for schematic authoring, layout generation, and DRC/LVS/PEX.

Validated: creating a library, binding the gpdk090 tech, opening gpdk090 pcells,
placing instances, and saving cellviews all work this way.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from . import config, vm

SKILL_RUNS_ROOT = "/home/work/mcp_skill_runs"
PDK_CDSLIB = "/home/work/cds.lib"
PDK_TECH_LIB = "gpdk090"

_MARK = "@@@SKILLFILE::"
_END = "@@@ENDFILE"


@dataclass
class SkillResult:
    ok: bool
    run_name: str
    log: str
    values: dict = field(default_factory=dict)     # markers of form "KEY=..."
    files: dict = field(default_factory=dict)       # embedded text files


def _parse_markers(log: str) -> dict:
    """Collect 'MCP:<key>=<value>' lines that SKILL prints for structured output."""
    out = {}
    for m in re.finditer(r"MCP:([A-Za-z0-9_]+)=(.*)", log):
        out[m.group(1)] = m.group(2).strip()
    return out


def run_skill(skill_code: str, run_name: str | None = None,
              scratch_lib: str = "mcp_work", extra_defines: list[str] | None = None,
              read_back: list[str] | None = None, timeout: int = 400) -> SkillResult:
    run_name = run_name or f"skill_{uuid.uuid4().hex[:8]}"
    workdir = f"{SKILL_RUNS_ROOT}/{run_name}"
    defines = [f'DEFINE {scratch_lib} ./{scratch_lib}'] + (extra_defines or [])
    defines_txt = "\n".join(defines)

    # push the SKILL program as a file (avoids heredoc quoting issues)
    jid = uuid.uuid4().hex[:8]
    local_il = config.WORK_DIR / f"{jid}.il"
    local_il.write_text(skill_code.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    guest_il = f"/tmp/{jid}.il"
    vm.push(local_il, guest_il)

    readback_cmds = ""
    for f in (read_back or []):
        readback_cmds += (
            f'if [ -f "{f}" ]; then echo "{_MARK}{f}"; cat "{f}"; echo "{_END}"; fi\n'
        )

    body = f"""
rm -rf {workdir}; mkdir -p {workdir}; cd {workdir}
cat > cds.lib <<'CDSLIB'
SOFTINCLUDE {PDK_CDSLIB}
{defines_txt}
CDSLIB
cp {guest_il} ./run.il
echo "=== virtuoso SKILL (headless, Xvfb) ==="
xvfb-run -a virtuoso -nograph -replay ./run.il -log ./ciw.log < /dev/null
echo "@@@VIRTUOSO_RC=$?"
echo "=== ciw.log ==="
cat ./ciw.log 2>&1
{readback_cmds}
echo "@@@DONE"
"""
    res = vm.run_script(body, with_env=True, timeout=timeout, tag=f"skill_{run_name}")
    log = res.log
    ok = "MCP:OK=1" in log or "SKILL_OK" in log
    values = _parse_markers(log)

    files = {}
    idx = 0
    while True:
        s = log.find(_MARK, idx)
        if s == -1:
            break
        nl = log.find("\n", s)
        name = log[s + len(_MARK):nl].strip()
        e = log.find(_END, nl)
        if e == -1:
            break
        files[name] = log[nl + 1:e]
        idx = e + len(_END)

    return SkillResult(ok=ok, run_name=run_name, log=log, values=values, files=files)


def ciw_tail(log: str, n: int = 3000) -> str:
    """Trim to the informative part of a SKILL log (drop embedded file dumps)."""
    cut = log.find(_MARK)
    head = log[:cut] if cut != -1 else log
    return head[-n:]
