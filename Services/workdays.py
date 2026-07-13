# =========================
# IMPORTS
# =========================
import os
import logging
import calendar
from datetime import datetime
from Services.base_service import (
    write_csv,
    build_error_row,
    get_source_file_location,
    run_ti_process,
    move_processed_file,
)

# =========================
# CONSTANTS
# =========================
vMONTH_MAPPING = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

vCSV_HEADERS = [
    "SyncCode",
    "Year",
    "Month",
    "Calendar Days",
    "Working Days",
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
    vPath = os.path.join(get_source_file_location(), "Workdays.csv")
    vRows = build_error_row(vSync, vMessage, vCSV_HEADERS)
    write_csv(vPath, vCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vPath = os.path.join(get_source_file_location(), "Workdays.csv")

    vSync     = vData.get("SyncCode", "")
    vWorkdays = vData.get("Workdays", [])
    vNow      = datetime.now()
    vDate     = vNow.strftime("%Y-%m-%d")
    vTime     = vNow.strftime("%H:%M:%S")

    vYears  = {vWd.get("PeriodYear") for vWd in vWorkdays if vWd.get("PeriodYear") is not None}
    vWd_Map = {
        (vWd.get("PeriodYear"), vWd.get("PeriodMonth")): vWd.get("WorkDays")
        for vWd in vWorkdays
        if vWd.get("PeriodYear") is not None and vWd.get("PeriodMonth") is not None
    }

    vRows = []

    for vYear in sorted(vYears):
        for vMonth in range(1, 13):
            vRows.append({
                "SyncCode"     : vSync,
                "Year"         : vYear,
                "Month"        : vMONTH_MAPPING[vMonth],
                "Calendar Days": calendar.monthrange(vYear, vMonth)[1],
                "Working Days" : vWd_Map.get((vYear, vMonth), ""),
                "Status"       : 1,
                "Message"      : "Success",
                "Date"         : vDate,
                "Time"         : vTime
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
        run_ti_process("LoadData-01-Workdays")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(vPath)