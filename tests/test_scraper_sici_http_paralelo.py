"""Servidor simulado: valida sessões WebForms isoladas e agregação concorrente."""

from concurrent.futures import as_completed as as_completed_real
import json
from pathlib import Path
import tempfile
from threading import Barrier, Event, Lock
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from scraper_sici_http import ARVORE, ColetorHTTP, main


class PortalSimulado:
    def __init__(self, paralelo=False, falhar=None):
        self.paralelo = paralelo
        self.falhar = falhar
        self.sessoes = []
        self.lock = Lock()
        self.barreira = Barrier(4)
        self.ultimo_primeiro = Event()
        self.ativos = 0
        self.max_ativos = 0
        self.concluidos = []

    def sessao(self):
        portal = self

        class Sessao:
            def __init__(self):
                self.headers = {}
                self.fechada = False
                self.versao = 0
                with portal.lock:
                    self.identidade = len(portal.sessoes)
                    portal.sessoes.append(self)

            def resposta(self, selecionado=0):
                self.versao += 1
                self.estado = f"sessao-{self.identidade}-versao-{self.versao}"
                linhas = "".join(
                    f'''<table><tr><td><div style="width:20px"></div></td>
                    <td><img src="folder-D.gif"></td><td>
                    <a id="{ARVORE}t{i}" href="javascript:__doPostBack('arvore','s1\\\\{i}')">ORG{i}</a>
                    </td></tr></table>''' for i in range(6))
                html = f'''<form><input type="hidden" name="__VIEWSTATE" value="{self.estado}">
                    <input id="{ARVORE}_SelectedNode" value="{ARVORE}t{selecionado}">
                    <div id="{ARVORE}">{linhas}</div>
                    <span id="ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada">AREA{selecionado}</span>
                    <span id="ContentPlaceHolder1_lblCargo">Cargo</span>
                    <span id="ContentPlaceHolder1_lblTitular">Titular</span></form>'''
                return SimpleNamespace(content=html.encode(), raise_for_status=lambda: None)

            def get(self, url, timeout):
                return self.resposta()

            def post(self, url, data, timeout):
                dados = dict(data)
                if dados["__VIEWSTATE"] != self.estado:
                    raise AssertionError("VIEWSTATE compartilhado ou desatualizado")
                indice = int(dados["__EVENTARGUMENT"].split("\\")[-1])
                with portal.lock:
                    portal.ativos += 1
                    portal.max_ativos = max(portal.max_ativos, portal.ativos)
                try:
                    if portal.paralelo and indice < 4:
                        portal.barreira.wait(timeout=10)
                        if indice == 0:
                            if not portal.ultimo_primeiro.wait(timeout=10):
                                raise AssertionError("Tarefas não executaram em paralelo")
                    if indice == portal.falhar:
                        raise requests.Timeout("Falha simulada")
                    resposta = self.resposta(indice)
                    with portal.lock:
                        portal.concluidos.append(indice)
                    if indice == 3:
                        portal.ultimo_primeiro.set()
                    return resposta
                finally:
                    with portal.lock:
                        portal.ativos -= 1

            def close(self):
                self.fechada = True

        return Sessao()


