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
sCONTROL_PANEL_CUBE       = "00-ControlPanelAPI"
sCONTROL_PANEL_ITEM_DIM   = "ControlPanelAPIItem"
sCONTROL_PANEL_MEASURE_DIM = "MeasureControlPanel"

# Elemen path (measure String) -> key hasil & fallback .env masing-masing
sPATH_ELEMENTS = {
    "DataFolderLocation"       : BASE_PATH,
    "SourceFileLocation"       : MASTERDATA_PATH,
    "SourceFileBackupLocation" : MOVED_MASTERDATA_PATH,
    "SourceFileLogsLocation"   : LOG_PATH,
}

sCACHE_ELEMENT = "CacheDuration(Seconds)"

sDefault_Path = MASTERDATA_PATH.strip()

# =========================
# GLOBAL CACHE
# =========================
vControl_Panel_Cache  = None
nCache_Fetched_At     = 0
nCache_Duration       = 0
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
def _fetch_from_cube():
    vResult = {sKey: sFallback for sKey, sFallback in sPATH_ELEMENTS.items()}
    vResult[sCACHE_ELEMENT] = 0

    with get_tm1() as tm1:
        vDf = tm1.cubes.cells.execute_mdx_dataframe(f"""
            SELECT
                {{[{sCONTROL_PANEL_MEASURE_DIM}].[String],
                  [{sCONTROL_PANEL_MEASURE_DIM}].[Numeric]}} ON COLUMNS,
                {{[{sCONTROL_PANEL_ITEM_DIM}].Members}} ON ROWS
            FROM [{sCONTROL_PANEL_CUBE}]
        """)

    sFound_Path_Keys = set()

    if vDf.empty:
        vLog.warning("Cube 00-ControlPanelAPI returned empty result, using .env fallback for all paths.")
        return vResult, sFound_Path_Keys

    for _, vRow in vDf.iterrows():
        sItem_Name = str(vRow["ControlPanelAPIItem"]).strip()
        sMeasure   = str(vRow["MeasureControlPanel"]).strip()
        vValue     = vRow["Value"]

        if sItem_Name in sPATH_ELEMENTS and sMeasure == "String":
            if vValue is not None and str(vValue).strip() not in ("", "nan", "None"):
                vResult[sItem_Name] = str(vValue).strip()
                sFound_Path_Keys.add(sItem_Name)

        elif sItem_Name == sCACHE_ELEMENT and sMeasure == "Numeric":
            vResult[sCACHE_ELEMENT] = _to_int_safe(vValue)

    for sKey in sPATH_ELEMENTS:
        if sKey not in sFound_Path_Keys:
            vLog.warning(f"Element '{sKey}' value null, using .env: {vResult[sKey]}")

    return vResult, sFound_Path_Keys


# =========================
# GET CONTROL PANEL DATA (CACHED)
# =========================
def get_control_panel_data() -> dict:
    global vControl_Panel_Cache, nCache_Fetched_At, nCache_Duration

    nNow = time.time()

    with vCache_Lock:
        vCache_Masih_Berlaku = (
            vControl_Panel_Cache is not None
            and nCache_Duration != 0
            and (nNow - nCache_Fetched_At) < nCache_Duration
        )
        if vCache_Masih_Berlaku:
            return vControl_Panel_Cache

        try:
            vData, sFound_Path_Keys = _fetch_from_cube()
            nNew_Duration    = vData.get(sCACHE_ELEMENT, 0)
            vAll_Paths_Found = sFound_Path_Keys == set(sPATH_ELEMENTS.keys())

            if nNew_Duration != 0 and vAll_Paths_Found:
                vControl_Panel_Cache = vData
                nCache_Fetched_At    = nNow
                nCache_Duration      = nNew_Duration
                vLog.info(f"CacheDuration(Seconds) value {nNew_Duration}. cache activated.")
            else:
                vControl_Panel_Cache = None
                nCache_Fetched_At    = 0
                nCache_Duration      = 0

                if nNew_Duration != 0 and not vAll_Paths_Found:
                    vLog.warning(
                        "One or more path elements missing in cube, cache skipped "
                        "even though CacheDuration is valid."
                    )
                else:
                    vLog.warning("CacheDuration(Seconds) value 0. cache not activated.")

            return vData

        except Exception as vError:
            vLog.error(f"TM1 error fetching control panel cube: {vError}")

            if vControl_Panel_Cache is not None:
                vLog.warning("Cube unreachable, using last valid cache.")
                return vControl_Panel_Cache

            vLog.warning("Cube unreachable and no cache available, using full .env fallback.")
            vFallback = {sKey: sVal for sKey, sVal in sPATH_ELEMENTS.items()}
            vFallback[sCACHE_ELEMENT] = 0
            return vFallback


