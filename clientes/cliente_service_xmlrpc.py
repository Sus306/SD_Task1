# client_service_interactive.py

import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer
import threading

def recibir_insulto(insulto):
    print(f"Recibido insulto: {insulto}")
    return "OK"

def start_client_server(ip="127.0.0.1", port=9000):
    """
    Inicia el servidor XML-RPC que recibirá los insultos difundidos.
    """
    server = SimpleXMLRPCServer((ip, port), allow_none=True)
    server.register_function(recibir_insulto, "recibir_insulto")
    print(f"Cliente suscriptor del Service escuchando en {ip}:{port}...")
    server.serve_forever()

def main():
    # Arranca en un hilo el servidor para recibir insultos
    threading.Thread(target=start_client_server, daemon=True).start()
    
    # Conecta con el InsultService (asegúrate de que está en ejecución en el puerto 8000)
    service = xmlrpc.client.ServerProxy("http://127.0.0.1:8000", allow_none=True)
    
    # Suscribe este cliente al Service (usando la IP y puerto que escucha este cliente)
    response = service.subscribe("127.0.0.1", 9000)
    print("Respuesta de suscripción:", response)
    
    # Bucle interactivo para enviar insultos al Service
    while True:
        insult = input("Introduce un insulto para enviar al service (o 'salir' para terminar): ")
        if insult.lower() == 'salir':
            break
        response = service.add_insult(insult)
        print("Respuesta del service:", response)

if __name__ == "__main__":
    main()
