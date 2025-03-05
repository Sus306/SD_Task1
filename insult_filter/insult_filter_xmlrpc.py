import xmlrpc.server

class InsultFilterXMLRPC:
    def __init__(self):
        self.filtered_texts = []

    def filter_text(self, text):
        filtered_text = text.replace("insult", "CENSORED")
        self.filtered_texts.append(filtered_text)
        return filtered_text

    def get_filtered_texts(self):
        return self.filtered_texts

server = xmlrpc.server.SimpleXMLRPCServer(("localhost", 8001))
server.register_instance(InsultFilterXMLRPC())
print("XML-RPC Filter Service running on port 8001...")
server.serve_forever()