import Pyro4
import time

# Lista de frases de ejemplo (algunas contienen insultos y el comando especial 'lista')
phrases = [
    "You are an idiota and a fool.",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_phrases():
    # Conectar al InsultFilter a través del Name Server
    ns = Pyro4.locateNS()
    filter_uri = ns.lookup("insult.filter")
    filter_service = Pyro4.Proxy(filter_uri)

    for phrase in phrases:
        text = phrase.strip()
        # Comando especial 'lista'
        if text.lower() == "lista":
            print("\n[Comando 'lista' detectado: solicitando historial de frases filtradas]")
            try:
                history = filter_service.filter_text(text)
            except Exception as e:
                print("Error al obtener historial:", e)
                time.sleep(3)
                continue

            if not history:
                print("No hay frases filtradas aún.")
            else:
                print("Historial de frases filtradas:")
                for idx, entry in enumerate(history, 1):
                    print(f" {idx}. {entry}")
        else:
            print("\nFrase original:", text)
            try:
                filtered = filter_service.filter_text(text)
                print("Frase filtrada:", filtered)
            except Exception as e:
                print("Error al filtrar la frase:", e)

        time.sleep(3)

if __name__ == "__main__":
    produce_phrases()
