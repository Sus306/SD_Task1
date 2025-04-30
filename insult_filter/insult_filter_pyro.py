import Pyro4
import threading
import redis
import time
import re

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
            time.sleep(10)

    @Pyro4.expose
    def filter_text(self, text):
        """
        Filtra la frase reemplazando insultos por '***'.
        Si el texto es 'lista', devuelve el historial de frases filtradas.
        """
        text_clean = text.strip().lower()
        if text_clean == 'lista':
            # Devuelve historial completo
            return self.filtered_texts

        # Refresh the insult list on every call
        self.insults = set(self.redis_client.smembers('insults'))
        filtered_text = text
        for insult in self.insults:
            filtered_text = re.sub(re.escape(insult), "***", filtered_text, flags=re.IGNORECASE)
        self.filtered_texts.append(filtered_text)
        return filtered_text

    @Pyro4.expose
    def get_filtered_texts(self):
        """
        Devuelve todas las frases filtradas hasta el momento.
        """
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
