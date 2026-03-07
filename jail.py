import logging
import subprocess
import sys

def run_command(cmd):
    logging.info(f"Executing: {cmd}")
    try:
        result = subprocess.run(
                cmd,
                shell=True,
                check=True,
                text=True,
                capture_output=True
        )
        if result.stdout.strip():
            logging.info(f"Output:\n{result.stdout.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Jail command failed! Error:\n{e.stderr.strip()}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)


def create(jail_name, root_path):
    cmd = f"jail -c name={jail_name} path={root_path} host.hostname={jail_name} ip4=inherit persist"
    run_command(cmd)
    logging.info(f"Started jail: {jail_name} at {root_path}")

def execute(jail_name, command):
    cmd = f"jexec {jail_name} {command}"
    logging.info(f"Running '{command}' inside jail '{jail_name}'")
    return run_command(cmd)

def destroy(jail_name):
    cmd = f"jail -r {jail_name}"
    run_command(cmd)
    logging.info(f"Destroyed jai: {jail_name}")

