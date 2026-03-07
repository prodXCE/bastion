import time
import logging
import requests
import runner

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - WORKER - %(message)s"
)

API_URL = "http://localhost:8080"


def start_polling():
    logging.info("Worker started. Polling Control Plan for jobs...")
    while True:
        try:
            response = requests.get(f"{API_URL}/worker/poll")
            data = response.json()

            if data.get("has_job"):
                job = data["job"]
                job_id = job["job_id"]
                repo_url = job["repo_url"]
                cmd = job["cmd"]

                logging.info(f"Worker received jon: {job_id}")

                try:
                    job_output = runner.execute_pipeline(job_id, repo_url, cmd)
                    final_status = "SUCCESS"
                except Exception as e:
                    job_output = str(e)
                    final_status = "FAILED"

                requests.post(
                        f"{API_URL}/jobs/{job_id}/logs",
                        json={"output": job_output}
                )

                requests.post(
                        f"{API_URL}/jobs/{job_id}/complete",
                        json={"status": final_status}
                )

                logging.info(f"Worker reported {final_status} for {job_id}")

        except requests.execeptions.ConnectionError:
            logging.warning("Cannot connect to Control Plane. Is the API running?")

        time.sleep(5)

if __name__ == "__main__":
    start_polling()

