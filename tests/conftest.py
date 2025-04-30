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
    proc = subprocess.Popen(
        ["python3", "framework.py"],
        cwd=proj_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Espera a que inicialicen todos los servicios (XMLRPC, Redis, Rabbit, Pyro)
    time.sleep(5)
    yield
    # Al terminar la sesión de tests, matamos el framework
    proc.terminate()
    proc.wait()
