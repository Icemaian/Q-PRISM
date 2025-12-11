import os
import shutil
import subprocess
from qprism.netem.profiles import NetemProfile

def apply_profile(profile: NetemProfile, interface: str = "lo", dry_run: bool = False):
    cmd = ["tc", "qdisc", "replace", "dev", interface, "root", "netem"]
    if profile.rtt_ms > 0:
        if profile.jitter_ms and profile.jitter_ms > 0:
            cmd += ["delay", f"{profile.rtt_ms}ms", f"{profile.jitter_ms}ms", "distribution", "normal"]
        else:
            cmd += ["delay", f"{profile.rtt_ms}ms"]
    if profile.loss and profile.loss > 0:
        loss_percent = profile.loss * 100.0
        loss_str = f"{loss_percent:.4f}".rstrip('0').rstrip('.')
        cmd += ["loss", f"{loss_str}%"]
    if dry_run:
        return cmd
    # Make host machine has tc
    if shutil.which("tc") is None:
        raise FileNotFoundError("tc commad not found. Please install tc")
    # Make sure script has root privilege
    if os.geteuid() != 0:
        raise PermissionError("Root privileges are required to apply netem profiles")
    subprocess.run(cmd, check=True)
    return True

def clear(interface: str = "lo", dry_run: bool = False) -> bool | list[str]:
    cmd = ["tc", "qdisc", "del", "dev", interface, "root"]
    if dry_run:
        return cmd
    if shutil.which("tc") is None:
        raise FileNotFoundError("tc command not found, please install")
    if os.geteuid() != 0:
        raise PermissionError("Root privileges are required to clear netem profile")
    subprocess.run(cmd, check=True)
    return True
