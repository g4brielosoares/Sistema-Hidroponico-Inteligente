from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request, Response

from backend.config import Config
from backend.services.xml_service import XMLService
from backend.services.alert_service import avaliar_leitura
from backend.models.hidroponia import Leitura, ComandoAtuador

from backend.models.hidroponia import SistemaHidroponico

api_bp = Blueprint("api", __name__)
xml_service = XMLService()


# ---------- AUTENTICAÇÃO DISPOSITIVOS (RNF2) ----------

def require_api_key(func):
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if key != Config.DEVICE_API_KEY:
            return jsonify({"error": "Não autorizado"}), 401
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# ---------- RF1 + RF6 + RNF5: registrar leituras ----------

@api_bp.post("/leituras")
@require_api_key
def registrar_leitura():
    """
    Registra uma nova leitura. Se falhar ao salvar o XML,
    armazena em buffer local (leituras_pendentes.json).
    Body:
    {
      "sensorId": "s-ph-01",
      "dataHora": "2025-10-24T11:00:00Z",
      "valor": 6.4,
      "unidade": ""
    }
    """
    data = request.json

    leitura_dict = {
        "sensorId": data["sensorId"],
        "dataHora": data["dataHora"].replace("Z", "+00:00"),
        "valor": data["valor"],
        "unidade": data.get("unidade"),
        "criadoEm": datetime.utcnow().isoformat()
    }

    try:
        sistema = xml_service.load_from_file()
        nova_leitura = Leitura(
            sensor_id=leitura_dict["sensorId"],
            data_hora=datetime.fromisoformat(leitura_dict["dataHora"]),
            valor=Decimal(str(leitura_dict["valor"])),
            unidade=leitura_dict["unidade"],
        )
        sistema.leituras.append(nova_leitura)
        xml_service.save_to_file(sistema)
        return jsonify({"message": "Leitura registrada com sucesso"}), 201
    except Exception as e:
        xml_service.add_pending_leitura(leitura_dict)
        return jsonify({
            "message": "Leitura armazenada localmente (modo offline)",
            "detalhe": str(e)
        }), 202


# ---------- RF6 + RNF7: listar leituras (JSON) ----------

@api_bp.get("/leituras")
def listar_leituras():
    """
    Lista leituras, com opção de filtro por data:
    /api/leituras?data_inicio=2025-10-24&data_fim=2025-10-25
    """
    sistema = xml_service.load_from_file()
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    leituras = sistema.leituras

    if data_inicio:
        dt_ini = datetime.fromisoformat(data_inicio)
        leituras = [l for l in leituras if l.data_hora >= dt_ini]
    if data_fim:
        dt_fim = datetime.fromisoformat(data_fim)
        leituras = [l for l in leituras if l.data_hora <= dt_fim]

    sensores_map = {s.id: s for s in sistema.sensores}

    resposta = []
    for l in leituras:
        sensor = sensores_map.get(l.sensor_id)
        avaliacao = avaliar_leitura(sensor, l) if sensor else {"status": "desconhecido", "alerta": None}
        resposta.append(
            {
                "sensorId": l.sensor_id,
                "tipo": sensor.tipo if sensor else None,
                "unidade": l.unidade,
                "dataHora": l.data_hora.isoformat(),
                "valor": float(l.valor),
                "status": avaliacao["status"],
                "alerta": avaliacao["alerta"],
            }
        )

    return jsonify(resposta)


# ---------- RF8: exportar leituras em XML filtrado ----------

@api_bp.get("/exportar/xml")
def exportar_xml_filtrado():
    """
    Exporta leituras em formato XML, filtradas por data,
    mantendo a estrutura conforme o XSD.
    """
    sistema = xml_service.load_from_file()
    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")

    leituras = sistema.leituras
    if data_inicio:
        dt_ini = datetime.fromisoformat(data_inicio)
        leituras = [l for l in leituras if l.data_hora >= dt_ini]
    if data_fim:
        dt_fim = datetime.fromisoformat(data_fim)
        leituras = [l for l in leituras if l.data_hora <= dt_fim]

    # cria uma cópia rasa apenas mudando as leituras
    sistema_filtrado = SistemaHidroponico(
        id=sistema.id,
        meta=sistema.meta,
        sensores=sistema.sensores,
        leituras=leituras,
        atuadores=sistema.atuadores,
    )

    xml_bytes = xml_service.to_xml_bytes(sistema_filtrado)
    return Response(xml_bytes, mimetype="application/xml")


# ---------- RF4 + RF6: registrar comandos de atuadores ----------

@api_bp.post("/atuadores/comando")
@require_api_key
def registrar_comando_atuador():
    """
    Registra comando em um atuador (histórico de comandos).
    Body:
    {
      "atuadorId": "a-bomba-01",
      "dataHora": "2025-10-24T09:50:00Z",
      "acao": "desligar"
    }
    """
    data = request.json
    sistema = xml_service.load_from_file()

    atuador = next((a for a in sistema.atuadores if a.id == data["atuadorId"]), None)
    if not atuador:
        return jsonify({"error": "Atuador não encontrado"}), 404

    novo_cmd = ComandoAtuador(
        data_hora=datetime.fromisoformat(data["dataHora"].replace("Z", "+00:00")),
        acao=data["acao"],
    )
    atuador.comandos.append(novo_cmd)

    xml_service.save_to_file(sistema)

    return jsonify({"message": "Comando registrado com sucesso"}), 201


# ---------- RF5: listar alertas ----------

@api_bp.get("/alertas")
def listar_alertas():
    """
    Lista apenas leituras que estão fora da faixa ideal.
    """
    sistema = xml_service.load_from_file()
    sensores_map = {s.id: s for s in sistema.sensores}

    alertas = []
    for l in sistema.leituras:
        sensor = sensores_map.get(l.sensor_id)
        if not sensor:
            continue
        avaliacao = avaliar_leitura(sensor, l)
        if avaliacao["alerta"]:
            alertas.append(
                {
                    "sensorId": l.sensor_id,
                    "tipo": sensor.tipo,
                    "dataHora": l.data_hora.isoformat(),
                    "valor": float(l.valor),
                    "mensagem": avaliacao["alerta"],
                }
            )

    return jsonify(alertas)
