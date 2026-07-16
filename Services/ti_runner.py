# =========================
# IMPORTS
# =========================
from Integrations.tm1_connection import get_tm1
from Core.logger import get_logger

vLog = get_logger()


# =========================
# RUN TI PROCESS
# =========================
def run_ti_process(sProcess_Name):
    try:
        with get_tm1() as tm1:
            vSuccess, sStatus, sError_Log = tm1.processes.execute_with_return(sProcess_Name)

            if not vSuccess:
                vLog.error(f"TI process failed '{sProcess_Name}' | Status: {sStatus} | Log: {sError_Log}")
                raise RuntimeError("TI Process Failed")

            vLog.info(f"TI process success '{sProcess_Name}' | Status: {sStatus}")

    except RuntimeError:
        raise
    except Exception as vError:
        vLog.error(f"TI process error '{sProcess_Name}': {vError}")
        raise RuntimeError("TI Process Failed")