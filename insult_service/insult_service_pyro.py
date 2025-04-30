import Pyro4
import threading
import redis
import random
import time

@Pyro4.expose
class InsultService(object):
    def __init__(self):
        # Connexió a Redis
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        # Llista de subscriptors
        self.subscribers = []
        # Difusor iniciat
        threading.Thread(target=self._broadcaster, daemon=True).start()

    def add_insult(self, insult):
        """
        Guarda l'insult a Redis
        """
        added = self.redis_client.sadd("insults", insult)
        if added:
            print(f"Insulto '{insult}' agregado correctamente a Redis.")
            return f"Insulto '{insult}' agregado correctamente a Redis."
        else:
            return f"El insulto '{insult}' ya existe en Redis."

    def get_insults(self):
        """
        Recupera insults guardats a Redis.
        """
        return list(self.redis_client.smembers("insults"))

    def subscribe(self, subscriber_uri):
        if subscriber_uri not in self.subscribers:
            self.subscribers.append(subscriber_uri)
            print(f"Suscriptor agregado: {subscriber_uri}")
            return f"Suscriptor {subscriber_uri} agregado correctamente."
        return f"El suscriptor {subscriber_uri} ya estaba registrado."

    def _broadcaster(self):
        """
        Difunde insults guardats en Redis als subscriptors cada 5 segons.
        """
        while True:
            time.sleep(5)
            insults = list(self.redis_client.smembers("insults"))
            if insults and self.subscribers:
                insult = random.choice(insults)
                print(f"Broadcasting insult: {insult}")
                active_subscribers = []
                for uri in self.subscribers:
                    try:
                        subscriber = Pyro4.Proxy(uri)
                        subscriber.receive_insult(insult)
                        active_subscribers.append(uri)
                    except Exception as e:
                        print(f"Error enviando a {uri}: {e}")
                self.subscribers = active_subscribers

def main():
    Pyro4.config.SERIALIZER = "serpent"
    daemon = Pyro4.Daemon("127.0.0.1")
    ns     = Pyro4.locateNS()
    service= InsultService()
    uri    = daemon.register(service)
    ns.register("insult.service", uri)
    print("InsultService listo. URI =", uri)

    # Sólo UN hilo broadcaster
    

    daemon.requestLoop()

if __name__ == "__main__":
    main()
