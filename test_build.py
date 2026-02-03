import sys
from bastion.core import janitor
from bastion.runner import executor
from bastion.core.types import Job

def run_c_compilation_test():
    print(">>> INITIALIZING REAL-WORLD C COMPILATION TEST <<<")

    # 1. Clean Slate
    janitor.cleanup_all()

    # 2. Define the Job
    # We use a multi-line string for the C code to keep it readable.
    c_source_code = r"""
    #include <stdio.h>
    int main() {
        printf(\"Hello from the Isolated Bastion Jail!\\n\");
        printf(\"If you can read this, the C binary executed successfully.\\n\");
        return 0;
    }
    """

    # We construct the shell command to write this string to a file.
    # We use printf because it handles newlines (\n) better than echo in some shells.
    write_cmd = f"printf '{c_source_code}' > main.c"

    job = Job(
        name="Compile C Application",
        commands=[
            # Step 1: Verify environment
            "echo '-> Step 1: Checking Compiler Version'",
            "clang --version",

            # Step 2: Inject Source Code
            "echo '-> Step 2: Injecting Source Code'",
            write_cmd,
            "ls -l main.c", # Prove the file exists

            # Step 3: Compile
            "echo '-> Step 3: Compiling...'",
            "clang main.c -o my_app",
            "ls -l my_app", # Prove the binary exists

            # Step 4: Execution Test (Integration Testing)
            "echo '-> Step 4: Running Binary inside Jail'",
            "./my_app"
        ],
        artifacts=[
            "my_app",    # The compiled binary
            "main.c"     # The source code (for debugging)
        ]
    )

    # 3. Run the Engine
    executor.run_job(job)

    # 4. Final Output
    print(f"\nTest Complete. Job Status: {job.status.name}")

if __name__ == "__main__":
    # Root check
    import os
    if os.geteuid() != 0:
        print("Error: This script must be run as root (to manage ZFS/Jails).")
        sys.exit(1)

    try:
        run_c_compilation_test()
    except KeyboardInterrupt:
        janitor.cleanup_all()
