# main.py
import sys
import time

from bastion.core import janitor
from bastion.core.types import Job, JobStatus
from bastion.runner import executor

def main():
    print("========================================")
    print("   BASTION CI - SYSTEM STARTUP")
    print("========================================")

    janitor.cleanup_all()
    print("\nSystem is clean. Ready to accept jobs.\n")


    test_job = Job(
        name="Integration Test Build",
        commands=[
            "echo 'Step 1: Hello from inside the Jail!'",
            "whoami",
            "date",
            "echo 'Step 2: Creating a build artifact...'",
            "echo 'This is a secret binary file' > build_result.txt",
            "echo 'Step 3: verifying isolation...'",
            "ls -la /"
        ],
        artifacts=[
            "build_result.txt"
        ]
    )

    print(f"-> Queuing Job: {test_job.name} (ID: {test_job.id})")
    time.sleep(1)

    executor.run_job(test_job)

    print("\n========================================")
    print("   FINAL JOB REPORT")
    print("========================================")
    print(f"Status:   {test_job.status.name}")
    print(f"Duration: {test_job.duration:.4f} seconds")
    print(f"Log File: {test_job.log_path}")

    if test_job.status == JobStatus.SUCCESS:
        print("\nArtifacts saved to:")
        print(f"  var/artifacts/job-{test_job.id}/")
    else:
        print("\nBuild Failed. Check logs for details.")

    if test_job.status == JobStatus.SUCCESS:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    if sys.platform not in ["freebsd11", "freebsd12", "freebsd13", "freebsd14", "freebsd15"]:
        if not sys.platform.startswith("freebsd"):
            print(f"CRITICAL ERROR: Bastion only runs on FreeBSD. Detected: {sys.platform}")
            print("This software relies on ZFS and Jails kernel primitives.")
            sys.exit(1)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Caught Ctrl+C. Initiating Emergency Cleanup...")
        janitor.cleanup_all()
        sys.exit(130)
