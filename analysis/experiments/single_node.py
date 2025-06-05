#!/usr/bin/env python3
"""
single_node.py

Mide throughput de un solo nodo (Service o Filter)
para N peticiones o durante un tiempo fijo sobre cada middleware.
"""
import argparse
import subprocess
import time
import csv
import sys
import os
import xmlrpc.client
import redis
import pika
import Pyro4
import json
import uuid

# Parámetros de insultos y mensajes
INSULT = "bench_insult"
PHRASE = f"Hello {INSULT} world"

# Directorios de servicios y filtros
BASE    = os.path.abspath(os.path.join(os.getcwd(), "..", ".."))
SERV_DIR = os.path.join(BASE, "insult_service")
FIL_DIR  = os.path.join(BASE, "insult_filter")

# Claves de Redis para el filter
TEXTS_QUEUE   = "texts_queue"
RESULTS_QUEUE = "filtered_texts"
INSULTS_KEY   = "insults"

# ——— Helpers para arrancar servicios/filtros ——————————————————————————

def start_xmlrpc_service():
    return subprocess.Popen(
        [sys.executable, os.path.join(SERV_DIR, "insult_service_xmlrpc.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def start_pyro_ns():
    p = subprocess.Popen(
        [sys.executable, "-m", "Pyro4.naming", "-n", "127.0.0.1", "-p", "9090"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    time.sleep(0.5)
    return p

def start_pyro_service():
    return subprocess.Popen(
        [sys.executable, os.path.join(SERV_DIR, "insult_service_pyro.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def start_redis_filter():
    return subprocess.Popen(
        [sys.executable, os.path.join(FIL_DIR, "insult_filter_redis.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def start_rabbitmq_filter():
    return subprocess.Popen(
        [sys.executable, os.path.join(FIL_DIR, "insult_filter_rabbitmq.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

# ——— SERVICE BENCHMARKS ——————————————————————————————————————————————

def measure_service_xmlrpc(n):
    cli = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
    cli.add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        cli.add_insult(f"{INSULT}_{i}")
    return time.perf_counter() - start


def make_iter_service_xmlrpc():
    cli = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
    cli.add_insult(INSULT)
    def it():
        cli.add_insult(INSULT)
    return it


def measure_service_pyro(n):
    ns  = Pyro4.locateNS(host="127.0.0.1", port=9090)
    svc = Pyro4.Proxy(ns.lookup("insult.service"))
    svc.add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        svc.add_insult(f"{INSULT}_{i}")
    return time.perf_counter() - start


def make_iter_service_pyro():
    ns  = Pyro4.locateNS(host="127.0.0.1", port=9090)
    svc = Pyro4.Proxy(ns.lookup("insult.service"))
    svc.add_insult(INSULT)
    def it():
        svc.add_insult(INSULT)
    return it

# ——— FILTER BENCHMARKS ——————————————————————————————————————————————

def measure_filter_redis(n):
    # Conexión y preparación de colas y set de insultos
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.sadd(INSULTS_KEY, INSULT)
    r.delete(TEXTS_QUEUE, RESULTS_QUEUE)

    start = time.perf_counter()
    for i in range(n):
        # Enviar texto a filtrar
        r.rpush(TEXTS_QUEUE, PHRASE)
        # Esperar resultado del filtro
        r.blpop(RESULTS_QUEUE)
    return time.perf_counter() - start


def make_iter_filter_redis():
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.sadd(INSULTS_KEY, INSULT)
    r.delete(TEXTS_QUEUE, RESULTS_QUEUE)
    def it():
        r.rpush(TEXTS_QUEUE, PHRASE)
        r.blpop(RESULTS_QUEUE)
    return it


def measure_filter_rabbitmq(n):
    # Publicador y consumidor para RabbitMQ
    conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    pub      = conn_pub.channel()
    pub.queue_declare(queue="text_queue", durable=True)
    conn_cb  = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    cb       = conn_cb.channel()
    result   = cb.queue_declare(queue='', exclusive=True)
    cbq      = result.method.queue
    cb.queue_purge(queue=cbq)

    start = time.perf_counter()
    for i in range(n):
        corr = str(uuid.uuid4())
        pub.basic_publish(
            exchange='', routing_key='text_queue',
            properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr),
            body=PHRASE
        )
        # Esperar respuesta correlacionada
        while True:
            method_frame, props, body = cb.basic_get(queue=cbq, auto_ack=True)
            if method_frame and props.correlation_id == corr:
                break
    conn_pub.close()
    conn_cb.close()
    return time.perf_counter() - start


def make_iter_filter_rabbitmq():
    conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    pub      = conn_pub.channel()
    pub.queue_declare(queue="text_queue", durable=True)
    conn_cb  = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    cb       = conn_cb.channel()
    result   = cb.queue_declare(queue='', exclusive=True)
    cbq      = result.method.queue
    cb.queue_purge(queue=cbq)
    def it():
        corr = str(uuid.uuid4())
        pub.basic_publish(
            exchange='', routing_key='text_queue',
            properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr),
            body=PHRASE
        )
        while True:
            method_frame, props, body = cb.basic_get(queue=cbq, auto_ack=True)
            if method_frame and props.correlation_id == corr:
                break
    return it

# ——— MAIN —————————————————————————————————————————————————

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mw",   choices=["xmlrpc","redis","rabbitmq","pyro"], required=True)
    parser.add_argument("--mode", choices=["service","filter"], required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n",        "--num",      type=int,   help="Número de peticiones")
    group.add_argument("--duration",            type=float, help="Duración en segundos para medir throughput")
    parser.add_argument("--csv", help="CSV de salida")
    args = parser.parse_args()

    # 1) Arrancar servicio o filtro
    procs = []
    if args.mode == "service":
        if args.mw == "xmlrpc":
            procs.append(start_xmlrpc_service())
        elif args.mw == "pyro":
            procs.append(start_pyro_ns()); procs.append(start_pyro_service())
        else:
            print("Modo service solo soporta xmlrpc o pyro"); sys.exit(1)
    else:
        if args.mw == "redis":
            procs.append(start_redis_filter())
        elif args.mw == "rabbitmq":
            procs.append(start_rabbitmq_filter())
        else:
            print("Modo filter solo soporta redis o rabbitmq"); sys.exit(1)
    time.sleep(0.5)

    # 2) Seleccionar funciones de benchmark
    service_funcs = {
        "xmlrpc": (measure_service_xmlrpc, make_iter_service_xmlrpc),
        "pyro":   (measure_service_pyro,   make_iter_service_pyro),
    }
    filter_funcs = {
        "redis":    (measure_filter_redis,    make_iter_filter_redis),
        "rabbitmq": (measure_filter_rabbitmq, make_iter_filter_rabbitmq),
    }

    meas_fn, iter_fn = (service_funcs if args.mode=="service" else filter_funcs)[args.mw]

    # 3) Ejecutar benchmark
    if args.duration is not None:
        it = iter_fn()
        print(f"Running {args.mode}/{args.mw} for {args.duration:.1f}s (throughput mode)…")
        start = time.perf_counter(); ops = 0
        while time.perf_counter() - start < args.duration:
            it(); ops += 1
        elapsed = time.perf_counter() - start; n = ops
    else:
        n = args.num
        print(f"Running {args.mode}/{args.mw} with {n} iterations…")
        elapsed = meas_fn(n)

    ops_per_s = n/elapsed if elapsed>0 else 0.0
    print(f"Time: {elapsed:.3f}s   Throughput: {ops_per_s:.1f} ops/s")

    # 4) Guardar CSV si se pide
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["mode","mw","num_or_duration","time_s","ops_per_s"])
            w.writerow([args.mode, args.mw, args.num or args.duration, f"{elapsed:.6f}", f"{ops_per_s:.2f}"])
        print(f"Results saved to {args.csv}")

    # 5) Terminar procesos arrancados
    for p in procs:
        p.terminate()
        p.wait()
