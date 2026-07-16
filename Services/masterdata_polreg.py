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
# CONSTANTS Csv Header
# =========================
sCSV_HEADERS = [
    "SyncCode",
    "MainDealerCode",
    "DealerCode",
    "PolregCode",
    "PolregName",
    "Status",
    "Message",
    "Date",
    "Time"
]

vLog = logging.getLogger("app")


# =========================
# WRITE ERROR CSV
# =========================
def write_error_csv(vSync, sMessage):
    sFile_Name = get_file_name(vSync, "MasterData_Polreg.csv")
    sPath = os.path.join(get_source_file_location(), sFile_Name)
    vRows = build_error_row(vSync, sMessage, sCSV_HEADERS)
    write_csv(sPath, sCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vData = normalize("PR01", vData)

    vSync      = vData.get("SyncCode", "")
    sFile_Name = get_file_name(vSync, "MasterData_Polreg.csv")
    sPath      = os.path.join(get_source_file_location(), sFile_Name)

    sNow  = datetime.now()
    sDate = sNow.strftime("%Y-%m-%d")
    sTime = sNow.strftime("%H:%M:%S")

    vRows = []

    for vMain in vData.get("MainDealers", []):
        vMainDealerCode = vMain.get("MainDealerCode", "")

        for vDealer in vMain.get("Dealers", []):
            vRows.append({
                "SyncCode"      : vSync,
                "MainDealerCode": vMainDealerCode,
                "DealerCode"    : vDealer.get("DealerCode", ""),
                "PolregCode"    : vDealer.get("PolregCode", ""),
                "PolregName"    : vDealer.get("PolregName", ""),
                "Status"        : 1,
                "Message"       : "Success",
                "Date"          : sDate,
                "Time"          : sTime
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
        run_ti_process("LoadData-01-MappingDealerPolreg")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(sPath)