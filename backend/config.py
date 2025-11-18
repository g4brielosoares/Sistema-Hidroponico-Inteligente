import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_DIR = os.path.join(BASE_DIR, "xml")


class Config:
    SECRET_KEY = "uma-secret-key-qualquer"

    # arquivos principais
    XML_SCHEMA_PATH = os.path.join(XML_DIR, "hidroponia.xsd")
    XML_DATA_PATH = os.path.join(XML_DIR, "hidroponia.xml")

    # arquivo de leituras pendentes (fila offline)
    XML_PENDING_PATH = os.path.join(XML_DIR, "leituras_pendentes.xml")

    # chave de autenticação dos "dispositivos" (gateway/simulador)
    DEVICE_API_KEY = "MEU_TOKEN_DISPOSITIVO_SUPER_SECRETO"
