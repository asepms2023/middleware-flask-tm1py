# =========================
# IMPORTS
# =========================
import re
import json
import logging

vLog = logging.getLogger("app")


# =========================
# RESPONSE HELPER
# =========================
def res(vSync, vStatus, vMessage, vHttp=200):
    from flask import jsonify
    return jsonify({
        "SyncCode": vSync,
        "Status"  : vStatus,
        "Message" : vMessage
    }), vHttp


# =========================
# RESPONSE ERROR HELPER
# =========================
def res_error(vMessage, vHttp=400):
    from flask import jsonify
    return jsonify({
        "error"            : "invalid_request",
        "error_description": vMessage
    }), vHttp


# =========================
# EXTRACT SYNCCODE FROM RAW
# =========================
def extract_sync_from_raw(vRaw: str) -> str:
    vMatch = re.search(r'"SyncCode"\s*:\s*"([^"]*)"', vRaw)
    return vMatch.group(1) if vMatch else ""


# =========================
# SAFE PARSE JSON
# =========================
def safe_parse_json(vRaw: str):
    try:
        return json.loads(vRaw), None
    except json.JSONDecodeError as vError:
        vLog.warning(
            f"JSON parse failed | Reason: {vError.msg} | "
            f"Line: {vError.lineno} | Col: {vError.colno}"
        )
        vMatch = re.search(r'"(\w+)"\s*:\s*[,\}\]]', vRaw)
        if vMatch:
            return None, f"{vMatch.group(1)} is invalid (Line {vError.lineno}, Col {vError.colno})"
        return None, f"Invalid JSON (Line {vError.lineno}, Col {vError.colno})"