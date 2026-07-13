# =========================
# IMPORTS
# =========================
import subprocess
import sys
import os
import shutil
import time
import psutil
from dotenv import load_dotenv

# =========================
# LOAD ENV
# =========================
vScript_Dir = os.path.dirname(os.path.abspath(__file__))
vEnv_Path   = os.path.join(vScript_Dir, ".env")
load_dotenv(vEnv_Path)

# =========================
# APP DIRECTORY (LOKASI run_py.py / app.py SENDIRI)
# =========================
vApp_Dir = vScript_Dir

CURRENT_PID = os.getpid()


# =========================
# KILL TARGET PYTHON PROCESSES
# =========================
def kill_target_python_processes():
    vTarget_Norm = os.path.normcase(os.path.normpath(vApp_Dir))

    for vProc in psutil.process_iter(["pid", "name"]):
        try:
            if vProc.info["pid"] == CURRENT_PID:
                continue

            vName = (vProc.info.get("name") or "").lower()
            if not vName.startswith("python"):
                continue
            try:
                vProc_Cwd = os.path.normcase(os.path.normpath(vProc.cwd()))
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue

            if vProc_Cwd == vTarget_Norm:
                vProc.terminate()
                try:
                    vProc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    vProc.kill()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


kill_target_python_processes()

time.sleep(1)


# =========================
# CLEAR PYCACHE
# =========================
sys.dont_write_bytecode = True

for vRoot, vDirs, vFiles in os.walk(vApp_Dir):
    for vDir in vDirs:
        if vDir == "__pycache__":
            vCache_Path = os.path.join(vRoot, vDir)
            shutil.rmtree(vCache_Path, ignore_errors=True)
sys.dont_write_bytecode = False


# =========================
# START APP
# =========================
os.chdir(vApp_Dir)

vProc = subprocess.Popen([
    sys.executable,
    "app.py"
])

try:
    vProc.wait()
except KeyboardInterrupt:
    vProc.terminate()
    vProc.wait()