# =========================
# IMPORTS
# =========================
import os
import csv
import time
import shutil
import threading
from datetime import datetime
from Integrations.tm1_connection import get_tm1
from Core.logger import get_logger
from Core.settings import (
    MASTERDATA_PATH,
    BASE_PATH,
    LOG_PATH,
    MOVED_MASTERDATA_PATH,
)

# =========================
# CONFIG
# =========================
if not MASTERDATA_PATH or MASTERDATA_PATH.strip() == "":
    raise EnvironmentError("MASTERDATA_PATH is not set in .env")

# =========================
# CUBE REFERENCE
# =========================
# Cube    : 00-ControlPanelAPI
vCONTROL_PANEL_CUBE       = "00-ControlPanelAPI"
vCONTROL_PANEL_ITEM_DIM   = "ControlPanelAPIItem"
vCONTROL_PANEL_MEASURE_DIM = "MeasureControlPanel"

# Elemen path (measure String)
vPATH_ELEMENTS = {
    "SourceTM1pyLocation"       : BASE_PATH,
    "SourceFileLocation"       : MASTERDATA_PATH,
    "SourceFileBackupLocation" : MOVED_MASTERDATA_PATH,
    "SourceFileLogsLocation"   : LOG_PATH,
}
vCACHE_ELEMENT = "CacheDuration(Seconds)"

vDefault_Path = MASTERDATA_PATH.strip()

# =========================
# GLOBAL CACHE
# =========================
vControl_Panel_Cache  = None
vCache_Fetched_At     = 0
vCache_Duration       = 0
vCache_Lock           = threading.Lock()

vLog = get_logger()


# =========================
# SAFE INT PARSE
# =========================
def _to_int_safe(vValue) -> int:
    try:
        if vValue is None or str(vValue).strip() == "":
            return 0
        return int(float(vValue))
    except (ValueError, TypeError):
        return 0


# =========================
# FETCH CONTROL PANEL CUBE
# =========================
def _fetch_from_cube() -> dict:
    vResult = {vKey: vFallback for vKey, vFallback in vPATH_ELEMENTS.items()}
    vResult[vCACHE_ELEMENT] = 0

    with get_tm1() as tm1:
        vDf = tm1.cubes.cells.execute_mdx_dataframe(f"""
            SELECT
                {{[{vCONTROL_PANEL_MEASURE_DIM}].[String],
                  [{vCONTROL_PANEL_MEASURE_DIM}].[Numeric]}} ON COLUMNS,
                {{[{vCONTROL_PANEL_ITEM_DIM}].Members}} ON ROWS
            FROM [{vCONTROL_PANEL_CUBE}]
        """)

    if vDf.empty:
        vLog.warning("Cube 00-ControlPanelAPI returned empty result, using .env fallback for all paths.")
        return vResult

    vFound_Path_Keys = set()

    for _, vRow in vDf.iterrows():
        vItem_Name = str(vRow["ControlPanelAPIItem"]).strip()
        vMeasure   = str(vRow["MeasureControlPanel"]).strip()
        vValue     = vRow["Value"]

        if vItem_Name in vPATH_ELEMENTS and vMeasure == "String":
            if vValue is not None and str(vValue).strip() not in ("", "nan", "None"):
                vResult[vItem_Name] = str(vValue).strip()
                vFound_Path_Keys.add(vItem_Name)

        elif vItem_Name == vCACHE_ELEMENT and vMeasure == "Numeric":
            vResult[vCACHE_ELEMENT] = _to_int_safe(vValue)

    for vKey in vPATH_ELEMENTS:
        if vKey not in vFound_Path_Keys:
            vLog.warning(f"Element '{vKey}' value null, using .env: {vResult[vKey]}")

    return vResult


