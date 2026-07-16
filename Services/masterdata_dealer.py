# =========================
# IMPORTS
# =========================
import os
import logging
from datetime import datetime
from Utils.normalizer import normalize
from Services.base_service import (
    write_csv,
    build_error_row,
    get_source_file_location,
    get_file_name,
    run_ti_process,
    move_processed_file,
)

# =========================
# CONSTANTS Header CSV
# =========================
sCSV_HEADERS = [
    "SyncCode",
    "MainDealerCode",
    "MainDealerName",
    "MainDealerCodeHSO",
    "DealerCode",
    "DealerName",
    "DealerAHMCode",
    "GroupDealerCode",
    "GroupDealerName",
    "TypeChannel",
    "AreaQQ",
    "IsSemiQQ",
    "FlagQQ",
    "Status",
    "Message",
    "Date",
    "Time"
]

vLog = logging.getLogger("app")


# =========================
# GET FLAG QQ
# =========================
def get_flag_qq(vAreaQQ: str, vIsSemiQQ: str) -> str:
    if vIsSemiQQ == "1":
        return "SemiQQ"
    if vAreaQQ and vAreaQQ.strip() != "":
        return "QQ"
    return "Reguler"


# =========================
# WRITE ERROR CSV
# =========================
def write_error_csv(vSync, sMessage):
    sFile_Name = get_file_name(vSync, "MasterData_Dealer.csv")
    sPath = os.path.join(get_source_file_location(), sFile_Name)
    vRows = build_error_row(vSync, sMessage, sCSV_HEADERS)
    write_csv(sPath, sCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vData = normalize("MD01", vData)

    vSync      = vData.get("SyncCode", "")
    sFile_Name = get_file_name(vSync, "MasterData_Dealer.csv")
    sPath      = os.path.join(get_source_file_location(), sFile_Name)

    sNow  = datetime.now()
    sDate = sNow.strftime("%Y-%m-%d")
    sTime = sNow.strftime("%H:%M:%S")

    vRows = []

    for vMain in vData.get("MainDealers", []):
        vMainDealerCode    = vMain.get("MainDealerCode", "")
        vMainDealerName    = vMain.get("MainDealerName", "")
        vMainDealerCodeHSO = vMain.get("MainDealerCodeHSO", "")

        for vDealer in vMain.get("Dealers", []):
            vAreaQQ   = vDealer.get("AreaQQ") or ""
            vIsSemiQQ = vDealer.get("IsSemiQQ") or "0"
            vFlagQQ   = get_flag_qq(vAreaQQ, vIsSemiQQ)

            vRows.append({
                "SyncCode"         : vSync,
                "MainDealerCode"   : vMainDealerCode,
                "MainDealerName"   : vMainDealerName,
                "MainDealerCodeHSO": vMainDealerCodeHSO,
                "DealerCode"       : vDealer.get("DealerCode", ""),
                "DealerName"       : vDealer.get("DealerName", ""),
                "DealerAHMCode"    : vDealer.get("DealerAHMCode", ""),
                "GroupDealerCode"  : vDealer.get("GroupDealerCode", ""),
                "GroupDealerName"  : vDealer.get("GroupDealerName", ""),
                "TypeChannel"      : vDealer.get("TypeChannel", ""),
                "AreaQQ"           : vAreaQQ,
                "IsSemiQQ"         : vIsSemiQQ,
                "FlagQQ"           : vFlagQQ,
                "Status"           : 1,
                "Message"          : "Success",
                "Date"             : sDate,
                "Time"             : sTime
            })

    try:
        write_csv(sPath, sCSV_HEADERS, vRows)
    except Exception as vError:
        vLog.error(f"[{vSync}] CSV error: {vError}")
        raise RuntimeError("Internal Server Error")

    # =========================
    # RUN TI PROCESS
    # =========================
    try:
        run_ti_process("LoadData-Dealer")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(sPath)