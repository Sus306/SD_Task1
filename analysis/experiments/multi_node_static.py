#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import time
from multiprocessing import Process, Queue
import redis
import pika
import csv
import uuid
import threading
import xmlrpc.client
import Pyro4

# ————— Transporte persistente para XMLRPC ——————————————————————
class PersistentTransport(xmlrpc.client.Transport):
    def __init__(self):
        super().__init__()
        self._connections = {}
    def make_connection(self, host):
        if host not in self._connections:
            self._connections[host] = super().make_connection(host)
        return self._connections[host]
    def close(self):
        for conn in self._connections.values():
            try: conn.close()
            except: pass
        self._connections.clear()

# ————— Paths ———————————————————————————————————————————————
BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          os.pardir, os.pardir))
BASE_DIR2 = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          os.pardir))
SERV_DIR  = os.path.join(BASE_DIR, "insult_service")
FIL_DIR   = os.path.join(BASE_DIR, "insult_filter")
GRAPHS_DIR= os.path.join(BASE_DIR2, "graphs")

XMLRPC_BASE_PORT_SERVICE = 8000
XMLRPC_BASE_PORT_FILTER  = 8001
PYRO_NS_PORT             = 9090

def start_process(cmd, silent=True):
    return subprocess.Popen(
        cmd, cwd=BASE_DIR,
        stdout=(subprocess.DEVNULL if silent else None),
        stderr=(subprocess.DEVNULL if silent else None),
    )

# ————— Launch servers ———————————————————————————————————————
def launch_servers(mode, mw, nodes):
    procs = []
    if mw == "xmlrpc":
        base   = (XMLRPC_BASE_PORT_SERVICE if mode=="service"
                  else XMLRPC_BASE_PORT_FILTER)
        script = ("insult_service_xmlrpc.py" if mode=="service"
                  else "insult_filter_xmlrpc.py")
        folder = (SERV_DIR if mode=="service" else FIL_DIR)
        for i in range(nodes):
            port = base + i
            cmd  = [sys.executable, os.path.join(folder, script), str(port)]
            p = start_process(cmd)
            procs.append((p, port))
            time.sleep(0.2)

    elif mw == "rabbitmq":
        # Aquí asumimos broker y Redis ya arrancados externamente
        script = os.path.join(FIL_DIR, "insult_filter_rabbitmq.py")
        for i in range(nodes):
            p = subprocess.Popen(
                [sys.executable, script],
                cwd=BASE_DIR,
                stdout=None, stderr=None
            )
            procs.append((p, None))
            time.sleep(1)
        time.sleep(2)

    elif mw == "redis":
        # asumimos Redis ya arrancado externamente
        script = ("insult_service_redis.py" if mode=="service"
                  else "insult_filter_redis.py")
        folder = (SERV_DIR if mode=="service" else FIL_DIR)
        for i in range(nodes):
            p = start_process([sys.executable,
                               os.path.join(folder, script)])
            procs.append((p, None))
            time.sleep(0.2)

    elif mw == "pyro":
        ns_p = start_process([sys.executable, "-m", "Pyro4.naming",
                              "-n", "127.0.0.1", "-p", str(PYRO_NS_PORT)])
        procs.append((ns_p, None))
        time.sleep(1)
        script = ("insult_service_pyro.py" if mode=="service"
                  else "insult_filter_pyro.py")
        folder = (SERV_DIR if mode=="service" else FIL_DIR)
        for i in range(nodes):
            p = start_process([sys.executable,
                               os.path.join(folder, script)])
            procs.append((p, None))
            time.sleep(0.2)

    else:
        raise RuntimeError(f"Middleware '{mw}' no soportado")
    return procs

