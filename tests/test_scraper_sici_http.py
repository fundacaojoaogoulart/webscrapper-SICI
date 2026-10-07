import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
import pandas as pd

from scraper_sici_http import ARVORE, CAMPOS, ColetorHTTP, No, comparar, evento, main


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
        filhos = {
            orgao.caminho: [paralelo, presidencia],
            presidencia.caminho: [unidade],
            unidade.caminho: [subordinada],
        }
        with patch.object(self.coletor, "expandir", side_effect=lambda caminho: filhos[caminho]), \
                patch.object(self.coletor, "capturar") as capturar:
            self.coletor.percorrer_indireta(orgao)
        self.assertEqual([(c.args[0].texto, c.args[2]) for c in capturar.call_args_list], [
            ("Presidência", "1º"), ("Diretoria", "2º"), ("Gerência", "3º")])
        self.assertNotIn(paralelo.caminho, self.coletor.visitados)
        self.assertNotIn(subordinada.caminho, self.coletor.visitados)

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
