import logging
import zfs 
import subprocess
import jail

def execute_pipeline(job_id, repo_url, command):

    BASE_DATASET = "zroot/bastion/base"
    snapshot_path = f"{BASE_DATASET}@fresh-install"
    clone_dataset = f"zroot/bastion/builds/{job_id}"
    mount_path = f"/{clone_dataset}"

    logging.info(f"=== Starting Pipeline for {job_id} ===")

    output_log = ""

    try:
        logging.info("Step 1: Provisioning ephemeral environment...")
        zfs.create_dataset("zroot/bastion/builds")
        zfs.clone_snapshot(snapshot_path, clone_dataset)
        
        logging.info("Injecting DNS resolver into environment...")
        subprocess.run(f"cp /etc/resolv.conf {mount_path}/etc/resolv.conf", shell=True, check=True)

        jail.create(job_id, mount_path)

        logging.info(f"Cloning {repo_url} into /workspace...")
        clone_cmd = f"git clone {repo_url} /workspace"
        clone_output = jail.execute(job_id, clone_cmd)

        logging.info(f"Executing user tests in workspace...")
        test_cmd = f"/bin/sh -c 'cd /workspace && {command}'"
        test_output = jail.execute(job_id, test_cmd)

        logging.info("Build completed successfully!")

        output_log = f"--- GIT CLONE ---\n{clone_output}\n--- TESTS ---\n{test_output}"
        return output_log

    except Exception as e:
        error_msg = f"Build Failed! An error occurred: {e}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    finally:
        logging.info("Initiating guaranteed cleanup...")
        try:
            jail.destroy(job_id)
        except Exception as e:
            logging.warning(f"Could not destroy jail (it may not have started): {e}")

        try:
            zfs.destroy_dataset(clone_dataset)
        except Exception as e:
            logging.warning(f"Could not destroy dataset: {e}")

        logging.info(f"=== Pipeline for {job_id} finished and environment obliterated ===")

