from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
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

# ---------------- FUNÇÕES ----------------

def obter_nivel_por_id(element_id):
    elemento = driver.find_element(By.ID, element_id)
    tr = elemento.find_element(By.XPATH, "./ancestor::tr")
    divs = tr.find_elements(By.XPATH, ".//div[contains(@style,'width:20px')]")
    return len(divs)

def capturar_dados_painel():
    area = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
    ) or ""

    cargo = driver.execute_script(
        "return document.getElementById('ContentPlaceHolder1_lblCargo')?.innerText;"
    ) or ""

    return area.strip(), cargo.strip()

def expandir_tudo():
    print("Expandindo toda a árvore...")

    while True:
        botoes = driver.find_elements(
            By.XPATH,
            "//img[starts-with(@alt,'Expand')]"
        )

        if not botoes:
            break

        botao = botoes[-1]

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                botao
            )

            quantidade_antes = len(botoes)
            botao.click()

            wait.until(
                lambda d: len(d.find_elements(
                    By.XPATH,
                    "//img[starts-with(@alt,'Expand')]"
                )) != quantidade_antes
            )

            time.sleep(0.2)

        except:
            continue

    print("Expansão completa finalizada.\n")


# ---------------- EXECUÇÃO ----------------

expandir_tudo()

index = 0
orgao_atual = None
capturar_ramo = False

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

    if nivel == 0:
        index += 1
        continue

    # Se for órgão raiz
    if nivel == 1:
        orgao_atual = texto

        tr = elemento.find_element(By.XPATH, "./ancestor::tr")
        imagens = tr.find_elements(By.XPATH, ".//img[contains(@src,'img-folder-closed-')]")

        capturar_ramo = False
        for img in imagens:
            src = img.get_attribute("src")
            if src.endswith("-A.gif") or src.endswith("-D.gif"):
                capturar_ramo = True
                break

    if capturar_ramo and nivel <= 3:

        area_antes = driver.execute_script(
            "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
        )

        driver.find_element(By.ID, element_id).click()

        wait.until(
            lambda d: d.execute_script(
                "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
            ) != area_antes
        )

        area, cargo = capturar_dados_painel()

        resultados.append({
            "órgão": orgao_atual,
            "escalão": f"{nivel}º",
            "área": area,
            "cargo": cargo
        })

        print(f"Capturado: {orgao_atual} | {area}")

    index += 1


df = pd.DataFrame(resultados)
df.to_excel("sici_completo.xlsx", index=False)

driver.quit()

print("Processo finalizado.")
