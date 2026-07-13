# =========================
# IMPORTS
# =========================
import importlib
import logging
from flask import request
from Validation.validator import validate
from Core.auth import verify_token
from Core.response import res, extract_sync_from_raw, safe_parse_json

vLog = logging.getLogger("app")


# =========================
# DYNAMIC HANDLER
# =========================
def make_handler(vModule, vFunction, vAuth_Cfg, vExpected_Sync):

    def handler():

        # =========================
        # VALIDASI TOKEN
        # =========================
        vAuth          = request.headers.get("Authorization", "")
        vPayload, vErr = verify_token(vAuth, vAuth_Cfg["secret_key"])

        if vErr:
            vLog.warning(f"Unauthorized | {vErr} | from {request.remote_addr}")
            return res("", 0, vErr, 401)

        # =========================
        # VALIDASI CONTENT-TYPE
        # =========================
        if "application/json" not in request.content_type:
            vLog.warning(f"Invalid Content-Type: {request.content_type} | from {request.remote_addr}")
            return res("", 0, "Content-Type must be application/json", 400)

        # =========================
        # PARSE JSON
        # =========================
        vRaw              = request.get_data(as_text=True)
        vData, vParse_Err = safe_parse_json(vRaw)

        vSync = ""
        if isinstance(vData, dict):
            vSync = vData.get("SyncCode", "") or ""
        elif vParse_Err:
            vSync = extract_sync_from_raw(vRaw)

        # =========================
        # JSON PARSE ERROR
        # =========================
        if vParse_Err:
            vLog.warning(f"[{vSync}] JSON parse error: {vParse_Err}")
            try:
                if hasattr(vModule, "write_error_csv"):
                    vModule.write_error_csv(vSync, vParse_Err)
            except Exception as vError:
                vLog.error(f"[{vSync}] write_error_csv failed: {vError}")
            return res(vSync, 0, vParse_Err, 400)

        # =========================
        # VALIDATION
        # =========================
        vErr = validate(vData, vRaw, vExpected_Sync)
        if vErr:
            vLog.warning(f"[{vSync}] Validation error: {vErr}")
            try:
                if hasattr(vModule, "write_error_csv"):
                    vModule.write_error_csv(vSync, vErr)
            except Exception as vError:
                vLog.error(f"[{vSync}] write_error_csv failed: {vError}")
            return res(vSync, 0, vErr, 400)

        # =========================
        # PROCESS
        # =========================
        try:
            vLog.info(f"[{vSync}] Start process: {vModule.__name__}.{vFunction}")
            vFunc = getattr(vModule, vFunction)
            vFunc(vData)
            vLog.info(f"[{vSync}] Process completed: Success")
            return res(vSync, 1, "Success", 200)

        except Exception as vError:
            vLog.error(f"[{vSync}] Internal error: {vError}")
            return res(vSync, 0, str(vError), 500)

    return handler


# =========================
# REGISTER ROUTES
# =========================
def register(vApp, vCfg):
    for vRoute in vCfg["routes"]:
        if not vRoute.get("active", True):
            vLog.info(f"Route skipped (inactive): {vRoute['endpoint']} → {vRoute['service']}")
            continue

        try:
            vModule = importlib.import_module(vRoute["service"])
        except Exception as vError:
            vLog.error(f"Failed to import module '{vRoute['service']}': {vError}")
            raise

        vHandler          = make_handler(
            vModule,
            vRoute["function"],
            vCfg["auth"],
            vRoute["synccode"]
        )
        vHandler.__name__ = vRoute["endpoint"].replace("/", "_")

        vApp.add_url_rule(
            vRoute["endpoint"],
            vHandler.__name__,
            vHandler,
            methods=["POST"]
        )
        vLog.info(f"Route registered: {vRoute['endpoint']} → {vRoute['service']}")