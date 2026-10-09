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
import unicodedata

from bs4 import BeautifulSoup
import pandas as pd
import requests

import config_manager


URL = "https://sici.rio.rj.gov.br/PAG/principal.aspx"
PREFIXO = "ContentPlaceHolder1_"
ARVORE = PREFIXO + "ua_treeview"
CAMPOS = ["órgão", "escalão", "área", "cargo", "titular"]
CAMPO_COMPETENCIAS = "competências"
STATUS_COMPETENCIAS = "status_competencias"
ERRO_COMPETENCIAS = "erro_competencias"
COLUNAS = CAMPOS + [CAMPO_COMPETENCIAS, "data_extracao"]
SELETOR_INFORMACOES = PREFIXO + "DDLInformacoesGerais"
EVENTO_INFORMACOES = "ctl00$ContentPlaceHolder1$DDLInformacoesGerais"
PAINEL_COMPETENCIAS = PREFIXO + "PanelCompetenciaInterno"
EVENTO = re.compile(r"__doPostBack\('([^']*)','([^']*)'\)")
ORGAOS_INDIRETA = (
    "CCPAR", "CET-RIO", "CMTC RIO", "COMLURB", "GEO-RIO", "IPLANRIO",
    "RIO-ÁGUAS", "RIOFILME", "RIOLUZ", "RIOSAÚDE", "RIOTUR", "RIO-URBE",
)


def normalizar_nome_orgao(valor):
    valor = unicodedata.normalize("NFKD", valor)
    valor = "".join(c for c in valor if not unicodedata.combining(c))
    return " ".join(valor.casefold().replace("-", " ").split())


