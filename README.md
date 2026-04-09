# Bastion CI: Distributed Ephemeral CI Runtime

Bastion is a custom-built, distributed Continuous Integration (CI) runtime engine engineered from scratch on FreeBSD. It leverages OS-level virtualization and advanced filesystem mechanics to execute untrusted code in secure, ephemeral environments. By treating infrastructure as completely disposable, Bastion guarantees zero cross-contamination between builds, ensuring every test runs from a pristine, mathematically identical state.

---

## Architectural Highlights

- **Ephemeral Environments** — Utilizes native FreeBSD Jails and ZFS Copy-on-Write (CoW) snapshots for deeply isolated, instant-booting workspace cloning, bypassing the slow startup times of traditional Virtual Machines.
- **Distributed Polling Architecture** — Decouples the Control Plane (API) from the Worker Nodes for horizontal scaling. Workers asynchronously pull jobs over HTTP, easily bypassing strict corporate firewalls.
- **Automated Base Provisioning** — A robust CLI securely injects host packages (`git`, compilers, etc.) directly into disconnected ZFS base images without starting a jail, baking dependencies into the core snapshot to prevent configuration drift.
- **Chained Execution & Git Integration** — Dynamically injects host DNS routing (`resolv.conf`), authenticates with remote version control, provisions a `/workspace`, and chains user test commands seamlessly.
- **Observability Pipeline** — Captures `stdout` and `stderr` directly from isolated jails, streaming telemetry back to the Control Plane for immediate remote debugging.
- **Guaranteed Teardown** — Uses strict deterministic error handling (`try...finally` blocks) to completely obliterate network routing, cloned datasets, and jailed processes, preventing resource leaks regardless of build outcomes.

---

## Prerequisites

To run the Bastion Worker Node or local CLI, your host machine requires:

| Requirement | Detail |
|-------------|--------|
| **Operating System** | FreeBSD 15.0+ (for native Jail APIs) |
| **Filesystem** | ZFS configured with a `zroot` pool (for CoW dataset cloning) |
| **Python** | Python 3.11+ |
| **Privileges** | Root access (`sudo`) on worker nodes to securely manipulate Jails and ZFS datasets |

---

## Installation & Setup

**1. Clone the repository:**

```sh
git clone https://www.github.com/prodXCE/bastion
cd bastion
```

**2. Install Python dependencies:**

> Using a virtual environment is highly recommended.

```sh
pip install fastapi uvicorn pydantic requests
```

**3. Initialize the Storage Backend:**

Creates the base ZFS datasets (`zroot/bastion/base`) and initial immutable snapshots.

```sh
sudo python3 bastion.py init
```

**4. Provision the Base Image:**

Installs required packages into the base image so future ephemeral clones have them pre-installed.

```sh
sudo python3 bastion.py update-base git ca_root_nss
```

---

## Usage Guide: Distributed CI Mode

This primary mode requires running the Control Plane, one or more Worker Agents, and submitting payloads via an HTTP client.

### 1. Start the Control Plane (API)

Routes traffic, holds the job queue, and stores telemetry. Does not require root privileges.

```sh
uvicorn api:app --host 0.0.0.0 --port 8080
```

### 2. Start the Worker Agent

Polls the Control Plane for new jobs, manages the ZFS/Jail lifecycle, and executes builds. Must be run on the FreeBSD host with root privileges.

```sh
sudo $(which python3) worker.py
```

### 3. Submit a CI Job

Submit a JSON payload to the Control Plane containing a unique ID, Git repository URL, and the test command.

```sh
curl -X POST http://localhost:8080/jobs \
     -H "Content-Type: application/json" \
     -d '{
           "job_id": "test-run-1",
           "repo_url": "https://github.com/octocat/Hello-World.git",
           "cmd": "ls -la"
         }'
```

### 4. Retrieve Build Logs

Query the API for terminal output to diagnose test failures or verify successes after the worker finishes.

```sh
curl http://localhost:8080/jobs/test-run-1/logs
```

---

## Usage Guide: Local CLI Administration

Use the `bastion.py` CLI tool for local debugging or system administration. All commands require `sudo`.

### Initialize Base Infrastructure

Creates the `zroot/bastion/base` dataset and takes the first read-only snapshot.

