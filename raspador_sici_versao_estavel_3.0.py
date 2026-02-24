from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
import time
import datetime

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

# Limites estritos
driver.set_page_load_timeout(30)
driver.set_script_timeout(30)
wait = WebDriverWait(driver, 15)

driver.get("https://sici.rio.rj.gov.br/PAG/principal.aspx")
time.sleep(3)

resultados = []

# 🔥 CONFIGURAÇÃO DO FILTRO (em letras minúsculas)
# Adicione aqui as palavras ou siglas que devem ser ignoradas.
PALAVRAS_IGNORADAS = [
    "escola ",
    "escola municipal", 
    "ciep", 
    "creche municipal", 
    "edi ", # Espaço no final ajuda a não cortar palavras que comecem com edi
    "c.m.", 
    "e.m.",
    "espaço de desenvolvimento infantil",
    "biblioteca escolar",
    "centro de desenvolvimento de educação integrada",
    "hospital",
    "gerência do parque",
    "centro de referência de assistência social",
    "centro de referência especializado de assistência social"
]

# ---------------- UTIL ----------------

def deve_ignorar(texto_orgao):
    """Verifica se o nome do órgão contém alguma palavra da blocklist"""
    texto_lower = texto_orgao.lower()
    return any(palavra in texto_lower for palavra in PALAVRAS_IGNORADAS)

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
    area = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
    ) or ""
    cargo = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblCargo')?.innerText;"
    ) or ""
    return area.strip(), cargo.strip()

def clicar_por_id(el_id):
    try:
        elemento = driver.find_element(By.ID, el_id)
    except:
        return

    classe = elemento.get_attribute("class") or ""
    if "selectedTreeNode" in classe:
        return

    area_antes = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
    )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
    driver.execute_script("arguments[0].click();", elemento)

    esperar_ajax()

    try:
        wait.until(
            lambda d: d.execute_script(
                "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
            ) != area_antes
        )
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

# ---------------- PROCESSAMENTO ----------------

i = 0
orgao_atual = None
processando_ramo = False
id_n1_anterior = None
id_n2_anterior = None 

print("🚀 Iniciando a raspagem de dados...")
tempo_inicio = time.time() 

try: 
    while True:
        links = driver.find_elements(
            By.XPATH,
            "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
        )

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

        if not texto:
            i += 1
            continue

        if nivel == 0:
            i += 1
            continue

        # 🔥 VERIFICA O FILTRO DE PALAVRAS AQUI
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
                valido = any(
                    img.get_attribute("src").endswith("-A.gif") or
                    img.get_attribute("src").endswith("-D.gif")
                    for img in imgs
                )
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

            expandir_por_id(el_id)
            clicar_por_id(el_id)
            
            area1, cargo1 = capturar_painel()

            resultados.append({
                "órgão": orgao_atual,
                "escalão": "1º",
                "área": area1,
                "cargo": cargo1
            })
            print(f"▶️ Entrando no Órgão: {orgao_atual}")

            i += 1
            continue

        # -------- NÍVEL 2 --------
        if nivel == 2:
            if processando_ramo:
                if id_n2_anterior and id_n2_anterior != el_id:
                    print(f"  🧹 Fechando setor anterior de 2º escalão...")
                    recolher_por_id(id_n2_anterior)
                    
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

                area2, cargo2 = capturar_painel()

                resultados.append({
                    "órgão": orgao_atual,
                    "escalão": "2º",
                    "área": area2,
                    "cargo": cargo2
                })
            i += 1
            continue

        # -------- NÍVEL 3 --------
        if nivel == 3:
            if processando_ramo:
                clicar_por_id(el_id)

                area3, cargo3 = capturar_painel()

                resultados.append({
                    "órgão": orgao_atual,
                    "escalão": "3º",
                    "área": area3,
                    "cargo": cargo3
                })
            i += 1
            continue

        # Ignorar Níveis 4 em diante
        i += 1

        if i % 20 == 0 and len(resultados) > 0:
            try:
                pd.DataFrame(resultados).to_excel("sici_parcial.xlsx", index=False)
            except:
                pass

except Exception as e:
    print(f"\n🛑 O script foi interrompido (Timeout ou Erro): {e}")
    print("Iniciando rotina de emergência para salvar os dados coletados...")

finally:
    if len(resultados) > 0:
        agora = datetime.datetime.now()
        data_extracao_str = agora.strftime("%d/%m/%Y %H:%M:%S") 
        nome_arquivo_data = agora.strftime("%Y%m%d_%H%M")       
        
        df = pd.DataFrame(resultados)
        df["data_extracao"] = data_extracao_str
        
        nome_arquivo = f"sici_extracao_{nome_arquivo_data}.xlsx"
        df.to_excel(nome_arquivo, index=False)
        print(f"\n✅ SUCESSO! Arquivo '{nome_arquivo}' salvo com {len(resultados)} registros.")
    else:
        print("\nNenhum dado foi coletado antes da interrupção.")
        
    driver.quit()
    print("Navegador encerrado.")

    tempo_fim = time.time()
    duracao_segundos = tempo_fim - tempo_inicio
    tempo_formatado = str(datetime.timedelta(seconds=int(duracao_segundos)))
    
    print("-" * 40)
    print(f"⏱️ Tempo total de execução: {tempo_formatado}")
    print("-" * 40)