# =========================
# GET CONTROL PANEL DATA (CACHED)
# =========================
def get_control_panel_data() -> dict:
    global vControl_Panel_Cache, vCache_Fetched_At, vCache_Duration

    vNow = time.time()

    with vCache_Lock:
        vCache_Masih_Berlaku = (
            vControl_Panel_Cache is not None
            and vCache_Duration != 0
            and (vNow - vCache_Fetched_At) < vCache_Duration
        )
        if vCache_Masih_Berlaku:
            return vControl_Panel_Cache

        try:
            vData = _fetch_from_cube()
            vNew_Duration = vData.get(vCACHE_ELEMENT, 0)

            if vNew_Duration != 0:
                vControl_Panel_Cache = vData
                vCache_Fetched_At    = vNow
                vCache_Duration      = vNew_Duration
                vLog.info(f"CacheDuration(Seconds) value {vNew_Duration}. cache activated.")
            else:
                vControl_Panel_Cache = None
                vCache_Fetched_At    = 0
                vCache_Duration      = 0
                vLog.warning("CacheDuration(Seconds) value 0. cache not activated.")

            return vData

        except Exception as vError:
            vLog.error(f"TM1 error fetching control panel cube: {vError}")

            if vControl_Panel_Cache is not None:
                vLog.warning("Cube unreachable, using last valid cache.")
                return vControl_Panel_Cache

            vLog.warning("Cube unreachable and no cache available, using full .env fallback.")
            vFallback = {vKey: vVal for vKey, vVal in vPATH_ELEMENTS.items()}
            vFallback[vCACHE_ELEMENT] = 0
            return vFallback


# =========================
# CONVENIENCE GETTERS
# =========================
def get_source_file_location() -> str:
    return get_control_panel_data().get("SourceFileLocation", vDefault_Path)


def get_source_file_backup_location() -> str:
    return get_control_panel_data().get("SourceFileBackupLocation", MOVED_MASTERDATA_PATH)


def get_data_folder_location() -> str:
    return get_control_panel_data().get("SourceTM1pyLocation", BASE_PATH)


def get_source_file_logs_location() -> str:
    return get_control_panel_data().get("SourceFileLogsLocation", LOG_PATH)


# =========================
# RUN TI PROCESS
# =========================
def run_ti_process(vProcess_Name):
    try:
        with get_tm1() as tm1:
            vSuccess, vStatus, vError_Log = tm1.processes.execute_with_return(vProcess_Name)

            if not vSuccess:
                vLog.error(f"TI process failed '{vProcess_Name}' | Status: {vStatus} | Log: {vError_Log}")
                raise RuntimeError("TI Process Failed")

            vLog.info(f"TI process success '{vProcess_Name}' | Status: {vStatus}")

    except RuntimeError:
        raise
    except Exception as vError:
        vLog.error(f"TI process error '{vProcess_Name}': {vError}")
        raise RuntimeError("TI Process Failed")


# =========================
# MOVE PROCESSED FILE
# =========================
def move_processed_file(vSource_Path: str) -> bool:
    if not os.path.exists(vSource_Path):
        vLog.error(f"Move file failed: source file not found: {vSource_Path}")
        return False

    vBackup_Dir = get_source_file_backup_location()

    try:
        os.makedirs(vBackup_Dir, exist_ok=True)

        vFile_Name         = os.path.basename(vSource_Path)
        vName, vExt        = os.path.splitext(vFile_Name)
        vTimestamp         = datetime.now().strftime("%Y%m%d_%H%M%S")
        vDest_File_Name    = f"{vName}_{vTimestamp}{vExt}"
        vDest_Path         = os.path.join(vBackup_Dir, vDest_File_Name)

        shutil.move(vSource_Path, vDest_Path)
        vLog.info(f"File moved: {vSource_Path} -> {vDest_Path}")
        return True

    except Exception as vError:
        vLog.error(
            f"Failed to move file '{vSource_Path}' to backup folder "
            f"'{vBackup_Dir}': {vError}. Old file will be overwritten on next run."
        )
        return False


# =========================
# WRITE CSV
# =========================
def write_csv(vPath, vHeaders, vRows):
    os.makedirs(os.path.dirname(vPath), exist_ok=True)

    try:
        with open(vPath, "w", newline="", encoding="utf-8") as vFile:
            vWriter = csv.DictWriter(vFile, fieldnames=vHeaders)
            vWriter.writeheader()
            vWriter.writerows(vRows)

        vLog.info(f"CSV written successfully: {vPath} | Rows: {len(vRows)}")

    except PermissionError:
        vLog.error(f"CSV write failed: file is currently open or locked: {vPath}")
        raise

    except Exception as vError:
        vLog.error(f"CSV write failed: {vPath} | Error: {vError}")
        raise


# =========================
# BUILD ERROR ROW
# =========================
def build_error_row(vSync, vMessage, vTemplate):
    vNow = datetime.now()
    vRow = {k: "" for k in vTemplate}
    vRow["SyncCode"] = vSync or ""
    vRow["Status"]   = 0
    vRow["Message"]  = vMessage
    vRow["Date"]     = vNow.strftime("%Y-%m-%d")
    vRow["Time"]     = vNow.strftime("%H:%M:%S")
    return [vRow]