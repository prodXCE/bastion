import argparse
import logging
import zfs
import jail
import runner

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
)

def main():
    parser = argparse.ArgumentParser(description="Bastion CI Runtime")
    subparser = parser.add_subparsers(dest="command", help="Available commands")
    init_parser = subparser.add_parser("init", help="Initialize the ZFS base environment")
    spawn_parser = subparser.add_parser("spawn", help="Spawn a completely isolated build environment")
    spawn_parser.add_argument("job_id", help="The ID for this build job (e.g., job-1)")
    run_parser = subparser.add_parser("run", help="Run a command inside a specific job's jail")
    run_parser.add_argument("job_id", help="The ID of the build job")
    run_parser.add_argument("cmd", help="The command to run (e.g., 'uname -a')")
    clean_parser = subparser.add_parser("clean", help="Destroy a build environment")
    clean_parser.add_argument("job_id", help="The ID of the build job to destroy")

    submit_parser = subparser.add_parser("submit", help="Run a full ephemeral CI Pipeline")
    submit_parser.add_argument("job_id", help="The unique ID for this run (e.g., job-123)")
    submit_parser.add_argument("cmd", help="The test command to execute inside the jail")

    args = parser.parse_args()

    BASE_DATASET = "zroot/bastion/base"

    if args.command == "init":
        logging.info("Initializing Bastion base environment...")
        zfs.create_dataset(BASE_DATASET)
        zfs.create_snapshot(BASE_DATASET, "fresh-install")
        logging.info("Initialization complete. Base snapshot is ready.")

    elif args.command == "spawn":
        snapshot_path = f"{BASE_DATASET}@fresh-install"
        clone_dataset = f"zroot/bastion/builds/{args.job_id}"
        mount_path = f"/{clone_dataset}"
        logging.info(f"Spawning ephemeral environment for {args.job_id}...")
        zfs.create_dataset("zroot/bastion/builds")
        zfs.clone_snapshot(snapshot_path, clone_dataset)
        logging.info(f"Starting isolated jail for {args.job_id}...")
        jail.create(args.job_id, mount_path)
        logging.info(f"Envionment {args.job_id} is fully operational.")

    elif args.command == "run":
        jail.execute(args.job_id, args.cmd)

    elif args.command == "clean":
        clone_path = f"zroot/bastion/builds/{args.job_id}"
        logging.info(f"Stopping jail {args.job_id}...")
        jail.destroy(args.job_id)
        logging.info(f"Cleaning up environment for {args.job_id}...")
        zfs.destroy_dataset(clone_path)
        logging.info(f"Cleanup for {args.job_id} complete. No trace remains.")

    elif args.command == "submit":
        runner.execute_pipeline(args.job_id, args.cmd)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
