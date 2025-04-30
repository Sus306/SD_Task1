import xmlrpc.client
import time

# Lista de frases de ejemplo que contienen insultos y el comando especial "lista"
phrases = [
    "You are an idiota and a fool.",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_phrases(filter_server_url="http://127.0.0.1:8001"):
    """
    Envía cada frase al InsultFilter para que sea filtrada.
    Si la frase es "lista", solicita y muestra el historial de frases filtradas.
    """
    filter_service = xmlrpc.client.ServerProxy(filter_server_url, allow_none=True)
    
    for phrase in phrases:
        if phrase.strip().lower() == "lista":
            print("\n[Comando 'lista' detectado: solicitando historial de frases filtradas]")
            try:
                history = filter_service.get_filtered_texts()
                if not history:
                    print("No hay frases filtradas aún.")
                else:
                    print("Historial de frases filtradas:")
                    for idx, f in enumerate(history, 1):
                        print(f" {idx}. {f}")
            except Exception as e:
                print("Error al obtener historial:", e)
        else:
            print("\nFrase original:", phrase)
            try:
                filtered = filter_service.filter_phrase(phrase)
                print("Frase filtrada:", filtered)
            except Exception as e:
                print("Error al filtrar la frase:", e)
        time.sleep(2)  # Pausa antes de la siguiente iteración

if __name__ == "__main__":
    produce_phrases()
