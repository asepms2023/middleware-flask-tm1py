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
    run_ti_process,
    move_processed_file,
)

# =========================
# CONSTANTS Header CSV
# =========================
vCSV_HEADERS = [
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
def write_error_csv(vSync, vMessage):
    vPath = os.path.join(get_source_file_location(), "MasterData_Dealer.csv")
    vRows = build_error_row(vSync, vMessage, vCSV_HEADERS)
    write_csv(vPath, vCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vPath = os.path.join(get_source_file_location(), "MasterData_Dealer.csv")
    vData = normalize("MD01", vData)

    vSync = vData.get("SyncCode", "")
    vNow  = datetime.now()
    vDate = vNow.strftime("%Y-%m-%d")
    vTime = vNow.strftime("%H:%M:%S")

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
                "Date"             : vDate,
                "Time"             : vTime
            })

    try:
        write_csv(vPath, vCSV_HEADERS, vRows)
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
    move_processed_file(vPath)