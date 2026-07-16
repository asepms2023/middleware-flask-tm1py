# =========================
# IMPORTS
# =========================
import time
import threading
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
sCONTROL_PANEL_CUBE        = "00-ControlPanelAPI"
sCONTROL_PANEL_ITEM_DIM    = "ControlPanelAPIItem"
sCONTROL_PANEL_MEASURE_DIM = "MeasureControlPanel"

sPATH_ELEMENTS = {
    "DataFolderLocation"       : BASE_PATH,
    "SourceFileLocation"       : MASTERDATA_PATH,
    "SourceFileBackupLocation" : MOVED_MASTERDATA_PATH,
    "SourceFileLogsLocation"   : LOG_PATH,
}

sCACHE_ELEMENT = "CacheDuration(Seconds)"
sDefault_Path  = MASTERDATA_PATH.strip()

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
    return get_control_panel_data().get("SourceFileLocation", sDefault_Path)


def get_source_file_backup_location() -> str:
    return get_control_panel_data().get("SourceFileBackupLocation", MOVED_MASTERDATA_PATH)


def get_data_folder_location() -> str:
    return get_control_panel_data().get("DataFolderLocation", BASE_PATH)


def get_source_file_logs_location() -> str:
    return get_control_panel_data().get("SourceFileLogsLocation", LOG_PATH)