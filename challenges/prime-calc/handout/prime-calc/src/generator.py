import json
import math
import os
import time
from pathlib import Path


DATA_DIR = Path(os.environ.get("DATA_DIR", "/app/data"))
ACTIVE_CONFIG = DATA_DIR / "runtime" / "active-config.json"
OUTPUT_FILE = DATA_DIR / "output" / "latest.txt"


def read_config() -> tuple[int, str, int]:
    try:
        values = json.loads(ACTIVE_CONFIG.read_text())
        return max(2, int(values["initial_search_value"])), values["search_method"], ACTIVE_CONFIG.stat().st_mtime_ns
    except (OSError, ValueError, TypeError, KeyError):
        return 2, "prime", 0


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def is_mersenne_prime(exponent: int) -> bool:
    if exponent == 2:
        return True
    if not is_prime(exponent):
        return False
    mersenne = (1 << exponent) - 1
    residue = 4
    for _ in range(exponent - 2):
        residue = (residue * residue - 2) % mersenne
    return residue == 0


candidate, search_method, config_version = read_config()
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

while True:
    configured_start, configured_method, latest_version = read_config()
    if latest_version != config_version:
        candidate = configured_start
        search_method = configured_method
        config_version = latest_version

    found = is_prime(candidate) if search_method == "prime" else is_mersenne_prime(candidate)
    if found:
        prime = candidate if search_method == "prime" else (1 << candidate) - 1
        with OUTPUT_FILE.open("a") as output:
            output.write(f"{prime}\n")
        time.sleep(0.02)
    candidate += 1
    time.sleep(0.0005)