# ————— Client process ——————————————————————————————————————
def client_proc(name, mode, mw, ports, reqs, out_q):
    start = time.perf_counter()
    try:
        if mw == "xmlrpc":
            # … tu lógica XMLRPC …
            transport = PersistentTransport()
            for port in ports:
                proxy = xmlrpc.client.ServerProxy(f"http://127.0.0.1:{port}",
                                                  transport=transport)
            # warmup
            proxy.add_insult("warmup")
            for _ in range(reqs):
                proxy.add_insult("load_test")

        elif mw == "rabbitmq":
            # publisher
            conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
            pub      = conn_pub.channel()
            pub.queue_declare(queue="text_queue", durable=True)

            # callback queue exclusiva
            conn_cb    = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
            cb         = conn_cb.channel()
            result     = cb.queue_declare(queue="", exclusive=True)
            callback_q = result.method.queue

            responses = {}

            # — Warm-up —
            warm = str(uuid.uuid4())
            responses[warm] = None
            pub.basic_publish(
                exchange="", routing_key="text_queue",
                properties=pika.BasicProperties(
                    reply_to=callback_q,
                    correlation_id=warm
                ),
                body="warmup"
            )
            # polling hasta recibir el warm-up
            while responses[warm] is None:
                m = cb.basic_get(queue=callback_q, auto_ack=True)
                if m[0] and m[1].correlation_id == warm:
                    responses[warm] = m[2].decode()

            # — Peticiones reales —
            for _ in range(reqs):
                corr = str(uuid.uuid4())
                responses[corr] = None
                pub.basic_publish(
                    exchange="", routing_key="text_queue",
                    properties=pika.BasicProperties(
                        reply_to=callback_q,
                        correlation_id=corr
                    ),
                    body="load_test"
                )
                while responses[corr] is None:
                    m = cb.basic_get(queue=callback_q, auto_ack=True)
                    if m[0] and m[1].correlation_id == corr:
                        responses[corr] = m[2].decode()

            conn_pub.close()
            conn_cb.close()


        elif mw == "redis":
            rcli = redis.Redis(host="localhost", port=6379,
                               db=0, decode_responses=True)
            for _ in range(reqs):
                rcli.rpush("texts_queue", "load_test")
                rcli.blpop("filtered_texts")

        elif mw == "pyro":
            ns = Pyro4.locateNS(host="127.0.0.1", port=PYRO_NS_PORT)
            proxy = Pyro4.Proxy(ns.lookup("insult.service"))
            proxy.add_insult("warmup")
            for _ in range(reqs):
                proxy.add_insult("load_test")

        else:
            raise RuntimeError(f"Unknown middleware {mw}")

    except Exception as e:
        print(f"Client {name} error: {e!r}")

    elapsed = time.perf_counter() - start
    out_q.put((name, elapsed))

# ————— Main ———————————————————————————————————————————————
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",     choices=["service","filter"], required=True)
    parser.add_argument("--mw",       choices=["xmlrpc","pyro","redis","rabbitmq"], required=True)
    parser.add_argument("--nodes",    type=int, required=True)
    parser.add_argument("--clients",  type=int, required=True)
    parser.add_argument("--requests", type=int, required=True)
    parser.add_argument("--csv",      required=True)
    args = parser.parse_args()

    servers = launch_servers(args.mode, args.mw, args.nodes)
    time.sleep(1)
    ports   = [port for (_, port) in servers if port is not None]

    out_q, procs = Queue(), []
    for i in range(args.clients):
        p = Process(target=client_proc,
                    args=(f"c{i}", args.mode, args.mw,
                          ports, args.requests, out_q),
                    daemon=True)
        p.start(); procs.append(p)

    results = [out_q.get() for _ in procs]
    for p in procs:
        p.join(1); p.terminate()

    os.makedirs(GRAPHS_DIR, exist_ok=True)
    dst = os.path.join(GRAPHS_DIR, os.path.basename(args.csv))
    with open(dst, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mw","nodes","clients","requests","client","time_s","ops_per_s"])
        for name, elapsed in sorted(results):
            w.writerow([args.mw, args.nodes, args.clients, args.requests,
                        name, f"{elapsed:.6f}", f"{args.requests/elapsed:.2f}"])
    print(f"Resultados guardados en {dst}")

    # cerramos servidores/filtros
    for p, _ in servers:
        try: p.terminate(); p.wait(timeout=1)
        except: pass

if __name__ == "__main__":
    main()
