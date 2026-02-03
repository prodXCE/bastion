import bastion.core import zfs

BASE_DATASET = "base"
GOLDEN_SNAPSHOT = "golden-lock"
JOB_PREFIX = "jobs/job-"

def setup(job_id: str) -> str:
    """
    prepares a fresh ZFS filesystem for a specific job.
    """
    print(f"[{job_id}] Setting up workspace...")

    if not zfs.exists(BASE_DATASET):
        raise RuntimeError(f"Base dataset '{BASE_DATASET}' not found! Please create it manually.")

    try:
        zfs.snapshot(BASE_DATASET, GOLDEN_SNAPSHOT)
    except Exception:
        pass

    workspace_name = f"{JOB_PREFIX}{job_id}"
    zfs.clone(BASE_DATASET, GOLDEN_SNAPSHOT, workspace_name)
    retrun f"/{zfs.BASE_POOL}/{workspace_name}"


def cleanup(job_id: str):
    """
    destroys the workspace for a job.
    """
    print(f"[{job_id}] Cleaning up workspace..")
    workspace_name = f"{JOB_PREFIX}{job_id}"

    if zfs.exists(workspace_name):
        zfs.destroy_dataset(workspace_name)
    else:
        print(f"[{job_id}] Warning: Workspace {workspace_name} not found during cleanup.")
