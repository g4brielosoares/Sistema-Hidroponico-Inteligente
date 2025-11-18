import os


class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    XML_SCHEMA_PATH = os.path.join(BASE_DIR, "xml", "hidroponia.xsd")
    XML_STORAGE_PATH = os.path.join(BASE_DIR, "xml", "exemplo_hidroponia.xml")
    PENDING_BUFFER_PATH = os.path.join(BASE_DIR, "xml", "leituras_pendentes.json")

    # Segurança (RNF2): API key simples para autenticar dispositivos IoT
    DEVICE_API_KEY = os.environ.get("DEVICE_API_KEY", "chave-dev-exemplo")

    SECRET_KEY = 123456789
