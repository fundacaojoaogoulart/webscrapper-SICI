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

def expandir_apenas_ramos_validos():
    print("Expandindo apenas ramos A/D...")

    # Primeiro pegar todos os órgãos nível 1
    links = driver.find_elements(
        By.XPATH,
        "//a[starts-with(@id,'ContentPlaceHolder1_ua_treeviewt')]"
    )

    orgaos_validos_ids = []

    for elemento in links:
        texto = elemento.text.strip()
        if not texto:
            continue

        element_id = elemento.get_attribute("id")
        nivel = obter_nivel_por_id(element_id)

        if nivel == 1:
            tr = elemento.find_element(By.XPATH, "./ancestor::tr")
            imagens = tr.find_elements(
                By.XPATH,
                ".//img[contains(@src,'img-folder-closed-')]"
            )

            for img in imagens:
                src = img.get_attribute("src")
                if src.endswith("-A.gif") or src.endswith("-D.gif"):
                    orgaos_validos_ids.append(element_id)
                    break

    # Agora expandir apenas esses ramos
    for orgao_id in orgaos_validos_ids:
        while True:
            try:
                elemento = driver.find_element(By.ID, orgao_id)
                tr = elemento.find_element(By.XPATH, "./ancestor::tr")

                botao_expandir = tr.find_elements(
                    By.XPATH,
                    ".//img[starts-with(@alt,'Expand')]"
                )

                if not botao_expandir:
                    break

                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    botao_expandir[0]
                )

                botao_expandir[0].click()
                time.sleep(0.4)

            except:
                break

    print("Expansão seletiva concluída.")


# ---------------- EXECUÇÃO ----------------

print("Expandindo toda a árvore...")
expandir_apenas_ramos_validos()
print("Expansão concluída.\n")

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

    # Ignorar PCRJ (nível 0)
    if nivel == 0:
        index += 1
        continue

    # Quando for nível 1 (órgão raiz)
    if nivel == 1:
        orgao_atual = texto

        # verificar letra somente no nível 1
        tr = driver.find_element(By.ID, element_id).find_element(By.XPATH, "./ancestor::tr")
        imagens = tr.find_elements(By.XPATH, ".//img[contains(@src,'img-folder-closed-')]")

        capturar_ramo = False
        for img in imagens:
            src = img.get_attribute("src")
            if src.endswith("-A.gif") or src.endswith("-D.gif"):
                capturar_ramo = True
                break

    # Captura somente se ramo válido
    if capturar_ramo and nivel <= 3:

        try:
            area_antes = driver.execute_script(
                "return document.getElementById('ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada')?.innerText;"
            )
        except:
            area_antes = ""

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


# ---------------- EXPORTAÇÃO ----------------

df = pd.DataFrame(resultados)
df.to_excel("sici_completo.xlsx", index=False)

driver.quit()

print("\nProcesso finalizado. Arquivo 'sici_completo.xlsx' gerado com sucesso.")