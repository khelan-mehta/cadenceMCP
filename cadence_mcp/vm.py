"""VMware guest-exec bridge.

The Cadence tools run inside a VMware VM. We drive them from the Windows host
with `vmrun`, using the validated pattern:
    copyFileFromHostToGuest  <script.sh>
    runProgramInGuest        /bin/bash -l <script.sh>   (redirects its own stdout)
    copyFileFromGuestToHost  <output files>

`runProgramInGuest` does NOT capture stdout, so every script we run redirects
`exec > logfile 2>&1` internally and we copy the log back.
"""
from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import config


class VMError(RuntimeError):
    pass


def _vmrun(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    cmd = [config.VMRUN, "-T", "ws", "-gu", config.GUEST_USER, "-gp", config.GUEST_PASS, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def is_running() -> bool:
    try:
        cp = subprocess.run([config.VMRUN, "list"], capture_output=True, text=True, timeout=30)
    except Exception:
        return False
    return config.VMX in cp.stdout


def guest_ready() -> bool:
    """True if VMware Tools accepts guest-exec (guest booted + logged in)."""
    try:
        cp = _vmrun("runProgramInGuest", config.VMX, "/bin/echo", "ready", timeout=30)
    except Exception:
        return False
    return cp.returncode == 0


def start(wait: bool = True, timeout: int = 420) -> str:
    """Power on the VM (headless) and optionally wait for guest-exec."""
    if not is_running():
        cp = subprocess.run([config.VMRUN, "-T", "ws", "start", config.VMX, "nogui"],
                            capture_output=True, text=True, timeout=120)
        if cp.returncode != 0:
            raise VMError(f"failed to start VM: {cp.stderr or cp.stdout}")
    if not wait:
        return "starting"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if guest_ready():
            return "ready"
        time.sleep(8)
    raise VMError("VM started but guest-exec not ready before timeout")


def stop(hard: bool = False) -> str:
    mode = "hard" if hard else "soft"
    cp = subprocess.run([config.VMRUN, "-T", "ws", "stop", config.VMX, mode],
                        capture_output=True, text=True, timeout=120)
    return "stopped" if cp.returncode == 0 else (cp.stderr or cp.stdout)


def push(local: Path | str, guest: str) -> None:
    cp = _vmrun("copyFileFromHostToGuest", config.VMX, str(local), guest)
    if cp.returncode != 0:
        raise VMError(f"push {local} -> {guest} failed: {cp.stderr or cp.stdout}")


def pull(guest: str, local: Path | str) -> bool:
    cp = _vmrun("copyFileFromGuestToHost", config.VMX, guest, str(local))
    return cp.returncode == 0


@dataclass
class ScriptResult:
    returncode: int
    log: str
    pulled: dict[str, Path] = field(default_factory=dict)   # guest path -> local path


def run_script(
    body: str,
    pull_files: Iterable[str] = (),
    with_env: bool = True,
    timeout: int = 300,
    tag: str = "job",
) -> ScriptResult:
    """Run a bash script inside the guest and return its combined log.

    `body` is bash. We prepend the Cadence env (unless with_env=False) and wrap
    with `exec > log 2>&1`. Requested guest files in `pull_files` are copied back
    to the host WORK_DIR and returned in `.pulled`.
    """
    jid = f"{tag}_{uuid.uuid4().hex[:8]}"
    guest_log = f"/tmp/{jid}.log"
    guest_sh = f"/tmp/{jid}.sh"
    local_sh = config.WORK_DIR / f"{jid}.sh"
    local_log = config.WORK_DIR / f"{jid}.log"

    env = config.CADENCE_ENV + "\n" if with_env else ""
    script = f"#!/bin/bash\nexec > {guest_log} 2>&1\n{env}\n{body}\n"
    local_sh.write_text(script.replace("\r\n", "\n"), encoding="utf-8", newline="\n")

    push(local_sh, guest_sh)
    cp = _vmrun("runProgramInGuest", config.VMX, "/bin/bash", "-l", guest_sh, timeout=timeout)
    rc = cp.returncode

    pull(guest_log, local_log)
    log = local_log.read_text(encoding="utf-8", errors="replace") if local_log.exists() else ""

    pulled: dict[str, Path] = {}
    for gp in pull_files:
        name = gp.rstrip("/").split("/")[-1]
        dest = config.WORK_DIR / f"{jid}__{name}"
        if pull(gp, dest):
            pulled[gp] = dest
    return ScriptResult(returncode=rc, log=log, pulled=pulled)


def status() -> dict:
    running = is_running()
    ready = guest_ready() if running else False
    return {
        "vmx": config.VMX,
        "running": running,
        "guest_ready": ready,
        "guest_user": config.GUEST_USER,
    }
