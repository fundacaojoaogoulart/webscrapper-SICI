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
    def __init__(self, paralelo=False, falhar=None, painel_ausente=False, falhar_uma_vez=False,
                 falhar_restauracao=False, li_vazio_uma_vez=False, li_vazio_persistente=False,
                 li_vazio_indice=0):
        self.paralelo = paralelo
        self.falhar = falhar
        self.painel_ausente = painel_ausente
        self.falhar_uma_vez = falhar_uma_vez
        self.falhar_restauracao = falhar_restauracao
        self.li_vazio_uma_vez = li_vazio_uma_vez
        self.li_vazio_persistente = li_vazio_persistente
        self.li_vazio_indice = li_vazio_indice
        self.falhas_registradas = set()
        self.vazios_registrados = set()
        self.sessoes = []
        self.lock = Lock()
        self.barreira = Barrier(4)
        self.ultimo_primeiro = Event()
        self.paralelismo_validado = False
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

            def resposta(self, selecionado=0, modo="1", li_vazio=False):
                self.versao += 1
                self.estado = f"sessao-{self.identidade}-versao-{self.versao}"
                linhas = "".join(
                    f'''<table><tr><td><div style="width:20px"></div></td>
                    <td><img src="folder-D.gif"></td><td>
                    <a id="{ARVORE}t{i}" href="javascript:__doPostBack('arvore','s1\\\\{i}')">ORG{i}</a>
                    </td></tr></table>''' for i in range(6))
                itens_competencias = "<ul><li></li></ul>" if li_vazio else (
                    f"<ul><li>Competência {selecionado}</li><li>Outra {selecionado}</li></ul>" if modo == "2" else "")
                painel = "" if portal.painel_ausente and modo == "2" else (
                    f'<div id="ContentPlaceHolder1_PanelCompetenciaInterno">'
                    f'{itens_competencias}</div>')
                html = f'''<form><input type="hidden" name="__VIEWSTATE" value="{self.estado}">
                    <input id="{ARVORE}_SelectedNode" value="{ARVORE}t{selecionado}">
                    <select id="ContentPlaceHolder1_DDLInformacoesGerais" name="ctl00$ContentPlaceHolder1$DDLInformacoesGerais">
                      <option value="1" {'selected="selected"' if modo == '1' else ''}>Informações Gerais</option>
                      <option value="2" {'selected="selected"' if modo == '2' else ''}>Competências</option>
                    </select>
                    {painel}
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
                evento_alvo = dados["__EVENTTARGET"]
                if evento_alvo == "ctl00$ContentPlaceHolder1$DDLInformacoesGerais":
                    if portal.falhar_restauracao and dados[evento_alvo] == "1":
                        raise requests.ConnectionError("Falha simulada ao restaurar o painel")
                    self.modo = dados[evento_alvo]
                    li_vazio = False
                    if self.modo == "2":
                        with portal.lock:
                            li_vazio = (self.selecionado == portal.li_vazio_indice and
                                        (portal.li_vazio_persistente or
                                         (portal.li_vazio_uma_vez and self.selecionado not in portal.vazios_registrados)))
                            if li_vazio:
                                portal.vazios_registrados.add(self.selecionado)
                    return self.resposta(self.selecionado, self.modo, li_vazio)
                indice = int(dados["__EVENTARGUMENT"].split("\\")[-1])
                self.selecionado = indice
                with portal.lock:
                    portal.ativos += 1
                    portal.max_ativos = max(portal.max_ativos, portal.ativos)
                try:
                    if portal.paralelo and not portal.paralelismo_validado and indice < 4:
                        portal.barreira.wait(timeout=10)
                        if indice == 0:
                            if not portal.ultimo_primeiro.wait(timeout=10):
                                raise AssertionError("Tarefas não executaram em paralelo")
                    if indice == portal.falhar:
                        with portal.lock:
                            falhou_antes = indice in portal.falhas_registradas
                            portal.falhas_registradas.add(indice)
                        if not portal.falhar_uma_vez or not falhou_antes:
                            raise requests.Timeout("Falha simulada")
                    resposta = self.resposta(indice, getattr(self, "modo", "1"))
                    with portal.lock:
                        portal.concluidos.append(indice)
                    if indice == 3:
                        portal.ultimo_primeiro.set()
                        portal.paralelismo_validado = True
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
                coletor.coletar(trabalhadores=trabalhadores, pausa_recuperacao=0)
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
        self.assertEqual(paralelo.requisicoes, 25)  # descoberta/GET por órgão + três postbacks por unidade
        self.assertEqual(len(portal.sessoes), 7)
        self.assertTrue(all(s.fechada for s in portal.sessoes))
        self.assertEqual(paralelo.trabalhadores_utilizados, 4)
        self.assertTrue(all(o["status"] == "concluida" for o in paralelo.orgaos))
        self.assertTrue(all(r["competências"] == f"Competência {i}\nOutra {i}"
                            for i, r in enumerate(paralelo.resultados)))

    def test_falha_preserva_outros_orgaos_exporta_parcial_e_nao_compara(self):
        portal = PortalSimulado(paralelo=True, falhar=2)
        with tempfile.TemporaryDirectory() as pasta, \
                patch("scraper_sici_http.requests.Session", side_effect=portal.sessao), \
                patch("scraper_sici_http.config_manager.ler_config", return_value={"PALAVRAS_IGNORADAS": []}), \
                patch("scraper_sici_http.comparar") as comparar:
            referencia = Path(pasta) / "ref.xlsx"
            pd.DataFrame([dict(zip(["órgão", "escalão", "área", "cargo", "titular"], ["ORG0", "1º", "AREA0", "Cargo", "Titular"]))]).to_excel(referencia, index=False)
            codigo = main(["--saida-dir", pasta, "--pausa-recuperacao", "0", "--comparar", str(referencia)])
            self.assertEqual(codigo, 1)
            comparar.assert_not_called()
            arquivo = next(Path(pasta).glob("sici_http_PARCIAL_*.xlsx"))
            dados = pd.read_excel(arquivo)
            self.assertEqual(len(dados), 5)
            self.assertIn("competências", dados.columns)
            metricas = json.loads(arquivo.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metricas["trabalhadores_utilizados"], 4)
            self.assertEqual(metricas["orgaos"][2]["status"], "PARCIAL")
            self.assertIn("Timeout", metricas["orgaos"][2]["erro"])
            self.assertEqual([t["trabalhadores_configurados"] for t in metricas["orgaos"][2]["tentativas"]], [4, 2, 1])
            self.assertEqual(metricas["orgaos"][2]["etapa_erro"], "seleção da unidade")
            self.assertEqual(set(dados["status_competencias"]), {"concluida"})
            self.assertTrue(all(s.fechada for s in portal.sessoes))

    def test_painel_de_competencias_ausente_marca_orgao_parcial(self):
        portal = PortalSimulado(painel_ausente=True)
        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                with self.assertRaisesRegex(RuntimeError, "ORG0"):
                    coletor.coletar(orgao="ORG0", trabalhadores=1, pausa_recuperacao=0)
            finally:
                coletor.sessao.close()
        self.assertEqual(coletor.orgaos[0]["status"], "PARCIAL")
        self.assertIn("Resposta sem painel de competências", coletor.orgaos[0]["erro"])

    def test_recuperacao_substitui_tentativa_parcial_sem_duplicar_registros(self):
        portal = PortalSimulado(falhar=2, falhar_uma_vez=True)
        coletor = self.coletar(portal, 4)
        self.assertEqual(len(coletor.resultados), 6)
        self.assertEqual(len([r for r in coletor.resultados if r["órgão"] == "ORG2"]), 1)
        orgao = coletor.orgaos[2]
        self.assertEqual(orgao["status"], "concluida")
        self.assertEqual(len(orgao["tentativas"]), 2)
        self.assertEqual([t["trabalhadores_configurados"] for t in orgao["tentativas"]], [4, 2])

    def test_conteudo_competencias_preservado_se_falha_so_ao_restaurar_dropdown(self):
        portal = PortalSimulado(falhar_restauracao=True)
        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                with self.assertRaisesRegex(RuntimeError, "ORG0"):
                    coletor.coletar(orgao="ORG0", trabalhadores=1, pausa_recuperacao=0)
            finally:
                coletor.sessao.close()
        registro = coletor.resultados[0]
        self.assertEqual(registro["status_competencias"], "erro")
        self.assertEqual(registro["competências"], "Competência 0\nOutra 0")
        self.assertIn("restaurar o painel", registro["erro_competencias"])

    def test_li_presente_sem_texto_falha_e_entra_na_recuperacao(self):
        portal = PortalSimulado(li_vazio_uma_vez=True, li_vazio_indice=2)
        coletor = self.coletar(portal, 4)
        registro = next(r for r in coletor.resultados if r["órgão"] == "ORG2")
        orgao = next(o for o in coletor.orgaos if o["orgao"] == "ORG2")
        self.assertEqual(orgao["status"], "concluida")
        self.assertEqual(len(orgao["tentativas"]), 2)
        self.assertEqual(registro["status_competencias"], "concluida")
        self.assertEqual(registro["competências"], "Competência 2\nOutra 2")

    def test_li_presente_sem_texto_persistente_permanece_parcial(self):
        portal = PortalSimulado(li_vazio_persistente=True, li_vazio_indice=2)
        with patch("scraper_sici_http.requests.Session", side_effect=portal.sessao):
            coletor = ColetorHTTP(ignoradas=[])
            try:
                with self.assertRaisesRegex(RuntimeError, "ORG2"):
                    coletor.coletar(orgao="ORG2", trabalhadores=1, pausa_recuperacao=0)
            finally:
                coletor.sessao.close()
        registro = coletor.resultados[0]
        self.assertEqual(registro["status_competencias"], "erro")
        self.assertIn("<li>", registro["erro_competencias"])

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
                    coletor.coletar(pausa_recuperacao=0)
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
                coletor.coletar(orgao="ORG3", pausa_recuperacao=0)
            finally:
                coletor.sessao.close()
        config.assert_called_once()
        self.assertEqual(coletor.trabalhadores_utilizados, 1)
        self.assertEqual([r["órgão"] for r in coletor.resultados], ["ORG3"])


if __name__ == "__main__":
    unittest.main()
