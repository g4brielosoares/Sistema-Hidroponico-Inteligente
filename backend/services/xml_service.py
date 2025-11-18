from datetime import datetime
from decimal import Decimal
import random

from lxml import etree

from backend.config import Config


# Faixas ideais por tipo de sensor (para simulação e alertas)
FAIXAS = {
    "pH": (Decimal("4.5"), Decimal("7.5")),
    "EC": (Decimal("0.5"), Decimal("3.0")),
    "temperatura": (Decimal("10"), Decimal("35")),
    "nível": (Decimal("0"), Decimal("100")),
    "luminosidade": (Decimal("0"), Decimal("200000")),
}

UNIDADES_POR_TIPO = {
    "pH": "",
    "EC": "mS/cm",
    "temperatura": "°C",
    "nível": "%",
    "luminosidade": "lux",
}

class XMLService:
    def __init__(self):
        # Caminhos vindos do Config
        self.schema_path = Config.XML_SCHEMA_PATH
        self.data_path = Config.XML_DATA_PATH

        # Carrega e compila o XSD
        xsd_doc = etree.parse(self.schema_path)
        self.schema = etree.XMLSchema(xsd_doc)

    # ------------------------------------------------------------------
    # Helpers internos: carregar/salvar SEMPRE validando pelo XSD
    # ------------------------------------------------------------------

    def _load_tree(self) -> etree._ElementTree:
        """
        Carrega o XML em memória e valida contra o XSD.
        Se estiver inválido, lança exceção de validação.
        """
        tree = etree.parse(self.data_path)
        self.schema.assertValid(tree)
        return tree

    def _save_tree(self, tree: etree._ElementTree) -> None:
        """
        Valida o XML modificado contra o XSD e, se estiver ok,
        salva de volta no arquivo.
        """
        self.schema.assertValid(tree)
        tree.write(
            self.data_path,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

    # ------------------------------------------------------------------
    # SENSORES
    # ------------------------------------------------------------------

    def listar_sensores(self):
        """
        Retorna sensores como lista de dicts:
        {
          "id": ...,
          "tipo": ...,
          "unidade": ...,
          "modelo": ...,
          "localizacao": ...
        }
        Últimos sensores adicionados aparecem primeiro.
        """
        tree = self._load_tree()
        root = tree.getroot()
        sensores_el = root.find("sensores")

        sensores = []
        for s in sensores_el.findall("sensor"):
            sensores.append(
                {
                    "id": s.get("id"),
                    "tipo": s.findtext("tipo"),
                    "unidade": s.findtext("unidade"),
                    "modelo": s.findtext("modelo"),
                    "localizacao": s.findtext("localizacao"),
                }
            )

        # último no XML vem primeiro na UI
        return list(reversed(sensores))

    def cadastrar_sensor(self, data: dict) -> None:
        """
        data = {
          "id": "s-ph-02",
          "tipo": "pH",
          "modelo": "...",
          "localizacao": "..."
        }
        A unidade é definida automaticamente com base no tipo.
        """
        tree = self._load_tree()
        root = tree.getroot()
        sensores_el = root.find("sensores")

        # Impede IDs duplicados
        for s in sensores_el.findall("sensor"):
            if s.get("id") == data["id"]:
                raise ValueError("Já existe sensor com esse ID.")

        sensor_el = etree.SubElement(sensores_el, "sensor")
        sensor_el.set("id", data["id"])

        tipo = data["tipo"]
        unidade_auto = UNIDADES_POR_TIPO.get(tipo, "")

        tipo_el = etree.SubElement(sensor_el, "tipo")
        tipo_el.text = tipo

        unidade_el = etree.SubElement(sensor_el, "unidade")
        unidade_el.text = unidade_auto  # sempre alguma string (pode ser "")

        modelo_el = etree.SubElement(sensor_el, "modelo")
        modelo_el.text = data.get("modelo") or ""

        loc_el = etree.SubElement(sensor_el, "localizacao")
        loc_el.text = data.get("localizacao") or ""

        self._save_tree(tree)

    def limpar_sensores(self) -> None:
        """
        Remove todos os sensores e recria um sensor placeholder mínimo
        para não quebrar o XSD (minOccurs implícito em 1).
        """
        tree = self._load_tree()
        root = tree.getroot()
        sensores_el = root.find("sensores")

        for s in list(sensores_el.findall("sensor")):
            sensores_el.remove(s)

        # Cria um sensor mínimo válido (placeholder)
        sensor_el = etree.SubElement(sensores_el, "sensor", id="sensor-placeholder")
        etree.SubElement(sensor_el, "tipo").text = "pH"
        etree.SubElement(sensor_el, "unidade").text = ""
        etree.SubElement(sensor_el, "modelo").text = ""
        etree.SubElement(sensor_el, "localizacao").text = ""

        self._save_tree(tree)

    # ------------------------------------------------------------------
    # ATUADORES
    # ------------------------------------------------------------------

    def listar_atuadores(self):
        """
        Retorna atuadores como lista de dicts:
        {
          "id": ...,
          "tipo": ...,
          "ultimoComando": {
            "dataHora": ...,
            "comando": ...
          } ou None
        }
        Últimos atuadores adicionados aparecem primeiro.
        """
        tree = self._load_tree()
        root = tree.getroot()
        atuadores_el = root.find("atuadores")

        if atuadores_el is None:
            return []

        atuadores = []
        for a in atuadores_el.findall("atuador"):
            uc = a.find("ultimoComando")
            ultimo = None
            if uc is not None:
                ultimo = {
                    "dataHora": uc.findtext("dataHora"),
                    "comando": uc.findtext("comando"),
                }

            atuadores.append(
                {
                    "id": a.get("id"),
                    "tipo": a.findtext("tipo"),
                    "ultimoComando": ultimo,
                }
            )

        return list(reversed(atuadores))

    def cadastrar_atuador(self, data: dict) -> None:
        """
        data = {
          "id": "a-bomba-02",
          "tipo": "bombaNutrientes"
        }
        """
        tree = self._load_tree()
        root = tree.getroot()
        atuadores_el = root.find("atuadores")
        if atuadores_el is None:
            atuadores_el = etree.SubElement(root, "atuadores")

        for a in atuadores_el.findall("atuador"):
            if a.get("id") == data["id"]:
                raise ValueError("Já existe atuador com esse ID.")

        a_el = etree.SubElement(atuadores_el, "atuador")
        a_el.set("id", data["id"])

        tipo_el = etree.SubElement(a_el, "tipo")
        tipo_el.text = data["tipo"]

        self._save_tree(tree)

    def limpar_atuadores(self) -> None:
        """
        Remove todos os atuadores.
        (No XSD, atuadores é opcional minOccurs=0, então pode zerar.)
        """
        tree = self._load_tree()
        root = tree.getroot()
        atuadores_el = root.find("atuadores")

        if atuadores_el is not None:
            for a in list(atuadores_el.findall("atuador")):
                atuadores_el.remove(a)

        self._save_tree(tree)

    # ------------------------------------------------------------------
    # LEITURAS
    # ------------------------------------------------------------------

    def listar_leituras(self):
        """
        Retorna leituras como lista de dicts:
        {
          "sensorId": ...,
          "tipo": ...,
          "unidade": ...,
          "dataHora": ...,
          "valor": float
        }
        Ordenado da leitura mais recente para a mais antiga.
        """
        tree = self._load_tree()
        root = tree.getroot()

        sensores_el = root.find("sensores")
        sensores_map = {s.get("id"): s for s in sensores_el.findall("sensor")}

        leituras_el = root.find("leituras")
        leituras = []

        for l in leituras_el.findall("leitura"):
            sensor_ref = l.get("sensorRef")
            unidade = l.get("unidade")
            data_hora = l.findtext("dataHora")
            valor = l.findtext("valor")

            sensor = sensores_map.get(sensor_ref)
            tipo = sensor.findtext("tipo") if sensor is not None else None

            leituras.append(
                {
                    "sensorId": sensor_ref,
                    "tipo": tipo,
                    "unidade": unidade,
                    "dataHora": data_hora,
                    "valor": float(valor),
                }
            )

        # mais recente primeiro
        leituras.sort(key=lambda x: x["dataHora"], reverse=True)
        return leituras

    def limpar_leituras(self) -> None:
        """
        Remove todas as leituras e cria uma leitura "placeholder"
        mínima para não quebrar o XSD (minOccurs implícito).
        """
        tree = self._load_tree()
        root = tree.getroot()
        leituras_el = root.find("leituras")

        for l in list(leituras_el.findall("leitura")):
            leituras_el.remove(l)

        # cria leitura mínima válida apontando para algum sensor existente
        sensores_el = root.find("sensores")
        primeiro_sensor = sensores_el.find("sensor")
        sensor_id = primeiro_sensor.get("id")

        placeholder = etree.SubElement(leituras_el, "leitura", sensorRef=sensor_id)
        etree.SubElement(placeholder, "dataHora").text = datetime.utcnow().isoformat() + "Z"
        etree.SubElement(placeholder, "valor").text = "0.0"

        self._save_tree(tree)

    # ------------------------------------------------------------------
    # ALERTAS (derivados de leituras x faixas ideais)
    # ------------------------------------------------------------------

    def listar_alertas(self):
        """
        Considera alerta toda leitura cujo valor esteja fora da faixa
        definida em FAIXAS por tipo de sensor.
        Retorna:
        {
          "sensorId": ...,
          "tipo": ...,
          "dataHora": ...,
          "valor": float,
          "mensagem": ...
        }
        """
        leituras = self.listar_leituras()
        tree = self._load_tree()
        root = tree.getroot()

        sensores_el = root.find("sensores")
        sensores_map = {s.get("id"): s for s in sensores_el.findall("sensor")}

        alertas = []
        for l in leituras:
            sensor = sensores_map.get(l["sensorId"])
            if not sensor:
                continue

            tipo = sensor.findtext("tipo")
            faixa = FAIXAS.get(tipo)
            if not faixa:
                continue

            minimo, maximo = faixa
            valor = Decimal(str(l["valor"]))

            if valor < minimo:
                msg = f"{tipo} abaixo da faixa ideal ({valor} < {minimo})"
            elif valor > maximo:
                msg = f"{tipo} acima da faixa ideal ({valor} > {maximo})"
            else:
                continue

            alertas.append(
                {
                    "sensorId": l["sensorId"],
                    "tipo": tipo,
                    "dataHora": l["dataHora"],
                    "valor": float(valor),
                    "mensagem": msg,
                }
            )

        alertas.sort(key=lambda x: x["dataHora"], reverse=True)
        return alertas

    # ------------------------------------------------------------------
    # SIMULAÇÃO DE CICLO
    # ------------------------------------------------------------------

    def simular_ciclo(self):
        """
        Para cada sensor no XML:
          - Gera uma nova leitura (às vezes fora da faixa)
          - Se estiver fora da faixa, atualiza ultimoComando do primeiro atuador
        Sempre valida o XML contra o XSD antes de salvar.
        Retorna a lista de leituras geradas neste ciclo.
        """
        tree = self._load_tree()
        root = tree.getroot()

        sensores_el = root.find("sensores")
        leituras_el = root.find("leituras")
        atuadores_el = root.find("atuadores")

        agora_iso = datetime.utcnow().isoformat() + "Z"
        novas_leituras = []

        for sensor in sensores_el.findall("sensor"):
            sensor_id = sensor.get("id")
            tipo = sensor.findtext("tipo")
            unidade = sensor.findtext("unidade") or None

            faixa = FAIXAS.get(tipo)
            if faixa:
                minimo, maximo = faixa
                # 80% das leituras dentro da faixa, 20% fora
                if random.random() < 0.8:
                    valor = random.uniform(float(minimo), float(maximo))
                else:
                    if random.random() < 0.5:
                        valor = float(minimo) - random.uniform(0.1, 1.0)
                    else:
                        valor = float(maximo) + random.uniform(0.1, 1.0)
            else:
                valor = random.uniform(0, 100)

            valor_dec = Decimal(str(round(valor, 2)))

            leitura_el = etree.SubElement(
                leituras_el,
                "leitura",
                sensorRef=sensor_id,
            )
            if unidade:
                leitura_el.set("unidade", unidade)

            etree.SubElement(leitura_el, "dataHora").text = agora_iso
            etree.SubElement(leitura_el, "valor").text = str(valor_dec)

            novas_leituras.append(
                {
                    "sensorId": sensor_id,
                    "tipo": tipo,
                    "unidade": unidade,
                    "dataHora": agora_iso,
                    "valor": float(valor_dec),
                }
            )

            # Atualiza atuador (se houver) quando fora da faixa
            if faixa and atuadores_el is not None:
                minimo, maximo = faixa
                cmd = None
                if valor_dec < minimo:
                    cmd = "ligar"
                elif valor_dec > maximo:
                    cmd = "desligar"

                if cmd:
                    atuador = atuadores_el.find("atuador")
                    if atuador is not None:
                        uc = atuador.find("ultimoComando")
                        if uc is None:
                            uc = etree.SubElement(atuador, "ultimoComando")
                            etree.SubElement(uc, "dataHora")
                            etree.SubElement(uc, "comando")

                        uc.find("dataHora").text = agora_iso
                        uc.find("comando").text = cmd

        # Valida e persiste o XML modificado
        self._save_tree(tree)

        return novas_leituras
