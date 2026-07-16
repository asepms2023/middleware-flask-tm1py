# =========================
# IMPORTS
# =========================
import os
import logging
import threading
from datetime import datetime
from dateutil.relativedelta import relativedelta
from Core.settings import LOG_PATH

# =========================
# CONFIG
# =========================
if not LOG_PATH or LOG_PATH.strip() == "":
    raise EnvironmentError("LOG_PATH is not set in .env")

sLog_Dir  = LOG_PATH.strip()
sSeq_File = os.path.join(sLog_Dir, "log_seq.txt")

_FLUSH_EVERY = 10


# =========================
# READ SEQUENCE FROM FILE
# =========================
def _read_seq() -> int:
    try:
        if os.path.exists(sSeq_File):
            with open(sSeq_File, "r") as f:
                sParts = f.read().strip().split("|")
                if len(sParts) == 2:
                    sDate_Saved = sParts[0].strip()
                    nSeq_Saved  = int(sParts[1].strip())
                    sToday      = datetime.now().strftime("%Y%m%d")
                    if sDate_Saved == sToday:
                        return nSeq_Saved
    except Exception:
        pass
    return 0


# =========================
# WRITE SEQUENCE TO FILE
# =========================
def _write_seq(nSeq: int):
    try:
        sToday = datetime.now().strftime("%Y%m%d")
        with open(sSeq_File, "w") as f:
            f.write(f"{sToday}|{nSeq}")
    except Exception:
        pass


# =========================
# SEQUENCE FILTER
# =========================
class SequenceFilter(logging.Filter):

    def __init__(self):
        super().__init__()
        self._seq         = _read_seq()
        self._unflushed   = 0
        self._lock        = threading.Lock()

    def filter(self, record):
        with self._lock:
            self._seq        += 1
            record.seq        = self._seq
            self._unflushed  += 1

            # Flush ke disk setiap _FLUSH_EVERY log
            if self._unflushed >= _FLUSH_EVERY:
                _write_seq(self._seq)
                self._unflushed = 0

        return True

    def flush(self):
        with self._lock:
            _write_seq(self._seq)
            self._unflushed = 0

    def reset(self):
        with self._lock:
            self._seq       = 0
            self._unflushed = 0
            _write_seq(0)


# =========================
# GLOBAL INSTANCES
# =========================
_vSeq_Filter      : SequenceFilter   = None
_vRotation_Thread : threading.Thread = None
_vStop_Rotation   : threading.Event  = threading.Event()


# =========================
# GET LOG PATH (DAILY)
# =========================
def get_log_path():
    sNow       = datetime.now()
    sFile_Name = f"app_{sNow.strftime('%Y%m%d')}.log"
    return os.path.join(sLog_Dir, sFile_Name)


# =========================
# DELETE OLD LOGS (LEBIH DARI 1 BULAN LALU)
# =========================
def _cleanup_old_logs():
    try:
        sNow    = datetime.now()
        sCutoff = sNow.replace(day=1) - relativedelta(months=1)
        vLogger = logging.getLogger("app")

        for sFile in os.listdir(sLog_Dir):
            if not sFile.startswith("app_") or not sFile.endswith(".log"):
                continue
            try:
                sDate_Part = sFile.replace("app_", "").replace(".log", "")
                sFile_Date = datetime.strptime(sDate_Part, "%Y%m%d")
            except ValueError:
                continue

            if sFile_Date < sCutoff:
                sFile_Path = os.path.join(sLog_Dir, sFile)
                os.remove(sFile_Path)
                vLogger.info(f"Old log deleted: {sFile}")

    except Exception as vError:
        logging.getLogger("app").error(f"cleanup_old_logs error: {vError}")


# =========================
# ATTACH FILE HANDLER
# =========================
def _attach_file_handler(vLogger: logging.Logger, sLog_Path: str, vReset_Seq: bool = False):
    global _vSeq_Filter

    vFormatter = logging.Formatter(
        "[%(seq)s] %(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    for vHandler in list(vLogger.handlers):
        if isinstance(vHandler, logging.FileHandler):
            vHandler.close()
            vLogger.removeHandler(vHandler)

    if _vSeq_Filter:
        if vReset_Seq:
            _vSeq_Filter.reset()
        else:
            _vSeq_Filter.flush()

    vFile_Handler = logging.FileHandler(sLog_Path, encoding="utf-8")
    vFile_Handler.setFormatter(vFormatter)
    vLogger.addHandler(vFile_Handler)


# =========================
# BACKGROUND ROTATION WORKER
# =========================
def _rotation_worker():
    vLogger       = logging.getLogger("app")
    sCurrent_Path = get_log_path()

    while not _vStop_Rotation.is_set():
        _vStop_Rotation.wait(timeout=60)

        if _vStop_Rotation.is_set():
            break

        sNew_Path = get_log_path()
        if os.path.abspath(sNew_Path) != os.path.abspath(sCurrent_Path):
            _attach_file_handler(vLogger, sNew_Path, vReset_Seq=True)
            sCurrent_Path = sNew_Path
            vLogger.info(f"New log file created: {os.path.basename(sNew_Path)}")
            _cleanup_old_logs()


# =========================
# SETUP LOGGER
# =========================
def setup_logger():
    global _vSeq_Filter, _vRotation_Thread, _vStop_Rotation

    os.makedirs(sLog_Dir, exist_ok=True)

    vLogger = logging.getLogger("app")
    vLogger.propagate = False

    if not vLogger.handlers:
        vLogger.setLevel(logging.INFO)

        sToday = datetime.now().strftime("%Y%m%d")
        try:
            if os.path.exists(sSeq_File):
                with open(sSeq_File, "r") as f:
                    sParts = f.read().strip().split("|")
                    if len(sParts) == 2 and sParts[0].strip() != sToday:
                        _write_seq(0)
        except Exception:
            pass

        _vSeq_Filter = SequenceFilter()
        vLogger.addFilter(_vSeq_Filter)

        sLog_Path = get_log_path()
        _attach_file_handler(vLogger, sLog_Path, vReset_Seq=False)

    if _vRotation_Thread is None or not _vRotation_Thread.is_alive():
        _vStop_Rotation.clear()
        _vRotation_Thread = threading.Thread(
            target=_rotation_worker,
            name="LogRotationThread",
            daemon=True
        )
        _vRotation_Thread.start()

    return vLogger


# =========================
# GET LOGGER
# =========================
def get_logger():
    global _vSeq_Filter

    vLogger = logging.getLogger("app")

    if _vSeq_Filter is None:
        _vSeq_Filter = SequenceFilter()
        vLogger.addFilter(_vSeq_Filter)

    return vLogger


# =========================
# STOP LOGGER (DIPANGGIL SAAT SHUTDOWN BERSIH)
# =========================
def stop_logger():
    if _vSeq_Filter:
        _vSeq_Filter.flush()
    _vStop_Rotation.set()