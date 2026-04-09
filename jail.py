# jail.py
import logging
import subprocess
import secrets

BRIDGE_NAME = "bridge0"
JAIL_SUBNET = "10.10.0"
JAIL_GATEWAY = "10.10.0.1"

def run_command(cmd):
    logging.info(f"Jail: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
        if result.stdout.strip():
            logging.info(f"Output:\n{result.stdout.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Jail command failed: {e.stderr.strip()}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

def setup_host_network():
    logging.info("Setting up host bridge network for VNET jails...")
    subprocess.run("ifconfig bridge0 create", shell=True)
    subprocess.run(f"ifconfig {BRIDGE_NAME} inet {JAIL_GATEWAY}/24 up", shell=True, check=True)
    subprocess.run("sysctl net.inet.ip.forwarding=1", shell=True, check=True)
    logging.info(f"Host bridge ready at {JAIL_GATEWAY}/24")

def allocate_jail_ip():
    last_octet = secrets.randbelow(253) + 2
    return f"{JAIL_SUBNET}.{last_octet}"

def create_epair(jail_name):
    result = subprocess.run("ifconfig epair create", shell=True, check=True, text=True, capture_output=True)
    host_side = result.stdout.strip()
    jail_side = host_side[:-1] + "b"
    subprocess.run(f"ifconfig {BRIDGE_NAME} addm {host_side} up", shell=True, check=True)
    logging.info(f"Created epair for {jail_name}: host={host_side}, jail={jail_side}")
    return host_side, jail_side

def destroy_epair(host_side):
    subprocess.run(f"ifconfig {host_side} destroy", shell=True)
    logging.info(f"Epair {host_side} destroyed.")

def create(jail_name, root_path):
    jail_ip = allocate_jail_ip()
    host_side, jail_side = create_epair(jail_name)
    try:
        cmd = f"jail -c name={jail_name} path={root_path} host.hostname={jail_name} vnet=new vnet.interface={jail_side} persist"
        run_command(cmd)
        subprocess.run(f"jexec {jail_name} ifconfig {jail_side} name eth0", shell=True, check=True)
        subprocess.run(f"jexec {jail_name} ifconfig eth0 inet {jail_ip}/24 up", shell=True, check=True)
        subprocess.run(f"jexec {jail_name} route add default {JAIL_GATEWAY}", shell=True, check=True)
        logging.info(f"VNET jail {jail_name} started. IP: {jail_ip}")
        return host_side
    except Exception as e:
        destroy_epair(host_side)
        raise e

def execute(jail_name, command):
    cmd = f"jexec {jail_name} {command}"
    logging.info(f"Executing inside '{jail_name}': {command}")
    return run_command(cmd)

def destroy(jail_name):
    cmd = f"jail -r {jail_name}"
    run_command(cmd)
    logging.info(f"Jail destroyed: {jail_name}")