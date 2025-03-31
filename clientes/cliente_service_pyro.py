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

    threading.Thread(target=daemon.requestLoop, daemon=True).start()

    # Ahora el cliente puede enviar insults al servei manualment
    while True:
        insult = input("Introduce un insulto nuevo (o 'salir' para terminar): ")
        if insult.lower() == 'salir':
            break
        response = service.add_insult(insult)
        print("Respuesta del InsultService:", response)

if __name__ == "__main__":
    import threading
    start_subscriber()
