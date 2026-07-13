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

vLog_Dir  = LOG_PATH.strip()
vSeq_File = os.path.join(vLog_Dir, "log_seq.txt")

_FLUSH_EVERY = 10


# =========================
# READ SEQUENCE FROM FILE
# =========================
def _read_seq() -> int:
    try:
        if os.path.exists(vSeq_File):
            with open(vSeq_File, "r") as f:
                vParts = f.read().strip().split("|")
                if len(vParts) == 2:
                    vDate_Saved = vParts[0].strip()
                    vSeq_Saved  = int(vParts[1].strip())
                    vToday      = datetime.now().strftime("%Y%m%d")
                    if vDate_Saved == vToday:
                        return vSeq_Saved
    except Exception:
        pass
    return 0


# =========================
# WRITE SEQUENCE TO FILE
# =========================
def _write_seq(vSeq: int):
    try:
        vToday = datetime.now().strftime("%Y%m%d")
        with open(vSeq_File, "w") as f:
            f.write(f"{vToday}|{vSeq}")
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
        """Flush paksa ke disk — dipanggil saat rotation, shutdown, atau reset."""
        with self._lock:
            _write_seq(self._seq)
            self._unflushed = 0

    def reset(self):
        """Reset sequence ke 0 saat hari berganti."""
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
    vNow       = datetime.now()
    vFile_Name = f"app_{vNow.strftime('%Y%m%d')}.log"
    return os.path.join(vLog_Dir, vFile_Name)


# =========================
# DELETE OLD LOGS (LEBIH DARI 1 BULAN LALU)
# =========================
def _cleanup_old_logs():
    try:
        vNow    = datetime.now()
        vCutoff = vNow.replace(day=1) - relativedelta(months=1)
        vLogger = logging.getLogger("app")

        for vFile in os.listdir(vLog_Dir):
            if not vFile.startswith("app_") or not vFile.endswith(".log"):
                continue
            try:
                vDate_Part = vFile.replace("app_", "").replace(".log", "")
                vFile_Date = datetime.strptime(vDate_Part, "%Y%m%d")
            except ValueError:
                continue

            if vFile_Date < vCutoff:
                vFile_Path = os.path.join(vLog_Dir, vFile)
                os.remove(vFile_Path)
                vLogger.info(f"Old log deleted: {vFile}")

    except Exception as vError:
        logging.getLogger("app").error(f"cleanup_old_logs error: {vError}")


# =========================
# ATTACH FILE HANDLER
# =========================
def _attach_file_handler(vLogger: logging.Logger, vLog_Path: str, vReset_Seq: bool = False):
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

    vFile_Handler = logging.FileHandler(vLog_Path, encoding="utf-8")
    vFile_Handler.setFormatter(vFormatter)
    vLogger.addHandler(vFile_Handler)


# =========================
# BACKGROUND ROTATION WORKER
# =========================
def _rotation_worker():
    vLogger       = logging.getLogger("app")
    vCurrent_Path = get_log_path()

    while not _vStop_Rotation.is_set():
        _vStop_Rotation.wait(timeout=60)

        if _vStop_Rotation.is_set():
            break

        vNew_Path = get_log_path()
        if os.path.abspath(vNew_Path) != os.path.abspath(vCurrent_Path):
            _attach_file_handler(vLogger, vNew_Path, vReset_Seq=True)
            vCurrent_Path = vNew_Path
            vLogger.info(f"New log file created: {os.path.basename(vNew_Path)}")
            _cleanup_old_logs()


# =========================
# SETUP LOGGER
# =========================
def setup_logger():
    global _vSeq_Filter, _vRotation_Thread, _vStop_Rotation

    os.makedirs(vLog_Dir, exist_ok=True)

    vLogger = logging.getLogger("app")
    vLogger.propagate = False

    if not vLogger.handlers:
        vLogger.setLevel(logging.INFO)

        vToday = datetime.now().strftime("%Y%m%d")
        try:
            if os.path.exists(vSeq_File):
                with open(vSeq_File, "r") as f:
                    vParts = f.read().strip().split("|")
                    if len(vParts) == 2 and vParts[0].strip() != vToday:
                        _write_seq(0)
        except Exception:
            pass

        _vSeq_Filter = SequenceFilter()
        vLogger.addFilter(_vSeq_Filter)

        vLog_Path = get_log_path()
        _attach_file_handler(vLogger, vLog_Path, vReset_Seq=False)

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