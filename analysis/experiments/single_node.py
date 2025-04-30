#!/usr/bin/env python3
"""
single_node.py

Mide throughput de un solo nodo (Service o Filter)
para N peticiones (--num) o durante un tiempo fijo (--duration)
sobre cada middleware.
"""

import time
import argparse
import csv
import uuid
import json
import xmlrpc.client
import redis
import pika
import Pyro4
import re

# Parámetros
INSULT = "bench_insult"
PHRASE = f"Hello {INSULT} world"

# ——— Medición clásica para N peticiones ——————————————————————————————

def measure_service_xmlrpc(n):
    cli = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
    cli.add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        cli.add_insult(f"{INSULT}_{i}")
    return time.perf_counter() - start

def measure_service_redis(n):
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.sadd("insults", INSULT)
    start = time.perf_counter()
    for i in range(n):
        r.sadd("insults", f"{INSULT}_{i}")
    return time.perf_counter() - start

def measure_service_rabbitmq(n):
    conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    ch_pub   = conn_pub.channel()
    # Declaramos la cola como durable=True (coincide con el servicio)
    ch_pub.queue_declare(queue="insult_rpc_queue", durable=True)

    # Consumidor sobre direct-reply-to
    responses = {}
    def on_response(ch, method, props, body):
        responses[props.correlation_id] = True

    ch_pub.basic_consume(
        queue='amq.rabbitmq.reply-to',
        on_message_callback=on_response,
        auto_ack=True
    )

    # Warm-up: drenar la primera respuesta
    corr0 = str(uuid.uuid4())
    ch_pub.basic_publish(
        exchange='',
        routing_key='insult_rpc_queue',
        properties=pika.BasicProperties(
            reply_to='amq.rabbitmq.reply-to',
            correlation_id=corr0,
            delivery_mode=1
        ),
        body=json.dumps({"command": "add_insult", "data": "warmup"})
    )
    while corr0 not in responses:
        conn_pub.process_data_events()

    # Benchmark real
    start = time.perf_counter()
    for i in range(n):
        corr = str(uuid.uuid4())
        responses[corr] = False
        ch_pub.basic_publish(
            exchange='',
            routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(
                reply_to='amq.rabbitmq.reply-to',
                correlation_id=corr,
                delivery_mode=1
            ),
            body=json.dumps({"command": "add_insult", "data": f"bench_{i}"})
        )
        # esperamos nuestra respuesta
        while not responses[corr]:
            conn_pub.process_data_events()
    elapsed = time.perf_counter() - start

    conn_pub.close()
    return elapsed


def measure_service_pyro(n):
    ns   = Pyro4.locateNS()
    svc  = Pyro4.Proxy(ns.lookup("insult.service"))
    svc.add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        svc.add_insult(f"{INSULT}_{i}")
    return time.perf_counter() - start

def measure_filter_xmlrpc(n):
    flt = xmlrpc.client.ServerProxy("http://127.0.0.1:8001", allow_none=True)
    xmlrpc.client.ServerProxy("http://127.0.0.1:8000").add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        flt.filter_phrase(PHRASE)
    return time.perf_counter() - start

def measure_filter_redis(n):
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.sadd("insults", INSULT)
    TEXTQ, RESQ = "texts_queue", "filtered_texts"
    r.delete(TEXTQ, RESQ)
    start = time.perf_counter()
    for i in range(n):
        r.rpush(TEXTQ, PHRASE)
        r.blpop(RESQ)
    return time.perf_counter() - start

def measure_filter_rabbitmq(n):
    conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    pub = conn_pub.channel()
    pub.queue_declare(queue="insult_rpc_queue", durable=True)
    conn_cb = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    cb = conn_cb.channel()
    res = cb.queue_declare(queue="", exclusive=True)
    cbq = res.method.queue
    cb.queue_purge(queue=cbq)

    # warmup
    warm_id = str(uuid.uuid4())
    pub.basic_publish(
        exchange='', routing_key='insult_rpc_queue',
        properties=pika.BasicProperties(
            reply_to=cbq,
            correlation_id=warm_id,
            delivery_mode=1
        ),
        body=json.dumps({"command":"get_insults","data":None})
    )
    while True:
        method, props, body = cb.basic_get(queue=cbq, auto_ack=True)
        if method and props.correlation_id == warm_id:
            break

    start = time.perf_counter()
    for i in range(n):
        corr = str(uuid.uuid4())
        pub.basic_publish(
            exchange='', routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr),
            body=PHRASE
        )
        while True:
            method, props, body = cb.basic_get(queue=cbq, auto_ack=True)
            if method and props.correlation_id == corr:
                break
    conn_pub.close(); conn_cb.close()
    return time.perf_counter() - start

def measure_filter_pyro(n):
    ns   = Pyro4.locateNS()
    flt  = Pyro4.Proxy(ns.lookup("insult.filter"))
    Pyro4.Proxy(ns.lookup("insult.service")).add_insult(INSULT)
    start = time.perf_counter()
    for i in range(n):
        flt.filter_text(PHRASE)
    return time.perf_counter() - start

# ——— Generadores para modo duration ——————————————————————————————————

def make_iter(mode, mw):
    if mode=="service" and mw=="xmlrpc":
        cli = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
        cli.add_insult(INSULT)
        return lambda: cli.add_insult(INSULT)
    if mode=="service" and mw=="redis":
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.sadd("insults", INSULT)
        return lambda: r.sadd("insults", INSULT)
    if mode=="service" and mw=="rabbitmq":
        # reutiliza la lógica de direct-reply-to warmup
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        pub = conn.channel(); pub.queue_declare(queue="insult_rpc_queue", durable=False)
        responses = {}
        def on_resp(ch, meth, props, body): responses[props.correlation_id]=True
        pub.basic_consume(queue='amq.rabbitmq.reply-to', on_message_callback=on_resp, auto_ack=True)
        # warmup
        c0=str(uuid.uuid4())
        pub.basic_publish(exchange='', routing_key='insult_rpc_queue',
                          properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to', correlation_id=c0, delivery_mode=1),
                          body=json.dumps({"command":"add_insult","data":"warmup"}))
        while c0 not in responses: conn.process_data_events()
        return lambda: (
            lambda corr=str(uuid.uuid4()): (
                responses.setdefault(corr, False),
                pub.basic_publish(exchange='', routing_key='insult_rpc_queue',
                                  properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to', correlation_id=corr, delivery_mode=1),
                                  body=json.dumps({"command":"add_insult","data":"bench"})),
                # espera respuesta
                (_ for _ in iter(lambda: None, None) if not responses[corr]).throw(SystemExit)  # hack para bloquear
            )
        )()[2]
    if mode=="service" and mw=="pyro":
        ns=Pyro4.locateNS(); svc=Pyro4.Proxy(ns.lookup("insult.service")); svc.add_insult(INSULT)
        return lambda: svc.add_insult(INSULT)
    if mode=="filter" and mw=="xmlrpc":
        flt = xmlrpc.client.ServerProxy("http://127.0.0.1:8001", allow_none=True)
        xmlrpc.client.ServerProxy("http://127.0.0.1:8000").add_insult(INSULT)
        return lambda: flt.filter_phrase(PHRASE)
    if mode=="filter" and mw=="redis":
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.sadd("insults", INSULT)
        TEXTQ, RESQ = "texts_queue", "filtered_texts"
        r.delete(TEXTQ, RESQ)
        return lambda: (r.rpush(TEXTQ, PHRASE), r.blpop(RESQ))
    if mode=="filter" and mw=="rabbitmq":
        # similar al servicio RabbitMQ
        conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        pub = conn_pub.channel(); pub.queue_declare(queue="insult_rpc_queue", durable=True)
        conn_cb = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        cb = conn_cb.channel(); res=cb.queue_declare(queue="", exclusive=True); cbq=res.method.queue; cb.queue_purge(queue=cbq)
        return lambda corr=str(uuid.uuid4()): (
            pub.basic_publish(exchange='', routing_key='insult_rpc_queue',
                              properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr),
                              body=PHRASE),
            # espera
            next(_ for _ in iter(lambda: cb.basic_get(queue=cbq, auto_ack=True), None) if _[1].correlation_id==corr)
        )[1]
    if mode=="filter" and mw=="pyro":
        ns=Pyro4.locateNS(); flt=Pyro4.Proxy(ns.lookup("insult.filter"))
        Pyro4.Proxy(ns.lookup("insult.service")).add_insult(INSULT)
        return lambda: flt.filter_text(PHRASE)

    raise RuntimeError(f"Modo {mode}/{mw} no soportado")


# ——— MAIN —————————————————————————————————————————————————

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["service","filter"], required=True)
    parser.add_argument("--mw",   choices=["xmlrpc","redis","rabbitmq","pyro"], required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", "--num",      type=int,   help="Número de peticiones")
    group.add_argument("--duration",       type=float, help="Duración en segundos para medir throughput")
    parser.add_argument("--csv", help="Fichero CSV de salida")
    args = parser.parse_args()

    if args.duration:
        it = make_iter(args.mode, args.mw)
        print(f"Running {args.mode}/{args.mw} for {args.duration:.1f}s (throughput mode)…")
        start = time.perf_counter()
        ops = 0
        while time.perf_counter() - start < args.duration:
            it()
            ops += 1
        elapsed = time.perf_counter() - start
        n = ops
    else:
        # medida clásica
        fn = {
            "service": {
                "xmlrpc": measure_service_xmlrpc,
                "redis":  measure_service_redis,
                "rabbitmq": measure_service_rabbitmq,
                "pyro":   measure_service_pyro
            },
            "filter": {
                "xmlrpc": measure_filter_xmlrpc,
                "redis":  measure_filter_redis,
                "rabbitmq": measure_filter_rabbitmq,
                "pyro":   measure_filter_pyro
            }
        }[args.mode][args.mw]
        n = args.num
        print(f"Running {args.mode}/{args.mw} with {n} iterations…")
        elapsed = fn(n)

    ops_per_s = n / elapsed if elapsed>0 else 0.0
    print(f"Time: {elapsed:.3f}s   Throughput: {ops_per_s:.1f} ops/s")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["mode","mw","n","time_s","ops_per_s"])
            writer.writerow([args.mode, args.mw, n, f"{elapsed:.6f}", f"{ops_per_s:.2f}"])
        print(f"Results saved to {args.csv}")
