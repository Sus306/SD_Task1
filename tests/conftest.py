# tests/conftest.py
import pytest
import subprocess
import time
import os
import signal

@pytest.fixture(scope="session", autouse=True)
def start_framework():
    # Ajusta la ruta si tu framework.py no está en la raíz del proyecto.
    proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Arrancamos framework.py y todos sus subprocesos en un grupo de procesos
    proc = subprocess.Popen(
        ["python3", "framework.py"],
        cwd=proj_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid  # start new session to capture all children
    )
    # Espera a que inicialicen todos los servicios (XMLRPC, Redis, Rabbit, Pyro)
    time.sleep(5)
    yield
    # Teardown: shut down all server processes
    try:
        # Kill any redis-server instances started by framework
        subprocess.run(["pkill", "-f", "redis-server"], check=False)
    except Exception:
        pass
    try:
        # Kill any rabbitmq-server instances
        subprocess.run(["pkill", "-f", "rabbitmq-server"], check=False)
    except Exception:
        pass
    # Finally, terminate the framework process group
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait()
