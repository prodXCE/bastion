import streamlit as st
import requests
import time
import pandas as pd

API_URL = "http://localhost:8080"

st.set_page_config(
    page_title="Bastion CI",
    page_icon="🏰",
    layout="wide"
)

def get_summary():
    try:
        r = requests.get(f"{API_URL}/metrics/summary", timeout=3)
        return r.json()
    except Exception:
        return {}

def get_all_jobs():
    try:
        r = requests.get(f"{API_URL}/metrics/all", timeout=3)
        data = r.json()
        return data.get("metrics", [])
    except Exception:
        return []

def get_teams():
    try:
        r = requests.get(f"{API_URL}/teams", timeout=3)
        return r.json().get("teams", [])
    except Exception:
        return []

def get_job_logs(job_id, api_key):
    try:
        r = requests.get(
            f"{API_URL}/jobs/{job_id}/logs",
            headers={"x-api-key": api_key},
            timeout=5
        )
        return r.json()
    except Exception:
        return {"logs": "Could not fetch logs."}

def submit_job_to_api(job_id, repo_url, cmd, priority, api_key):
    try:
        r = requests.post(
            f"{API_URL}/jobs",
            headers={"x-api-key": api_key},
            json={
                "job_id": job_id,
                "repo_url": repo_url,
                "cmd": cmd,
                "priority": priority
            },
            timeout=5
        )
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500

def cancel_job_api(job_id, api_key):
    try:
        r = requests.delete(
            f"{API_URL}/jobs/{job_id}",
            headers={"x-api-key": api_key},
            timeout=5
        )
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500

st.title("🏰 Bastion CI")
st.caption("Distributed Ephemeral CI Runtime")
st.divider()

with st.sidebar:
    st.header("⚙️ Configuration")

    api_key = st.text_input(
        "API Key",
        type="password",
        placeholder="bstn_..."
    )

    st.divider()
    st.caption("Bastion CI — Phase 6 Complete")

    auto_refresh = st.checkbox("Auto-refresh every 10 seconds", value=False)

    if auto_refresh:
        time.sleep(10)
        st.rerun()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "🚀 Submit Job",
    "📋 Jobs",
    "👥 Teams"
])

with tab1:
    st.header("System Overview")

    summary = get_summary()

    if not summary:
        st.warning("⚠️ Cannot connect to the Bastion API. Is it running?")
        st.code("uvicorn api:app --host 0.0.0.0 --port 8080")
    else:
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Jobs", summary.get("total_jobs", 0))
        with col2:
            st.metric("Queued", summary.get("queued_count", 0))
        with col3:
            st.metric("Running", summary.get("running_count", 0))
        with col4:
            st.metric("Success Rate", f"{summary.get('success_rate', 0)}%")
        with col5:
            st.metric("Avg Duration", f"{summary.get('avg_duration', 0)}s")

        st.divider()

        st.subheader("Build Metrics")

        metrics_data = get_all_jobs()

        if metrics_data:
            df = pd.DataFrame(metrics_data)

            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.write("**Build Duration Over Time (seconds)**")
                if "duration_seconds" in df.columns and "job_id" in df.columns:
                    chart_df = df[["job_id", "duration_seconds"]].set_index("job_id")
                    st.bar_chart(chart_df)

            with chart_col2:
                st.write("**Exit Codes (0=Success, 1=Failure)**")
                if "exit_code" in df.columns:
                    exit_counts = df["exit_code"].value_counts().reset_index()
                    exit_counts.columns = ["exit_code", "count"]
                    st.bar_chart(exit_counts.set_index("exit_code"))
        else:
            st.info("No metrics yet. Submit some jobs to see charts here.")

with tab2:
    st.header("Submit a New CI Job")

    if not api_key:
        st.warning("Enter your API key in the sidebar to submit jobs.")
    else:
        with st.form("submit_job_form"):
            job_id = st.text_input("Job ID", placeholder="my-build-001")
            repo_url = st.text_input("Repository URL", placeholder="https://github.com/user/repo.git")
            cmd = st.text_input("Test Command", placeholder="python3 -m pytest")

            priority = st.selectbox(
                "Priority",
                options=[1, 2, 3, 4],
                index=2,
                format_func=lambda x: {
                    1: "1 — Critical",
                    2: "2 — High",
                    3: "3 — Normal",
                    4: "4 — Low"
                }[x]
            )

            submitted = st.form_submit_button("🚀 Submit Job")

        if submitted:
            if not job_id or not repo_url or not cmd:
                st.error("All fields are required.")
            else:
                result, status_code = submit_job_to_api(
                    job_id, repo_url, cmd, priority, api_key
                )

                if status_code == 200:
                    st.success(f"✅ Job '{job_id}' submitted successfully!")
                    st.json(result)
                elif status_code == 409:
                    st.error(f"❌ Job ID '{job_id}' already exists.")
                elif status_code == 401:
                    st.error("❌ Invalid API key.")
                else:
                    st.error(f"❌ Error: {result.get('detail', 'Unknown error')}")

