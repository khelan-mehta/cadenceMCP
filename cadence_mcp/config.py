"""Central configuration for the Cadence MCP server.

Everything host/VM-specific lives here so the rest of the code stays portable.
Values were discovered and validated live against the installed appliance.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Host paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent           # ...\cadence MCP
DATA_DIR = PROJECT_ROOT / "data"                                # runs, cache
RUNS_DIR = DATA_DIR / "runs"                                    # one json per run
WORK_DIR = DATA_DIR / "work"                                    # scratch scripts/outputs
for _d in (DATA_DIR, RUNS_DIR, WORK_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# VMware bridge
# ---------------------------------------------------------------------------
VMRUN = os.environ.get(
    "CADENCE_VMRUN",
    r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
)
VMX = os.environ.get(
    "CADENCE_VMX",
    r"C:\Users\NG\Downloads\_Getintopc.com_Cadence_IC_Design_Virtuoso_6.17_Pre-Installed"
    r"\RHEL6_WORK.vmx",
)

# Self-heal: if the configured .vmx does not exist (folder reorganized, stale
# CADENCE_VMX env from an old MCP config), search the usual places for it so a
# wrong path can never hard-block the server.
if not Path(VMX).exists():
    for _root in (Path(r"C:\Users\NG\Downloads"), Path(r"C:\Users\NG\Desktop"),
                  Path(r"C:\Users\NG\Documents")):
        if not _root.exists():
            continue
        _hits = list(_root.glob("**/RHEL6_WORK.vmx"))
        if _hits:
            VMX = str(_hits[0])
            break
GUEST_USER = os.environ.get("CADENCE_GUEST_USER", "work")
GUEST_PASS = os.environ.get("CADENCE_GUEST_PASS", "111111")

# Where runs live inside the guest
GUEST_RUNS_ROOT = "/home/work/mcp_runs"

# ---------------------------------------------------------------------------
# Cadence environment (validated: uncounted license used directly via file,
# so NO license daemon needs to run). This block is prepended to every guest
# script so spectre/ocean/virtuoso are on PATH and licensed.
# ---------------------------------------------------------------------------
CADENCE_ENV = r"""
export MMSIM_ROOT=/opt/MMSIM151
export CDS=/opt/IC617
export CDS_LIC_FILE=/opt/IC617/share/license/license.dat
export LM_LICENSE_FILE=/opt/IC617/share/license/license.dat
export CDS_AUTO_64BIT=ALL
export OA_HOME=/opt/IC617/oa_v22.50.036/
export CDS_Netlisting_Mode=Analog
export PATH=$MMSIM_ROOT/tools/bin:$MMSIM_ROOT/tools/spectre/bin:$CDS/tools/bin:$CDS/tools/dfII/bin:$PATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/IC617/tools/lib:/opt/IC617/tools/lib64
""".strip()

# ---------------------------------------------------------------------------
# PDK (validated devices) -- gpdk090 90nm
# ---------------------------------------------------------------------------
PDK_NAME = "gpdk090"
PDK_MODEL_INCLUDE = "/home/work/gpdk090_v4.6/models/spectre/gpdk090.scs"
# Available corner sections in the model library:
PDK_CORNERS = ["NN", "SS", "SF", "FF", "FS"]      # NN = typical
PDK_DEFAULT_CORNER = "NN"

# Dashboard
DASHBOARD_HOST = os.environ.get("CADENCE_DASH_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.environ.get("CADENCE_DASH_PORT", "8765"))
