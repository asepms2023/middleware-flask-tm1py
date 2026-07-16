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
sScript_Dir = os.path.dirname(os.path.abspath(__file__))
sEnv_Path   = os.path.join(sScript_Dir, ".env")
load_dotenv(sEnv_Path)

# =========================
# APP DIRECTORY
# =========================
sApp_Dir = sScript_Dir

CURRENT_PID = os.getpid()


# =========================
# KILL TARGET PYTHON PROCESSES
# =========================
def kill_target_python_processes():
    sTarget_Norm = os.path.normcase(os.path.normpath(sApp_Dir))

    for vProc in psutil.process_iter(["pid", "name"]):
        try:
            if vProc.info["pid"] == CURRENT_PID:
                continue

            sName = (vProc.info.get("name") or "").lower()
            if not sName.startswith("python"):
                continue

            try:
                sProc_Cwd = os.path.normcase(os.path.normpath(vProc.cwd()))
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue

            if sProc_Cwd == sTarget_Norm:
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

for sRoot, sDirs, sFiles in os.walk(sApp_Dir):
    for sDir in sDirs:
        if sDir == "__pycache__":
            sCache_Path = os.path.join(sRoot, sDir)
            shutil.rmtree(sCache_Path, ignore_errors=True)
sys.dont_write_bytecode = False


# =========================
# START APP
# =========================
os.chdir(sApp_Dir)

vProc = subprocess.Popen([
    sys.executable,
    "app.py"
])

try:
    vProc.wait()
except KeyboardInterrupt:
    vProc.terminate()
    vProc.wait()