# bastion/core/janitor.py

from bastion.core import zfs, jails
from bastion.core.utils import run_command
from bastion.runner.workspace import JOB_PREFIX

def scan_zombie_jails():
    """
    Finds any running jails that look like Bastion jobs and kills them.
    """
    print("-> JANITOR: Scanning for zombie jails...")

    try:
        output = run_command(["jls", "name"])
    except Exception:
        return

    active_jails = output.splitlines()

    count = 0
    for jail_name in active_jails:
        if jail_name.startswith("job-"):
            print(f"   [KILL] Found zombie jail: {jail_name}")
            jails.stop_jail(jail_name)
            count += 1

    print(f"-> JANITOR: Cleaned up {count} zombie jails.")

def scan_leaked_datasets():
    """
    Finds any ZFS datasets that look like Bastion workspaces and destroys them.
    """
    print("-> JANITOR: Scanning for leaked datasets...")

    parent_path = f"{zfs.BASE_POOL}/{JOB_PREFIX.rstrip('/')}"

    try:
        output = run_command(["zfs", "list", "-r", "-t", "filesystem", "-H", "-o", "name", parent_path])
    except Exception:
        return

    datasets = output.splitlines()

    count = 0
    for ds in datasets:
        if "job-" in ds and ds != parent_path:
            print(f"   [DESTROY] Found leaked dataset: {ds}")

            try:
                run_command(["zfs", "destroy", "-r", "-f", ds])
                count += 1
            except Exception as e:
                print(f"   [ERR] Failed to destroy {ds}: {e}")

    print(f"-> JANITOR: Cleaned up {count} leaked datasets.")

def cleanup_all():
    """
    The main entry point for system cleanup.
    """
    print("=== BASTION SYSTEM CLEANUP ===")
    scan_zombie_jails()
    scan_leaked_datasets()
    print("=== CLEANUP COMPLETE ===")
