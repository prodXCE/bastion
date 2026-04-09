import argparse
import logging
import subprocess
import requests
import zfs
import jail
import runner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_DATASET  = "zroot/bastion/base"
SNAPSHOT_NAME = "fresh-install"
API_URL       = "http://localhost:8080"


def main():
    parser    = argparse.ArgumentParser(description="Bastion CI — Administration CLI")
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

    provision_parser = subparser.add_parser("provision-team-base", help="Create team base image")
    provision_parser.add_argument("team_id")
    provision_parser.add_argument("packages", nargs="*")

    subparser.add_parser(
        "setup-network",
        help="Initialize the VNET bridge network on the host (run once, requires root)"
    )

    args = parser.parse_args()

    if args.command == "init":
        logging.info("Initializing Bastion...")
        zfs.create_dataset(BASE_DATASET)
        zfs.create_snapshot(BASE_DATASET, SNAPSHOT_NAME)
        logging.info("Done.")

    elif args.command == "setup-network":
        jail.setup_host_network()
        logging.info("Host network ready for VNET jails.")

    elif args.command == "update-base":
        mount_path      = f"/{BASE_DATASET}"
        packages_string = " ".join(args.packages)
        logging.info(f"Installing: {packages_string}")
        result = subprocess.run(f"pkg -r {mount_path} install -y {packages_string}", shell=True)
        if result.returncode != 0:
            logging.error("Installation failed.")
            return
        zfs.create_snapshot(BASE_DATASET, SNAPSHOT_NAME)
        logging.info("Base image updated.")

    elif args.command == "spawn":
        snapshot_path = f"{BASE_DATASET}@{SNAPSHOT_NAME}"
        clone_dataset = f"zroot/bastion/builds/{args.job_id}"
        mount_path    = f"/{clone_dataset}"
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
            data     = response.json()
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
            logging.error("Cannot reach the API.")

    elif args.command == "list-teams":
        try:
            response = requests.get(f"{API_URL}/teams")
            data     = response.json()
            print(f"\nTeams ({data['total']}):")
            for team in data["teams"]:
                print(f"  {team['team_id']}  |  {team['team_name']}  |  {team['created_at']}")
        except requests.exceptions.ConnectionError:
            logging.error("Cannot reach the API.")

    elif args.command == "provision-team-base":
        team_dataset = f"zroot/bastion/teams/{args.team_id}/base"
        team_mount   = f"/{team_dataset}"
        zfs.create_dataset(team_dataset)
        if args.packages:
            packages_string = " ".join(args.packages)
            result = subprocess.run(f"pkg -r {team_mount} install -y {packages_string}", shell=True)
            if result.returncode != 0:
                logging.error("Installation failed.")
                return
        zfs.create_snapshot(team_dataset, SNAPSHOT_NAME)
        logging.info(f"Team {args.team_id} base ready.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()