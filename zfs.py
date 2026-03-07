import logging
import subprocess
import sys

def run_command(cmd):
    logging.info(f"Executing: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"ZFS command failed! Error:\n{e.stderr.strip()}"
        logging.error(error.msg)
        raise RuntimeError(error_msg)

def create_dataset(dataset_name):
    run_command(f"zfs create -p {dataset_name}")
    logging.info(f"Created dataset: {dataset_name}")

def create_snapshot(dataset_name, snapshot_name):
    run_command(f"zfs snapshot {dataset_name}@{snapshot_name}")
    logging.info(f"Created snapshot: {dataset_name}@{snapshot_name}")

def clone_snapshot(snapshot_path, clone_name):
    run_command(f"zfs clone {snapshot_path} {clone_name}")
    logging.info(f"Cloned {snapshot_path} into {clone_name}")

def destroy_dataset(dataset_name):
    run_command(f"zfs destroy -R {dataset_name}")
    logging.info(f"Destroyed dataset: {dataset_name}")



