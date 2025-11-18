from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class Sensor:
    id: str
    tipo: str            # pH, EC, temperatura, nível, luminosidade
    unidade: str
    modelo: Optional[str] = None
    localizacao: Optional[str] = None


@dataclass
class Leitura:
    sensor_id: str       # referência ao Sensor.id (IDREF)
    data_hora: datetime
    valor: Decimal
    unidade: Optional[str] = None


@dataclass
class ComandoAtuador:
    data_hora: datetime
    acao: str            # ligar, desligar, dosarNutriente, etc.


@dataclass
class Atuador:
    id: str
    tipo: str
    comandos: List[ComandoAtuador]


@dataclass
class MetaSistema:
    nome: str
    local: str
    versao: Optional[str] = None


@dataclass
class SistemaHidroponico:
    id: str
    meta: MetaSistema
    sensores: List[Sensor]
    leituras: List[Leitura]
    atuadores: List[Atuador]