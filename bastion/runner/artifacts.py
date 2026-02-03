import shutil
import os
from pathlib import Path

ARTIFACT_ROOT = Path.cwd() / "var" / "artifacts"

def collect_artifacts(job_id: str, workspace_path: str, artifacts_paths: list[str]):
    """
    copies requested files from the temp workspace to the perm artifact dir.
    """
    if not artifact_paths:
        return

    print(f"[{job_id}] Collecting {len(artifact_paths)} artifacts...")

    job_artifact_dir = ARTIFACT_ROOT / f"job-{job_id}"
    job_artifact_dir.mkdir(parents=True, exist_ok=True)

    for rel_path in artifact_paths:
        clean_rel_path = rel_path.lstrip("/")
        source_path = Path(workspace_path) / clean_rel_path

        dest_path = job_artifact_dir / Path(rel_path).name

    try:
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"   [OK] Saved: {rel_path}")
        else:
            print(f"   [MISSING] Could not find: {rel_path}")
    except Exception as e:
        print(f"   [ERROR] Failed to copy {rel_path}: {e}")
