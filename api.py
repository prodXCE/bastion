import logging
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Bastion Control Plane")


@app.on_event("startup")
def on_startup():
    logging.info("Bastion Control Plane starting...")
    db.initialize_database()
    logging.info("Ready.")


class JobRequest(BaseModel):
    job_id:   str
    repo_url: str
    cmd:      str
    priority: int = 3

class JobResult(BaseModel):
    status: str

class LogPayload(BaseModel):
    output: str

class TeamRequest(BaseModel):
    team_name: str

class MetricsPayload(BaseModel):
    duration_seconds: float
    exit_code:        int
    log_size_bytes:   int


def verify_api_key(x_api_key):
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="No API key provided. Add x-api-key to your headers."
        )
    team = db.get_team_by_api_key(x_api_key)
    if team is None:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )
    return team


@app.post("/teams")
def register_team(request: TeamRequest):
    team_info = db.create_team(request.team_name)
    logging.info(f"New team: {request.team_name}")
    return {
        "message":   "Team registered. Save your API key — it will not be shown again.",
        "team_id":   team_info["team_id"],
        "team_name": team_info["team_name"],
        "api_key":   team_info["api_key"]
    }


@app.get("/teams")
def list_teams():
    teams = db.get_all_teams()
    return {"total": len(teams), "teams": teams}


@app.post("/jobs")
def submit_job(request: JobRequest, x_api_key: Optional[str] = Header(None)):
    team = verify_api_key(x_api_key)

    if db.job_exists(request.job_id):
        raise HTTPException(
            status_code=409,
            detail=f"Job ID '{request.job_id}' already exists."
        )

    if request.priority not in (1, 2, 3, 4):
        raise HTTPException(
            status_code=400,
            detail="Priority must be 1 (Critical), 2 (High), 3 (Normal), or 4 (Low)."
        )

    db.create_job(
        job_id   = request.job_id,
        team_id  = team["team_id"],
        repo_url = request.repo_url,
        cmd      = request.cmd,
        priority = request.priority
    )

    logging.info(f"Job {request.job_id} queued by {team['team_name']} (priority {request.priority})")
    return {
        "status":   "queued",
        "job_id":   request.job_id,
        "priority": request.priority
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str, x_api_key: Optional[str] = Header(None)):
    team = verify_api_key(x_api_key)
    job  = db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["team_id"] != team["team_id"]:
        raise HTTPException(status_code=403, detail="This job does not belong to your team.")

    return job


@app.get("/jobs/{job_id}/logs")
def get_logs(job_id: str, x_api_key: Optional[str] = Header(None)):
    team = verify_api_key(x_api_key)
    job  = db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["team_id"] != team["team_id"]:
        raise HTTPException(status_code=403, detail="This job does not belong to your team.")

    return {
        "job_id": job_id,
        "status": job["status"],
        "logs":   db.get_log(job_id)
    }


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str, x_api_key: Optional[str] = Header(None)):
    team = verify_api_key(x_api_key)
    job  = db.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["team_id"] != team["team_id"]:
        raise HTTPException(status_code=403, detail="This job does not belong to your team.")

    cancelled = db.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be cancelled. It may already be finished."
        )

    return {"status": "cancelled", "job_id": job_id}


@app.get("/my-jobs")
def get_my_jobs(x_api_key: Optional[str] = Header(None)):
    team = verify_api_key(x_api_key)
    jobs = db.get_jobs_for_team(team["team_id"])
    return {
        "team":       team["team_name"],
        "total_jobs": len(jobs),
        "jobs":       jobs
    }


@app.get("/worker/poll")
def worker_poll():
    job = db.get_next_queued_job()
    if job is not None:
        logging.info(f"Sending job {job['job_id']} to worker.")
        return {"has_job": True, "job": job}
    return {"has_job": False}


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, result: JobResult):
    if not db.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    db.update_job_status(job_id, result.status)
    logging.info(f"Job {job_id} finished: {result.status}")
    return {"status": "recorded"}


@app.post("/jobs/{job_id}/logs")
def upload_logs(job_id: str, payload: LogPayload):
    if not db.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    db.save_log(job_id, payload.output)
    return {"status": "logs_saved"}


@app.post("/jobs/{job_id}/metrics")
def record_metrics(job_id: str, payload: MetricsPayload):
    if not db.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    db.save_metrics(
        job_id           = job_id,
        duration_seconds = payload.duration_seconds,
        exit_code        = payload.exit_code,
        log_size_bytes   = payload.log_size_bytes
    )

    logging.info(f"Metrics saved for job {job_id}: {payload.duration_seconds:.1f}s")
    return {"status": "metrics_saved"}


@app.get("/jobs/{job_id}/cancelled")
def check_cancelled(job_id: str):
    return {"cancelled": db.is_job_cancelled(job_id)}


@app.get("/metrics/summary")
def metrics_summary():
    return db.get_metrics_summary()


@app.get("/metrics/all")
def all_metrics():
    return {"metrics": db.get_all_metrics()}


@app.get("/jobs/{job_id}/metrics")
def job_metrics(job_id: str):
    if not db.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    metrics = db.get_metrics(job_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="No metrics for this job yet.")
    return metrics


@app.get("/events")
def get_all_events():
    events = db.get_events()
    return {"total": len(events), "events": events}


@app.get("/jobs/{job_id}/events")
def get_job_events(job_id: str):
    if not db.job_exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job_id": job_id, "events": db.get_events(job_id)}