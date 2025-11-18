from decimal import Decimal
from backend.models.hidroponia import Leitura, Sensor

# Faixas sugeridas por tipo (RF5)
FAIXAS = {
    "pH": (Decimal("4.5"), Decimal("7.5")),
    "EC": (Decimal("0.5"), Decimal("3.0")),
    "temperatura": (Decimal("10"), Decimal("35")),
    "nível": (Decimal("0"), Decimal("100")),
    "luminosidade": (Decimal("0"), Decimal("200000")),
}


def avaliar_leitura(sensor: Sensor, leitura: Leitura) -> dict:
    """
    Retorna um dicionário com status e mensagem de alerta (se houver).
    """
    faixa = FAIXAS.get(sensor.tipo)
    if faixa is None:
        return {"status": "desconhecido", "alerta": None}

    minimo, maximo = faixa

    if leitura.valor < minimo:
        return {
            "status": "critico-baixo",
            "alerta": f"{sensor.tipo} abaixo do ideal ({leitura.valor} < {minimo})",
        }

    if leitura.valor > maximo:
        return {
            "status": "critico-alto",
            "alerta": f"{sensor.tipo} acima do ideal ({leitura.valor} > {maximo})",
        }

    return {"status": "ok", "alerta": None}
