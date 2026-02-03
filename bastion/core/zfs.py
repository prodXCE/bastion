from bastion.core.utils import run_command

BASE_POOL = "zroot/bastion"

def _run_cmd(args: List[str]) -> str:
    """
    internal helper func to run shell comnds safely
    """
    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True
        )

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print(f"COMMAND FAILED: {' '.join(args)}")
        print(f"ERROR DETAILS: {e.stderr}")
        raise e

def create_dataset(name: str):
   """
   creates a new container
   """
   full_path = f"{BASE_POOL}/{name}"
   print(f" -> ZFS: Creating dataset {full_path}")
   run_command(["zfs", "create", full_path])


def destroy_dataset(name: str):
    """
    destroys a container and everything inside it
    """
    full_path = f"{BASE_POOL}/{name}"
    print(f" -> ZFS: Destroying dataset {full_path}")

    run_command(["zfs", "destroy", "-r", "-f", full_path])


def snapshot(dataset_name: str, snapshot_name: str):
    """
    freezes a dataset in time.
    """
    full_path = f"{BASE_POO}/{dataset_name}@{snapshot_name}"
    print(f" -> ZFS: Snapshotting {full_path}")

    run_command(["zfs", "snapshot", full_path])


def clone(origin_dataset: str, origin_snapshot:str, new_name: str):
    """
    creates a writeable copy from a snapshot
    """
    snapshot_path = f"{BASE_POOL}/{origin_dataset}@{origin_snapshot}"
    target_path = f"{BASE_POOL}/{new_name}"

    print(f" -> ZFS: Cloning {snapshot_path} to {target_path}")
    run_command(["zfs", "clone", snapshot_path, target_path])


def exists(name: str) -> bool:
    """
    checks if a dataset exists
    """

    full_path = f"{BASE_POOL}/{name}"
    try:
        run_command(["zfs", "list", full_path])
        return True
    except subprocess.CalledProcessError:
        return False
