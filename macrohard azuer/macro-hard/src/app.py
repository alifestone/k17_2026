import json
import os
import re
from urllib.parse import urljoin
from urllib.request import urlopen

from flask import Flask, jsonify, request, session

# internal only url
API_BASE = os.environ.get("API_BASE", "https://accounts.internal/api/")

STAGING_ROOT = "/tmp/users"
FETCH_TIMEOUT = 5

FLAG = os.environ.get("FLAG")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

EDITABLE_FIELDS = ("vcpu", "quota", "capacity")
MEMBER_SETTINGS = {}


MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MiB total request body
MAX_UPLOAD_FILES = 16  # files per import
MAX_FILE_SIZE = 64 * 1024  # 64 KiB per file

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


# helpers
class ValidationError(Exception):
    pass


def fetch(base, resource):
    return json.load(urlopen(urljoin(base, resource), timeout=FETCH_TIMEOUT))


def apply_settings(record):
    settings = {}
    for field in EDITABLE_FIELDS:
        if field in record:
            value = record[field]
            if not isinstance(value, (int, float)):
                raise ValidationError(f"{field} must be a number")
            settings[field] = int(value)
    return settings


# endpoints
@app.get("/members")
def list_members():
    return jsonify(
        members=[
            {"member": name, "settings": settings}
            for name, settings in MEMBER_SETTINGS.items()
        ]
    )


@app.post("/members")
def create_member():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="expected a JSON object"), 400

    username = body.get("username")
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        return jsonify(error="invalid member"), 400
    if username in MEMBER_SETTINGS:
        return jsonify(error="member already exists"), 409

    MEMBER_SETTINGS[username] = {field: 0 for field in EDITABLE_FIELDS}
    return jsonify(member=username, settings=MEMBER_SETTINGS[username]), 201


@app.post("/members/<username>/settings")
def update_settings(username):
    if username not in MEMBER_SETTINGS:
        return jsonify(error="no such member"), 404

    record = request.get_json(silent=True)
    if not isinstance(record, dict):
        return jsonify(error="expected a JSON object"), 400

    try:
        settings = apply_settings(record)
    except ValidationError as exc:
        return jsonify(error=str(exc)), 400

    MEMBER_SETTINGS[username].update(settings)
    return jsonify(member=username, settings=MEMBER_SETTINGS[username])


@app.get("/members/<username>/settings")
def get_settings(username):
    if username not in MEMBER_SETTINGS:
        return jsonify(error="no such member"), 404
    return jsonify(member=username, settings=MEMBER_SETTINGS[username])


@app.post("/upload")
def upload():
    files = request.files.getlist("files")
    if len(files) > MAX_UPLOAD_FILES:
        return jsonify(error="too many files"), 400

    staged = []
    try:
        pending = []
        for storage in files:
            name = os.path.basename(storage.filename or "") #check??
            if not name:
                continue

            raw = storage.read()
            if len(raw) > MAX_FILE_SIZE:
                raise ValidationError(f"{name}: file too large")
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                raise ValidationError(f"{name}: not valid JSON")

            if not isinstance(record, dict):
                raise ValidationError(f"{name}: record must be a JSON object")

            account = record.get("account")
            if not isinstance(account, str) or not USERNAME_RE.match(account):
                raise ValidationError(f"{name}: record has no valid account")

            dest_dir = os.path.join(STAGING_ROOT, account)
            os.makedirs(dest_dir, exist_ok=True)
            path = os.path.join(dest_dir, name)
            with open(path, "wb") as f:
                f.write(raw)
            staged.append((account, path))
            pending.append(record)

        for record in pending:
            apply_settings(record)
    except ValidationError as exc:
        for _, path in staged:
            os.remove(path)
        return jsonify(error=str(exc)), 400

    for _, path in staged:
        os.remove(path)
    return jsonify(imported=sorted({account for account, _ in staged}))


@app.post("/console/select")
def console_select():
    session["account"] = request.form.get("account", "")
    return jsonify(account=session["account"])


@app.get("/console/permissions")
def console_permissions():
    account = session.get("account")
    if not account:
        return jsonify(error="no account selected"), 400

    base = urljoin(API_BASE, account)
    try:
        permissions = fetch(base, "permissions")
    except (OSError, ValueError):
        return jsonify(error="could not load account"), 502
    session["elevated"] = permissions.get("role") == "admin"

    return jsonify(role=permissions.get("role"), elevated=session["elevated"])


@app.get("/console/export")
def console_export():
    if not session.get("elevated"):
        return jsonify(error="not authorised"), 403

    account = session.get("account")
    if not account:
        return jsonify(error="no account selected"), 400

    base = urljoin(API_BASE, account)
    try:
        settings = fetch(base, "user/settings")
    except (OSError, ValueError):
        return jsonify(error="could not load account"), 502

    if not settings.get("export_enabled"):
        return jsonify(error="export not enabled for this account"), 403

    return jsonify(flag=FLAG)


@app.get("/")
def index():
    if os.path.exists(os.path.join(app.static_folder, "index.html")):
        return app.send_static_file("index.html")
    return jsonify(service="org-console", status="ok")


if __name__ == "__main__":
    os.makedirs(STAGING_ROOT, exist_ok=True)
    app.run(host="0.0.0.0", port=8000, threaded=True)
