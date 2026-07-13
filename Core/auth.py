# =========================
# IMPORTS
# =========================
import os
import jwt
import hmac
import uuid
import json
import threading
from datetime import datetime, timedelta, timezone
from Core.settings import BASE_PATH


# =========================
# JTI STORAGE PATH
# =========================
_vJTI_File = os.path.join(BASE_PATH.strip(), "active_jti.json")


# =========================
# JTI MEMORY CACHE
_vCached_JTI = None


# =========================
# TOKEN LOCK
# =========================
vToken_Lock = threading.Lock()


# =========================
# LOAD ACTIVE JTI
# =========================
def _load_jti() -> str | None:
    global _vCached_JTI

    # Prioritas 1: pakai cache memory
    if _vCached_JTI:
        return _vCached_JTI

    # Prioritas 2: baca dari file (saat restart)
    try:
        if os.path.exists(_vJTI_File):
            with open(_vJTI_File, "r") as f:
                vData = json.load(f)
                _vCached_JTI = vData.get("jti")
                return _vCached_JTI
    except Exception:
        pass

    return None


# =========================
# SAVE ACTIVE JTI
# =========================
def _save_jti(vJTI: str):
    global _vCached_JTI

    try:
        with open(_vJTI_File, "w") as f:
            json.dump({"jti": vJTI}, f)
        _vCached_JTI = vJTI
    except Exception:
        pass


# =========================
# GENERATE JWT TOKEN
# =========================
def generate_token(vAuth_Cfg: dict) -> dict:

    # Waktu saat token dibuat (UTC)
    vNow = datetime.now(timezone.utc)

    # Waktu expired = sekarang + expires_in detik
    vExpires_At = vNow + timedelta(
        seconds=vAuth_Cfg["expires_in"]
    )

    # JWT ID unik untuk membedakan setiap token
    vJTI = str(uuid.uuid4())

    # Payload JWT
    vPayload = {
        "sub"  : vAuth_Cfg["client_id"],
        "scope": vAuth_Cfg["scope"],
        "iat"  : int(vNow.timestamp()),
        "exp"  : int(vExpires_At.timestamp()),
        "jti"  : vJTI,
    }

    # Encode dan sign JWT dengan HS256
    vToken = jwt.encode(
        vPayload,
        vAuth_Cfg["secret_key"],
        algorithm="HS256"
    )

    # Simpan JTI ke memory cache + file.
    # File lama otomatis tertimpa sehingga token
    # sebelumnya langsung tidak valid.
    with vToken_Lock:
        _save_jti(vJTI)

    # Response standar OAuth-style
    return {
        "access_token": vToken,
        "token_type"  : "Bearer",
        "expires_in"  : vAuth_Cfg["expires_in"],
        "scope"       : vAuth_Cfg["scope"],
    }


# =========================
# SAFE COMPARE
# =========================
def _safe_compare(vA: str, vB: str) -> bool:
    return hmac.compare_digest(
        vA.encode("utf-8"),
        vB.encode("utf-8")
    )


# =========================
# VALIDATE REQUEST
# =========================
def validate_request(vForm: dict, vAuth_Cfg: dict):

    # Ambil nilai dari form dengan default string kosong
    vGrant_Type    = vForm.get("grant_type", "")
    vUsername      = vForm.get("username", "")
    vPassword      = vForm.get("password", "")
    vScope         = vForm.get("scope", "")
    vClient_Id     = vForm.get("client_id", "")
    vClient_Secret = vForm.get("client_secret", "")

    # Validasi grant_type
    if vGrant_Type != vAuth_Cfg["grant_type"]:
        return (
            f"grant_type must be "
            f"'{vAuth_Cfg['grant_type']}'"
        )

    # Validasi scope
    if vScope != vAuth_Cfg["scope"]:
        return (
            f"scope must be "
            f"'{vAuth_Cfg['scope']}'"
        )

    # Validasi username
    if not _safe_compare(
        vUsername,
        vAuth_Cfg["username"]
    ):
        return "Invalid username or password"

    # Validasi password
    if not _safe_compare(
        vPassword,
        vAuth_Cfg["password"]
    ):
        return "Invalid username or password"

    # Validasi client_id
    if not _safe_compare(
        vClient_Id,
        vAuth_Cfg["client_id"]
    ):
        return "Invalid client_id or client_secret"

    # Validasi client_secret
    if not _safe_compare(
        vClient_Secret,
        vAuth_Cfg["client_secret"]
    ):
        return "Invalid client_id or client_secret"

    # Semua valid
    return None


# =========================
# VERIFY TOKEN
# =========================
def verify_token(vAuth_Header: str, vSecret_Key: str):

    # Header harus berbentuk:
    # Authorization: Bearer <token>
    if not vAuth_Header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"

    # Ambil string JWT setelah kata "Bearer"
    vToken = vAuth_Header.replace(
        "Bearer ",
        ""
    ).strip()

    # Token kosong setelah di-trim
    if not vToken:
        return None, "Token is empty"

    try:
        vPayload = jwt.decode(
            vToken,
            vSecret_Key,
            algorithms=["HS256"]
        )

        # Ambil JWT ID
        vJTI = vPayload.get("jti")

        # Token tanpa JTI dianggap invalid
        if not vJTI:
            return None, "Invalid token"

        with vToken_Lock:
            vActive_JTI = _load_jti()

            # Tidak ada JTI tersimpan
            if vActive_JTI is None:
                return None, "Invalid token"

            # Token bukan token terbaru
            if vJTI != vActive_JTI:
                return None, "Token has been revoked"

        # Semua valid
        return vPayload, None

    # Token valid tetapi sudah melewati exp
    except jwt.ExpiredSignatureError:
        return None, "Token expired"

    # Signature salah, format rusak, dsb.
    except jwt.InvalidTokenError:
        return None, "Invalid token"