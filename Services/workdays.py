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
    get_file_name,
    run_ti_process,
    move_processed_file,
)

# =========================
# CONSTANTS
# =========================
sMONTH_MAPPING = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
}

sCSV_HEADERS = [
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
def write_error_csv(vSync, sMessage):
    sFile_Name = get_file_name(vSync, "Workdays.csv")
    sPath = os.path.join(get_source_file_location(), sFile_Name)
    vRows = build_error_row(vSync, sMessage, sCSV_HEADERS)
    write_csv(sPath, sCSV_HEADERS, vRows)


# =========================
# PROCESS DATA
# =========================
def process_data(vData):
    vSync      = vData.get("SyncCode", "")
    sFile_Name = get_file_name(vSync, "Workdays.csv")
    sPath      = os.path.join(get_source_file_location(), sFile_Name)

    vWorkdays = vData.get("Workdays", [])
    sNow      = datetime.now()
    sDate     = sNow.strftime("%Y-%m-%d")
    sTime     = sNow.strftime("%H:%M:%S")

    vYears  = {sWd.get("PeriodYear") for sWd in vWorkdays if sWd.get("PeriodYear") is not None}
    sWd_Map = {
        (sWd.get("PeriodYear"), sWd.get("PeriodMonth")): sWd.get("WorkDays")
        for sWd in vWorkdays
        if sWd.get("PeriodYear") is not None and sWd.get("PeriodMonth") is not None
    }

    vRows = []

    for vYear in sorted(vYears):
        for vMonth in range(1, 13):
            vRows.append({
                "SyncCode"     : vSync,
                "Year"         : vYear,
                "Month"        : sMONTH_MAPPING[vMonth],
                "Calendar Days": calendar.monthrange(vYear, vMonth)[1],
                "Working Days" : sWd_Map.get((vYear, vMonth), ""),
                "Status"       : 1,
                "Message"      : "Success",
                "Date"         : sDate,
                "Time"         : sTime
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
        run_ti_process("LoadData-01-Workdays")
    except RuntimeError:
        raise

    # =========================
    # MOVE FILE SETELAH TI SUKSES
    # =========================
    move_processed_file(sPath)