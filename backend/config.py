import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_DIR = os.path.join(BASE_DIR, "xml")

class Config:
    SECRET_KEY = "alguma-secret-key-qualquer"

    # caminhos usados pelo XMLService
    XML_SCHEMA_PATH = os.path.join(XML_DIR, "hidroponia.xsd")
    XML_DATA_PATH   = os.path.join(XML_DIR, "hidroponia.xml")
