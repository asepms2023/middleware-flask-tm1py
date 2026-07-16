# =========================
# FACADE
# =========================
# File ini cuma re-export
# Logic sebenarnya ada di:
#   Services/control_panel.py  -> cube Control Panel, cache, path getters
#   Services/file_naming.py    -> FileNamePrefix per SyncCode, cache
#   Services/ti_runner.py      -> eksekusi TI process
#   Services/file_ops.py       -> write_csv, move_processed_file, build_error_row

from Services.control_panel import (
    get_control_panel_data,
    get_source_file_location,
    get_source_file_backup_location,
    get_data_folder_location,
    get_source_file_logs_location,
)
from Services.file_naming import get_file_name
from Services.ti_runner import run_ti_process
from Services.file_ops import write_csv, move_processed_file, build_error_row