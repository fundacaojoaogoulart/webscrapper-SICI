from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import time
import datetime
import match_lideres
import tkinter as tk
from tkinter import messagebox
import os
import atualizador_MFE
import config_manager

# 🔥 CONFIGURAÇÃO DO FILTRO 
# PALAVRAS_IGNORADAS = [
#     "escola ", "ciep", "creche", "centro de educação de jovens e adultos",
#     "edi ", "c.m.", "e.m.", "espaço de desenvolvimento infantil",
#     "biblioteca escolar", "centro de desenvolvimento de educação integrada",
#     "hospital", "gerência do parque", "centro de referência de assistência social",
#     "centro de referência da assistência social", "centro de referência especializado de assistência social",
#     "centro de referência especializado da assistência social", "centro municipal de referência",
#     "fundo municipal", "unidade municipal de reinserção", "central de recepção",
#     "centro de cidadania", "conselho", "comitê", "fundo", "comissão",
#     "vila olímpica", "casa viva", "centro esportivo", "junta especial",
#     "juntas", "museu histórico"
# ]


# ---------------- FUNÇÕES UTILITÁRIAS ----------------

def exibir_alerta(titulo, mensagem, tipo="info"):
    root = tk._default_root
    if root is None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
    if tipo == "error":
        messagebox.showerror(titulo, mensagem)
    elif tipo == "warning":
        messagebox.showwarning(titulo, mensagem)
    else:
        messagebox.showinfo(titulo, mensagem)


