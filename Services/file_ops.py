# =========================
# IMPORTS
# =========================
import os
import csv
import shutil
from datetime import datetime
from Core.logger import get_logger
from Services.control_panel import get_source_file_backup_location

vLog = get_logger()


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