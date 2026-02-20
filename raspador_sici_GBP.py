from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

# ---------------- CONFIG ----------------

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

driver.get("https://sici.rio.rj.gov.br/PAG/principal.aspx")
time.sleep(2)

resultados = []
ORGAO_ALVO = "GBP"

# ---------------- FUNÇÕES ----------------

def obter_nivel_por_id(element_id):
    elemento = driver.find_element(By.ID, element_id)
    tr = elemento.find_element(By.XPATH, "./ancestor::tr")
    divs = tr.find_elements(By.XPATH, ".//div[contains(@style,'width:20px')]")
    return len(divs)

def capturar_dados_painel():
    try:
        area = driver.find_element(
            By.ID,
            "ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada"
        ).text.strip()
    except:
        area = ""

    try:
        cargo = driver.find_element(
            By.ID,
            "ContentPlaceHolder1_lblCargo"
        ).text.strip()
    except:
        cargo = ""

    return area, cargo

# def expandir_no_por_texto(texto_no):
#     links = driver.find_elements(
#         By.XPATH,
#         "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
#     )

#     for l in links:
#         if l.text.strip() == texto_no:
#             tr = l.find_element(By.XPATH, "./ancestor::tr")
#             try:
#                 botao_expandir = tr.find_element(
#                     By.XPATH,
#                     ".//img[starts-with(@alt,'Expand')]"
#                 )
#                 botao_expandir.click()
#                 time.sleep(1)
#             except:
#                 pass
#             break

# # ---------------- EXPANSÃO ----------------

# # 1️⃣ Expandir GBP
# expandir_no_por_texto(ORGAO_ALVO)
time.sleep(1)

# Expandir todos os níveis 2 dentro de GBP de forma segura

while True:
    expandido = False

    links = driver.find_elements(
        By.XPATH,
        "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
    )

    for l in links:
        try:
            texto = l.text.strip()
            if not texto:
                continue

            element_id = l.get_attribute("id")
            nivel = obter_nivel_por_id(element_id)

            if nivel == 2:
                tr = driver.find_element(By.ID, element_id).find_element(By.XPATH, "./ancestor::tr")

                botao_expandir = tr.find_elements(
                    By.XPATH,
                    ".//img[starts-with(@alt,'Expand')]"
                )

                if botao_expandir:
                    botao_expandir[0].click()
                    time.sleep(0.7)
                    expandido = True
                    break   # IMPORTANTE: sair do loop e rebuscar DOM

        except:
            continue

    if not expandido:
        break

# ---------------- CAPTURA ----------------

index = 0
capturando = False

while True:
    links = driver.find_elements(
        By.XPATH,
        "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
    )

    if index >= len(links):
        break

    elemento = links[index]
    texto = elemento.text.strip()

    if not texto:
        index += 1
        continue

    element_id = elemento.get_attribute("id")
    nivel = obter_nivel_por_id(element_id)

    # if nivel == 1 and texto == ORGAO_ALVO:
    #     capturando = True

    # elif nivel == 1 and capturando and texto != ORGAO_ALVO:
    #     break
    if nivel == 1 :
        capturando = True

    elif nivel == 1 and capturando:
        break
    if capturando and nivel <= 3:
# Captura texto atual antes do clique
        try:
            area_antes = driver.find_element(
                By.ID,
                "ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada"
            ).text
        except:
            area_antes = ""

        driver.find_element(By.ID, element_id).click()

        # Espera até o painel mudar
        wait.until(
            lambda d: d.find_element(
                By.ID,
                "ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada"
            ).text != area_antes
        )

        area, cargo = capturar_dados_painel()

        resultados.append({
            "órgão": ORGAO_ALVO,
            "escalão": f"{nivel}º",
            "área": area,
            "cargo": cargo
        })

        print(f"Capturado: {area} | {cargo}")

    index += 1

# ---------------- EXPORTAÇÃO ----------------

df = pd.DataFrame(resultados)
df.to_excel("teste_GBP.xlsx", index=False)

driver.quit()