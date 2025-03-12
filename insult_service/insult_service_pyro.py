import Pyro4
import threading
import time
import random

@Pyro4.expose
class InsultService(object):
    def __init__(self):
        # Almacenamos los insultos en un set (para evitar duplicados)
        self.insults = set()
        # Lista de suscriptores (se almacenan las URIs de los clientes, ej. "PYRO:...@IP:puerto")
        self.subscribers = []
        # Iniciamos el difusor en un hilo en segundo plano
        threading.Thread(target=self._broadcaster, daemon=True).start()

    def add_insult(self, insult):
        """
        Recibe un insulto de forma remota y lo almacena si no existe.
        """
        if insult not in self.insults:
            self.insults.add(insult)
            print(f"Insulto agregado: {insult}")
            return f"Insulto '{insult}' agregado correctamente."
        else:
            return f"El insulto '{insult}' ya existe."

    def get_insults(self):
        """
        Devuelve la lista de insultos almacenados.
        """
        return list(self.insults)

    def subscribe(self, subscriber_uri):
        """
        Registra un suscriptor a partir de su URI Pyro.
        """
        if subscriber_uri not in self.subscribers:
            self.subscribers.append(subscriber_uri)
            print(f"Suscriptor agregado: {subscriber_uri}")
            return f"Suscriptor {subscriber_uri} agregado correctamente."
        return f"El suscriptor {subscriber_uri} ya estaba registrado."

    def _broadcaster(self):
        """
        Cada 5 segundos, difunde un insulto aleatorio a todos los suscriptores.
        Si algún suscriptor falla, se elimina de la lista.
        """
        while True:
            time.sleep(5)
            if self.insults and self.subscribers:
                insult = random.choice(list(self.insults))
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
    # Configuramos Pyro para que use pickle si es necesario
    Pyro4.config.SERIALIZER = "pickle"
    daemon = Pyro4.Daemon("127.0.0.1")  # O la IP que prefieras
    ns = Pyro4.locateNS()  # Asume que el Name Server ya está corriendo
    service = InsultService()
    uri = daemon.register(service)
    ns.register("insult.service", uri)
    print("InsultService listo. URI =", uri)
    daemon.requestLoop()

if __name__ == "__main__":
    main()
