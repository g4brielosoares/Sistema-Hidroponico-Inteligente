from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request, Response

from backend.config import Config
from backend.services.xml_service import XMLService

api_bp = Blueprint("api", __name__)
xml_service = XMLService()


# helper de autenticação de dispositivo

def require_device_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-API-KEY")
        if api_key != Config.DEVICE_API_KEY:
            return jsonify({"error": "Não autorizado (dispositivo)."}), 401
        return f(*args, **kwargs)
    return wrapper


# SENSORES 

@api_bp.get("/api/sensores")
def api_listar_sensores():
    sensores = xml_service.listar_sensores()
    return jsonify(sensores)


@api_bp.post("/api/sensores")
def api_cadastrar_sensor():
    data = request.json or {}
    try:
        xml_service.cadastrar_sensor(
            {
                "id": data["id"],
                "tipo": data["tipo"],
                "modelo": data.get("modelo"),
                "localizacao": data.get("localizacao"),
            }
        )
        return jsonify({"message": "Sensor cadastrado com sucesso."}), 201
    except KeyError:
        return jsonify({"error": "Campos obrigatórios: id, tipo."}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar XML: {str(e)}"}), 500


@api_bp.delete("/api/sensores")
def api_limpar_sensores():
    try:
        xml_service.limpar_sensores()
        return jsonify({"message": "Sensores limpos no XML."})
    except Exception as e:
        return jsonify({"error": f"Erro ao limpar sensores: {str(e)}"}), 500


# ATUADORES

@api_bp.get("/api/atuadores")
def api_listar_atuadores():
    atuadores = xml_service.listar_atuadores()
    return jsonify(atuadores)


@api_bp.post("/api/atuadores")
def api_cadastrar_atuador():
    data = request.json or {}
    try:
        xml_service.cadastrar_atuador(
            {
                "id": data["id"],
                "tipo": data["tipo"],
            }
        )
        return jsonify({"message": "Atuador cadastrado com sucesso."}), 201
    except KeyError:
        return jsonify({"error": "Campos obrigatórios: id, tipo."}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Erro ao salvar XML: {str(e)}"}), 500


@api_bp.delete("/api/atuadores")
def api_limpar_atuadores():
    try:
        xml_service.limpar_atuadores()
        return jsonify({"message": "Atuadores limpos no XML."})
    except Exception as e:
        return jsonify({"error": f"Erro ao limpar atuadores: {str(e)}"}), 500

# HISTÓRICO DE COMANDOS 

@api_bp.get("/api/atuadores/comandos")
def api_listar_comandos():
    """
    Lista o histórico de comandos de todos os atuadores.
    """
    comandos = xml_service.listar_comandos()
    return jsonify(comandos)


@api_bp.delete("/api/atuadores/comandos")
def api_limpar_comandos():
    """
    Limpa o histórico de comandos dos atuadores (mantendo os atuadores).
    """
    try:
        xml_service.limpar_historico_comandos()
        return jsonify({"message": "Histórico de comandos dos atuadores limpo no XML."})
    except Exception as e:
        return jsonify({"error": f"Erro ao limpar histórico de comandos: {str(e)}"}), 500


# LEITURAS / ALERTAS 

@api_bp.get("/api/leituras")
def api_listar_leituras():
    leituras = xml_service.listar_leituras()
    return jsonify(leituras)


@api_bp.delete("/api/leituras")
def api_limpar_leituras():
    try:
        xml_service.limpar_leituras()
        return jsonify({"message": "Histórico de leituras limpo no XML."})
    except Exception as e:
        return jsonify({"error": f"Erro ao limpar leituras: {str(e)}"}), 500


@api_bp.get("/api/alertas")
def api_listar_alertas():
    alertas = xml_service.listar_alertas()
    return jsonify(alertas)


# SIMULAÇÃO (gateway) 

@api_bp.post("/api/simulacao/tick")
@require_device_auth
def api_simulacao_tick():
    try:
        novas = xml_service.simular_ciclo()
        return jsonify({"novasLeituras": novas})
    except Exception as e:
        return jsonify({"error": f"Erro na simulação: {str(e)}"}), 500


@api_bp.post("/api/sync-pendentes")
@require_device_auth
def api_sync_pendentes():
    try:
        qtd = xml_service.sincronizar_pendentes()
        return jsonify({"sincronizadas": qtd})
    except Exception as e:
        return jsonify({"error": f"Erro na sincronização: {str(e)}"}), 500


# EXPORTAÇÃO XML (RF8) 

@api_bp.get("/api/exportar/xml")
def api_exportar_xml():
    """
    Query params:
      inicio=2025-10-24T00:00:00Z
      fim=2025-10-24T23:59:59Z
    ou apenas data 'YYYY-MM-DD'.
    """
    inicio_str = request.args.get("inicio")
    fim_str = request.args.get("fim")

    if not inicio_str or not fim_str:
        return jsonify({"error": "Parâmetros 'inicio' e 'fim' são obrigatórios."}), 400

    def parse_dt(s: str) -> datetime:
        # se vier só data (YYYY-MM-DD)
        if len(s) == 10:
            return datetime.fromisoformat(s + "T00:00:00+00:00")
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    try:
        dt_inicio = parse_dt(inicio_str)
        dt_fim = parse_dt(fim_str)
    except Exception:
        return jsonify({"error": "Formato de data inválido. Use ISO 8601."}), 400

    if dt_inicio > dt_fim:
        return jsonify({"error": "Data inicial não pode ser maior que a final."}), 400

    try:
        xml_bytes = xml_service.exportar_leituras_filtradas(dt_inicio, dt_fim)
        return Response(
            xml_bytes,
            mimetype="application/xml",
            headers={
                "Content-Disposition": "attachment; filename=leituras_filtradas.xml"
            },
        )
    except Exception as e:
        return jsonify({"error": f"Erro ao exportar XML: {str(e)}"}), 500
