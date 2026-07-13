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
# CONSTANTS Csv Header
# =========================
vCSV_HEADERS = [
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
def write_error_csv(vSync, vMessage):
    vPath = os.path.join(get_source_file_location(), "MasterData_Polreg.csv")
    vRows = build_error_row(vSync, vMessage, vCSV_HEADERS)
    write_csv(vPath, vCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vPath = os.path.join(get_source_file_location(), "MasterData_Polreg.csv")
    vData = normalize("PR01", vData)

    vSync = vData.get("SyncCode", "")
    vNow  = datetime.now()
    vDate = vNow.strftime("%Y-%m-%d")
    vTime = vNow.strftime("%H:%M:%S")

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
                "Date"          : vDate,
                "Time"          : vTime
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
        run_ti_process("LoadData-01-MappingDealerPolreg")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(vPath)