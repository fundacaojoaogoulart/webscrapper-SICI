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
wait = WebDriverWait(driver, 10)

driver.get("https://sici.rio.rj.gov.br/PAG/principal.aspx")
time.sleep(2)

resultados = []

# ---------------- UTIL ----------------

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

def clicar_nome_por_texto(texto):

    elemento = driver.find_element(
        By.XPATH,
        f"//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt') and normalize-space()='{texto}']"
    )

    # 🔍 Se já está selecionado, não clicar
    classe = elemento.get_attribute("class") or ""
    if "selectedTreeNode" in classe:
        return

    area_antes = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
    )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elemento)
    driver.execute_script("arguments[0].click();", elemento)

    try:
        wait.until(
            lambda d: d.execute_script(
                "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
            ) != area_antes
        )
    except:
        pass  # evita crash se painel não mudar
def expandir_se_existir(elemento):
    try:
        tr = elemento.find_element(By.XPATH, "./ancestor::tr")
        botao = tr.find_element(By.XPATH, ".//img[starts-with(@alt,'Expand')]")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", botao)
        botao.click()
        time.sleep(0.5)
    except:
        pass

# ---------------- PEGAR ÓRGÃOS A/D ----------------

links = driver.find_elements(
    By.XPATH,
    "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
)

orgaos_validos = []

for el in links:
    texto = el.text.strip()
    if not texto:
        continue
    if obter_nivel(el) == 0:
        continue
    if obter_nivel(el) == 1:
        tr = el.find_element(By.XPATH, "./ancestor::tr")
        imgs = tr.find_elements(By.XPATH, ".//img[contains(@src,'img-folder-closed-')]")

        for img in imgs:
            src = img.get_attribute("src")
            if src.endswith("-A.gif") or src.endswith("-D.gif"):
                orgaos_validos.append(texto)
                break

# ---------------- PROCESSAR CADA ÓRGÃO ----------------

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
            tr = el.find_element(By.XPATH, "./ancestor::tr")
            imgs = tr.find_elements(By.XPATH, ".//img[contains(@src,'img-folder-closed-')]")

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

        # 🔥 EXPANDE
        expandir_se_existir(el)

        # 🔥 CLICA E CAPTURA N1
        clicar_nome_por_texto(texto)
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
    if processando_ramo and nivel == 2:

        texto_n2 = texto

        expandir_se_existir(el)

        clicar_nome_por_texto(texto_n2)

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
    if processando_ramo and nivel == 3:

        texto_n3 = texto

        clicar_nome_por_texto(texto_n3)

        area3, cargo3 = capturar_painel()

        resultados.append({
            "órgão": orgao_atual,
            "escalão": "3º",
            "área": area3,
            "cargo": cargo3
        })

        i += 1
        continue

    i += 1

df = pd.DataFrame(resultados)
df.to_excel("sici_final.xlsx", index=False)

driver.quit()

print("Processo finalizado.")