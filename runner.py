import logging
import subprocess
import time
import requests
import zfs
import jail

BASE_DATASET  = "zroot/bastion/base"
SNAPSHOT_NAME = "fresh-install"
API_URL       = "http://localhost:8080"


def check_if_cancelled(job_id):
    try:
        response = requests.get(f"{API_URL}/jobs/{job_id}/cancelled")
        return response.json().get("cancelled", False)
    except Exception:
        return False


def execute_pipeline(job_id, repo_url, command):

    snapshot_path = f"{BASE_DATASET}@{SNAPSHOT_NAME}"
    clone_dataset = f"zroot/bastion/builds/{job_id}"
    mount_path    = f"/{clone_dataset}"

    logging.info(f"=== Pipeline starting: {job_id} ===")

    output_log   = ""
    exit_code    = 1
    start_time   = time.time()
    epair_host   = None

    try:
        if check_if_cancelled(job_id):
            raise RuntimeError("Job was cancelled before starting.")

        logging.info(f"[{job_id}] Step 1: Cloning base snapshot...")
        zfs.create_dataset("zroot/bastion/builds")
        zfs.clone_snapshot(snapshot_path, clone_dataset)

        if check_if_cancelled(job_id):
            raise RuntimeError("Job was cancelled during setup.")

        logging.info(f"[{job_id}] Step 2: Setting up DNS...")
        subprocess.run(
            f"cp /etc/resolv.conf {mount_path}/etc/resolv.conf",
            shell=True,
            check=True
        )

        if check_if_cancelled(job_id):
            raise RuntimeError("Job was cancelled before jail started.")

        logging.info(f"[{job_id}] Step 3: Starting VNET jail...")
        epair_host = jail.create(job_id, mount_path)

        if check_if_cancelled(job_id):
            raise RuntimeError("Job was cancelled before git clone.")

        logging.info(f"[{job_id}] Step 4: Cloning {repo_url}...")
        clone_output = jail.execute(job_id, f"git clone {repo_url} /workspace")

        if check_if_cancelled(job_id):
            raise RuntimeError("Job was cancelled before running command.")

        logging.info(f"[{job_id}] Step 5: Running: {command}")
        test_output = jail.execute(job_id, f"/bin/sh -c 'cd /workspace && {command}'")

        logging.info(f"[{job_id}] Pipeline completed successfully.")

        output_log = (
            f"--- CLONE OUTPUT ---\n{clone_output}\n\n"
            f"--- COMMAND OUTPUT ---\n{test_output}"
        )
        exit_code = 0
        return output_log

    except Exception as e:
        error_message = f"Pipeline failed for {job_id}: {e}"
        logging.error(error_message)
        output_log = error_message
        raise RuntimeError(error_message)

    finally:
        end_time         = time.time()
        duration_seconds = end_time - start_time
        log_size_bytes   = len(output_log.encode())

        try:
            requests.post(
                f"{API_URL}/jobs/{job_id}/metrics",
                json={
                    "duration_seconds": duration_seconds,
                    "exit_code":        exit_code,
                    "log_size_bytes":   log_size_bytes
                }
            )
        except Exception as e:
            logging.warning(f"[{job_id}] Could not send metrics: {e}")

        logging.info(f"[{job_id}] Cleaning up...")

        try:
            jail.destroy(job_id)
        except Exception as e:
            logging.warning(f"[{job_id}] Could not destroy jail: {e}")

        if epair_host is not None:
            jail.destroy_epair(epair_host)

        try:
            zfs.destroy_dataset(clone_dataset)
        except Exception as e:
            logging.warning(f"[{job_id}] Could not destroy dataset: {e}")

        logging.info(f"=== Pipeline done: {job_id}. Duration: {duration_seconds:.1f}s ===")