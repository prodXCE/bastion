import subprocess
from typing import List

def run_command(args: List[str]) -> str:
    """
    executes a shell command safely and return the output.
    """
    try:
        if isinstance(args, str):
            raise ValueError("run_command expects a List[str], not a single string.")

        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True
        )

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {' '.join(args)}\nError Output: {e.stderr}"
        print(f"[SYSTEM ERROR] {error_msg}")
        raise e