# =========================
# CONVENIENCE GETTERS
# =========================
def get_source_file_location() -> str:
    """Folder tempat CSV ditulis pertama kali, sebelum TI dijalankan."""
    return get_control_panel_data().get("SourceFileLocation", sDefault_Path)


def get_source_file_backup_location() -> str:
    """Folder tujuan pemindahan file setelah TI sukses."""
    return get_control_panel_data().get("SourceFileBackupLocation", MOVED_MASTERDATA_PATH)


def get_data_folder_location() -> str:
    return get_control_panel_data().get("DataFolderLocation", BASE_PATH)


def get_source_file_logs_location() -> str:
    return get_control_panel_data().get("SourceFileLogsLocation", LOG_PATH)


# =========================
# GET FILE NAME (BERDASARKAN SYNCCODE ATTRIBUTE)
# =========================
def get_file_name(sSync_Code: str, sDefault_Name: str) -> str:
    try:
        with get_tm1() as tm1:
            vDf = tm1.cubes.cells.execute_mdx_dataframe("""
                SELECT
                    NON EMPTY {[}ElementAttributes_SyncCode].[FileNamePrefix]} ON COLUMNS,
                    {[SyncCode].[SyncCode].Members} ON ROWS
                FROM [}ElementAttributes_SyncCode]
            """)
    except Exception as vError:
        vLog.warning(f"Failed to fetch FileNamePrefix for '{sSync_Code}': {vError}. Using default file name.")
        return sDefault_Name

    for _, vRow in vDf.iterrows():
        if str(vRow["SyncCode"]).strip() == sSync_Code:
            sPrefix = str(vRow["Value"]).strip()
            if sPrefix and sPrefix.lower() not in ("nan", "none"):
                return f"{sPrefix}.csv"

    return sDefault_Name


# =========================
# RUN TI PROCESS
# =========================
def run_ti_process(sProcess_Name):
    try:
        with get_tm1() as tm1:
            vSuccess, sStatus, sError_Log = tm1.processes.execute_with_return(sProcess_Name)

            if not vSuccess:
                vLog.error(f"TI process failed '{sProcess_Name}' | Status: {sStatus} | Log: {sError_Log}")
                raise RuntimeError("TI Process Failed")

            vLog.info(f"TI process success '{sProcess_Name}' | Status: {sStatus}")

    except RuntimeError:
        raise
    except Exception as vError:
        vLog.error(f"TI process error '{sProcess_Name}': {vError}")
        raise RuntimeError("TI Process Failed")


# =========================
# MOVE PROCESSED FILE
# =========================
def move_processed_file(sSource_Path: str) -> bool:
    if not os.path.exists(sSource_Path):
        vLog.error(f"Move file failed: source file not found: {sSource_Path}")
        return False

    sBackup_Dir = get_source_file_backup_location()

    try:
        os.makedirs(sBackup_Dir, exist_ok=True)

        sFile_Name         = os.path.basename(sSource_Path)
        sName, sExt        = os.path.splitext(sFile_Name)
        sTimestamp         = datetime.now().strftime("%Y%m%d_%H%M%S")
        sDest_File_Name    = f"{sName}_{sTimestamp}{sExt}"
        sDest_Path         = os.path.join(sBackup_Dir, sDest_File_Name)

        shutil.move(sSource_Path, sDest_Path)
        vLog.info(f"File moved: {sSource_Path} -> {sDest_Path}")
        return True

    except Exception as vError:
        vLog.error(
            f"Failed to move file '{sSource_Path}' to backup folder "
            f"'{sBackup_Dir}': {vError}. Old file will be overwritten on next run."
        )
        return False


# =========================
# WRITE CSV
# =========================
def write_csv(sPath, sHeaders, vRows):
    os.makedirs(os.path.dirname(sPath), exist_ok=True)

    try:
        with open(sPath, "w", newline="", encoding="utf-8") as vFile:
            vWriter = csv.DictWriter(vFile, fieldnames=sHeaders)
            vWriter.writeheader()
            vWriter.writerows(vRows)

        vLog.info(f"CSV written successfully: {sPath} | Rows: {len(vRows)}")

    except PermissionError:
        vLog.error(f"CSV write failed: file is currently open or locked: {sPath}")
        raise

    except Exception as vError:
        vLog.error(f"CSV write failed: {sPath} | Error: {vError}")
        raise


# =========================
# BUILD ERROR ROW
# =========================
def build_error_row(vSync, sMessage, sTemplate):
    sNow = datetime.now()
    vRow = {k: "" for k in sTemplate}
    vRow["SyncCode"] = vSync or ""
    vRow["Status"]   = 0
    vRow["Message"]  = sMessage
    vRow["Date"]     = sNow.strftime("%Y-%m-%d")
    vRow["Time"]     = sNow.strftime("%H:%M:%S")
    return [vRow]