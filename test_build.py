import sys
from bastion.core import janitor
from bastion.runner import executor
from bastion.core.types import Job

def run_c_compilation_test():
    print(">>> INITIALIZING REAL-WORLD C COMPILATION TEST <<<")

    janitor.cleanup_all()

    c_source_code = r"""
    #include <stdio.h>
    int main() {
        printf(\"Hello from the Isolated Bastion Jail!\\n\");
        printf(\"If you can read this, the C binary executed successfully.\\n\");
        return 0;
    }
    """

    write_cmd = f"printf '{c_source_code}' > main.c"

    job = Job(
        name="Compile C Application",
        commands=[
            "echo '-> Step 1: Checking Compiler Version'",
            "clang --version",

            "echo '-> Step 2: Injecting Source Code'",
            write_cmd,
            "ls -l main.c",

            "echo '-> Step 3: Compiling...'",
            "clang main.c -o my_app",
            "ls -l my_app",

            "echo '-> Step 4: Running Binary inside Jail'",
            "./my_app"
        ],
        artifacts=[
            "my_app",
            "main.c"
        ]
    )

    executor.run_job(job)

    print(f"\nTest Complete. Job Status: {job.status.name}")

if __name__ == "__main__":
    import os
    if os.geteuid() != 0:
        print("Error: This script must be run as root (to manage ZFS/Jails).")
        sys.exit(1)

    try:
        run_c_compilation_test()
    except KeyboardInterrupt:
        janitor.cleanup_all()