def orgao_indireto(nome):
    return normalizar_nome_orgao(nome) in {normalizar_nome_orgao(n) for n in ORGAOS_INDIRETA}


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
        self.trabalhadores_por_rodada = []
        self.trabalhadores_configurados_por_rodada = []
        self.etapa_atual = "inicialização"
        self.unidade_atual = None

    def requisitar(self, dados=None):
        if self.cancelamento.is_set():
            raise RuntimeError("Coleta cancelada.")
        inicio = time.perf_counter()
        if dados is None:
            self.etapa_atual = "GET inicial"
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

    def postback(self, alvo, argumento, substituir=None):
        dados = [(k, v) for k, v in self.formulario()
                 if k not in {"__EVENTTARGET", "__EVENTARGUMENT", "__ASYNCPOST", *(substituir or {})}]
        dados.extend((chave, valor) for chave, valor in (substituir or {}).items())
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
                elif src.endswith("-E.gif"):
                    tipo = "E"
                elif src.endswith("-F.gif"):
                    tipo = "F"
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
        self.etapa_atual = "expansão da árvore"
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
        self.unidade_atual = no.texto
        self.etapa_atual = "seleção da unidade"
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
        registro = dict(zip(CAMPOS, [orgao, escalao, area, cargo, titular]))
        registro[CAMPO_COMPETENCIAS] = ""
        registro[STATUS_COMPETENCIAS] = "pendente"
        registro[ERRO_COMPETENCIAS] = ""
        self.resultados.append(registro)
        try:
            competencias = self.competencias(no.caminho, registro)
            registro[CAMPO_COMPETENCIAS] = competencias
            registro[STATUS_COMPETENCIAS] = "concluida" if competencias else "vazia"
        except Exception as exc:
            registro[STATUS_COMPETENCIAS] = "erro"
            registro[ERRO_COMPETENCIAS] = f"{type(exc).__name__}: {exc}"
            raise

    def competencias(self, caminho, registro=None):
        self.etapa_atual = "validação do dropdown de competências"
        seletor = self.pagina.find(id=SELETOR_INFORMACOES)
        if seletor is None or seletor.find("option", value="2") is None or seletor.find("option", value="1") is None:
            raise RuntimeError("Dropdown de informações não contém as opções esperadas.")
        if seletor.find("option", selected=True) is None or seletor.find("option", selected=True).get("value") != "1":
            raise RuntimeError("Painel não estava em Informações Gerais antes de ler competências.")
        self.etapa_atual = "abertura do painel de competências"
        self.postback(EVENTO_INFORMACOES, "", {"ctl00$ContentPlaceHolder1$DDLInformacoesGerais": "2"})
        self._validar_selecao(caminho)
        seletor = self.pagina.find(id=SELETOR_INFORMACOES)
        selecionada = seletor.find("option", selected=True) if seletor else None
        if selecionada is None or selecionada.get("value") != "2":
            raise RuntimeError("Resposta não confirmou o modo Competências (value=2).")
        painel = self.pagina.find(id=PAINEL_COMPETENCIAS)
        if painel is None:
            raise RuntimeError("Resposta sem painel de competências.")
        estilo = painel.get("style", "").replace(" ", "").lower()
        if "display:none" in estilo or "visibility:hidden" in estilo:
            raise RuntimeError("Painel de competências está oculto na resposta.")
        elementos_lista = painel.find_all("li")
        itens = [texto(item) for item in elementos_lista]
        conteudo = "\n".join(item for item in itens if item)
        if elementos_lista and not conteudo:
            raise RuntimeError("Painel de Competências contém item(ns) <li>, mas o texto extraído está vazio.")
        if not conteudo:
            conteudo = texto(painel)
        if registro is not None:
            registro[CAMPO_COMPETENCIAS] = conteudo
        self.etapa_atual = "restauração de Informações Gerais"
        self.postback(EVENTO_INFORMACOES, "", {"ctl00$ContentPlaceHolder1$DDLInformacoesGerais": "1"})
        self._validar_selecao(caminho)
        seletor = self.pagina.find(id=SELETOR_INFORMACOES)
        selecionada = seletor.find("option", selected=True) if seletor else None
        if selecionada is None or selecionada.get("value") != "1":
            raise RuntimeError("Não foi possível restaurar Informações Gerais.")
        return conteudo

    def _validar_selecao(self, caminho):
        selecionado = self.pagina.find(id=ARVORE + "_SelectedNode")
        link = self.pagina.find(id=selecionado.get("value", "")) if selecionado else None
        if link is None or evento(link)[1] != "s" + caminho:
            raise RuntimeError(f"Unidade selecionada mudou durante a leitura: {caminho}")

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

    def percorrer_indireta(self, orgao_no):
        """Coleta somente o ramo da Presidência como escalões 1º a 3º."""
        if self.cancelamento.is_set():
            raise RuntimeError("Coleta cancelada.")
        filhos_orgao = self.expandir(orgao_no.caminho)
        presidencias = [filho for filho in filhos_orgao
                        if filho.texto.strip().casefold() == "presidência"]
        if len(presidencias) != 1:
            raise RuntimeError(
                f"Esperada uma Presidência em {orgao_no.texto}; encontradas {len(presidencias)}."
            )

        def percorrer_ramo(no, escalao):
            if self.cancelamento.is_set():
                raise RuntimeError("Coleta cancelada.")
            if no.caminho in self.visitados:
                raise RuntimeError(f"Nó visitado mais de uma vez: {no.caminho}")
            self.visitados.add(no.caminho)
            if not no.texto or any(p in no.texto.lower() for p in self.ignoradas):
                return
            filhos = self.expandir(no.caminho) if escalao < 3 else []
            self.capturar(no, orgao_no.texto, f"{escalao}º")
            for filho in filhos:
                if filho.nivel != no.nivel + 1:
                    raise RuntimeError(f"Hierarquia inesperada: {filho.caminho}")
                percorrer_ramo(filho, escalao + 1)

        percorrer_ramo(presidencias[0], 1)

    def _coletar_orgao(self, no, administracao="direta"):
        """Uma tarefa possui sessão, cookies, VIEWSTATE e resultados próprios."""
        inicio = time.perf_counter()
        coletor = None
        erro = None
        etapa = None
        unidade = None
        try:
            coletor = ColetorHTTP(self.timeout, self.ignoradas, self.cancelamento)
            coletor.administracao = administracao
            coletor.requisitar()
            atual = coletor.localizar(no.caminho)
            if (atual.texto, atual.nivel, atual.tipo) != (no.texto, no.nivel, no.tipo):
                raise RuntimeError("O órgão mudou entre a descoberta e a coleta.")
            if orgao_indireto(atual.texto):
                coletor.percorrer_indireta(atual)
            else:
                coletor.percorrer(atual, atual.texto, atual.tipo)
        except Exception as exc:
            erro = f"{type(exc).__name__}: {exc}"
            etapa = coletor.etapa_atual if coletor is not None else "criação da sessão"
            unidade = coletor.unidade_atual if coletor is not None else None
        finally:
            if coletor is not None:
                coletor.sessao.close()
        registros = coletor.resultados if coletor is not None else []
        return registros, {
            "orgao": no.texto, "caminho": no.caminho,
            "status": "PARCIAL" if erro else "concluida", "erro": erro,
            "etapa_erro": etapa, "unidade_erro": unidade,
            "registros": len(registros),
            "requisicoes": coletor.requisicoes if coletor is not None else 0,
            "segundos_http": coletor.segundos_http if coletor is not None else 0.0,
            "segundos_coleta": round(time.perf_counter() - inicio, 3),
        }

    def _executar_rodada(self, raizes, trabalhadores, administracao="direta"):
        executor = ThreadPoolExecutor(max_workers=min(trabalhadores, len(raizes)), thread_name_prefix="sici")
        tarefas = []
        interrompido = False
        try:
            for no in raizes:
                tarefas.append(executor.submit(self._coletar_orgao, no, administracao))
            for tarefa in as_completed(tarefas):
                _, info = tarefa.result()
                print(f"{info['orgao']}: {info['status']}, {info['registros']} registros "
                      f"em {info['segundos_coleta']:.1f}s", flush=True)
        except KeyboardInterrupt:
            self.cancelamento.set()
            for tarefa in tarefas:
                tarefa.cancel()
            interrompido = True
        except BaseException:
            self.cancelamento.set()
            for tarefa in tarefas:
                tarefa.cancel()
            raise
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
        resultados = {}
        for indice, no in enumerate(raizes):
            tarefa = tarefas[indice] if indice < len(tarefas) else None
            if tarefa is None or tarefa.cancelled():
                registros, info = [], {
                    "orgao": no.texto, "caminho": no.caminho, "status": "PARCIAL",
                    "erro": "Tarefa não executada.", "etapa_erro": "agendamento",
                    "unidade_erro": None, "registros": 0, "requisicoes": 0,
                    "segundos_http": 0.0, "segundos_coleta": 0.0,
                }
            else:
                registros, info = tarefa.result()
            resultados[no.caminho] = (registros, info)
        if interrompido:
            self.interrompido = True
        return resultados

    def coletar(self, orgao=None, trabalhadores=4, pausa_recuperacao=5, administracao="direta"):
        if trabalhadores < 1:
            raise ValueError("O número de trabalhadores deve ser positivo.")
        if pausa_recuperacao < 0:
            raise ValueError("A pausa de recuperação não pode ser negativa.")
        if administracao not in {"direta", "indireta", "ambas"}:
            raise ValueError("Administração deve ser direta, indireta ou ambas.")
        self.administracao = administracao
        self.requisitar()
        todos_nos = [n for n in self.nos() if n.nivel == 1]
        diretos = [n for n in todos_nos if n.tipo in {"A", "D"} and not orgao_indireto(n.texto)]
        nomes_indireta = {normalizar_nome_orgao(nome) for nome in ORGAOS_INDIRETA}
        indiretos = [n for n in todos_nos if orgao_indireto(n.texto)]
        if administracao == "direta":
            raizes = diretos
        elif administracao == "indireta":
            raizes = indiretos
        else:
            raizes = diretos + indiretos
        if orgao:
            raizes = [n for n in raizes
                      if normalizar_nome_orgao(n.texto) == normalizar_nome_orgao(orgao)]
        raizes = [n for n in raizes if n.texto and not any(p in n.texto.lower() for p in self.ignoradas)]
        if not raizes:
            raise RuntimeError("Nenhum órgão encontrado para o escopo solicitado.")
        if administracao in {"indireta", "ambas"}:
            encontrados = {normalizar_nome_orgao(n.texto) for n in indiretos}
            faltantes = sorted(n for n in nomes_indireta if n not in encontrados)
            if orgao:
                faltantes = [n for n in faltantes if n == normalizar_nome_orgao(orgao)]
            if faltantes:
                raise RuntimeError("Órgãos da administração indireta ausentes na árvore: " + ", ".join(faltantes))
        if len({n.caminho for n in raizes}) != len(raizes):
            raise RuntimeError("Órgãos duplicados na árvore inicial.")
        self.trabalhadores_utilizados = min(trabalhadores, len(raizes))
        self.interrompido = False
        print(f"Coletando {len(raizes)} órgãos com {self.trabalhadores_utilizados} trabalhadores...", flush=True)
        pendentes = list(raizes)
        finais = {}
        historico = {no.caminho: [] for no in raizes}
        trabalhadores_rodada = self.trabalhadores_utilizados
        numero_rodada = 1
        # A redução pela metade dos trabalhadores fornece bit_length(N) rodadas
        # (N, N//2, ..., 1). Com um único trabalhador isso daria uma rodada só,
        # sem retry; garantimos ao menos duas rodadas para que as parciais sejam
        # tentadas novamente também na execução serial.
        max_rodadas = max(2, self.trabalhadores_utilizados.bit_length())
        while pendentes:
            trabalhadores_efetivos = min(trabalhadores_rodada, len(pendentes))
            self.trabalhadores_por_rodada.append(trabalhadores_efetivos)
            self.trabalhadores_configurados_por_rodada.append(trabalhadores_rodada)
            print(f"Rodada {numero_rodada}: {len(pendentes)} órgãos pendentes, "
                  f"{trabalhadores_efetivos} trabalhadores.", flush=True)
            rodada = self._executar_rodada(pendentes, trabalhadores_rodada, administracao)
            novos_pendentes = []
            for no in pendentes:
                registros, info = rodada[no.caminho]
                historico[no.caminho].append({**info, "rodada": numero_rodada,
                                              "trabalhadores_configurados": trabalhadores_rodada,
                                              "trabalhadores": min(trabalhadores_rodada, len(pendentes))})
                if info["status"] == "concluida":
                    finais[no.caminho] = (registros, info)
                else:
                    novos_pendentes.append(no)
                    # Mantém uma tentativa parcial completa, sem misturar dados
                    # de sessões e estados WebForms distintos.
                    anterior = finais.get(no.caminho)
                    if anterior is None or len(registros) > len(anterior[0]):
                        finais[no.caminho] = (registros, info)
            pendentes = novos_pendentes
            if not pendentes or self.interrompido or numero_rodada >= max_rodadas:
                break
            trabalhadores_rodada = max(1, trabalhadores_rodada // 2)
            numero_rodada += 1
            if pausa_recuperacao:
                time.sleep(pausa_recuperacao)

        self.resultados = []
        for no in raizes:
            registros, info = finais[no.caminho]
            self.resultados.extend(registros)
            tentativas = historico[no.caminho]
            info = {**info, "tentativas": tentativas}
            self.orgaos.append(info)
            self.requisicoes += sum(t["requisicoes"] for t in tentativas)
            self.segundos_http += sum(t["segundos_http"] for t in tentativas)
        falhas = [info["orgao"] for info in self.orgaos if info["status"] != "concluida"]
        if self.interrompido:
            raise KeyboardInterrupt()
        if falhas:
            raise RuntimeError("Coleta incompleta nos órgãos: " + ", ".join(falhas))


def ler_extracao(caminho, orgao=None):
    with pd.ExcelFile(caminho) as arquivo:
        abas = ["Direta", "Indireta"] if {"Direta", "Indireta"}.issubset(arquivo.sheet_names) else [arquivo.sheet_names[0]]
        quadros = []
        for aba in abas:
            df = pd.read_excel(arquivo, sheet_name=aba, dtype=str, keep_default_na=False)
            ausentes = set(CAMPOS) - set(df.columns)
            if ausentes:
                raise ValueError(f"{caminho} ({aba}): colunas ausentes: {sorted(ausentes)}")
            quadros.append(df)
    df = pd.concat(quadros, ignore_index=True)
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
    parser.add_argument("--administracao", choices=("direta", "indireta", "ambas"), default="direta",
                        help="Escopo da coleta (padrão: direta)")
    parser.add_argument("--comparar", type=Path, help="Excel original gerado pelo Selenium")
    parser.add_argument("--somente-comparar", type=Path, help="Excel HTTP existente; não acessa o portal")
    pasta_app = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
    parser.add_argument("--saida-dir", type=Path, default=pasta_app / "resultados_http")
    parser.add_argument("--timeout", type=float, default=30, help="Timeout HTTP em segundos (padrão: 30)")
    parser.add_argument("--trabalhadores", type=int, default=4, help="Órgãos simultâneos (padrão: 4; use 1 para execução serial)")
    parser.add_argument("--pausa-recuperacao", type=float, default=5,
                        help="Pausa em segundos entre rodadas de recuperação (padrão: 5)")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout deve ser positivo")
    if args.trabalhadores < 1:
        parser.error("--trabalhadores deve ser positivo")
    if args.pausa_recuperacao < 0:
        parser.error("--pausa-recuperacao não pode ser negativa")
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
            coletor.coletar(args.orgao, args.trabalhadores, args.pausa_recuperacao, args.administracao)
            if not coletor.resultados:
                raise RuntimeError("Coleta sem registros.")
        except (Exception, KeyboardInterrupt) as exc:
            erro = f"{type(exc).__name__}: {exc}"
        finally:
            coletor.sessao.close()
        duracao = time.perf_counter() - inicio
        fim_coleta = datetime.now().astimezone()
        status = "PARCIAL" if erro else "concluida"
        arquivo = args.saida_dir / f"sici_http_{args.administracao}_{status}_{carimbo}.xlsx"
        df = pd.DataFrame(coletor.resultados, columns=CAMPOS + [CAMPO_COMPETENCIAS, STATUS_COMPETENCIAS, ERRO_COMPETENCIAS])
        df["data_extracao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if args.administracao == "ambas":
            indiretos = df["órgão"].map(orgao_indireto).astype(bool)
            with pd.ExcelWriter(arquivo, engine="openpyxl") as writer:
                df.loc[~indiretos].to_excel(writer, sheet_name="Direta", index=False)
                df.loc[indiretos].to_excel(writer, sheet_name="Indireta", index=False)
        else:
            df.to_excel(arquivo, index=False)
        metricas = {
            "status": status, "erro": erro, "orgao": args.orgao,
            "administracao": args.administracao,
            "registros": len(df), "requisicoes": coletor.requisicoes,
            "segundos_coleta": round(duracao, 3),
            "segundos_http": round(coletor.segundos_http, 3),
            "inicio_coleta": inicio_coleta.isoformat(), "fim_coleta": fim_coleta.isoformat(),
            "trabalhadores_solicitados": args.trabalhadores,
            "trabalhadores_utilizados": coletor.trabalhadores_utilizados,
            "trabalhadores_por_rodada": coletor.trabalhadores_por_rodada,
            "trabalhadores_configurados_por_rodada": coletor.trabalhadores_configurados_por_rodada,
            "pausa_recuperacao_segundos": args.pausa_recuperacao,
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
