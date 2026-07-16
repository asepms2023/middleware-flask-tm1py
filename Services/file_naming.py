# =========================
# IMPORTS
# =========================
import time
import threading
from Integrations.tm1_connection import get_tm1
from Core.logger import get_logger
from Services import control_panel as cp

vLog = get_logger()

# =========================
# GLOBAL CACHE
# =========================
vFileName_Cache      = {}
vFileName_Cache_Lock = threading.Lock()


# =========================
# GET FILE NAME (BERDASARKAN SYNCCODE ATTRIBUTE, CACHED)
# =========================
def get_file_name(sSync_Code: str, sDefault_Name: str) -> str:
    global vFileName_Cache

    cp.get_control_panel_data()

    nNow = time.time()

    with vFileName_Cache_Lock:
        if sSync_Code in vFileName_Cache and cp.nCache_Duration != 0:
            sCached_Prefix, nFetched_At = vFileName_Cache[sSync_Code]
            if (nNow - nFetched_At) < cp.nCache_Duration:
                return f"{sCached_Prefix}.csv"

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

    sPrefix_Found = None
    for _, vRow in vDf.iterrows():
        if str(vRow["SyncCode"]).strip() == sSync_Code:
            sValue = str(vRow["Value"]).strip()
            if sValue and sValue.lower() not in ("nan", "none"):
                sPrefix_Found = sValue
            break

    with vFileName_Cache_Lock:
        if sPrefix_Found is not None and cp.nCache_Duration != 0:
            vFileName_Cache[sSync_Code] = (sPrefix_Found, nNow)
        else:
            vFileName_Cache.pop(sSync_Code, None)

    return f"{sPrefix_Found}.csv" if sPrefix_Found else sDefault_Name