with tab3:
    st.header("All Jobs")

    col_refresh, col_filter = st.columns([1, 3])

    with col_refresh:
        if st.button("🔄 Refresh"):
            st.rerun()

    with col_filter:
        status_filter = st.selectbox(
            "Filter by status",
            ["All", "QUEUED", "RUNNING", "SUCCESS", "FAILED", "CANCELLED"]
        )

    all_metrics = get_all_jobs()

    if all_metrics:
        df = pd.DataFrame(all_metrics)

        if status_filter != "All" and "status" in df.columns:
            df = df[df["status"] == status_filter]

        if df.empty:
            st.info(f"No jobs with status: {status_filter}")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No jobs yet. Submit one in the Submit Job tab.")

    st.divider()

    st.subheader("View Job Logs")

    if not api_key:
        st.warning("Enter your API key in the sidebar to view logs.")
    else:
        log_job_id = st.text_input("Enter Job ID to view logs")

        col_view, col_cancel = st.columns(2)

        with col_view:
            if st.button("📄 View Logs"):
                if log_job_id:
                    log_data = get_job_logs(log_job_id, api_key)

                    if "logs" in log_data:
                        st.write(f"**Status:** {log_data.get('status', 'Unknown')}")
                        st.code(log_data["logs"], language=None)
                    else:
                        st.error(log_data.get("detail", "Could not fetch logs."))

        with col_cancel:
            if st.button("🛑 Cancel Job"):
                if log_job_id:
                    result, status_code = cancel_job_api(log_job_id, api_key)
                    if status_code == 200:
                        st.success(f"Job '{log_job_id}' cancelled.")
                        st.rerun()
                    else:
                        st.error(result.get("detail", "Could not cancel."))

    st.divider()
    st.subheader("Live Log Stream")
    st.caption("Polls the API every 3 seconds while a job is running.")

    live_job_id = st.text_input("Job ID to watch live", key="live_job_input")

    if live_job_id and api_key:
        if st.button("▶️ Start Live Watch"):

            log_box = st.empty()
            status_box = st.empty()

            stop_watching = False

            while not stop_watching:
                log_data = get_job_logs(live_job_id, api_key)

                current_status = log_data.get("status", "UNKNOWN")
                status_box.write(f"**Current Status:** `{current_status}`")

                log_text = log_data.get("logs", "No logs yet...")
                log_box.code(log_text, language=None)

                if current_status in ("SUCCESS", "FAILED", "CANCELLED"):
                    stop_watching = True
                    st.success(f"Job finished with status: {current_status}")
                else:
                    time.sleep(3)

with tab4:
    st.header("Registered Teams")

    if st.button("🔄 Refresh Teams"):
        st.rerun()

    teams = get_teams()

    if teams:
        df_teams = pd.DataFrame(teams)
        st.dataframe(df_teams, use_container_width=True, hide_index=True)
    else:
        st.info("No teams registered yet.")

    st.divider()

    st.subheader("Register a New Team")

    with st.form("register_team_form"):
        new_team_name = st.text_input("Team Name", placeholder="alpha-team")
        register_btn = st.form_submit_button("➕ Register Team")

    if register_btn:
        if not new_team_name:
            st.error("Team name is required.")
        else:
            try:
                r = requests.post(
                    f"{API_URL}/teams",
                    json={"team_name": new_team_name},
                    timeout=5
                )
                data = r.json()

                if r.status_code == 200:
                    st.success(f"Team '{new_team_name}' registered!")
                    st.warning("⚠️ Save this API key now. It will never be shown again.")
                    st.code(data.get("api_key", ""), language=None)
                    st.json({
                        "team_id": data.get("team_id"),
                        "team_name": data.get("team_name")
                    })
                else:
                    st.error(f"Error: {data.get('detail', 'Unknown error')}")
            except Exception as e:
                st.error(f"Cannot reach API: {e}")
