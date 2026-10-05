"""Coleta experimental do SICI por HTTP e comparação com o Excel do Selenium.

Exemplos:
    python scraper_sici_http.py --orgao GBP --comparar sici_extracao_20261005_0900.xlsx
    python scraper_sici_http.py --comparar sici_extracao_20261005_0900.xlsx
    python scraper_sici_http.py --somente-comparar coleta_http.xlsx --comparar coleta_selenium.xlsx
    python scraper_sici_http.py --trabalhadores 4 --comparar coleta_selenium.xlsx

Saídas em resultados_http/: Excel com as seis colunas originais, JSON com
tempos/status e relatório de comparação (resumo, contagens, faltantes, extras).
Use uma referência recente e o mesmo config.txt nas duas coletas. A comparação
é exata nos cinco campos de dados, inclusive duplicidades; ignora ordem e data.
Uma linha alterada aparece como faltante + extra, sem associação por nomes.
Código de saída: 0 = concluído/equivalente; 1 = coleta parcial; 2 = divergência.
Uma coleta interrompida é salva como PARCIAL e não comparada automaticamente.
Por padrão, quatro trabalhadores coletam órgãos com sessões independentes.
O Excel mantém a ordem dos órgãos na árvore. segundos_coleta mede o tempo
decorrido; segundos_http soma requisições concorrentes e pode superar esse tempo.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from threading import Event
import time

from bs4 import BeautifulSoup
import pandas as pd
import requests

import config_manager


URL = "https://sici.rio.rj.gov.br/PAG/principal.aspx"
PREFIXO = "ContentPlaceHolder1_"
ARVORE = PREFIXO + "ua_treeview"
CAMPOS = ["órgão", "escalão", "área", "cargo", "titular"]
COLUNAS = CAMPOS + ["data_extracao"]
EVENTO = re.compile(r"__doPostBack\('([^']*)','([^']*)'\)")


@dataclass(frozen=True)
class No:
    caminho: str
    texto: str
    nivel: int
    tipo: str
    expandir: tuple | None


def evento(link):
    encontrado = EVENTO.search(link.get("href", ""))
    if not encontrado:
        raise ValueError("Link da árvore sem postback reconhecido.")
    return tuple(valor.replace("\\\\", "\\") for valor in encontrado.groups())


def texto(elemento):
    if elemento is None:
        return ""
    # Aproxima o texto visível, incluindo quebras explícitas do painel.
    for br in elemento.find_all("br"):
        br.replace_with("\n")
    return elemento.get_text().replace("\xa0", " ").strip()


class ColetorHTTP:
    def __init__(self, timeout=30, ignoradas=None, cancelamento=None):
        self.sessao = requests.Session()
        # WebForms muda o HTML para clientes não reconhecidos (modo downlevel).
        self.sessao.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        self.timeout = timeout
        self.pagina = None
        self.requisicoes = 0
        self.segundos_http = 0.0
        self.resultados = []
        self.visitados = set()
        self.ignoradas = list(config_manager.ler_config()["PALAVRAS_IGNORADAS"] if ignoradas is None else ignoradas)
        self.cancelamento = cancelamento if cancelamento is not None else Event()
        self.orgaos = []
        self.trabalhadores_utilizados = 0

    def requisitar(self, dados=None):
        if self.cancelamento.is_set():
            raise RuntimeError("Coleta cancelada.")
        inicio = time.perf_counter()
        try:
            if dados is None:
                resposta = self.sessao.get(URL, timeout=self.timeout)
            else:
                resposta = self.sessao.post(URL, data=dados, timeout=self.timeout)
            resposta.raise_for_status()
        finally:
            self.requisicoes += 1
            self.segundos_http += time.perf_counter() - inicio
        pagina = BeautifulSoup(resposta.content, "html.parser")
        if pagina.find(id=ARVORE) is None or pagina.find("input", attrs={"name": "__VIEWSTATE"}) is None:
            raise RuntimeError("Resposta não contém a árvore/estado esperado do SICI.")
        self.pagina = pagina

    def formulario(self):
        form = self.pagina.find("form")
        dados = []
        for elemento in form.select("input[name], select[name], textarea[name]"):
            if elemento.has_attr("disabled"):
                continue
            nome = elemento["name"]
            if elemento.name == "select":
                opcoes = elemento.find_all("option", selected=True)
                if not opcoes:
                    primeira = elemento.find("option")
                    opcoes = [primeira] if primeira else []
                dados.extend((nome, op.get("value", op.get_text())) for op in opcoes)
            elif elemento.name == "textarea":
                dados.append((nome, elemento.get_text()))
            else:
                tipo = elemento.get("type", "text").lower()
                if tipo in {"submit", "button", "image", "reset", "file"}:
                    continue
                if tipo in {"checkbox", "radio"} and not elemento.has_attr("checked"):
                    continue
                dados.append((nome, elemento.get("value", "")))
        return dados

    def postback(self, alvo, argumento):
        dados = [(k, v) for k, v in self.formulario()
                 if k not in {"__EVENTTARGET", "__EVENTARGUMENT", "__ASYNCPOST"}]
        dados.extend([("__EVENTTARGET", alvo), ("__EVENTARGUMENT", argumento)])
        # POST completo: a resposta traz HTML e um novo VIEWSTATE juntos.
        # Não repetimos POSTs automaticamente: uma expansão pode ser um toggle.
        self.requisitar(dados)

    def nos(self):
        nos = []
        for link in self.pagina.find(id=ARVORE).find_all("a", id=re.compile(r"^" + ARVORE + r"t\d+$")):
            _, argumento = evento(link)
            if not argumento.startswith("s"):
                raise RuntimeError("Evento de seleção inesperado.")
            caminho = argumento[1:]
            if caminho.endswith("\\"):
                continue  # placeholder dos filhos ainda não carregados
            tr = link.find_parent("tr")
            nivel = len(tr.select('div[style*="width:20px"]'))
            tipo = ""
            expandir = None
            for imagem in tr.find_all("img"):
                src = imagem.get("src", "")
                if src.endswith("-A.gif"):
                    tipo = "A"
                elif src.endswith("-D.gif"):
                    tipo = "D"
                if imagem.get("alt", "").startswith("Expand"):
                    expandir = evento(imagem.find_parent("a"))
            nos.append(No(caminho, texto(link), nivel, tipo, expandir))
        return nos

    def localizar(self, caminho):
        encontrados = [no for no in self.nos() if no.caminho == caminho]
        if len(encontrados) != 1:
            raise RuntimeError(f"Nó ausente ou ambíguo: {caminho}")
        return encontrados[0]

    def expandir(self, caminho):
        no = self.localizar(caminho)
        if no.expandir:
            self.postback(*no.expandir)
            if self.localizar(caminho).expandir:
                raise RuntimeError(f"Expansão não confirmada: {no.texto}")
        filhos = [n for n in self.nos() if n.caminho.rpartition("\\")[0] == caminho]
        if no.expandir and not filhos:
            raise RuntimeError(f"Expansão sem filhos verificáveis: {no.texto}")
        return filhos

    def capturar(self, no, orgao, escalao):
        self.postback("ctl00$ContentPlaceHolder1$ua_treeview", "s" + no.caminho)
        selecionado = self.pagina.find(id=ARVORE + "_SelectedNode")
        link = self.pagina.find(id=selecionado.get("value", "")) if selecionado else None
        if link is None or evento(link)[1] != "s" + no.caminho:
            raise RuntimeError(f"Seleção não confirmada: {no.texto}")
        ids = ["lblNomeUnidadeGestaoSelecionada", "lblCargo", "lblTitular"]
        elementos = [self.pagina.find(id=PREFIXO + nome) for nome in ids]
        if elementos[0] is None:
            raise RuntimeError(f"Painel ausente após selecionar {no.texto}")
        area, cargo, titular = map(texto, elementos)
        self.resultados.append(dict(zip(CAMPOS, [orgao, escalao, area, cargo, titular])))

    def percorrer(self, no, orgao, tipo):
        if self.cancelamento.is_set():
            raise RuntimeError("Coleta cancelada.")
        if no.caminho in self.visitados:
            raise RuntimeError(f"Nó visitado mais de uma vez: {no.caminho}")
        self.visitados.add(no.caminho)
        if not no.texto or any(p in no.texto.lower() for p in self.ignoradas):
            return
        limite = 4 if tipo == "A" else 3
        # Mesmas regras do scraper atual: A não captura nível 1;
        # A: níveis 2/3/4 -> escalões 1/2/3; D: níveis 1/2/3.
        filhos = self.expandir(no.caminho) if no.nivel < limite else []
        if not (tipo == "A" and no.nivel == 1):
            escalao = no.nivel - 1 if tipo == "A" else no.nivel
            self.capturar(no, orgao, f"{escalao}º")
        for filho in filhos:
            if filho.nivel != no.nivel + 1:
                raise RuntimeError(f"Hierarquia inesperada: {filho.caminho}")
            self.percorrer(filho, orgao, tipo)

    def _coletar_orgao(self, no):
        """Uma tarefa possui sessão, cookies, VIEWSTATE e resultados próprios."""
        inicio = time.perf_counter()
        coletor = None
        erro = None
        try:
            coletor = ColetorHTTP(self.timeout, self.ignoradas, self.cancelamento)
            coletor.requisitar()
            atual = coletor.localizar(no.caminho)
            if (atual.texto, atual.nivel, atual.tipo) != (no.texto, no.nivel, no.tipo):
                raise RuntimeError("O órgão mudou entre a descoberta e a coleta.")
            coletor.percorrer(atual, atual.texto, atual.tipo)
        except Exception as exc:
            erro = f"{type(exc).__name__}: {exc}"
        finally:
            if coletor is not None:
                coletor.sessao.close()
        registros = coletor.resultados if coletor is not None else []
        return registros, {
            "orgao": no.texto, "caminho": no.caminho,
            "status": "PARCIAL" if erro else "concluida", "erro": erro,
            "registros": len(registros),
            "requisicoes": coletor.requisicoes if coletor is not None else 0,
            "segundos_http": coletor.segundos_http if coletor is not None else 0.0,
            "segundos_coleta": round(time.perf_counter() - inicio, 3),
        }

    def coletar(self, orgao=None, trabalhadores=4):
        if trabalhadores < 1:
            raise ValueError("O número de trabalhadores deve ser positivo.")
        self.requisitar()
        raizes = [n for n in self.nos() if n.nivel == 1 and n.tipo in {"A", "D"}]
        if orgao:
            raizes = [n for n in raizes if n.texto.casefold() == orgao.casefold()]
        raizes = [n for n in raizes if n.texto and not any(p in n.texto.lower() for p in self.ignoradas)]
        if not raizes:
            raise RuntimeError("Nenhum órgão A/D encontrado para o escopo solicitado.")
        if len({n.caminho for n in raizes}) != len(raizes):
            raise RuntimeError("Órgãos duplicados na árvore inicial.")
        self.trabalhadores_utilizados = min(trabalhadores, len(raizes))
        print(f"Coletando {len(raizes)} órgãos com {self.trabalhadores_utilizados} trabalhadores...", flush=True)
        executor = ThreadPoolExecutor(max_workers=self.trabalhadores_utilizados, thread_name_prefix="sici")
        tarefas = []
        try:
            for no in raizes:
                tarefas.append(executor.submit(self._coletar_orgao, no))
            for tarefa in as_completed(tarefas):
                _, info = tarefa.result()
                print(f"{info['orgao']}: {info['status']}, {info['registros']} registros "
                      f"em {info['segundos_coleta']:.1f}s", flush=True)
        except BaseException:
            # Ctrl+C cancela a fila; tarefas em curso param antes da próxima requisição.
            self.cancelamento.set()
            for tarefa in tarefas:
                tarefa.cancel()
            raise
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
            # Agrega apenas após terminar as tarefas, na ordem original da árvore.
            # Falhas preservam os registros já coletados e não viram sucesso.
            for indice, no in enumerate(raizes):
                tarefa = tarefas[indice] if indice < len(tarefas) else None
                if tarefa is None or tarefa.cancelled():
                    registros, info = [], {
                        "orgao": no.texto, "caminho": no.caminho, "status": "cancelada",
                        "erro": "Tarefa não executada.", "registros": 0,
                        "requisicoes": 0, "segundos_http": 0.0, "segundos_coleta": 0.0,
                    }
                else:
                    registros, info = tarefa.result()
                self.resultados.extend(registros)
                self.requisicoes += info["requisicoes"]
                self.segundos_http += info["segundos_http"]
                self.orgaos.append(info)
        falhas = [info["orgao"] for info in self.orgaos if info["status"] != "concluida"]
        if falhas:
            raise RuntimeError("Coleta incompleta nos órgãos: " + ", ".join(falhas))


def ler_extracao(caminho, orgao=None):
    df = pd.read_excel(caminho, dtype=str, keep_default_na=False)
    ausentes = set(CAMPOS) - set(df.columns)
    if ausentes:
        raise ValueError(f"{caminho}: colunas ausentes: {sorted(ausentes)}")
    if orgao:
        df = df[df["órgão"].str.casefold() == orgao.casefold()]
    if df.empty:
        raise ValueError(f"{caminho}: nenhum registro no escopo solicitado.")
    return df[CAMPOS]


def comparar(arquivo_http, referencia, destino, orgao=None):
    http = ler_extracao(arquivo_http, orgao)
    atual = ler_extracao(referencia, orgao)
    a = Counter(atual.itertuples(index=False, name=None))
    b = Counter(http.itertuples(index=False, name=None))
    faltantes, extras = a - b, b - a

    def diferencas(contador):
        return pd.DataFrame([dict(zip(CAMPOS + ["quantidade"], (*chave, qtd)))
                             for chave, qtd in contador.items()], columns=CAMPOS + ["quantidade"])

    contagens = pd.concat([
        atual.groupby(["órgão", "escalão"]).size().rename("selenium"),
        http.groupby(["órgão", "escalão"]).size().rename("http"),
    ], axis=1).fillna(0).astype(int).reset_index()
    contagens["diferença"] = contagens["http"] - contagens["selenium"]
    iguais = not faltantes and not extras
    resumo = {
        "referencia": str(Path(referencia).resolve()),
        "extracao_http": str(Path(arquivo_http).resolve()),
        "escopo": orgao or "todos os órgãos",
        "registros_selenium": len(atual), "registros_http": len(http),
        "ocorrencias_iguais": sum((a & b).values()),
        "faltantes_no_http": sum(faltantes.values()),
        "extras_no_http": sum(extras.values()),
        "equivalentes": iguais,
        "criterio": "Cinco campos exatos, incluindo multiplicidade; ordem e data_extracao ignoradas.",
    }
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        pd.DataFrame(resumo.items(), columns=["métrica", "valor"]).to_excel(writer, sheet_name="resumo", index=False)
        contagens.to_excel(writer, sheet_name="por_orgao_escalao", index=False)
        diferencas(faltantes).to_excel(writer, sheet_name="faltantes_no_http", index=False)
        diferencas(extras).to_excel(writer, sheet_name="extras_no_http", index=False)
    print(f"Comparação: {'EQUIVALENTES' if iguais else 'DIVERGENTES'}. Relatório: {destino}")
    return iguais


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--orgao", help="Nome exato do órgão, por exemplo GBP ou CASA CIVIL")
    parser.add_argument("--comparar", type=Path, help="Excel original gerado pelo Selenium")
    parser.add_argument("--somente-comparar", type=Path, help="Excel HTTP existente; não acessa o portal")
    pasta_app = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    parser.add_argument("--saida-dir", type=Path, default=pasta_app / "resultados_http")
    parser.add_argument("--timeout", type=float, default=30, help="Timeout HTTP em segundos (padrão: 30)")
    parser.add_argument("--trabalhadores", type=int, default=4, help="Órgãos simultâneos (padrão: 4; use 1 para execução serial)")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout deve ser positivo")
    if args.trabalhadores < 1:
        parser.error("--trabalhadores deve ser positivo")
    if args.somente_comparar and not args.comparar:
        parser.error("--somente-comparar exige --comparar")
    if args.comparar:
        ler_extracao(args.comparar, args.orgao)  # valida antes de acessar a rede
    args.saida_dir.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    arquivo = args.somente_comparar
    if arquivo is None:
        coletor = ColetorHTTP(args.timeout)
        inicio_coleta = datetime.now().astimezone()
        inicio = time.perf_counter()
        erro = None
        try:
            coletor.coletar(args.orgao, args.trabalhadores)
            if not coletor.resultados:
                raise RuntimeError("Coleta sem registros.")
        except (Exception, KeyboardInterrupt) as exc:
            erro = f"{type(exc).__name__}: {exc}"
        finally:
            coletor.sessao.close()
        duracao = time.perf_counter() - inicio
        fim_coleta = datetime.now().astimezone()
        status = "PARCIAL" if erro else "concluida"
        arquivo = args.saida_dir / f"sici_http_{status}_{carimbo}.xlsx"
        df = pd.DataFrame(coletor.resultados, columns=CAMPOS)
        df["data_extracao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        df.to_excel(arquivo, index=False)
        metricas = {
            "status": status, "erro": erro, "orgao": args.orgao,
            "registros": len(df), "requisicoes": coletor.requisicoes,
            "segundos_coleta": round(duracao, 3),
            "segundos_http": round(coletor.segundos_http, 3),
            "inicio_coleta": inicio_coleta.isoformat(), "fim_coleta": fim_coleta.isoformat(),
            "trabalhadores_solicitados": args.trabalhadores,
            "trabalhadores_utilizados": coletor.trabalhadores_utilizados,
            "nota_tempos": "segundos_coleta é tempo decorrido, sem exportação/comparação; segundos_http é a soma das requisições concorrentes, incluindo descoberta.",
            "orgaos": coletor.orgaos,
            "palavras_ignoradas": coletor.ignoradas,
        }
        arquivo.with_suffix(".json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{status}: {len(df)} registros em {duracao:.1f}s. Arquivo: {arquivo}")
        print(f"Tempo total da coleta HTTP: {duracao / 60:.2f} minutos ({duracao:.1f} segundos).")
        if erro:
            print(f"Coleta incompleta: {erro}")
            return 1
    if args.comparar:
        iguais = comparar(arquivo, args.comparar, args.saida_dir / f"comparacao_{carimbo}.xlsx", args.orgao)
        return 0 if iguais else 2
    print("Use --comparar com uma extração do Selenium para verificar equivalência.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
