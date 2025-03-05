# script.py
import os
import subprocess

def run_services():
    services = [
        "python insult_service/insult_service_xmlrpc.py",
        "python insult_service/insult_service_pyro.py",
        "python insult_service/insult_service_redis.py",
        "python insult_service/insult_service_rabbitmq.py",
        "python insult_filter/insult_filter_xmlrpc.py",
        "python insult_filter/insult_filter_pyro.py",
        "python insult_filter/insult_filter_redis.py",
        "python insult_filter/insult_filter_rabbitmq.py"
    ]
    processes = [subprocess.Popen(service, shell=True) for service in services]
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()

if __name__ == "__main__":
    run_services()