import Pyro4
import threading
import redis
import time

@Pyro4.expose
class InsultFilterPyRO(object):
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.insults = set()
        self.filtered_texts = []
        threading.Thread(target=self.update_insults_periodically, daemon=True).start()

    def update_insults(self):
        self.insults = set(self.redis_client.smembers('insults'))

    def update_insults_periodically(self):
        while True:
            self.update_insults()
            print("Insults updated from Redis:", self.insults)
            time.sleep(10)  # Actualitza cada 10 segons

    @Pyro4.expose
    def filter_text(self, text):
        filtered_text = text
        for insult in self.insults:
            filtered_text = filtered_text.replace(insult, "***")
        self.filtered_texts.append(filtered_text)
        return filtered_text

    @Pyro4.expose
    def get_filtered_texts(self):
        return self.filtered_texts

def main():
    Pyro4.config.SERIALIZER = "serpent"
    daemon = Pyro4.Daemon("127.0.0.1")
    ns = Pyro4.locateNS()
    uri = daemon.register(InsultFilterPyRO())
    ns.register("insult.filter", uri)
    print(f"Pyro Filter Service running at {uri}")
    daemon.requestLoop()

if __name__ == "__main__":
    main()