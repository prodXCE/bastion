# bastion.py
import argparse
import logging
import os
import subprocess
import requests
import zfs
import jail
import runner

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DATASET = "zroot/bastion/base"
SNAPSHOT_NAME = "fresh-install"
API_URL = "http://localhost:8080"

def populate_base_image(mount_path):
    freebsd_version = subprocess.run("uname -r", shell=True, capture_output=True, text=True).stdout.strip()
    arch = subprocess.run("uname -m", shell=True, capture_output=True, text=True).stdout.strip()
    logging.info(f"Detected FreeBSD {freebsd_version} on {arch}")
    base_url = "http://ftpmirror.your.org/pub/FreeBSD/releases/arm64/15.0-RELEASE/base.txz"
    logging.info(f"Downloading FreeBSD base system from:")
    logging.info(f"  {base_url}")
    logging.info("This may take a few minutes...")
    fetch_result = subprocess.run(f"fetch -o /tmp/bastion_base.txz {base_url}", shell=True)
    if fetch_result.returncode != 0:
        logging.error("Download failed. Check your internet connection.")
        logging.error(f"You can also manually download: {base_url}")
        logging.error(f"Then run: tar -xf base.txz -C {mount_path}")
        return False
    logging.info("Download complete. Extracting...")
    extract_result = subprocess.run(f"tar -xf /tmp/bastion_base.txz -C {mount_path}", shell=True)
    subprocess.run("rm -f /tmp/bastion_base.txz", shell=True)
    if extract_result.returncode != 0:
        logging.error("Extraction failed.")
        return False
    logging.info("FreeBSD base system extracted successfully.")
    return True

def bootstrap_pkg_in_base(mount_path):
    temp_jail = "bastion-bootstrap"
    logging.info("Bootstrapping pkg inside base image...")
    subprocess.run(f"mount -t devfs devfs {mount_path}/dev", shell=True, check=True)
    subprocess.run(f"cp /etc/resolv.conf {mount_path}/etc/resolv.conf", shell=True)
    result = subprocess.run(f"jail -c name={temp_jail} path={mount_path} host.hostname=bastion-bootstrap ip4=inherit persist", shell=True)
    if result.returncode != 0:
        subprocess.run(f"umount {mount_path}/dev", shell=True)
        logging.error("Could not start bootstrap jail.")
        return False
    try:
        subprocess.run(f"jexec {temp_jail} pkg bootstrap -y", shell=True, check=True)
        logging.info("pkg bootstrapped successfully.")
        return True
    except subprocess.CalledProcessError:
        logging.error("pkg bootstrap failed.")
        return False
    finally:
        subprocess.run(f"jail -r {temp_jail}", shell=True)
        subprocess.run(f"umount {mount_path}/dev", shell=True)

