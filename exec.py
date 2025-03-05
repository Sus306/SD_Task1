import xmlrpc.server
import Pyro4
import redis
import pika
import threading
import time

# ---------------- XML-RPC Implementation ----------------
class InsultServiceXMLRPC:
    def __init__(self):
        self.insults = set()

    def add_insult(self, insult):
        if insult not in self.insults:
            self.insults.add(insult)
            return f"Insult '{insult}' added."
        return "Insult already exists."

    def get_insults(self):
        return list(self.insults)

# Run XML-RPC server
server = xmlrpc.server.SimpleXMLRPCServer(("localhost", 8000))
server.register_instance(InsultServiceXMLRPC())
threading.Thread(target=server.serve_forever, daemon=True).start()

# ---------------- PyRO Implementation ----------------
@Pyro4.expose
class InsultServicePyRO:
    def __init__(self):
        self.insults = set()

    def add_insult(self, insult):
        if insult not in self.insults:
            self.insults.add(insult)
            return f"Insult '{insult}' added."
        return "Insult already exists."

    def get_insults(self):
        return list(self.insults)

# Run PyRO server
daemon = Pyro4.Daemon()
uri = daemon.register(InsultServicePyRO)
print(f"PyRO Server running at {uri}")
threading.Thread(target=daemon.requestLoop, daemon=True).start()

# ---------------- Redis Implementation ----------------
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def add_insult_redis(insult):
    if not redis_client.sismember("insults", insult):
        redis_client.sadd("insults", insult)
        return f"Insult '{insult}' added."
    return "Insult already exists."

def get_insults_redis():
    return list(redis_client.smembers("insults"))

# ---------------- RabbitMQ Implementation ----------------
def insult_callback(ch, method, properties, body):
    insult = body.decode()
    print(f"Received insult: {insult}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='insults')
channel.basic_consume(queue='insults', on_message_callback=insult_callback)
th = threading.Thread(target=channel.start_consuming, daemon=True)
th.start()

# ---------------- Execution Script ----------------
if __name__ == "__main__":
    print("Running all services...")
    time.sleep(2)
    print("Services started. Now you can send insults and retrieve them.")
