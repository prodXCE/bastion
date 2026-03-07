import logging
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Bastion Control Plane")

class JobRequest(BaseModel):
    job_id: str
    repo_url: str
    cmd: str

class JobResult(BaseModel):
    status: str

class LogPayload(BaseModel):
    output: str

job_queue = []
job_database = {}
job_logs = {}

@app.post("/jobs")
def submit_job(request: JobRequest):
    job_queue.append({"job_id": request.job_id, "repo_url": request.repo_url, "cmd": request.cmd})
    job_database[request.job_id] = "QUEUED"
    job_logs[request.job_id] = "Waiting for worker to start..."
    return {"status": "queued", "job_id": request.job_id}


@app.get("/worker/poll")
def worker_poll():
    if len(job_queue) > 0:
        job = job_queue.pop(0)
        job_database[job["job_id"]] = "RUNNING"
        return {"has_job": True, "job": job}
    return {"has_job": False}


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, result: JobResult):
    job_database[job_id] = result.status
    logging.info(f"API received completion for {job_id}: {result.status}")
    return {"status": "recorded"}

@app.post("/jobs/{job_id}/logs")
def upload_logs(job_id: str, payload: LogPayload):
    job_logs[job_id] = payload.output
    logging.info(f"API saved logs for {job_id}")
    return {"status": "logs_saved"}

@app.get("/job/{job_id}/logs")
def get_logs(job_id: str):
    logs = job_logs.get(job_id, "Error: Job ID not found.")
    status = job_database.get(job_id, "UNKNOWN")
    return {"job_id": job_id, "status": status, "logs": logs}
