# =========================
# IMPORTS
# =========================
import sys
import os
import signal
import json
import logging
from flask import Flask, request, jsonify
from Core.settings import BASE_PATH, LOG_PATH, MASTERDATA_PATH, SECRET_KEY, AUTH_USERNAME, AUTH_PASSWORD, CLIENT_SECRET
from Core.logger import setup_logger, stop_logger
from Core.auth import generate_token, validate_request
from Core.response import res_error
from Core.router import register

# =========================
# VALIDATE ENV & PATHS
# =========================
def _validate_env():
    sRequired = {
        "BASE_PATH"    : BASE_PATH,
        "SECRET_KEY"   : SECRET_KEY,
        "AUTH_USERNAME": AUTH_USERNAME,
        "AUTH_PASSWORD": AUTH_PASSWORD,
        "CLIENT_SECRET": CLIENT_SECRET,
    }
    sMissing = [k for k, v in sRequired.items() if not v or not v.strip()]

    if sMissing:
        raise EnvironmentError(f"Missing required env variables: {', '.join(sMissing)}")

    sRequired_Paths = {
        "BASE_PATH": BASE_PATH.strip(),
        "LOG_PATH" : LOG_PATH.strip(),
        "MASTERDATA_PATH" : MASTERDATA_PATH.strip(),
    }

    for sKey, sPath in sRequired_Paths.items():
        if not sPath:
            raise EnvironmentError(f"{sKey} is not set in .env")
        if not os.path.exists(sPath):
            raise FileNotFoundError(f"{sKey} path does not exist: '{sPath}'")

_validate_env()


# =========================
# FLASK APP
# =========================
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# =========================
# LOAD CONFIG
# =========================
def load_config():
    sConfig_Path = os.path.join(BASE_PATH.strip(), "config.json")

    try:
        with open(sConfig_Path, encoding="utf-8") as vFile:
            vCfg = json.load(vFile)
    except FileNotFoundError:
        raise FileNotFoundError(f"config.json not found at: {sConfig_Path}")
    except json.JSONDecodeError as vError:
        raise ValueError(f"config.json is not valid JSON: {vError}")

    # Inject secrets dari .env ke config (tidak disimpan di config.json)
    vCfg["auth"]["secret_key"]    = SECRET_KEY
    vCfg["auth"]["username"]      = AUTH_USERNAME
    vCfg["auth"]["password"]      = AUTH_PASSWORD
    vCfg["auth"]["client_secret"] = CLIENT_SECRET

    return vCfg


# =========================
# SETUP LOGGER & LOAD CONFIG
# =========================
setup_logger()
vLog = logging.getLogger("app")

try:
    vCfg = load_config()
except (FileNotFoundError, ValueError) as vError:
    logging.getLogger("app").error(f"Startup failed: {vError}")
    sys.exit(1)


# =========================
# SIGNAL HANDLER (GRACEFUL SHUTDOWN)
# =========================
def handle_shutdown(signum, frame):
    vLog.info("Server shutting down...")
    stop_logger()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)

if hasattr(signal, "SIGBREAK"):
    signal.signal(signal.SIGBREAK, handle_shutdown)


# =========================
# ENDPOINT: AUTH TOKEN
# =========================
@app.route("/auth/token", methods=["POST"])
def auth_token():
    if "application/x-www-form-urlencoded" not in request.content_type:
        return res_error("Content-Type must be application/x-www-form-urlencoded", 400)

    vForm = request.form
    vErr  = validate_request(vForm, vCfg["auth"])
    if vErr:
        vLog.warning(f"auth/token | Unauthorized | {vErr}")
        return res_error(vErr, 401)

    vToken_Data = generate_token(vCfg["auth"])
    vLog.info(f"auth/token | Token generated for client: {vForm.get('client_id')}")
    return jsonify(vToken_Data), 200


# =========================
# ENDPOINT: HEALTH CHECK
# =========================
@app.route("/health")
def health():
    return {"status": "running"}


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    from waitress import serve

    register(app, vCfg)
    vLog.info("Server started")
    serve(app, host=vCfg["server"]["host"], port=vCfg["server"]["port"], threads=vCfg["server"]["threads"])