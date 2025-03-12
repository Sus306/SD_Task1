# client_filter.py

import xmlrpc.client

def main():
    filter_service = xmlrpc.client.ServerProxy("http://127.0.0.1:8001", allow_none=True)
    # Frase de ejemplo para filtrar
    while True:
        phrase = input("Introduce una frase con un insulto (o 'salir' para terminar): ")
        if phrase.lower() == 'salir':
            break
        filtered = filter_service.filter_phrase(phrase)
        print("Frase filtrada:", filtered)

if __name__ == "__main__":
    main()
