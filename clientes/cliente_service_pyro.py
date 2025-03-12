import Pyro4
import threading

@Pyro4.expose
class InsultSubscriber(object):
    def receive_insult(self, insult):
        print("Insulto recibido:", insult)
        return "OK"

def start_subscriber(ip="127.0.0.1", port=9000):
    daemon = Pyro4.Daemon(ip, port)
    subscriber = InsultSubscriber()
    uri = daemon.register(subscriber)
    print("Cliente suscriptor listo. URI =", uri)
    
    # Suscribirse al InsultService
    ns = Pyro4.locateNS()
    service_uri = ns.lookup("insult.service")
    service = Pyro4.Proxy(service_uri)
    response = service.subscribe(str(uri))
    print("Respuesta de suscripción:", response)
    
    daemon.requestLoop()

if __name__ == "__main__":
    start_subscriber()
