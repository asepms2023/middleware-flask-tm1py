# =========================
# IMPORTS
# =========================
import os
from dotenv import load_dotenv

# =========================
# LOAD .ENV
# =========================
load_dotenv()

# =========================
# TM1 CONNECTION
# =========================
TM1_HOST     = os.environ.get("TM1_HOST", "")
TM1_PORT     = os.environ.get("TM1_PORT", "")
TM1_USER     = os.environ.get("TM1_USER", "")
TM1_PASSWORD = os.environ.get("TM1_PASSWORD", "")
TM1_SSL      = os.environ.get("TM1_SSL", "False") == "True"

# =========================
# AUTH
# =========================
SECRET_KEY    = os.environ.get("SECRET_KEY", "")
AUTH_USERNAME = os.environ.get("AUTH_USERNAME", "")
AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")

# =========================
# PATHS
# =========================
BASE_PATH             = os.environ.get("BASE_PATH", "")
LOG_PATH              = os.environ.get("LOG_PATH", "")
MASTERDATA_PATH       = os.environ.get("MASTERDATA_PATH", "")
MOVED_MASTERDATA_PATH = os.environ.get("MOVED_MASTERDATA_PATH", "").strip()