```sh
sudo python3 bastion.py init
```

### Update Base Image

Installs host packages into the disconnected base image and takes a new snapshot.

```sh
sudo python3 bastion.py update-base <package1> <package2>

# Example:
sudo python3 bastion.py update-base git python3 node20
```

### Spawn an Ephemeral Clone Manually

Clones the ZFS snapshot and boots an isolated jail without running tests.

```sh
sudo python3 bastion.py spawn <job_id>
```

### Execute Commands in a Running Clone

Runs a command inside a manually spawned jail.

```sh
sudo python3 bastion.py run <job_id> "<command>"

# Example:
sudo python3 bastion.py run debug-job-1 "uname -a"
```

### Destroy a Clone Manually

Stops the jail and completely destroys the ZFS clone dataset.

```sh
sudo python3 bastion.py clean <job_id>
```

### Run a Local Pipeline

Executes the full automated pipeline (Clone → Start Jail → Clone Git Repo → Test → Teardown) locally, bypassing the REST API.

```sh
sudo python3 bastion.py submit <job_id> "<command>"

# Example:
sudo python3 bastion.py submit local-test-1 "ls -la"
```



INSTRUCT : 
Step By Step Setup For Option 1
Step 1: Find the IP addresses of all your machines

On MacOS:

Bash

ifconfig | grep "inet " | grep -v 127.0.0.1
# Look for something like 192.168.64.1
On each FreeBSD VM:

Bash

ifconfig | grep "inet " | grep -v 127.0.0.1
# Look for something like 192.168.64.2 and 192.168.64.3
Write these down:

text

MacOS       → 192.168.64.1  (example, yours will differ)
FreeBSD VM1 → 192.168.64.2
FreeBSD VM2 → 192.168.64.3
Step 2: Put the right files on each machine

On MacOS — you only need:

text

api.py
db.py
dashboard.py
requirements_mac.txt
On each FreeBSD VM — you need everything:

text

worker.py
runner.py
jail.py
zfs.py
bastion.py
db.py (not used directly but imported)
The simplest way to transfer files:

Bash

# From MacOS, copy files to FreeBSD VM 1
scp api.py db.py dashboard.py your_username@192.168.64.1:~/bastion/

# Copy worker files to FreeBSD VM 1
scp worker.py runner.py jail.py zfs.py bastion.py your_username@192.168.64.2:~/bastion/

# Copy worker files to FreeBSD VM 2
scp worker.py runner.py jail.py zfs.py bastion.py your_username@192.168.64.3:~/bastion/
Step 3: Install dependencies on each machine

On MacOS:

Bash

pip3 install fastapi uvicorn pydantic requests streamlit pandas
On each FreeBSD VM:

Bash

pkg install python3 py39-pip
pip install requests
Step 4: Change the API_URL in worker.py on both FreeBSD VMs

Open worker.py on each FreeBSD VM and change:

Python

# Change this line
API_URL = "http://localhost:8080"

# To point to your MacOS machine's IP
API_URL = "http://192.168.64.1:8080"
Do the same in runner.py:

Python

# Change this line
API_URL = "http://localhost:8080"

# To
API_URL = "http://192.168.64.1:8080"
Step 5: Initialize Bastion on each FreeBSD VM

On FreeBSD VM 1:

Bash

cd ~/bastion
sudo python3 bastion.py init
sudo python3 bastion.py setup-network
sudo python3 bastion.py update-base git ca_root_nss
On FreeBSD VM 2:

Bash

cd ~/bastion
sudo python3 bastion.py init
sudo python3 bastion.py setup-network
sudo python3 bastion.py update-base git ca_root_nss
Step 6: Start everything

On MacOS Terminal 1:

Bash

cd ~/bastion
uvicorn api:app --host 0.0.0.0 --port 8080
On MacOS Terminal 2:

Bash

cd ~/bastion
streamlit run dashboard.py
# Opens browser at http://localhost:8501
On FreeBSD VM 1:

Bash

cd ~/bastion
sudo python3 worker.py
On FreeBSD VM 2:

Bash

cd ~/bastion
sudo python3 worker.py
Now you have two workers running in parallel. Jobs are distributed between them automatically.