class ParalelismoTest(unittest.TestCase):
    def coletar(self, portal, trabalhadores):
        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                coletor.coletar(trabalhadores=trabalhadores)
            finally:
                coletor.sessao.close()
        return coletor

    def test_quatro_sessoes_em_paralelo_equivalem_a_serial_na_ordem_original(self):
        portal = PortalSimulado(paralelo=True)
        paralelo = self.coletar(portal, 4)
        serial = self.coletar(PortalSimulado(), 1)
        self.assertEqual(portal.max_ativos, 4)
        self.assertNotEqual(portal.concluidos, list(range(6)))
        self.assertEqual(paralelo.resultados, serial.resultados)
        self.assertEqual([r["órgão"] for r in paralelo.resultados], [f"ORG{i}" for i in range(6)])
        self.assertEqual(paralelo.requisicoes, 13)  # descoberta + GET/POST de cada órgão
        self.assertEqual(len(portal.sessoes), 7)
        self.assertTrue(all(s.fechada for s in portal.sessoes))
        self.assertEqual(paralelo.trabalhadores_utilizados, 4)
        self.assertTrue(all(o["status"] == "concluida" for o in paralelo.orgaos))

    def test_falha_preserva_outros_orgaos_exporta_parcial_e_nao_compara(self):
        portal = PortalSimulado(paralelo=True, falhar=2)
        with tempfile.TemporaryDirectory() as pasta, \
                patch("scraper_sici_http.requests.Session", side_effect=portal.sessao), \
                patch("scraper_sici_http.config_manager.ler_config", return_value={"PALAVRAS_IGNORADAS": []}), \
                patch("scraper_sici_http.comparar") as comparar:
            referencia = Path(pasta) / "ref.xlsx"
            pd.DataFrame([dict(zip(["órgão", "escalão", "área", "cargo", "titular"], ["ORG0", "1º", "AREA0", "Cargo", "Titular"]))]).to_excel(referencia, index=False)
            codigo = main(["--saida-dir", pasta, "--comparar", str(referencia)])
            self.assertEqual(codigo, 1)
            comparar.assert_not_called()
            arquivo = next(Path(pasta).glob("sici_http_PARCIAL_*.xlsx"))
            dados = pd.read_excel(arquivo)
            self.assertEqual(len(dados), 5)
            metricas = json.loads(arquivo.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metricas["trabalhadores_utilizados"], 4)
            self.assertEqual(metricas["orgaos"][2]["status"], "PARCIAL")
            self.assertIn("Timeout", metricas["orgaos"][2]["erro"])
            self.assertTrue(all(s.fechada for s in portal.sessoes))

    def test_cancelamento_reune_concluidos_antes_de_exportar(self):
        portal = PortalSimulado()

        def interromper(tarefas):
            yield next(as_completed_real(tarefas))
            raise KeyboardInterrupt()

        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao), \
                patch("scraper_sici_http.as_completed", side_effect=interromper):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                with self.assertRaises(KeyboardInterrupt):
                    coletor.coletar(trabalhadores=1)
            finally:
                coletor.sessao.close()
        self.assertTrue(coletor.cancelamento.is_set())
        self.assertEqual(len(coletor.orgaos), 6)
        self.assertEqual(len(coletor.resultados), len(portal.concluidos))
        self.assertTrue(all(s.fechada for s in portal.sessoes))

    def test_preserva_registros_do_proprio_orgao_que_falhou(self):
        portal = PortalSimulado()
        percorrer_original = ColetorHTTP.percorrer

        def percorrer_e_falhar(coletor, no, orgao, tipo):
            percorrer_original(coletor, no, orgao, tipo)
            if orgao == "ORG2":
                raise RuntimeError("Falha depois de capturar um registro")

        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao), \
                patch.object(ColetorHTTP, "percorrer", percorrer_e_falhar):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                with self.assertRaisesRegex(RuntimeError, "ORG2"):
                    coletor.coletar()
            finally:
                coletor.sessao.close()
        self.assertEqual(len(coletor.resultados), 6)
        self.assertEqual(coletor.orgaos[2]["status"], "PARCIAL")
        self.assertEqual(coletor.orgaos[2]["registros"], 1)

    def test_orgao_unico_usa_um_trabalhador_e_config_e_lida_uma_vez(self):
        portal = PortalSimulado()
        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao), \
                patch("scraper_sici_http.config_manager.ler_config", return_value={"PALAVRAS_IGNORADAS": []}) as config:
            coletor = ColetorHTTP()
            try:
                coletor.coletar(orgao="ORG3")
            finally:
                coletor.sessao.close()
        config.assert_called_once()
        self.assertEqual(coletor.trabalhadores_utilizados, 1)
        self.assertEqual([r["órgão"] for r in coletor.resultados], ["ORG3"])


if __name__ == "__main__":
    unittest.main()
