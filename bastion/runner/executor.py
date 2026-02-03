import time
from pathlib import Path
from bastion.core.types import Job
from bastion.core import jails
from bastion.runner import workspace, artifacts

LOG_DIR = Path.cwd() / "var" / "logs"

def save_log(job_id: str, content: str):
    log_file = LOG_DIR / f"job-{job_id}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(content + "\n")
    return str(log_file)

def run_job(job: Job):
    print(f"[{job.id}] Starting execution for '{job.name}'...")
    job.start()

    job.log_path = str(LOG_DIR / f"job-{job.id}.log")
    save_log(job.id, f"=== BUILD STARTED: {job.name} ===\n")

    workspace_path = None

    try:
        save_log(job.id, "-> Setting up workspace...")
        workspace_path = workspace.setup(job.id)

        for cmd in job.commands:
            save_log(job.id, f"\n-> EXEC: {cmd}")
            print(f"[{job.id}] STEP: {cmd}")

            output = jails.create_and_run(
                jail_name=f"job-{job.id}",
                jail_path=workspace_path,
                command=cmd
            )

            save_log(job.id, output)

        save_log(job.id, "\n-> Collecting artifacts...")
        artifacts.collect_artifacts(
            job_id=job.id,
            workspace_path=workspace_path,
            artifact_paths=job.artifacts
        )

        save_log(job.id, "\n=== BUILD SUCCESS ===")
        job.complete(success=True)

    except Exception as e:
        error_msg = f"\n=== BUILD FAILED ===\nError: {str(e)}"
        print(f"[{job.id}] {error_msg}")
        save_log(job.id, error_msg)
        job.complete(success=False)

    finally:
        save_log(job.id, "\n-> Teardown initiated...")

        jails.stop_jail(f"job-{job.id}")

        if workspace_path:
            workspace.cleanup(job.id)

        print(f"[{job.id}] Log saved to: {job.log_path}")
