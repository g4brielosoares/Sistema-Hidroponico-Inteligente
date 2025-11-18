from flask import Blueprint, jsonify, request

from backend.services.xml_service import XMLService


api_bp = Blueprint("api", __name__)
xml_service = XMLService()


# -------- SENSORES --------

@api_bp.get("/api/sensores")
def api_listar_sensores():
    sensores = xml_service.listar_sensores()
    return jsonify(sensores)


@api_bp.post("/api/sensores")
def api_cadastrar_sensor():
    data = request.json
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


# -------- ATUADORES --------

@api_bp.get("/api/atuadores")
def api_listar_atuadores():
    atuadores = xml_service.listar_atuadores()
    return jsonify(atuadores)


@api_bp.post("/api/atuadores")
def api_cadastrar_atuador():
    data = request.json
    try:
        xml_service.cadastrar_atuador(
            {
                "id": data["id"],
                "tipo": data["tipo"],
            }
        )
        return jsonify({"message": "Atuador cadastrado com sucesso."}), 201
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


# -------- LEITURAS / ALERTAS / SIMULAÇÃO --------

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


@api_bp.post("/api/simulacao/tick")
def api_simulacao_tick():
    try:
        novas = xml_service.simular_ciclo()
        return jsonify({"novasLeituras": novas})
    except Exception as e:
        return jsonify({"error": f"Erro na simulação: {str(e)}"}), 500
