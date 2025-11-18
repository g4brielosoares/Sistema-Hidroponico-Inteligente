import json
from datetime import datetime
from decimal import Decimal
from typing import List

from lxml import etree

from backend.config import Config
from backend.models.hidroponia import (
    SistemaHidroponico,
    MetaSistema,
    Sensor,
    Leitura,
    Atuador,
    ComandoAtuador,
)


class XMLService:
    def __init__(self):
        self.schema_path = Config.XML_SCHEMA_PATH
        self.storage_path = Config.XML_STORAGE_PATH
        self.pending_path = Config.PENDING_BUFFER_PATH
        self._load_schema()

    def _load_schema(self):
        with open(self.schema_path, "rb") as f:
            schema_doc = etree.XML(f.read())
        self.schema = etree.XMLSchema(schema_doc)
        # RNF2: XXE desabilitado
        self.parser = etree.XMLParser(schema=self.schema, resolve_entities=False)

    def validate_xml(self, xml_string: str) -> bool:
        try:
            doc = etree.fromstring(xml_string.encode("utf-8"), self.parser)
            return self.schema.validate(doc)
        except etree.XMLSyntaxError as e:
            print("Erro de validação XML:", e)
            return False

    # ---------- BUFFER OFFLINE (RNF5) ----------

    def _load_pending(self) -> List[dict]:
        try:
            with open(self.pending_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    def _save_pending(self, pendentes: List[dict]):
        with open(self.pending_path, "w", encoding="utf-8") as f:
            json.dump(pendentes, f, ensure_ascii=False, indent=2)

    def add_pending_leitura(self, leitura_dict: dict):
        """
        RNF5: se não conseguir salvar o XML principal, guarda local por até 24h.
        """
        pendentes = self._load_pending()
        pendentes.append(leitura_dict)
        self._save_pending(pendentes)

    def flush_pending_leituras(self, sistema: SistemaHidroponico):
        """
        Sempre que carregar o sistema, tenta integrar leituras pendentes.
        Mantém apenas itens das últimas 24h.
        """
        pendentes = self._load_pending()
        if not pendentes:
            return

        agora = datetime.utcnow()
        novas_pendentes = []

        for item in pendentes:
            criado_em = datetime.fromisoformat(item["criadoEm"])
            if (agora - criado_em).total_seconds() > 24 * 3600:
                # descarta se passou de 24h
                continue

            try:
                l = Leitura(
                    sensor_id=item["sensorId"],
                    data_hora=datetime.fromisoformat(item["dataHora"]),
                    valor=Decimal(str(item["valor"])),
                    unidade=item.get("unidade"),
                )
                sistema.leituras.append(l)
            except Exception:
                # se falhar parse, mantém no buffer
                novas_pendentes.append(item)

        self._save_pending(novas_pendentes)

    # ---------- CARREGAR XML ----------

    def load_from_file(self) -> SistemaHidroponico:
        with open(self.storage_path, "rb") as f:
            tree = etree.parse(f, self.parser)
        root = tree.getroot()

        sistema_id = root.get("id")

        meta_el = root.find("meta")
        meta = MetaSistema(
            nome=meta_el.findtext("nome"),
            local=meta_el.findtext("local"),
            versao=meta_el.findtext("versao"),
        )

        sensores = []
        for s in root.findall("sensores/sensor"):
            sensores.append(
                Sensor(
                    id=s.get("id"),
                    tipo=s.findtext("tipo"),
                    unidade=s.findtext("unidade") or "",
                    modelo=s.findtext("modelo"),
                    localizacao=s.findtext("localizacao"),
                )
            )

        leituras = []
        for l in root.findall("leituras/leitura"):
            data_hora = datetime.fromisoformat(
                l.findtext("dataHora").replace("Z", "+00:00")
            )
            valor = Decimal(l.findtext("valor"))
            unidade = l.get("unidade")
            sensor_ref_el = l.find("sensorRef")
            sensor_ref = sensor_ref_el.get("ref")
            leituras.append(
                Leitura(
                    sensor_id=sensor_ref,
                    data_hora=data_hora,
                    valor=valor,
                    unidade=unidade,
                )
            )

        atuadores = []
        for a in root.findall("atuadores/atuador"):
            tipo = a.findtext("tipo")
            comandos_el = a.find("comandos")
            comandos = []
            if comandos_el is not None:
                for c in comandos_el.findall("comando"):
                    data_hora_c = datetime.fromisoformat(
                        c.findtext("dataHora").replace("Z", "+00:00")
                    )
                    acao = c.findtext("acao")
                    comandos.append(
                        ComandoAtuador(
                            data_hora=data_hora_c,
                            acao=acao,
                        )
                    )
            atuadores.append(
                Atuador(
                    id=a.get("id"),
                    tipo=tipo,
                    comandos=comandos,
                )
            )

        sistema = SistemaHidroponico(
            id=sistema_id,
            meta=meta,
            sensores=sensores,
            leituras=leituras,
            atuadores=atuadores,
        )

        # Integra leituras pendentes (RNF5)
        self.flush_pending_leituras(sistema)

        return sistema

    # ---------- GERAR XML (reutilizado em salvar e exportar) ----------

    def _build_xml_tree(self, sistema: SistemaHidroponico) -> etree._ElementTree:
        root = etree.Element("hidroponia", id=sistema.id)

        # meta
        meta_el = etree.SubElement(root, "meta")
        etree.SubElement(meta_el, "nome").text = sistema.meta.nome
        etree.SubElement(meta_el, "local").text = sistema.meta.local
        if sistema.meta.versao:
            etree.SubElement(meta_el, "versao").text = sistema.meta.versao

        # sensores
        sensores_el = etree.SubElement(root, "sensores")
        for s in sistema.sensores:
            s_el = etree.SubElement(sensores_el, "sensor", id=s.id)
            etree.SubElement(s_el, "tipo").text = s.tipo
            etree.SubElement(s_el, "unidade").text = s.unidade
            if s.modelo:
                etree.SubElement(s_el, "modelo").text = s.modelo
            if s.localizacao:
                etree.SubElement(s_el, "localizacao").text = s.localizacao

        # leituras
        leituras_el = etree.SubElement(root, "leituras")
        for l in sistema.leituras:
            l_el = etree.SubElement(leituras_el, "leitura")
            if l.unidade:
                l_el.set("unidade", l.unidade)
            etree.SubElement(l_el, "dataHora").text = l.data_hora.isoformat().replace(
                "+00:00", "Z"
            )
            sr = etree.SubElement(l_el, "sensorRef")
            sr.set("ref", l.sensor_id)
            etree.SubElement(l_el, "valor").text = str(l.valor)

        # atuadores
        atuadores_el = etree.SubElement(root, "atuadores")
        for a in sistema.atuadores:
            a_el = etree.SubElement(atuadores_el, "atuador", id=a.id)
            etree.SubElement(a_el, "tipo").text = a.tipo
            if a.comandos:
                comandos_el = etree.SubElement(a_el, "comandos")
                for c in a.comandos:
                    c_el = etree.SubElement(comandos_el, "comando")
                    etree.SubElement(c_el, "dataHora").text = c.data_hora.isoformat().replace(
                        "+00:00", "Z"
                    )
                    etree.SubElement(c_el, "acao").text = c.acao

        return etree.ElementTree(root)

    def to_xml_bytes(self, sistema: SistemaHidroponico) -> bytes:
        tree = self._build_xml_tree(sistema)
        xml_bytes = etree.tostring(
            tree,
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True
        )
        if not self.validate_xml(xml_bytes.decode("utf-8")):
            raise ValueError("XML gerado não é válido segundo o XSD")
        return xml_bytes

    def save_to_file(self, sistema: SistemaHidroponico):
        xml_bytes = self.to_xml_bytes(sistema)
        with open(self.storage_path, "wb") as f:
            f.write(xml_bytes)
