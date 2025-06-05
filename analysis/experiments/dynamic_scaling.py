#!/usr/bin/env python3
import os
import argparse
import subprocess
import threading
import time
import uuid
import json
from math import ceil
from time import perf_counter

import pika
import requests  # Para consultar la API HTTP de RabbitMQ

# ————— Rutas y colas —————————————————————————————————————
# Ahora escalamos el **filtro** RabbitMQ, no el servicio
FILTER_SCRIPT = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 "..", "..", "insult_filter",
                 "insult_filter_rabbitmq.py")
)
RPC_QUEUE    = "text_queue"   # cola en la que el filtro escucha
# En el filtro RabbitMQ tu código usa text_queue para filtrar,
# pero aquí medimos RPC en text_queue:
FILTER_QUEUE = RPC_QUEUE

# ————— Parámetros de escalado dinámico basado en BACKLOG ——
CAPACITY       = 950      # msgs/s que soporta un filtro
CHECK_INTERVAL = 1.0      # cada cuántos segundos chequeamos backlog
MIN_WORKERS    = 1
MAX_WORKERS    = 10

# ————— Escalador dinámico —————————————————————————————————————
class DynamicScaler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.workers = []
        self.running = True
        self.mgmt_url = (
            "http://guest:guest@127.0.0.1:15672"
            "/api/queues/%2F/" + RPC_QUEUE
        )
        # Arranca al menos MIN_WORKERS filtros
        self._scale_to(MIN_WORKERS, initial=True)

    def run(self):
        while self.running:
            try:
                resp = requests.get(self.mgmt_url, timeout=1)
                data = resp.json()
                B = data.get("messages", 0)
                λ = data.get("message_stats", {}) \
                        .get("publish_details", {}) \
                        .get("rate", 0.0)
            except Exception:
                B, λ = 0, 0.0

            Tr = CHECK_INTERVAL
            N = ceil((B + λ * Tr) / (CAPACITY * Tr))
            desired = max(MIN_WORKERS, min(MAX_WORKERS, N))

            print(f"[debug] B={B}, λ={λ:.1f}, desired={desired}")

            self._scale_to(desired)
            time.sleep(CHECK_INTERVAL)

    def stop(self):
        self.running = False
        self._scale_to(0)

    def _scale_to(self, target, initial=False):
        # Arranca nuevos filtros si hace falta
        while len(self.workers) < target:
            # silencioso para no ver los prints del filtro
            p = subprocess.Popen(
                ["python3", FILTER_SCRIPT],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self.workers.append(p)
            print(f"[scale] (+) levantado filtro, total = {len(self.workers)}")

        # Para filtros de más
        while len(self.workers) > target:
            p = self.workers.pop()
            p.terminate()
            print(f"[scale] (–) parado filtro, total = {len(self.workers)}")

        if initial:
            print(f"[scale] iniciados {len(self.workers)} filtro(s) inicialmente")

# ————— Benchmark dinámico RPC sobre RabbitMQ ——————————————————————
def dynamic_benchmark(n_requests):
    """Envia n_requests RPC al filtro RabbitMQ y mide tiempo total procesando la ráfaga."""
    # 1) Arranca el escalador
    scaler = DynamicScaler()
    scaler.start()
    time.sleep(1)  # dejamos que arranque el primer filtro

    # 2) Abrimos conexiones publisher + callback queue
    conn_pub = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    pub      = conn_pub.channel()
    pub.queue_declare(queue=FILTER_QUEUE, durable=True)

    conn_cb    = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    cb         = conn_cb.channel()
    result     = cb.queue_declare(queue="", exclusive=True)
    callback_q = result.method.queue

    # 3) Warm-up (solo para inicializar a un filtro activo)
    warm = str(uuid.uuid4())
    pub.basic_publish(
        exchange="", routing_key=FILTER_QUEUE,
        properties=pika.BasicProperties(
            reply_to=callback_q,
            correlation_id=warm
        ),
        body="warmup"
    )
    # esperamos la respuesta del warm-up
    while True:
        m = cb.basic_get(queue=callback_q, auto_ack=True)
        if m[0] and m[1].correlation_id == warm:
            break

    # 4) **Publicación masiva**: meter toda la ráfaga sin esperar respuestas
    for i in range(n_requests):
        corr = str(i)
        pub.basic_publish(
            exchange="", routing_key=FILTER_QUEUE,
            properties=pika.BasicProperties(
                reply_to=callback_q,
                correlation_id=corr
            ),
            body="load_test"
        )

    # 5) Pausa para que el escalador detecte el backlog
    time.sleep(CHECK_INTERVAL + 0.1)

    # 6) Consumo + medición: leemos exactamente n_requests respuestas
    start = perf_counter()
    received = 0
    seen = set()
    while received < n_requests:
        m = cb.basic_get(queue=callback_q, auto_ack=True)
        if m[0]:
            cid = m[1].correlation_id
            if cid not in seen:
                seen.add(cid)
                received += 1
    elapsed = perf_counter() - start

    # 7) Teardown
    scaler.stop()
    scaler.join()
    conn_pub.close()
    conn_cb.close()

    return elapsed


# ————— Main ———————————————————————————————————————————————
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--requests", type=int, required=True,
                   help="Número total de llamadas RPC")
    args = p.parse_args()

    print(f"Lanzando dynamic benchmark con {args.requests} peticiones…")
    t = dynamic_benchmark(args.requests)
    print(f"Terminado en {t:.3f}s → {args.requests/t:.1f} ops/s")
