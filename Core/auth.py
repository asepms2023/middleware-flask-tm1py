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
_sJTI_File = os.path.join(BASE_PATH.strip(), "active_jti.json")


# =========================
# JTI MEMORY CACHE
# =========================
_sCached_JTI = None


# =========================
# TOKEN LOCK
# =========================
vToken_Lock = threading.Lock()


# =========================
# LOAD ACTIVE JTI
# =========================
def _load_jti() -> str | None:
    global _sCached_JTI

    # Prioritas 1: pakai cache memory
    if _sCached_JTI:
        return _sCached_JTI

    # Prioritas 2: baca dari file (saat restart)
    try:
        if os.path.exists(_sJTI_File):
            with open(_sJTI_File, "r") as f:
                vData = json.load(f)
                _sCached_JTI = vData.get("jti")
                return _sCached_JTI
    except Exception:
        pass

    return None


# =========================
# SAVE ACTIVE JTI
# =========================
def _save_jti(sJTI: str):
    global _sCached_JTI

    try:
        with open(_sJTI_File, "w") as f:
            json.dump({"jti": sJTI}, f)
        _sCached_JTI = sJTI
    except Exception:
        pass


# =========================
# GENERATE JWT TOKEN
# =========================
def generate_token(vAuth_Cfg: dict) -> dict:

    # Waktu saat token dibuat (UTC)
    sNow = datetime.now(timezone.utc)

    # Waktu expired = sekarang + expires_in detik
    sExpires_At = sNow + timedelta(
        seconds=vAuth_Cfg["expires_in"]
    )

    # JWT ID unik untuk membedakan setiap token
    sJTI = str(uuid.uuid4())

    # Payload JWT
    vPayload = {
        "sub"  : vAuth_Cfg["client_id"],
        "scope": vAuth_Cfg["scope"],
        "iat"  : int(sNow.timestamp()),
        "exp"  : int(sExpires_At.timestamp()),
        "jti"  : sJTI,
    }

    # Encode dan sign JWT dengan HS256
    sToken = jwt.encode(
        vPayload,
        vAuth_Cfg["secret_key"],
        algorithm="HS256"
    )

    # Simpan JTI ke memory cache + file.
    # File lama otomatis tertimpa sehingga token
    # sebelumnya langsung tidak valid.
    with vToken_Lock:
        _save_jti(sJTI)

    # Response standar OAuth-style
    return {
        "access_token": sToken,
        "token_type"  : "Bearer",
        "expires_in"  : vAuth_Cfg["expires_in"],
        "scope"       : vAuth_Cfg["scope"],
    }


# =========================
# SAFE COMPARE
# =========================
def _safe_compare(sA: str, sB: str) -> bool:
    return hmac.compare_digest(
        sA.encode("utf-8"),
        sB.encode("utf-8")
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

    # Return (None) kalau valid, atau tuple (sError_Code, sError_Description)
    # mengikuti kode error standar OAuth2 (RFC 6749 5.2) sesuai jenis
    # kegagalannya masing-masing -- bukan satu kode generik untuk semua.

    # Validasi grant_type
    if vGrant_Type != vAuth_Cfg["grant_type"]:
        return (
            "unsupported_grant_type",
            f"grant_type must be '{vAuth_Cfg['grant_type']}'"
        )

    # Validasi scope
    if vScope != vAuth_Cfg["scope"]:
        return (
            "invalid_scope",
            f"scope must be '{vAuth_Cfg['scope']}'"
        )

    # Validasi username
    if not _safe_compare(
        vUsername,
        vAuth_Cfg["username"]
    ):
        return ("invalid_grant", "invalid_username_or_password")

    # Validasi password
    if not _safe_compare(
        vPassword,
        vAuth_Cfg["password"]
    ):
        return ("invalid_grant", "invalid_username_or_password")

    # Validasi client_id
    if not _safe_compare(
        vClient_Id,
        vAuth_Cfg["client_id"]
    ):
        return ("invalid_client", "invalid_client_id_or_secret")

    # Validasi client_secret
    if not _safe_compare(
        vClient_Secret,
        vAuth_Cfg["client_secret"]
    ):
        return ("invalid_client", "invalid_client_id_or_secret")

    # Semua valid
    return None


# =========================
# VERIFY TOKEN
# =========================
def verify_token(sAuth_Header: str, sSecret_Key: str):

    # Header harus berbentuk:
    # Authorization: Bearer <token>
    if not sAuth_Header.startswith("Bearer "):
        return None, "Missing or invalid Authorization header"

    # Ambil string JWT setelah kata "Bearer"
    sToken = sAuth_Header.replace(
        "Bearer ",
        ""
    ).strip()

    # Token kosong setelah di-trim
    if not sToken:
        return None, "Token is empty"

    try:
        vPayload = jwt.decode(
            sToken,
            sSecret_Key,
            algorithms=["HS256"]
        )

        # Ambil JWT ID
        sJTI = vPayload.get("jti")

        # Token tanpa JTI dianggap invalid
        if not sJTI:
            return None, "Invalid token"

        with vToken_Lock:
            sActive_JTI = _load_jti()

            # Tidak ada JTI tersimpan
            if sActive_JTI is None:
                return None, "Invalid token"

            # Token bukan token terbaru
            if sJTI != sActive_JTI:
                return None, "Token has been revoked"

        # Semua valid
        return vPayload, None

    # Token valid tetapi sudah melewati exp
    except jwt.ExpiredSignatureError:
        return None, "Token expired"

    # Signature salah, format rusak, dsb.
    except jwt.InvalidTokenError:
        return None, "Invalid token"