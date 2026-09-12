import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
CHECKPOINT_FILE = DATA_DIR / "checkpoint.dmtcp"
CHECKPOINT_WORK_DIR = DATA_DIR / ".checkpoint-work"
OUTPUT_DIR = DATA_DIR / "output"
STATUS_FILE = OUTPUT_DIR / "status.txt"
LOCK_FILE = DATA_DIR / "worker.lock"
GENERATOR = Path(__file__).with_name("generator.py")
COORD_PORT = os.environ.get("DMTCP_COORD_PORT", "7779")


def prepare_checkpoint_work_dir() -> Path:
    if CHECKPOINT_WORK_DIR.exists():
        shutil.rmtree(CHECKPOINT_WORK_DIR)
    CHECKPOINT_WORK_DIR.mkdir()
    return CHECKPOINT_WORK_DIR


def save_checkpoint(directory: Path) -> None:
    generated = sorted(directory.glob("ckpt_*.dmtcp"))
    shutil.copy2(generated[0], CHECKPOINT_FILE)
    shutil.rmtree(directory)


def dmtcp_command(command: str, success_codes: tuple[int, ...] = (0,)) -> None:
    completed = subprocess.run(
        ["dmtcp_command", "--coord-port", COORD_PORT, command],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode not in success_codes:
        raise subprocess.CalledProcessError(
            completed.returncode,
            completed.args,
            output=completed.stdout,
            stderr=completed.stderr,
        )


def launch(command: list[str], checkpoint_dir: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [
            "dmtcp_launch",
            "--new-coordinator",
            "--coord-port", COORD_PORT,
            "--ckptdir", str(checkpoint_dir),
            "--interval", "0",
            *command,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_after_checkpoint(supervisor: subprocess.Popen) -> None:
    dmtcp_command("--kcheckpoint", success_codes=(0, 2))
    supervisor.wait(timeout=10)


def set_status(message: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=timezone.utc).isoformat()
    STATUS_FILE.write_text(f"{now} {message}\n")


def initialise() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "configs").mkdir(parents=True, exist_ok=True)
    active_config = DATA_DIR / "runtime" / "active-config.json"
    if not active_config.exists():
        active_config.parent.mkdir(parents=True, exist_ok=True)
        active_config.write_text(json.dumps({"initial_search_value": 2, "search_method": "prime"}))
    if CHECKPOINT_FILE.is_file():
        return
    work_dir = prepare_checkpoint_work_dir()
    process = launch([sys.executable, str(GENERATOR)], work_dir)
    time.sleep(0.25)
    stop_after_checkpoint(process)
    save_checkpoint(work_dir)
    (OUTPUT_DIR / "latest.txt").write_text("")
    set_status("initial snapshot created")


def cycle() -> None:
    with LOCK_FILE.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        initialise()
        (OUTPUT_DIR / "latest.txt").write_text("")
        set_status("restarting generator")
        work_dir = prepare_checkpoint_work_dir()
        restored = subprocess.Popen(
            [
                "dmtcp_restart",
                "--new-coordinator",
                "--coord-port", COORD_PORT,
                "--ckptdir", str(work_dir),
                str(CHECKPOINT_FILE),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)
        stop_after_checkpoint(restored)
        save_checkpoint(work_dir)
        set_status("successfully generated and checkpointed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        initialise()
    elif len(sys.argv) > 1 and sys.argv[1] == "once":
        cycle()
    else:
        raise SystemExit("usage: worker.py {init|once}")
