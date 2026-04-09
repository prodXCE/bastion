import logging     
import subprocess  

def run_command(cmd):
    logging.info(f"ZFS: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"ZFS command failed: {e.stderr.strip()}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

def create_dataset(dataset_name):
    run_command(f"zfs create -p {dataset_name}")
    logging.info(f"Dataset created: {dataset_name}")

def create_snapshot(dataset_name, snapshot_name):
    run_command(f"zfs snapshot {dataset_name}@{snapshot_name}")
    logging.info(f"Snapshot created: {dataset_name}@{snapshot_name}")

def clone_snapshot(snapshot_path, clone_name):
    run_command(f"zfs clone {snapshot_path} {clone_name}")
    logging.info(f"Cloned {snapshot_path} into {clone_name}")

def destroy_dataset(dataset_name):
    run_command(f"zfs destroy -R {dataset_name}")
    logging.info(f"Dataset destroyed: {dataset_name}")