def iniciar_raspagem():
    """
    🔥 Toda a lógica principal foi embalada nesta função.
    O painel_principal.py chamará esta função.
    """

    # 🔥 CARREGA O ARQUIVO CONFIG.TXT SEMPRE QUE O ROBO INICIAR
    config_data = config_manager.ler_config()
    palavras_ignoradas = config_data['PALAVRAS_IGNORADAS']
    
    # 🔥 FUNÇÃO MOVIDA PARA DENTRO PARA LER A VARIÁVEL ATUALIZADA
    def deve_ignorar(texto_orgao):
        texto_lower = texto_orgao.lower()
        return any(palavra in texto_lower for palavra in palavras_ignoradas)
    
    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(30)
    driver.set_script_timeout(30)
    wait = WebDriverWait(driver, 15)

    def esperar_ajax():
        try:
            wait.until(lambda d: d.execute_script(
                "return (typeof Sys === 'undefined') || (!Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack());"
            ))
        except Exception:
            print("⚠️ Lentidão detectada: A página demorou muito para responder.")
        time.sleep(0.5)

    def obter_nivel(elemento):
        tr = elemento.find_element(By.XPATH, "./ancestor::tr")
        divs = tr.find_elements(By.XPATH, ".//div[contains(@style,'width:20px')]")
        return len(divs)

    def capturar_painel():
        area = driver.execute_script("return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;") or ""
        cargo = driver.execute_script("return document.getElementById('ContentPlaceHolder1_lblCargo')?.innerText;") or ""
        titular = driver.execute_script("return document.getElementById('ContentPlaceHolder1_lblTitular')?.innerText;") or ""
        return area.strip(), cargo.strip(), titular.strip()

    def clicar_por_id(el_id):
        try:
            elemento = driver.find_element(By.ID, el_id)
        except:
            return
        classe = elemento.get_attribute("class") or ""
        if "selectedTreeNode" in classe:
            return

        area_antes = driver.execute_script("return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
        driver.execute_script("arguments[0].click();", elemento)
        esperar_ajax()

        try:
            wait.until(lambda d: d.execute_script("return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;") != area_antes)
        except:
            pass

    def expandir_por_id(el_id):
        try:
            elemento = driver.find_element(By.ID, el_id)
            tr = elemento.find_element(By.XPATH, "./ancestor::tr")
            botoes = tr.find_elements(By.XPATH, ".//img[starts-with(@alt,'Expand')] | .//a[contains(@href, 'TreeView_ToggleNode')]")
            if not botoes:
                return 
            botao = botoes[0]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
            time.sleep(0.5) 
            driver.execute_script("arguments[0].click();", botao)
            esperar_ajax() 
            time.sleep(1)
        except Exception:
            pass

    def recolher_por_id(el_id):
        try:
            elemento = driver.find_element(By.ID, el_id)
            tr = elemento.find_element(By.XPATH, "./ancestor::tr")
            botoes = tr.find_elements(By.XPATH, ".//img[starts-with(@alt,'Collapse')]")
            if botoes:
                botao = botoes[0]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", botao)
                esperar_ajax()
        except:
            pass 

    driver.get("https://sici.rio.rj.gov.br/PAG/principal.aspx")
    time.sleep(3)

    resultados = []
    i = 0
    orgao_atual = None
    processando_ramo = False
    id_n1_anterior = None
    id_n2_anterior = None 
    id_n3_anterior = None 
    is_orgao_tipo_a = False 

    print("🚀 Iniciando a raspagem de dados...")
    tempo_inicio = time.time() 

    try: 
        while True:
            links = driver.find_elements(By.XPATH, "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]")
            if i >= len(links):
                break
            el = links[i]

            try:
                texto = el.text.strip()
                el_id = el.get_attribute("id")
                nivel = obter_nivel(el)
            except:
                i += 1
                continue

            if not texto or nivel == 0:
                i += 1
                continue

            if deve_ignorar(texto):
                print(f"🚫 Ignorando: {texto}")
                i += 1
                continue

            # -------- NÍVEL 1 --------
            if nivel == 1:
                try:
                    elemento_fresco = driver.find_element(By.ID, el_id)
                    tr = elemento_fresco.find_element(By.XPATH, "./ancestor::tr")
                    imgs = tr.find_elements(By.XPATH, ".//img")
                    is_tipo_a = any(img.get_attribute("src").endswith("-A.gif") for img in imgs)
                    is_tipo_d = any(img.get_attribute("src").endswith("-D.gif") for img in imgs)
                    valido = is_tipo_a or is_tipo_d
                except:
                    valido = False

                if not valido:
                    processando_ramo = False
                    i += 1
                    continue

                if processando_ramo and id_n1_anterior and id_n1_anterior != el_id:
                    print(f"🧹 Fechando órgão anterior de 1º escalão...")
                    recolher_por_id(id_n1_anterior)
                    id_n2_anterior = None 
                    id_n3_anterior = None 
                    
                    links = driver.find_elements(By.XPATH, "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]")
                    for index, link in enumerate(links):
                        try:
                            if link.text.strip() == texto and obter_nivel(link) == 1:
                                i = index 
                                el_id = link.get_attribute("id") 
                                break
                        except:
                            continue

                id_n1_anterior = el_id
                processando_ramo = True
                orgao_atual = texto
                is_orgao_tipo_a = is_tipo_a 

                expandir_por_id(el_id)
                
                if not is_orgao_tipo_a:
                    clicar_por_id(el_id)
                    area1, cargo1, titular1 = capturar_painel()
                    resultados.append({"órgão": orgao_atual, "escalão": "1º", "área": area1, "cargo": cargo1 ,"titular": titular1})
                
                tipo_txt = "A (Autarquia/Empresa)" if is_orgao_tipo_a else "D (Direta)"
                print(f"▶️ Entrando no Órgão: {orgao_atual} | Tipo: {tipo_txt}")
                i += 1
                continue

            # -------- NÍVEL 2 --------
            if nivel == 2:
                if processando_ramo:
                    if id_n2_anterior and id_n2_anterior != el_id:
                        print(f"  🧹 Fechando setor anterior de 2º escalão...")
                        recolher_por_id(id_n2_anterior)
                        id_n3_anterior = None 
                        
                        links = driver.find_elements(By.XPATH, "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]")
                        for index, link in enumerate(links):
                            try:
                                if link.text.strip() == texto and obter_nivel(link) == 2:
                                    i = index 
                                    el_id = link.get_attribute("id") 
                                    break
                            except:
                                continue

                    id_n2_anterior = el_id
                    expandir_por_id(el_id)
                    clicar_por_id(el_id)
                    area2, cargo2, titular2 = capturar_painel()
                    escalao_n2 = "1º" if is_orgao_tipo_a else "2º"
                    resultados.append({"órgão": orgao_atual, "escalão": escalao_n2, "área": area2, "cargo": cargo2, "titular": titular2})
                i += 1
                continue

            # -------- NÍVEL 3 --------
            if nivel == 3:
                if processando_ramo:
                    if is_orgao_tipo_a:
                        if id_n3_anterior and id_n3_anterior != el_id:
                            print(f"    🧹 Fechando setor anterior de 3º escalão...")
                            recolher_por_id(id_n3_anterior)
                            links = driver.find_elements(By.XPATH, "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]")
                            for index, link in enumerate(links):
                                try:
                                    if link.text.strip() == texto and obter_nivel(link) == 3:
                                        i = index 
                                        el_id = link.get_attribute("id") 
                                        break
                                except:
                                    continue

                        id_n3_anterior = el_id
                        expandir_por_id(el_id)
                        clicar_por_id(el_id)
                        area3, cargo3,titular3 = capturar_painel()
                        resultados.append({"órgão": orgao_atual, "escalão": "2º", "área": area3, "cargo": cargo3, "titular": titular3})
                    
                    else:
                        clicar_por_id(el_id)
                        area3, cargo3,titular3 = capturar_painel()
                        resultados.append({"órgão": orgao_atual, "escalão": "3º", "área": area3, "cargo": cargo3,"titular": titular3})
                i += 1
                continue

            # -------- NÍVEL 4 --------
            if nivel == 4:
                if processando_ramo and is_orgao_tipo_a:
                    clicar_por_id(el_id)
                    area4, cargo4, titular4 = capturar_painel()
                    resultados.append({"órgão": orgao_atual, "escalão": "3º", "área": area4, "cargo": cargo4, "titular": titular4})
                i += 1
                continue

            i += 1

            if i % 20 == 0 and len(resultados) > 0:
                try:
                    pd.DataFrame(resultados).to_excel("sici_parcial.xlsx", index=False)
                except:
                    pass

    except Exception as e:
        erro_msg = f"🛑 O script foi interrompido devido a um Timeout ou Erro:\n\n{e}\n\nA rotina de emergência será iniciada para tentar salvar os dados coletados."
        print(erro_msg)
        exibir_alerta("Erro na Extração SICI", erro_msg, "error")

    finally:
        tempo_fim = time.time()
        duracao_segundos = tempo_fim - tempo_inicio
        tempo_formatado = str(datetime.timedelta(seconds=int(duracao_segundos)))
        
        print("-" * 40)
        print(f"⏱️ Tempo total de execução: {tempo_formatado}")
        print("-" * 40)

        driver.quit()
        print("Navegador encerrado.")
    
        if len(resultados) > 0:
            agora = datetime.datetime.now()
            data_extracao_str = agora.strftime("%d/%m/%Y %H:%M:%S") 
            nome_arquivo_data = agora.strftime("%Y%m%d_%H%M")       
            
            df = pd.DataFrame(resultados)
            df["data_extracao"] = data_extracao_str
            
            import sys
            if getattr(sys, 'frozen', False):
                app_path = os.path.dirname(sys.executable)
            else:
                app_path = os.path.dirname(os.path.abspath(__file__))
            
            nome_arquivo_base = f"sici_extracao_{nome_arquivo_data}.xlsx"
            nome_arquivo = os.path.join(app_path, nome_arquivo_base)
            df.to_excel(nome_arquivo, index=False)
            
            msg_sucesso = f"✅ Raspagem do SICI concluída com sucesso!\n\nArquivo gerado: {nome_arquivo}\nTotal de registros extraídos: {len(resultados)}\nTempo de execução: {tempo_formatado}\nClique em OK para iniciar a conferência e atualização da planilha MFE."
            print(f"\n✅ SUCESSO! Arquivo '{nome_arquivo}' salvo com {len(resultados)} registros.")
            exibir_alerta("Raspagem Concluída", msg_sucesso, "info")
            
            print("\nIniciando conferência automática com a base Minibios...")
            # match_lideres.cruzar_planilhas(df)

            # 🔥 O PULO DO GATO: As perguntas interativas
            resposta_mfe = messagebox.askyesno("Etapa 2: Atualização MFE", "Deseja usar os dados recém-extraídos para ATUALIZAR a planilha MFE agora?")
            if resposta_mfe:
                print("\nIniciando conferência automática com a base MFE...")
                atualizador_MFE.atualizar_planilha_mfe(df)
                
            resposta_minibios = messagebox.askyesno("Etapa 3: Match de Líderes", "Deseja usar os dados recém-extraídos para CRUZAR LÍDERES (Minibios) agora?")
            if resposta_minibios:
                print("\nIniciando conferência automática com a base Minibios...")
                match_lideres.cruzar_planilhas(df)
        else:
            msg_vazio = "O processo foi interrompido antes que qualquer dado fosse coletado. Nenhuma planilha de extração será gerada."
            print(f"\n⚠️ {msg_vazio}")
            exibir_alerta("Raspagem Vazia", msg_vazio, "warning")
            




# Este bloco no final garante que se você rodar SÓ esse arquivo direto, 
# ele chama a raspagem. Se rodar pelo painel, não roda sozinho.
if __name__ == "__main__":
    iniciar_raspagem()