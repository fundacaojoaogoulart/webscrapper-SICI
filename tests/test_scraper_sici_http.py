import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
import pandas as pd

from scraper_sici_http import ARVORE, CAMPOS, ColetorHTTP, No, comparar, evento, ler_extracao, main


class ComparacaoTest(unittest.TestCase):
    def test_executavel_salva_ao_lado_do_exe(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            arquivo = pasta / "referencia.xlsx"
            pd.DataFrame([["GBP", "1º", "A", "C", "T"]], columns=CAMPOS).to_excel(arquivo, index=False)
            with patch("scraper_sici_http.sys.frozen", True, create=True), patch("scraper_sici_http.sys.executable", str(pasta / "SICI_HTTP_Teste.exe")):
                codigo = main(["--somente-comparar", str(arquivo), "--comparar", str(arquivo)])
            self.assertEqual(codigo, 0)
            self.assertEqual(len(list((pasta / "resultados_http").glob("comparacao_*.xlsx"))), 1)

    def test_ordem_data_duplicidades_e_alteracao_de_campo(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            referencia, http, relatorio = [pasta / n for n in ("ref.xlsx", "http.xlsx", "diff.xlsx")]
            linha = ["GBP", "1º", "Gabinete", "Chefe", "Pessoa A"]
            outra = ["GBP", "2º", "Assessoria", "Assessor", ""]
            df = pd.DataFrame([linha, linha, outra], columns=CAMPOS)
            df["data_extracao"] = "01/01/2026"
            df.to_excel(referencia, index=False)
            novo = df.iloc[::-1].copy()
            novo["data_extracao"] = "02/01/2026"
            novo.to_excel(http, index=False)
            self.assertTrue(comparar(http, referencia, relatorio))
            novo.iloc[:2].to_excel(http, index=False)
            self.assertFalse(comparar(http, referencia, relatorio))
            faltantes = pd.read_excel(relatorio, sheet_name="faltantes_no_http")
            self.assertEqual(faltantes["quantidade"].sum(), 1)
            novo.loc[novo.index[0], "cargo"] = "Outro cargo"
            novo.to_excel(http, index=False)
            self.assertFalse(comparar(http, referencia, relatorio))

    def test_escopo_nao_esconde_orgaos_ausentes_na_coleta_completa(self):
        with tempfile.TemporaryDirectory() as pasta:
            pasta = Path(pasta)
            ref, http, rel = [pasta / n for n in ("ref.xlsx", "http.xlsx", "diff.xlsx")]
            df = pd.DataFrame([["GBP", "1º", "A", "C", "T"], ["OUTRO", "1º", "B", "C", "T"]], columns=CAMPOS)
            df.to_excel(ref, index=False)
            df.iloc[:1].to_excel(http, index=False)
            self.assertFalse(comparar(http, ref, rel))
            self.assertTrue(comparar(http, ref, rel, "gbp"))


class EscoposTest(unittest.TestCase):
    def setUp(self):
        self.direto = No("1\\1", "GBP", 1, "D", None)
        self.indireto = No("1\\42", "CCPAR", 1, "E", None)
        self.conselho = No("1\\42\\10", "Conselho Fiscal", 2, "", None)
        self.presidencia = No("1\\42\\11", "Presidência", 2, "", None)
        self.diretoria = No("1\\42\\11\\12", "Diretoria", 3, "", None)
        self.gerencia = No("1\\42\\11\\12\\13", "Gerência", 4, "", None)
        self.filhos = {
            self.direto.caminho: [],
            self.indireto.caminho: [self.conselho, self.presidencia],
            self.conselho.caminho: [],
            self.presidencia.caminho: [self.diretoria],
            self.diretoria.caminho: [self.gerencia],
        }
        for alvo, kwargs in [
            ("ORGAOS_INDIRETA", {"new": ("CCPAR",)}),
            ("config_manager.ler_config", {"return_value": {"PALAVRAS_IGNORADAS": []}}),
            ("ColetorHTTP.requisitar", {}),
            ("ColetorHTTP.nos", {"side_effect": lambda: [self.direto, self.indireto]}),
            ("ColetorHTTP.expandir", {"side_effect": lambda c: self.filhos[c]}),
            ("ColetorHTTP.capturar", {"new": self.captura_simulada()}),
        ]:
            contexto = patch("scraper_sici_http." + alvo, **kwargs)
            contexto.start()
            self.addCleanup(contexto.stop)

    @staticmethod
    def captura_simulada():
        def capturar(coletor, no, orgao, escalao):
            coletor.resultados.append(dict(zip(CAMPOS, [orgao, escalao, no.texto, "Cargo", "Titular"])))
        return capturar

    def coletar(self, modo, trabalhadores=4):
        coletor = ColetorHTTP(ignoradas=[])
        self.addCleanup(coletor.sessao.close)
        coletor.coletar(administracao=modo, trabalhadores=trabalhadores, pausa_recuperacao=0)
        return coletor

    def test_indiretas_equivalentes_em_ambas_serial_paralelo_e_recuperacao(self):
        esperado = self.coletar("indireta").resultados
        self.assertEqual([(r["área"], r["escalão"]) for r in esperado], [
            ("Presidência", "1º"), ("Diretoria", "2º"), ("Gerência", "3º")])
        for trabalhadores in (1, 4):
            with self.subTest(trabalhadores=trabalhadores):
                ambos = self.coletar("ambas", trabalhadores)
                self.assertEqual([r for r in ambos.resultados if r["órgão"] == "CCPAR"], esperado)
                self.assertEqual(ambos.resultados[0]["órgão"], "GBP")

        original = ColetorHTTP.percorrer_indireta
        tentativas = []

        def falhar_uma_vez(coletor, no):
            tentativas.append(no.caminho)
            if len(tentativas) == 1:
                raise RuntimeError("Falha simulada")
            return original(coletor, no)

        with patch.object(ColetorHTTP, "percorrer_indireta", falhar_uma_vez):
            recuperado = self.coletar("ambas")
        self.assertEqual(len(tentativas), 2)
        self.assertEqual([r for r in recuperado.resultados if r["órgão"] == "CCPAR"], esperado)

    def test_indireto_com_icone_A_nao_duplica_nem_entra_em_direta(self):
        self.indireto = No(self.indireto.caminho, "CCPAR", 1, "A", None)
        self.assertEqual([r["órgão"] for r in self.coletar("direta").resultados], ["GBP"])
        self.assertEqual(len(self.coletar("ambas").resultados), 4)

    def test_exportacao_e_leitura_de_duas_abas_inclusive_parcial(self):
        for parcial in (False, True):
            with self.subTest(parcial=parcial), tempfile.TemporaryDirectory() as pasta:
                original = ColetorHTTP.percorrer_indireta

                def percorrer(coletor, no):
                    original(coletor, no)
                    if parcial:
                        raise RuntimeError("Falha após capturar")

                with patch.object(ColetorHTTP, "percorrer_indireta", percorrer):
                    codigo = main(["--administracao", "ambas", "--saida-dir", pasta, "--pausa-recuperacao", "0"])
                self.assertEqual(codigo, 1 if parcial else 0)
                arquivo = next(Path(pasta).glob("sici_http_*.xlsx"))
                abas = pd.read_excel(arquivo, sheet_name=None)
                self.assertEqual(list(abas), ["Direta", "Indireta"])
                self.assertEqual(abas["Direta"]["órgão"].tolist(), ["GBP"])
                self.assertEqual(abas["Indireta"]["órgão"].tolist(), ["CCPAR"] * 3)
                self.assertEqual(abas["Indireta"]["escalão"].tolist(), ["1º", "2º", "3º"])
                self.assertEqual(len(ler_extracao(arquivo)), 4)
                self.assertEqual(len(ler_extracao(arquivo, "CCPAR")), 3)
                referencia = Path(pasta) / "referencia.xlsx"
                pd.concat(abas.values()).to_excel(referencia, index=False)
                self.assertTrue(comparar(arquivo, referencia, Path(pasta) / "comparacao.xlsx"))

    def test_exportacao_ambas_com_aba_vazia_preserva_cabecalhos(self):
        with tempfile.TemporaryDirectory() as pasta:
            codigo = main(["--administracao", "ambas", "--orgao", "CCPAR", "--saida-dir", pasta])
            self.assertEqual(codigo, 0)
            arquivo = next(Path(pasta).glob("sici_http_*.xlsx"))
            abas = pd.read_excel(arquivo, sheet_name=None)
            self.assertTrue(abas["Direta"].empty)
            self.assertEqual(list(abas["Direta"].columns), list(abas["Indireta"].columns))
            self.assertEqual(len(ler_extracao(arquivo)), 3)


class NavegacaoTest(unittest.TestCase):
    def setUp(self):
        with patch("scraper_sici_http.config_manager.ler_config", return_value={"PALAVRAS_IGNORADAS": ["ignorar"]}):
            self.coletor = ColetorHTTP()
        self.addCleanup(self.coletor.sessao.close)

    def test_formulario_preserva_estado_e_exclui_botoes(self):
        self.coletor.pagina = BeautifulSoup('''<form>
            <input name="__VIEWSTATE" value="estado-novo" type="hidden">
            <input name="exportar" value="Exportar" type="submit">
            <input name="filtro" type="checkbox">
            <select name="tipo"><option value="D" selected>Direta</option></select>
            </form>''', "html.parser")
        with patch.object(self.coletor, "requisitar") as enviar:
            self.coletor.postback("arvore", "s1\\42")
        self.assertEqual(dict(enviar.call_args.args[0]), {
            "__VIEWSTATE": "estado-novo", "tipo": "D", "__EVENTTARGET": "arvore", "__EVENTARGUMENT": "s1\\42"})

    def test_painel_anterior_nao_e_aceito(self):
        self.coletor.pagina = BeautifulSoup(f'''<input id="{ARVORE}_SelectedNode" value="anterior">
            <a id="anterior" href="javascript:__doPostBack('arvore','s1\\1')">Anterior</a>''', "html.parser")
        with patch.object(self.coletor, "postback"), self.assertRaisesRegex(RuntimeError, "Seleção não confirmada"):
            self.coletor.capturar(No("1\\2", "B", 1, "D", None), "GBP", "1º")
        self.assertEqual(self.coletor.resultados, [])

    def test_hierarquia_A_D_e_filtro(self):
        for tipo, limite, niveis in [("A", 4, [2, 3, 4]), ("D", 3, [1, 2, 3])]:
            self.coletor.visitados.clear()
            nos = [No("\\".join(["1"] + [str(j) for j in range(1, i + 1)]), f"N{i}", i, tipo, None)
                   for i in range(1, limite + 1)]
            ignorado = No(nos[0].caminho + "\\ign", "ignorar setor", 2, "", None)
            filhos = {n.caminho: [nos[i + 1]] if i + 1 < len(nos) else [] for i, n in enumerate(nos)}
            filhos[nos[0].caminho].append(ignorado)
            with patch.object(self.coletor, "expandir", side_effect=lambda c: filhos[c]), patch.object(self.coletor, "capturar") as capturar:
                self.coletor.percorrer(nos[0], "ORG", tipo)
            self.assertEqual([c.args[0].nivel for c in capturar.call_args_list], niveis)
            self.assertEqual([c.args[2] for c in capturar.call_args_list], ["1º", "2º", "3º"])

    def test_indireta_comeca_na_presidencia_e_para_no_terceiro_escalao(self):
        orgao = No("1\\42", "CCPAR", 1, "E", None)
        paralelo = No("1\\42\\10", "Conselho Fiscal", 2, "", None)
        presidencia = No("1\\42\\11", "Presidência", 2, "", None)
        unidade = No("1\\42\\11\\12", "Diretoria", 3, "", None)
        subordinada = No("1\\42\\11\\12\\13", "Gerência", 4, "", None)
        quarto_escalao = No("1\\42\\11\\12\\13\\14", "Serviço", 5, "", None)
        filhos = {
            orgao.caminho: [paralelo, presidencia],
            presidencia.caminho: [unidade],
            unidade.caminho: [subordinada],
            subordinada.caminho: [quarto_escalao],
        }
        with patch.object(self.coletor, "expandir", side_effect=lambda caminho: filhos[caminho]), \
                patch.object(self.coletor, "capturar") as capturar:
            self.coletor.percorrer_indireta(orgao)
        self.assertEqual([(c.args[0].texto, c.args[2]) for c in capturar.call_args_list], [
            ("Presidência", "1º"), ("Diretoria", "2º"), ("Gerência", "3º")])
        self.assertNotIn(paralelo.caminho, self.coletor.visitados)
        self.assertIn(subordinada.caminho, self.coletor.visitados)
        self.assertNotIn(quarto_escalao.caminho, self.coletor.visitados)

    def test_normalizacao_dos_nomes_da_lista_indireta(self):
        from scraper_sici_http import normalizar_nome_orgao
        self.assertEqual(normalizar_nome_orgao("RIO-ÁGUAS"), normalizar_nome_orgao("Rio Águas"))
        self.assertEqual(normalizar_nome_orgao("CMTC RIO"), normalizar_nome_orgao("CMTC Rio"))

    def test_escape_do_caminho_webforms(self):
        link = BeautifulSoup(r'''<a href="javascript:__doPostBack('arvore','s1\\4100')">GBP</a>''', "html.parser").a
        self.assertEqual(evento(link), ("arvore", "s1\\4100"))

    def test_nos_separam_icone_placeholder_e_identidade(self):
        self.coletor.pagina = BeautifulSoup(f'''<div id="{ARVORE}"><table><tr>
            <td><div style="width:20px;height:1px"></div></td>
            <td><a href="javascript:__doPostBack('arvore','t1\\\\42')"><img alt="Expand ORG"></a></td>
            <td><a id="{ARVORE}t1i"><img src="folder-D.gif"></a></td>
            <td><a id="{ARVORE}t1" href="javascript:__doPostBack('arvore','s1\\\\42')">ORG</a></td>
            </tr></table><table><tr><td>
            <a id="{ARVORE}t2" href="javascript:__doPostBack('arvore','s1\\\\42\\\\')">0</a>
            </td></tr></table></div>''', "html.parser")
        nos = self.coletor.nos()
        self.assertEqual(nos, [No("1\\42", "ORG", 1, "D", ("arvore", "t1\\42"))])

    def test_nos_identificam_tipos_de_orgao_da_indireta(self):
        for tipo in ("E", "F"):
            self.coletor.pagina = BeautifulSoup(f'''<div id="{ARVORE}"><table><tr>
                <td><div style="width:20px;height:1px"></div></td>
                <td><a href="javascript:__doPostBack('arvore','t1\\\\42')"><img alt="Expand ORG"></a></td>
                <td><img src="folder-{tipo}.gif"></td><td>
                <a id="{ARVORE}t1" href="javascript:__doPostBack('arvore','s1\\\\42')">ORG</a>
                </td></tr></table></div>''', "html.parser")
            self.assertEqual(self.coletor.nos()[0].tipo, tipo)


if __name__ == "__main__":
    unittest.main()
