"""Run Virtuoso WITH its GUI on an Xvfb display inside the VM, capture PNG screenshots.

run_gui(il, shots=[...]) : il is SKILL; it can call mcpShot("name") to grab the
whole virtual screen into /home/work/widlar_shots/<name>.png. PNGs are pulled
back into designs/widlar/shots/.
"""
from __future__ import annotations
import re, uuid
from pathlib import Path
from cadence_mcp import config, vm

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"; SHOTS.mkdir(exist_ok=True)
GSHOT = "/home/work/widlar_shots"
RUNROOT = "/home/work/widlar_run"

PRELUDE = r'''
procedure( mcpShot(name)
  let( (f)
    hiRedraw()
    f = sprintf(nil "%s/%s.png" "''' + GSHOT + r'''" name)
    system(sprintf(nil "xwd -root -display $DISPLAY | convert xwd:- %s" f))
    printf("MCP:shot=%s\n" f)))
'''

def run_gui(il: str, shots: list[str] = (), timeout: int = 900, w=1600, h=1000,
            read_back: list[str] = (), tag="gui"):
    jid = uuid.uuid4().hex[:8]
    local_il = config.WORK_DIR / f"{tag}_{jid}.il"
    local_il.write_text((PRELUDE + il).replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    vm.push(local_il, f"/tmp/{jid}.il")
    rb = "".join(f'if [ -f "{f}" ]; then echo "@@@FILE::{f}"; cat "{f}"; echo "@@@ENDFILE"; fi\n' for f in read_back)
    body = f'''
mkdir -p {GSHOT} {RUNROOT}; cd {RUNROOT}
rm -f {GSHOT}/*.png
cat > cds.lib <<'CDSLIB'
SOFTINCLUDE /home/work/cds.lib
DEFINE widlar_lib /home/work/widlar_lib
CDSLIB
cp /tmp/{jid}.il ./run_{jid}.il
Xvfb :57 -screen 0 {w}x{h}x24 -nolisten tcp >/dev/null 2>&1 &
XP=$!
sleep 2
export DISPLAY=:57
timeout {timeout-60} virtuoso -replay ./run_{jid}.il -log ./ciw_{jid}.log < /dev/null
echo "@@@VIRTUOSO_RC=$?"
kill $XP
echo "=== ciw ==="; grep -v "^\\i" ./ciw_{jid}.log | tail -300
{rb}
ls -la {GSHOT}
'''
    res = vm.run_script(body, timeout=timeout, tag=tag)
    got = {}
    for s in shots:
        dst = SHOTS / f"{s}.png"
        if vm.pull(f"{GSHOT}/{s}.png", dst):
            got[s] = dst
    files = dict(re.findall(r"@@@FILE::(\S+)\n(.*?)@@@ENDFILE", res.log, re.S))
    return res.log, got, files
