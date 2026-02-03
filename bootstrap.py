import sys
import os
import shutil
from pathlib import Path

# Reuse the robust tools we already built
from bastion.core import zfs
from bastion.core.utils import run_command

# Configuration
FREEBSD_RELEASE = "14.1-RELEASE"
BASE_URL = f"ftp://ftp.freebsd.org/pub/FreeBSD/releases/amd64/{FREEBSD_RELEASE}/base.txz"
BASE_DATASET = "base"
SNAPSHOT_NAME = "golden-lock"

def check_root():
    if os.geteuid() != 0:
        print("Error: Bootstrapping requires root privileges (for ZFS/Jails).")
        print("Please run with sudo: sudo python3 bootstrap.py")
        sys.exit(1)

def bootstrap_system():
    print("========================================")
    print(f"   BASTION BOOTSTRAP ({FREEBSD_RELEASE})")
    print("========================================")

    # 1. Check if the base already exists
    if zfs.exists(BASE_DATASET):
        print(f"[SKIP] Base dataset '{zfs.BASE_POOL}/{BASE_DATASET}' already exists.")

        # Check if snapshot exists
        try:
            # We try to create it; if it fails, it likely exists.
            # In a real tool, we'd list snapshots to be sure.
            zfs.snapshot(BASE_DATASET, SNAPSHOT_NAME)
            print(f"[OK] Created snapshot @{SNAPSHOT_NAME}")
        except Exception:
            print(f"[SKIP] Snapshot @{SNAPSHOT_NAME} likely already exists.")

        print("\nSystem appears ready. Exiting.")
        return

    # 2. Create the ZFS Container
    print(f"\n-> Creating ZFS dataset: {zfs.BASE_POOL}/{BASE_DATASET}...")
    zfs.create_dataset(BASE_DATASET)

    # 3. Download the OS (base.txz)
    # We download to a temporary file on the host
    tmp_file = Path("/tmp/base.txz")
    if not tmp_file.exists():
        print(f"-> Downloading FreeBSD Base System from {BASE_URL}...")
        print("   (This may take a few minutes...)")
        try:
            # We use the system 'fetch' command (standard on FreeBSD)
            run_command(["fetch", "-o", str(tmp_file), BASE_URL])
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            # Cleanup the empty dataset so we can try again later
            zfs.destroy_dataset(BASE_DATASET)
            sys.exit(1)
    else:
        print("-> Found existing /tmp/base.txz, using cached file.")

    # 4. Extract the OS
    mountpoint = f"/{zfs.BASE_POOL}/{BASE_DATASET}"
    print(f"-> Extracting OS to {mountpoint}...")
    try:
        # tar -xf file.txz -C /destination
        run_command(["tar", "-xf", str(tmp_file), "-C", mountpoint])
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        zfs.destroy_dataset(BASE_DATASET)
        sys.exit(1)

    # 5. Network Configuration
    # Copy host DNS so the jail can access the internet
    print("-> Configuring DNS...")
    resolv_conf = Path(mountpoint) / "etc" / "resolv.conf"
    try:
        shutil.copy("/etc/resolv.conf", resolv_conf)
    except Exception as e:
        print(f"[WARN] Could not copy DNS config: {e}")

    # 6. Lock the Image (Snapshot)
    print(f"-> creating Golden Snapshot: @{SNAPSHOT_NAME}...")
    zfs.snapshot(BASE_DATASET, SNAPSHOT_NAME)

    # Cleanup temp file to save space
    if tmp_file.exists():
        os.remove(tmp_file)

    print("\n========================================")
    print("   BOOTSTRAP COMPLETE")
    print("========================================")
    print("You can now run 'sudo python3 test_build.py'")

if __name__ == "__main__":
    check_root()
    bootstrap_system()
