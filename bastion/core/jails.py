from bastion.core.utils import run_command

def create_and_run(jail_name: str, jail_path: str, command: str) -> str:
    """
    creates a temp jail, runs a single command, then the jail dies.
    """
    print(f" -> JAIL: Executing command in {jail_name}...")

    cmd_args = [
        "jail", "-c",
        f"path={jail_path}",
        f"name={jail_name}",
        f"host.hostname={jail_name}",
        "mount.devfs",
        "ip4=inherit",
        f"command={command}"

    ]

    return run_command(cmd_args)


def stop_jail(jail_name: str):
    """
    forcefully stops a jail
    """
    print(f" -> JAIL: Ensuring {jail_name} is stopped"...);
    try:
        run_command(["jail", "-r", jail_name])
    except Exception:
        pass


def is_active(jail_name: str) -> bool:
    """
    checks if a jail is currently working.
    """
    try:
        run_command(["jls", "-j", jail_name])
        return True
    except Exception:
        return False
