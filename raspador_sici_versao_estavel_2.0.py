from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

driver.get("https://sici.rio.rj.gov.br/PAG/principal.aspx")
time.sleep(3)

resultados = []

# ---------------- UTIL ----------------

def esperar_ajax():
    """Aguarda a conclusão de requisições AJAX do ASP.NET (UpdatePanel)"""
    try:
        wait.until(lambda d: d.execute_script(
            "return (typeof Sys === 'undefined') || (!Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack());"
        ))
    except:
        pass
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
    """Busca o elemento pelo seu ID único para evitar cliques em homônimos"""
    try:
        elemento = driver.find_element(By.ID, el_id)
    except:
        return

    # Se já está selecionado, não clicar
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
    """Expande o elemento buscando pelo ID para evitar perdas de referência na DOM"""
    try:
        elemento = driver.find_element(By.ID, el_id)
        tr = elemento.find_element(By.XPATH, "./ancestor::tr")
        
        # Busca o botão de forma mais flexível (seja a imagem ou o link do próprio nó)
        botoes = tr.find_elements(By.XPATH, ".//img[starts-with(@alt,'Expand')] | .//a[contains(@href, 'TreeView_ToggleNode')]")
        
        if not botoes:
            return # Se não encontrou o botão, o nó já está aberto ou não tem filhos
            
        botao = botoes[0]
        
        # Centraliza o elemento na tela
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
        time.sleep(0.5) # Pausa rápida para a rolagem estabilizar
        
        # 🔥 O pulo do gato: Clique via JavaScript não falha se algo estiver cobrindo o botão
        driver.execute_script("arguments[0].click();", botao)
        
        # Aguarda a requisição principal do servidor
        esperar_ajax() 
        
        # Fôlego extra para secretarias colossais (como SME e SMAS) montarem o HTML no navegador
        time.sleep(1) 
        
    except Exception as e:
        # Agora, se der erro, ele vai te avisar no terminal o que aconteceu em vez de pular em silêncio
        print(f"⚠️ Aviso: Falha ao tentar expandir o elemento ID {el_id}. Erro: {e}")
# ---------------- PROCESSAMENTO ÚNICO LINEAR ----------------

i = 0
orgao_atual = None
processando_ramo = False

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
        el_id = el.get_attribute("id") # 🔥 CAPTURAMOS O ID ÚNICO AQUI
        nivel = obter_nivel(el)
    except:
        i += 1
        continue

    if not texto:
        i += 1
        continue

    # Ignorar PCRJ
    if nivel == 0:
        i += 1
        continue

    # -------- NÍVEL 1 --------
    if nivel == 1:
        try:
            # Re-buscamos pelo ID para garantir que o elemento não ficou "stale"
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

        processando_ramo = True
        orgao_atual = texto

        # 🔥 Passamos o ID em vez do elemento ou texto
        expandir_por_id(el_id)
        clicar_por_id(el_id)
        
        area1, cargo1 = capturar_painel()

        resultados.append({
            "órgão": orgao_atual,
            "escalão": "1º",
            "área": area1,
            "cargo": cargo1
        })

        i += 1
        continue

    # -------- NÍVEL 2 --------
    if nivel == 2:
        if processando_ramo:
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

df = pd.DataFrame(resultados)
df.to_excel("sici_final.xlsx", index=False)

driver.quit()

print("Processo finalizado.")