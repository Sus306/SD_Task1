#!/usr/bin/env python3
import uuid

import subprocess, time, threading, yaml, sys, signal, json
import xmlrpc.client
import redis
import pika
import Pyro4
from xmlrpc.server import SimpleXMLRPCServer
import shutil

# Track which middleware is active for printing
CURRENT_SERVICE_MW = None
LAST_XMLRPC = None
LAST_PYRO = None

class ServiceManager:
    def __init__(self, cfg_path="services.yaml"):
        self.cfg = yaml.safe_load(open(cfg_path))
        self.procs = {}

    def start(self, name):
        spec = self.cfg[name]
        if spec.get("type") == "process":
            exe = spec["cmd"][0]
            if shutil.which(exe) is None:
                print(f"[SM][ERROR] '{exe}' not found in PATH.")
                sys.exit(1)
            print(f"[SM] Starting {name}: {' '.join(spec['cmd'])}")
            # Sólo para insult_filter_xmlrpc dejamos la salida a pantalla,
            # el resto la silenciamos:
            if name == "insult_filter_xmlrpc":
                p = subprocess.Popen(spec["cmd"])
            else:
                p = subprocess.Popen(
                    spec["cmd"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            self.procs[name] = p
            time.sleep(0.5)

    def stop(self, name):
        p = self.procs.pop(name, None)
        if p:
            print(f"[SM] Stopping {name}")
            p.terminate()
            p.wait()

    def start_all(self):
        for name in self.cfg:
            self.start(name)

    def stop_all(self):
        for name in list(self.procs):
            self.stop(name)

# ---------- Global Listeners ----------

def start_xmlrpc_listener(port=9000):
    global LAST_XMLRPC
    LAST_XMLRPC = None
    server = SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True, logRequests=False)
    def _recv(insult):
        global LAST_XMLRPC
        if CURRENT_SERVICE_MW == 'xmlrpc' and insult != LAST_XMLRPC:
            print(f"\n[XMLRPC ←] {insult}")
            LAST_XMLRPC = insult
        return "ok"
    server.register_function(_recv, "recibir_insulto")
    server.serve_forever()


def start_redis_listener(channel="insults_channel"):
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    pub = r.pubsub(); pub.subscribe(channel)
    for msg in pub.listen():
        if msg.get("type") == 'message' and CURRENT_SERVICE_MW == 'redis':
            print(f"\n[REDIS ←] {msg['data']}")


def start_rabbitmq_listener(exchange="insult_broadcast"):
    conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = conn.channel()
    ch.exchange_declare(exchange=exchange, exchange_type='fanout')
    q = ch.queue_declare(queue='', exclusive=True).method.queue
    ch.queue_bind(exchange=exchange, queue=q)
    def on_msg(ch_, method, props, body):
        if CURRENT_SERVICE_MW == 'rabbitmq':
            try:
                data = json.loads(body)
                insult = data.get('insult', '')
            except:
                insult = body.decode()
            print(f"\n[RABBIT ←] {insult}")
    ch.basic_consume(queue=q, on_message_callback=on_msg, auto_ack=True)
    ch.start_consuming()


def start_pyro_listener():
    global LAST_PYRO
    LAST_PYRO = None
    class Subscriber:
        @Pyro4.expose
        def receive_insult(self, insult):
            global LAST_PYRO
            if CURRENT_SERVICE_MW == 'pyro' and insult != LAST_PYRO:
                print(f"\n[PYRO   ←] {insult}")
                LAST_PYRO = insult
    daemon = Pyro4.Daemon(host='127.0.0.1')
    try:
        ns = Pyro4.locateNS()
        uri = ns.lookup('insult.service')
        sub = Subscriber()
        daemon.register(sub, objectId='insult_sub')
        cb_uri = daemon.uriFor('insult_sub')
        Pyro4.Proxy(uri).subscribe(str(cb_uri))
        daemon.requestLoop()
    except Exception:
        return


def service_repl():
    global CURRENT_SERVICE_MW
    xmlrpc_cli = xmlrpc.client.ServerProxy('http://127.0.0.1:8000', allow_none=True)
    rcli = redis.Redis(host='localhost', port=6379, decode_responses=True)

    # --- Configuración RabbitMQ para RPC add_insult ---
    rmq_rpc_conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rmq_rpc_ch   = rmq_rpc_conn.channel()
    rmq_rpc_ch.queue_declare(queue='insult_rpc_queue', durable=True)
    responses = {}
    def _on_rpc_response(ch_, method, props, body):
        responses[props.correlation_id] = body.decode()
    rmq_rpc_ch.basic_consume(
        queue='amq.rabbitmq.reply-to',
        on_message_callback=_on_rpc_response,
        auto_ack=True
    )

    # --- Configuración RabbitMQ para broadcast (si aún quieres seguir difundiendo) ---
    rmq_pub_conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    rmq_pub_ch   = rmq_pub_conn.channel()
    rmq_pub_ch.exchange_declare(exchange='insult_broadcast', exchange_type='fanout')

    try:
        ns = Pyro4.locateNS()
        uri = ns.lookup('insult.service')
        pyro_cli = Pyro4.Proxy(uri)
    except Exception:
        pyro_cli = None

    clients = {
        'xmlrpc':  lambda t: print('→', xmlrpc_cli.add_insult(t)),
        'redis':   lambda t: rcli.sadd('insults', t),
        'rabbitmq': lambda t: _rabbitmq_add_insult(t),
    }
    if pyro_cli:
        clients['pyro'] = lambda t: print('→', pyro_cli.add_insult(t))

    def _rabbitmq_add_insult(insult_text):
        # publica via RPC y espera respuesta
        corr_id = str(uuid.uuid4())
        responses[corr_id] = None
        payload = json.dumps({"command": "add_insult", "data": insult_text})
        rmq_rpc_ch.basic_publish(
            exchange='',
            routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(
                reply_to='amq.rabbitmq.reply-to',
                correlation_id=corr_id,
                delivery_mode=1
            ),
            body=payload
        )
        # procesa eventos hasta recibir la respuesta
        while responses[corr_id] is None:
            rmq_rpc_conn.process_data_events()
        print('→', responses.pop(corr_id))

    print('\nAvailable clients:', ', '.join(clients.keys()))
    choice = input('Choose middleware> ').strip()
    while choice not in clients:
        choice = input('Invalid—choose one of ' + ', '.join(clients.keys()) + '> ').strip()

    CURRENT_SERVICE_MW = choice
    if choice == 'xmlrpc':
        xmlrpc_cli.subscribe('127.0.0.1', 9000)

    print(f"==> Sending insults via {choice}. Type 'cambiar' to switch, 'salir' to quit.")
    while True:
        line = input(f'[{choice}]> ').strip()
        if line == 'salir':
            CURRENT_SERVICE_MW = None
            # cerramos conexiones RabbitMQ
            rmq_rpc_conn.close()
            rmq_pub_conn.close()
            return
        if line == 'cambiar':
            CURRENT_SERVICE_MW = None
            rmq_rpc_conn.close()
            rmq_pub_conn.close()
            return service_repl()
        clients[choice](line)


# ---------- Filter REPL (unchanged) ----------

def filter_repl():
    import os
    global CURRENT_SERVICE_MW
    CURRENT_SERVICE_MW = None

    script_dir = os.path.dirname(os.path.abspath(__file__))

    xmlrpc_filter = xmlrpc.client.ServerProxy('http://127.0.0.1:8001', allow_none=True)
    rcli = redis.Redis(host='localhost', port=6379, decode_responses=True)
    TEXTQ, RESQ = 'texts_queue', 'filtered_texts'
    try:
        ns = Pyro4.locateNS()
        uri = ns.lookup('insult.filter')
        pyro_filter = Pyro4.Proxy(uri)
    except:
        pyro_filter = None

    def rmq_manual(text):
        conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        ch = conn.channel()
        ch.queue_declare(queue='text_queue', durable=True)
        corr = str(uuid.uuid4())
        result = ch.queue_declare(queue='', exclusive=True)
        cbq = result.method.queue
        response = {'v': None}
        def on_response(ch_, method, props, body):
            if props.correlation_id == corr:
                response['v'] = body.decode()
                ch_.basic_ack(delivery_tag=method.delivery_tag)
                ch_.stop_consuming()
        ch.basic_consume(queue=cbq, on_message_callback=on_response, auto_ack=False)
        ch.basic_publish(
            exchange='', routing_key='text_queue',
            properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr, delivery_mode=2),
            body=text
        )
        ch.start_consuming()
        conn.close()
        return response['v']

    def rmq_history():
        payload = rmq_manual('lista')
        try:
            return json.loads(payload)
        except:
            return []

    runners = {
        'xmlrpc':   ['python3', os.path.join(script_dir, 'insult_producer/insult_producer_xmlrpc.py')],
        'redis':    ['python3', os.path.join(script_dir, 'insult_producer/insult_producer_redis.py')],
        'rabbitmq': ['python3', os.path.join(script_dir, 'insult_producer/insult_producer_rabbitmq.py')],
    }
    if pyro_filter:
        runners['pyro'] = ['python3', os.path.join(script_dir, 'insult_producer/insult_producer_pyro.py')]

    clients = {
        'xmlrpc':   lambda t: print('→', xmlrpc_filter.filter_phrase(t)),
        'redis':    lambda t: (rcli.rpush(TEXTQ, t), print('→', rcli.blpop(RESQ)[1])),
        'rabbitmq': lambda t: print('→', rmq_manual(t)),
    }
    if pyro_filter:
        clients['pyro'] = lambda t: print('→', pyro_filter.filter_text(t))

    # ←—— **THIS** is the only change here:
    history_funcs = {
        'xmlrpc':   lambda: xmlrpc_filter.get_filtered_texts(),
        'redis':    lambda: rcli.lrange('filtered_history', 0, -1),
        'rabbitmq': rmq_history,
    }
    if pyro_filter:
        history_funcs['pyro'] = lambda: pyro_filter.get_filtered_texts()

    valid = list(runners.keys())
    # bucle externo: permite cambiar de middleware o salir del modo filter
    while True:
        print('Filter mode middlewares:', ', '.join(valid))
        mw = input('Filter> choose middleware> ').strip().lower()
        if mw == 'service':
            return
        if mw not in valid:
            print('Invalid; type "service" to switch back')
            continue

        # Ejecutar productor elegido
        print(f"--- Ejecutando productor {mw} ---")
        subprocess.run(runners[mw])
        print(f"--- Productor {mw} terminado; ahora en modo interactivo (pulsar 'salir' para salir del modo filter o 'cambiar' para volver a la lista de mw) ---")

        # bucle interno: filtrar, ver historial, cambiar middleware o salir
        while True:
            txt = input(f'[{mw}]> ').strip()
            cmd = txt.lower()
            if cmd == 'salir':
                # limpiamos si es necesario y salimos del modo filter
                try:
                    rcli.delete('insults')
                except:
                    pass
                CURRENT_SERVICE_MW = None
                return
            if cmd in ('cambiar', 'service'):
                # volvemos a la selección de middleware
                CURRENT_SERVICE_MW = None
                break
            if cmd == 'lista':
                history = history_funcs.get(mw, lambda: [])()
                if not history:
                    print("No hay frases filtradas aún.")
                else:
                    print("Historial de frases filtradas:")
                    for idx, entry in enumerate(history, 1):
                        print(f" {idx}. {entry}")
                continue

            # Filtrado manual de texto
            try:
                result = clients[mw](txt)
                # para rabbitmq, nuestra función devuelve directamente el texto filtrado
                if mw == 'rabbitmq' and result is not None:
                    print(f"→ {result}")
            except Exception as e:
                print("Error al filtrar:", e)
        # al hacer 'cambiar' rompemos el bucle interno y volvemos a la selección


# ---------- Main ----------

def main():
    mgr = ServiceManager()
    mgr.start_all()
    threading.Thread(target=start_xmlrpc_listener, daemon=True).start()
    threading.Thread(target=start_redis_listener, daemon=True).start()
    threading.Thread(target=start_rabbitmq_listener, daemon=True).start()
    threading.Thread(target=start_pyro_listener, daemon=True).start()
    time.sleep(1)
    while True:
        mode = input("Enter mode ('service','filter','exit'): ").strip()
        if mode == 'service':
            service_repl()
        elif mode == 'filter':
            filter_repl()
        elif mode == 'exit':
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.flushdb()
            break
        else:
            print('Invalid mode')
    mgr.stop_all()

if __name__ == '__main__':
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    main()
