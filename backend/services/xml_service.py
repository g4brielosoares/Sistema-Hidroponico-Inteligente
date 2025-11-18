from datetime import datetime, timedelta
from decimal import Decimal
import os
import random

from lxml import etree

from backend.config import Config

# Faixas ideais por tipo de sensor
FAIXAS = {
    "pH": (Decimal("4.5"), Decimal("7.5")),
    "EC": (Decimal("0.5"), Decimal("3.0")),
    "temperatura": (Decimal("10"), Decimal("35")),
    "nível": (Decimal("0"), Decimal("100")),
    "luminosidade": (Decimal("0"), Decimal("200000")),
}

# Unidades automáticas por tipo
UNIDADES_POR_TIPO = {
    "pH": "",
    "EC": "mS/cm",
    "temperatura": "°C",
    "nível": "%",
    "luminosidade": "lux",
}


class XMLService:
    def __init__(self):
        # Caminhos
        self.schema_path = Config.XML_SCHEMA_PATH
        self.data_path = Config.XML_DATA_PATH
        self.pending_path = Config.XML_PENDING_PATH

        # Parser seguro contra XXE
        self.parser = etree.XMLParser(resolve_entities=False, no_network=True)

        # Carrega e compila o XSD
        xsd_doc = etree.parse(self.schema_path, parser=self.parser)
        self.schema = etree.XMLSchema(xsd_doc)

        # Garante arquivo de pendências
        self._init_pending_file()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _load_tree(self) -> etree._ElementTree:
        tree = etree.parse(self.data_path, parser=self.parser)
        self.schema.assertValid(tree)
        return tree

    def _save_tree(self, tree: etree._ElementTree) -> None:
        self.schema.assertValid(tree)
        tree.write(
            self.data_path,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

    # ---------- pendências (fila offline) ----------

    def _init_pending_file(self):
        if not os.path.exists(self.pending_path):
            root = etree.Element("pendencias")
            leituras_el = etree.SubElement(root, "leituras")
            tree = etree.ElementTree(root)
            tree.write(
                self.pending_path,
                encoding="utf-8",
                xml_declaration=True,
                pretty_print=True,
            )

    def _load_pending_tree(self) -> etree._ElementTree:
        return etree.parse(self.pending_path, parser=self.parser)

    def _save_pending_tree(self, tree: etree._ElementTree) -> None:
        tree.write(
            self.pending_path,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

    def adicionar_pendentes(self, leituras: list[dict]) -> None:
        """
        Adiciona leituras à fila offline (RNF5).
        Cada leitura: { sensorId, tipo, unidade, dataHora, valor }
        """
        tree = self._load_pending_tree()
        root = tree.getroot()
        leituras_el = root.find("leituras")

        for l in leituras:
            leitura_el = etree.SubElement(
                leituras_el,
                "leitura",
                sensorRef=l["sensorId"],
            )
            if l.get("unidade"):
                leitura_el.set("unidade", l["unidade"])
            dh = etree.SubElement(leitura_el, "dataHora")
            dh.text = l["dataHora"]
            val = etree.SubElement(leitura_el, "valor")
            val.text = str(Decimal(str(l["valor"])))

        self._save_pending_tree(tree)

    def sincronizar_pendentes(self) -> int:
        """
        Move leituras da fila offline para o XML principal,
        considerando apenas leituras com até 24h de idade.
        Retorna quantas leituras foram sincronizadas.
        """
        pend_tree = self._load_pending_tree()
        pend_root = pend_tree.getroot()
        pend_leituras_el = pend_root.find("leituras")

        pend_leituras = list(pend_leituras_el.findall("leitura"))
        if not pend_leituras:
            return 0

        now = datetime.utcnow()
        tree = self._load_tree()
        root = tree.getroot()
        leituras_el = root.find("leituras")

        transferidas = 0
        for l in pend_leituras:
            data_hora = l.findtext("dataHora")
            try:
                dt = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
            except Exception:
                # se não conseguir converter, descarta
                pend_leituras_el.remove(l)
                continue

            if now - dt <= timedelta(hours=24):
                # clona a leitura para o XML principal
                novo = etree.SubElement(
                    leituras_el,
                    "leitura",
                    sensorRef=l.get("sensorRef"),
                )
                if l.get("unidade"):
                    novo.set("unidade", l.get("unidade"))
                etree.SubElement(novo, "dataHora").text = data_hora
                etree.SubElement(novo, "valor").text = l.findtext("valor")
                transferidas += 1

            # de qualquer forma, remove da fila
            pend_leituras_el.remove(l)

        # salva ambos
        if transferidas > 0:
            self._save_tree(tree)
        self._save_pending_tree(pend_tree)
        return transferidas

    # ------------------------------------------------------------------
    # SENSORES
    # ------------------------------------------------------------------

    def listar_sensores(self):
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

        return list(reversed(sensores))

    def cadastrar_sensor(self, data: dict) -> None:
        tree = self._load_tree()
        root = tree.getroot()
        sensores_el = root.find("sensores")

        for s in sensores_el.findall("sensor"):
            if s.get("id") == data["id"]:
                raise ValueError("Já existe sensor com esse ID.")

        sensor_el = etree.SubElement(sensores_el, "sensor")
        sensor_el.set("id", data["id"])

        tipo = data["tipo"]
        unidade_auto = UNIDADES_POR_TIPO.get(tipo, "")

        etree.SubElement(sensor_el, "tipo").text = tipo
        etree.SubElement(sensor_el, "unidade").text = unidade_auto
        etree.SubElement(sensor_el, "modelo").text = data.get("modelo") or ""
        etree.SubElement(sensor_el, "localizacao").text = data.get("localizacao") or ""

        self._save_tree(tree)

    def limpar_sensores(self) -> None:
        tree = self._load_tree()
        root = tree.getroot()
        sensores_el = root.find("sensores")

        for s in list(sensores_el.findall("sensor")):
            sensores_el.remove(s)

        # placeholder para não quebrar XSD
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
        tree = self._load_tree()
        root = tree.getroot()
        atuadores_el = root.find("atuadores")

        if atuadores_el is None:
            return []

        atuadores = []
        for a in atuadores_el.findall("atuador"):
            comandos_el = a.find("comandos")
            comandos = []
            ultimo = None

            if comandos_el is not None:
                for c in comandos_el.findall("comando"):
                    cmd = {
                        "dataHora": c.findtext("dataHora"),
                        "acao": c.findtext("acao"),
                    }
                    comandos.append(cmd)
                if comandos:
                    # último comando é o mais recente pelo dataHora
                    comandos.sort(key=lambda x: x["dataHora"])
                    ultimo = comandos[-1]

            atuadores.append(
                {
                    "id": a.get("id"),
                    "tipo": a.findtext("tipo"),
                    "comandos": comandos,
                    "ultimoComando": ultimo,
                }
            )

        return list(reversed(atuadores))

    def cadastrar_atuador(self, data: dict) -> None:
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
        etree.SubElement(a_el, "tipo").text = data["tipo"]

        self._save_tree(tree)

    def limpar_atuadores(self) -> None:
        tree = self._load_tree()
        root = tree.getroot()
        atuadores_el = root.find("atuadores")
        if atuadores_el is not None:
            for a in list(atuadores_el.findall("atuador")):
                atuadores_el.remove(a)
        self._save_tree(tree)

    # ------------------------------------------------------------------
    # LEITURAS / ALERTAS
    # ------------------------------------------------------------------

    def listar_leituras(self):
        """
        Retorna leituras como lista de dicts:
        {
          "sensorId": ...,
          "tipo": ...,
          "unidade": ...,
          "dataHora": ...,
          "valor": float,
          "status": "dentro" | "abaixo" | "acima" | "sem-faixa",
          "mensagem": str,
          "foraFaixa": bool
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
            valor_str = l.findtext("valor")

            sensor = sensores_map.get(sensor_ref)
            tipo = sensor.findtext("tipo") if sensor is not None else None

            status = "sem-faixa"
            mensagem = "Faixa não configurada para esse tipo de sensor."
            fora_faixa = False

            try:
                valor_dec = Decimal(valor_str)
                valor_float = float(valor_dec)
            except Exception:
                valor_dec = None
                valor_float = None

            faixa = FAIXAS.get(tipo)
            if faixa and valor_dec is not None:
                minimo, maximo = faixa
                if valor_dec < minimo:
                    status = "abaixo"
                    mensagem = f"{tipo} abaixo da faixa ideal ({valor_dec} < {minimo})"
                    fora_faixa = True
                elif valor_dec > maximo:
                    status = "acima"
                    mensagem = f"{tipo} acima da faixa ideal ({valor_dec} > {maximo})"
                    fora_faixa = True
                else:
                    status = "dentro"
                    mensagem = "Dentro da faixa ideal."
                    fora_faixa = False

            leituras.append(
                {
                    "sensorId": sensor_ref,
                    "tipo": tipo,
                    "unidade": unidade,
                    "dataHora": data_hora,
                    "valor": valor_float,
                    "status": status,
                    "mensagem": mensagem,
                    "foraFaixa": fora_faixa,
                }
            )

        leituras.sort(key=lambda x: x["dataHora"] or "", reverse=True)
        return leituras

    def limpar_leituras(self) -> None:
        tree = self._load_tree()
        root = tree.getroot()
        leituras_el = root.find("leituras")

        for l in list(leituras_el.findall("leitura")):
            leituras_el.remove(l)

        # placeholder mínimo
        sensores_el = root.find("sensores")
        primeiro_sensor = sensores_el.find("sensor")
        sensor_id = primeiro_sensor.get("id")

        placeholder = etree.SubElement(leituras_el, "leitura", sensorRef=sensor_id)
        etree.SubElement(placeholder, "dataHora").text = datetime.utcnow().isoformat() + "Z"
        etree.SubElement(placeholder, "valor").text = "0.0"

        self._save_tree(tree)

    def listar_alertas(self):
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
    # SIMULAÇÃO DE CICLO (leituras + comandos)
    # ------------------------------------------------------------------

    def simular_ciclo(self):
        """
        Para cada sensor:
          - gera uma nova leitura
          - se fora da faixa, registra comando no primeiro atuador
        Se falhar ao salvar no XML principal, grava leituras na fila offline.
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

            # comandos do atuador (histórico)
            if faixa and atuadores_el is not None:
                minimo, maximo = faixa
                cmd_acao = None
                if valor_dec < minimo:
                    cmd_acao = "ligar"
                elif valor_dec > maximo:
                    cmd_acao = "desligar"

                if cmd_acao:
                    atuador = atuadores_el.find("atuador")
                    if atuador is not None:
                        comandos_el = atuador.find("comandos")
                        if comandos_el is None:
                            comandos_el = etree.SubElement(atuador, "comandos")
                        cmd_el = etree.SubElement(comandos_el, "comando")
                        etree.SubElement(cmd_el, "dataHora").text = agora_iso
                        etree.SubElement(cmd_el, "acao").text = cmd_acao

        # tenta salvar no XML principal, se falhar → fila offline
        try:
            self._save_tree(tree)
        except Exception:
            self.adicionar_pendentes(novas_leituras)

        return novas_leituras

    # ------------------------------------------------------------------
    # EXPORTAÇÃO DE LEITURAS EM XML (RF8)
    # ------------------------------------------------------------------

    def exportar_leituras_filtradas(self, dt_inicio: datetime, dt_fim: datetime) -> bytes:
        """
        Monta um XML 'hidroponia' com leituras filtradas por [dt_inicio, dt_fim].
        Meta / sensores / atuadores permanecem os mesmos.
        """
        tree = self._load_tree()
        root = tree.getroot()

        # novo root
        new_root = etree.Element("hidroponia", id=root.get("id"))

        # copia meta
        meta_src = root.find("meta")
        meta_new = etree.SubElement(new_root, "meta")
        for tag in ["nome", "local", "versao"]:
            el = meta_src.find(tag)
            if el is not None:
                etree.SubElement(meta_new, tag).text = el.text

        # copia sensores
        sensores_src = root.find("sensores")
        sensores_new = etree.SubElement(new_root, "sensores")
        for s in sensores_src.findall("sensor"):
            s_new = etree.SubElement(sensores_new, "sensor", id=s.get("id"))
            for tag in ["tipo", "unidade", "modelo", "localizacao"]:
                el = s.find(tag)
                etree.SubElement(s_new, tag).text = el.text if el is not None else ""

        # filtra leituras
        leituras_src = root.find("leituras")
        leituras_new = etree.SubElement(new_root, "leituras")

        for l in leituras_src.findall("leitura"):
            data_hora = l.findtext("dataHora")
            try:
                dt = datetime.fromisoformat(data_hora.replace("Z", "+00:00"))
            except Exception:
                continue

            if dt_inicio <= dt <= dt_fim:
                attrs = {"sensorRef": l.get("sensorRef")}
                if l.get("unidade"):
                    attrs["unidade"] = l.get("unidade")
                l_new = etree.SubElement(leituras_new, "leitura", **attrs)
                etree.SubElement(l_new, "dataHora").text = data_hora
                etree.SubElement(l_new, "valor").text = l.findtext("valor")

        # copia atuadores + comandos
        atuadores_src = root.find("atuadores")
        if atuadores_src is not None:
            atuadores_new = etree.SubElement(new_root, "atuadores")
            for a in atuadores_src.findall("atuador"):
                a_new = etree.SubElement(atuadores_new, "atuador", id=a.get("id"))
                etree.SubElement(a_new, "tipo").text = a.findtext("tipo")
                comandos_src = a.find("comandos")
                if comandos_src is not None:
                    comandos_new = etree.SubElement(a_new, "comandos")
                    for c in comandos_src.findall("comando"):
                        c_new = etree.SubElement(comandos_new, "comando")
                        etree.SubElement(c_new, "dataHora").text = c.findtext("dataHora")
                        etree.SubElement(c_new, "acao").text = c.findtext("acao")

        new_tree = etree.ElementTree(new_root)
        self.schema.assertValid(new_tree)  # ainda compatível com o XSD
        return etree.tostring(
            new_root,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )
