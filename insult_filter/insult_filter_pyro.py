import Pyro4

@Pyro4.expose
class InsultFilterPyRO:
    def __init__(self):
        self.filtered_texts = []

    def filter_text(self, text):
        filtered_text = text.replace("insult", "CENSORED")
        self.filtered_texts.append(filtered_text)
        return filtered_text

    def get_filtered_texts(self):
        return self.filtered_texts

daemon = Pyro4.Daemon()
uri = daemon.register(InsultFilterPyRO)
print(f"PyRO Filter Service running at {uri}")
daemon.requestLoop()