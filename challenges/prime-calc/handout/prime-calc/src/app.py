import fcntl
import io
import json
import os
import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file


BASE_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
CONFIG_DIR = BASE_DIR / "configs"
ACTIVE_CONFIG = BASE_DIR / "runtime" / "active-config.json"
OUTPUT_FILE = BASE_DIR / "output" / "latest.txt"
STATUS_FILE = BASE_DIR / "output" / "status.txt"
CHECKPOINT_FILE = BASE_DIR / "checkpoint.dmtcp"
LOCK_FILE = BASE_DIR / "worker.lock"
WORKER = Path(__file__).with_name("worker.py")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024


def read_text(path: Path, fallback: str) -> str:
    try:
        return path.read_text(errors="replace")[-64_000:]
    except OSError:
        return fallback


@app.get("/")
def index():
    return render_template(
        "index.html",
        primes=read_text(OUTPUT_FILE, "").splitlines(),
    )


@app.get("/api/status")
def status():
    return jsonify(
        status=read_text(STATUS_FILE, "worker starting"),
        output=read_text(OUTPUT_FILE, "")
    )


@app.get("/api/snapshot")
def download_snapshot():
    try:
        with LOCK_FILE.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            snapshot = io.BytesIO(CHECKPOINT_FILE.read_bytes())
    except FileNotFoundError:
        return jsonify(error="snapshot not available yet"), 404

    response = send_file(
        snapshot,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name="checkpoint.dmtcp",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/config")
def upload_config():
    uploaded = request.files.get("config")
    timestamp = request.form.get("timestamp", "")
    if uploaded is None or not timestamp:
        return jsonify(error="timestamp and config are required"), 400

    if not timestamp[0].isdigit():
        return jsonify(error="timestamp must be numeric"), 400

    name = timestamp if Path(timestamp).suffix else timestamp + ".json"
    destination = (CONFIG_DIR / name).resolve()
    if destination != BASE_DIR.resolve() and BASE_DIR.resolve() not in destination.parents:
        return jsonify(error="invalid config path"), 400
    destination.parent.mkdir(parents=True, exist_ok=True)
    uploaded.save(destination)

    try:
        values = json.loads(destination.read_text())
        initial = int(values["initial_search_value"])
        method = values["search_method"]
        if initial < 2 or method not in {"prime", "mersenne"}:
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError):
        return jsonify(error="invalid config contents"), 400

    ACTIVE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_CONFIG.write_text(json.dumps({
        "initial_search_value": initial,
        "search_method": method,
    }))
    return jsonify(method=method, initial_search_value=initial), 201


@app.post("/api/run")
def run_now():
    completed = subprocess.run(
        [sys.executable, str(WORKER), "once"],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    return jsonify(
        ok=completed.returncode == 0,
        stdout=completed.stdout[-8000:],
        stderr=completed.stderr[-8000:],
        status=read_text(STATUS_FILE, "unknown"),
        output=read_text(OUTPUT_FILE, ""),
    ), (200 if completed.returncode == 0 else 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