def main():
    parser = argparse.ArgumentParser(description="Bastion CI — Administration CLI")
    subparser = parser.add_subparsers(dest="command")

    subparser.add_parser("init", help="Initialize the ZFS base environment")

    update_parser = subparser.add_parser("update-base", help="Install packages into the base image")
    update_parser.add_argument("packages", nargs="+")

    spawn_parser = subparser.add_parser("spawn", help="Spawn an isolated jail")
    spawn_parser.add_argument("job_id")

    run_parser = subparser.add_parser("run", help="Run command inside a jail")
    run_parser.add_argument("job_id")
    run_parser.add_argument("cmd")

    clean_parser = subparser.add_parser("clean", help="Destroy a build environment")
    clean_parser.add_argument("job_id")

    submit_parser = subparser.add_parser("submit", help="Run a full local pipeline")
    submit_parser.add_argument("job_id")
    submit_parser.add_argument("repo_url")
    submit_parser.add_argument("cmd")

    create_team_parser = subparser.add_parser("create-team", help="Register a new team")
    create_team_parser.add_argument("team_name")

    subparser.add_parser("list-teams", help="List all teams")

    provision_parser = subparser.add_parser("provision-team-base", help="Create a dedicated base image for a team")
    provision_parser.add_argument("team_id")
    provision_parser.add_argument("packages", nargs="*")

    subparser.add_parser("setup-network", help="Initialize the VNET bridge")

    args = parser.parse_args()

    if args.command == "init":
        logging.info("Initializing Bastion base environment...")
        mount_path = f"/{BASE_DATASET}"
        zfs.create_dataset(BASE_DATASET)
        for d in ["/dev", "/workspace", "/tmp"]:
            os.makedirs(f"{mount_path}{d}", exist_ok=True)
        if not populate_base_image(mount_path):
            logging.error("Init failed at base system download step.")
            return
        if not bootstrap_pkg_in_base(mount_path):
            logging.error("Init failed at pkg bootstrap step.")
            return
        zfs.create_snapshot(BASE_DATASET, SNAPSHOT_NAME)
        logging.info("Done. Base snapshot is ready.")
        logging.info("Now run: sudo python3 bastion.py update-base git ca_root_nss")

    elif args.command == "update-base":
        mount_path = f"/{BASE_DATASET}"
        packages_string = " ".join(args.packages)
        temp_jail_name = "bastion-update-base"

        logging.info(f"Installing packages into base image: {packages_string}")
        logging.info("Starting temporary jail for pkg install...")

        subprocess.run(f"mount -t devfs devfs {mount_path}/dev", shell=True)
        subprocess.run(f"cp /etc/resolv.conf {mount_path}/etc/resolv.conf", shell=True)

        result = subprocess.run(f"jail -c name={temp_jail_name} path={mount_path} host.hostname=bastion-update ip4=inherit persist", shell=True)

        if result.returncode != 0:
            subprocess.run(f"umount {mount_path}/dev", shell=True)
            logging.error("Could not start temporary jail for update.")
            return

        try:
            install_result = subprocess.run(f"jexec {temp_jail_name} pkg install -y {packages_string}", shell=True)
            if install_result.returncode != 0:
                logging.error("pkg install failed.")
                return
            logging.info(f"Successfully installed: {packages_string}")

        finally:
            subprocess.run(f"jail -r {temp_jail_name}", shell=True)
            subprocess.run(f"umount {mount_path}/dev", shell=True)

        logging.info("Taking new snapshot...")
        subprocess.run(f"zfs destroy {BASE_DATASET}@{SNAPSHOT_NAME}", shell=True, capture_output=True)
        zfs.create_snapshot(BASE_DATASET, SNAPSHOT_NAME)
        logging.info(f"Base image updated with: {packages_string}")

    elif args.command == "setup-network":
        jail.setup_host_network()
        logging.info("Host network ready for VNET jails.")

    elif args.command == "spawn":
        snapshot_path = f"{BASE_DATASET}@{SNAPSHOT_NAME}"
        clone_dataset = f"zroot/bastion/builds/{args.job_id}"
        mount_path = f"/{clone_dataset}"
        zfs.create_dataset("zroot/bastion/builds")
        zfs.clone_snapshot(snapshot_path, clone_dataset)
        jail.create(args.job_id, mount_path)
        logging.info(f"Environment {args.job_id} ready.")

    elif args.command == "run":
        jail.execute(args.job_id, args.cmd)

    elif args.command == "clean":
        clone_path = f"zroot/bastion/builds/{args.job_id}"
        jail.destroy(args.job_id)
        zfs.destroy_dataset(clone_path)
        logging.info(f"{args.job_id} destroyed.")

    elif args.command == "submit":
        runner.execute_pipeline(args.job_id, args.repo_url, args.cmd)

    elif args.command == "create-team":
        try:
            response = requests.post(f"{API_URL}/teams", json={"team_name": args.team_name})
            data = response.json()
            print("\n" + "=" * 50)
            print("  TEAM REGISTERED")
            print("=" * 50)
            print(f"  Team Name : {data['team_name']}")
            print(f"  Team ID   : {data['team_id']}")
            print(f"  API Key   : {data['api_key']}")
            print("=" * 50)
            print("  SAVE THIS KEY. It will not be shown again.")
            print("=" * 50 + "\n")
        except requests.exceptions.ConnectionError:
            logging.error("Cannot reach the API. Is it running?")

    elif args.command == "list-teams":
        try:
            response = requests.get(f"{API_URL}/teams")
            data = response.json()
            print(f"\nTeams ({data['total']}):")
            for team in data["teams"]:
                print(f"  {team['team_id']}  |  {team['team_name']}  |  {team['created_at']}")
        except requests.exceptions.ConnectionError:
            logging.error("Cannot reach the API.")

    elif args.command == "provision-team-base":
        team_dataset = f"zroot/bastion/teams/{args.team_id}/base"
        team_mount = f"/{team_dataset}"
        temp_jail = f"bastion-provision-{args.team_id}"

        zfs.create_dataset(team_dataset)

        if not populate_base_image(team_mount):
            return
        if not bootstrap_pkg_in_base(team_mount):
            return

        if args.packages:
            packages_string = " ".join(args.packages)
            subprocess.run(f"mount -t devfs devfs {team_mount}/dev", shell=True)
            subprocess.run(f"jail -c name={temp_jail} path={team_mount} host.hostname={temp_jail} ip4=inherit persist", shell=True)
            try:
                subprocess.run(f"jexec {temp_jail} pkg install -y {packages_string}", shell=True)
            finally:
                subprocess.run(f"jail -r {temp_jail}", shell=True)
                subprocess.run(f"umount {team_mount}/dev", shell=True)

        zfs.create_snapshot(team_dataset, SNAPSHOT_NAME)
        logging.info(f"Team {args.team_id} base ready.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
