import time
import threading
import uuid
import json
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

import pytest
import redis
import pika
import Pyro4

@pytest.mark.usefixtures("start_framework")
class TestXMLRPC:
    @classmethod
    def setup_class(cls):
        cls.svc = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
        cls.flt = xmlrpc.client.ServerProxy("http://127.0.0.1:8001", allow_none=True)
        cls.received = []
        def recv(i):
            cls.received.append(i)
            return "OK"
        cls.server = SimpleXMLRPCServer(("127.0.0.1", 9010), allow_none=True, logRequests=False)
        cls.server.register_function(recv, "recibir_insulto")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.svc.subscribe("127.0.0.1", 9010)

    def test_no_duplicates(self):
        insult = "unittest_rpc"
        self.svc.add_insult(insult)
        self.svc.add_insult(insult)
        ins = self.svc.get_insults()
        assert ins.count(insult) == 1

    def test_broadcast(self):
        # Esperar hasta obtener un mensaje de tipo 'message'
        end = time.time() + 7
        msg = None
        while time.time() < end:
            if self.received:
                msg = self.received[0]
                break
            time.sleep(0.5)
        assert msg, "No llegó broadcast XMLRPC"
        assert msg in self.svc.get_insults()

    def test_filter(self):
        insult = "unittest_rpc"
        out = self.flt.filter_phrase(f"Hola {insult}")
        assert "***" in out

@pytest.mark.usefixtures("start_framework")
class TestRedis:
    @classmethod
    def setup_class(cls):
        cls.cli = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    def test_no_duplicates(self):
        ins = "unittest_redis"
        self.cli.sadd("insults", ins)
        self.cli.sadd("insults", ins)
        lst = list(self.cli.smembers("insults"))
        assert lst.count(ins) == 1

    def test_broadcast(self):
        ps = self.cli.pubsub()
        ps.subscribe("insults_channel")
        # descartar subscribe inicial
        start = time.time()
        msg = None
        while time.time() < start + 7:
            m = ps.get_message(timeout=1)
            if m and m.get("type") == "message":
                msg = m
                break
        ps.close()
        assert msg and msg["data"], f"No llegó broadcast Redis ({msg})"

    def test_filter(self):
        txt = "Texto unittest_redis"
        self.cli.rpush("texts_queue", txt)
        pair = self.cli.blpop("filtered_texts", timeout=7)
        assert pair is not None and "***" in pair[1]

@pytest.mark.usefixtures("start_framework")
class TestRabbitMQ:
    @classmethod
    def setup_class(cls):
        cls.conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        cls.ch   = cls.conn.channel()
        cls.rpc_q = "insult_rpc_queue"
        cls.ch.queue_declare(queue=cls.rpc_q, durable=True)

    def rpc_call(self, cmd, data):
        corr = str(uuid.uuid4())
        res  = self.ch.queue_declare(queue="", exclusive=True)
        cbq  = res.method.queue
        out  = {}
        def on_resp(ch, method, props, body):
            if props.correlation_id == corr:
                out["v"] = json.loads(body)
                ch.stop_consuming()
        self.ch.basic_consume(queue=cbq, on_message_callback=on_resp, auto_ack=True)
        req = {"command": cmd, "data": data}
        self.ch.basic_publish(
            exchange="", routing_key=self.rpc_q,
            properties=pika.BasicProperties(reply_to=cbq, correlation_id=corr),
            body=json.dumps(req)
        )
        # dejar un momento al servicio
        time.sleep(0.5)
        self.ch.start_consuming()
        return out.get("v")

    def test_no_duplicates(self):
        ins = "unittest_rmq"
        self.rpc_call("add_insult", ins)
        self.rpc_call("add_insult", ins)
        lst = self.rpc_call("get_insults", None) or []
        assert ins in lst

    def test_broadcast(self):
        rec = []
        info = self.ch.queue_declare(queue="", exclusive=True)
        qn = info.method.queue
        self.ch.queue_bind(exchange="insult_broadcast", queue=qn)
        def cb(ch, m, p, b):
            rec.append(json.loads(b).get("insult"))
            ch.stop_consuming()
        self.ch.basic_consume(queue=qn, on_message_callback=cb, auto_ack=True)
        # procesar eventos hasta hallar uno o tiempo
        end = time.time() + 7
        while time.time() < end and not rec:
            self.conn.process_data_events(time_limit=1)
        assert rec, "No llegó broadcast RabbitMQ"

    def test_filter(self):
        corr = str(uuid.uuid4())
        resq = self.ch.queue_declare(queue="", exclusive=True).method.queue
        out  = {}
        def on_f(ch, m, p, b):
            if p.correlation_id == corr:
                out["v"] = b.decode()
                ch.stop_consuming()
        self.ch.basic_consume(queue=resq, on_message_callback=on_f, auto_ack=True)
        self.ch.queue_declare(queue="text_queue", durable=True)
        self.ch.basic_publish(
            exchange="", routing_key="text_queue",
            properties=pika.BasicProperties(reply_to=resq, correlation_id=corr),
            body=f"Hola unittest_rmq"
        )
        # procesar eventos para respuesta
        end = time.time() + 7
        while time.time() < end and "v" not in out:
            self.conn.process_data_events(time_limit=1)
        assert "***" in out.get("v", "")

@pytest.mark.usefixtures("start_framework")
class TestPyro:
    @classmethod
    def setup_class(cls):
        ns = Pyro4.locateNS()
        cls.svc = Pyro4.Proxy(ns.lookup("insult.service"))
        cls.flt = Pyro4.Proxy(ns.lookup("insult.filter"))
        cls.received = []
        class Sub:
            @Pyro4.expose
            def receive_insult(self, i):
                cls.received.append(i)
        cls.daemon = Pyro4.Daemon()
        cb = cls.daemon.register(Sub())
        cls.svc.subscribe(str(cb))
        cls.th = threading.Thread(target=cls.daemon.requestLoop, daemon=True)
        cls.th.start()

    def test_no_duplicates(self):
        ins = "unittest_pyro"
        self.svc.add_insult(ins)
        self.svc.add_insult(ins)
        lst = self.svc.get_insults()
        assert lst.count(ins) == 1

    def test_broadcast(self):
        end = time.time() + 7
        while time.time() < end and not self.received:
            time.sleep(0.5)
        assert self.received and self.received[0] in self.svc.get_insults()

    def test_filter(self):
        out = self.flt.filter_text("Hola unittest_pyro")
        assert "***" in out
