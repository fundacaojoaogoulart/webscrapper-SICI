import pandas as pd
import openpyxl
from openpyxl.styles import PatternFill
import unicodedata
import re
import datetime
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

import area_negocio_ml # Módulo de Machine Learning

# ---------------- CONFIGURAÇÕES ----------------
NOME_ABA = "Todas as Funções (Editável)"
COR_ALERTA = "FFFF00" # Amarelo

# ---------------- DICIONÁRIOS INTERNOS (DE-PARA) ----------------
DIC_TIPOS = {
    "assessorchefe": "Assessor(a)", "assessorchefeespeciali": "Assessor(a)",
    "assessorchefei": "Assessor(a)", "assessorchefetecnico": "Assessor(a)",
    "coordenadorespecial": "Coordenador(a)", "coordenadorespecialsubprefeito": "Coordenador(a)",
    "coordenadorespecialdogabinetedoprefeito": "Coordenador(a)", "coordenadorgeral": "Coordenador(a)",
    "coordenadori": "Coordenador(a)", "coordenadorii": "Coordenador(a)", "coordenadortecnico": "Coordenador(a)",
    "gerentedeprocessoiii": "Gerente", "gerentei": "Gerente", "gerenteii": "Gerente",
    "gerenteiii": "Gerente", "gerenteiv": "Gerente",
    "diretordediretoriadeautarquia": "Diretor(a)", "diretorexecutivo": "Diretor(a)",
    "diretori": "Diretor(a)", "diretorii": "Diretor(a)", "diretoriii": "Diretor(a)", "diretoriv": "Diretor(a)",
    "chefedacasamilitar": "Chefe", "chefedegabinete": "Chefe",
    "chefeexecutivo": "Chefe", "chefeexecutivoderesilienciaeoperacoes": "Chefe",
    "ouvidor": "Ouvidor(a)", "ouvidordenucleoi": "Ouvidor(a)", "ouvidordenucleoii": "Ouvidor(a)",
    "presidente": "Presidente", "presidentedeautarquia": "Presidente", "presidenteii": "Presidente",
    "secretarioespecial": "Secretário(a)", "secretariomunicipal": "Secretário(a)",
    "subsecretario": "Subsecretário(a)",
    "superintendente": "Superintendente", "superintendenteexecutivo": "Superintendente", "superintendentetecnico": "Superintendente"
}

DIC_MACROAREA = {
    "casacivil": "Gestão", "cgm": "Gestão", "cgmrio": "Gestão", "gbp": "Gestão",
    "gmrio": "Planejamento Urbano e Econômico", "gvp": "Gestão", "ipp": "Gestão",
    "juvrio": "Social", "pgm": "Gestão", "previrio": "Gestão", "seacrio": "Social",
    "secid": "Social", "seconserva": "Infraestrutura e Logística Urbana",
    "sedecon": "Social", "sedhir": "Social", "segur": "Planejamento Urbano e Econômico",
    "seim": "Planejamento Urbano e Econômico", "semesqv": "Social",
    "seop": "Planejamento Urbano e Econômico", "sesrio": "Social", "sincrio": "Social",
    "sma": "Gestão", "smac": "Planejamento Urbano e Econômico", "smas": "Social",
    "smc": "Social", "smcg": "Gestão", "smct": "Planejamento Urbano e Econômico",
    "smde": "Planejamento Urbano e Econômico", "smdu": "Planejamento Urbano e Econômico",
    "sme": "Social", "smel": "Social", "smg": "Gestão", "smh": "Social",
    "smi": "Infraestrutura e Logística Urbana", "smit": "Gestão", "smpd": "Social",
    "smpda": "Social", "sms": "Social", "smte": "Social",
    "smtr": "Planejamento Urbano e Econômico", "smturrio": "Planejamento Urbano e Econômico",
    "spmrio": "Social", "smf": "Gestão"
}

# ---------------- UTILITÁRIOS ----------------
def normalizar(texto):
    if pd.isna(texto) or not str(texto).strip(): 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto.strip()

def normalizar_nome(texto):
    if pd.isna(texto) or not str(texto).strip(): 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = " ".join(texto.split()) 
    return texto

def inicializar_tkinter():
    root = tk._default_root
    if root is None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
    return root

def carregar_excecoes_poder_decisorio():
    arquivo_config = "excecoes_poder_decisorio.txt"
    cargos = []
    areas = []
    
    if not os.path.exists(arquivo_config):
        with open(arquivo_config, "w", encoding="utf-8") as f:
            f.write("# Este arquivo define regras extras para a coluna de Poder de Decisão (Coluna L).\n")
            f.write("# O sistema ignora maiúsculas, minúsculas e acentos na hora da leitura.\n\n")
            f.write("[CARGO_EXATO]\n")
            f.write("Chefe de Gabinete\n")
            f.write("Procurador Geral do Município\n")
            f.write("Subprocurador Geral do Município\n")
            f.write("Controlador Geral\n")
            f.write("Secretário Especial\n")
            f.write("Secretário Municipal\n")
            f.write("Subsecretário\n")
            f.write("Inspetor Geral\n")
            f.write("Presidente de Autarquia\n")
            f.write("Subcontrolador\n\n")
            f.write("[AREA_CONTEM]\n")
            f.write("Coordenadoria Regional de Educação\n")
    
    modo = None
    with open(arquivo_config, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if linha == "[CARGO_EXATO]":
                modo = "cargo"
                continue
            if linha == "[AREA_CONTEM]":
                modo = "area"
                continue
                
            if modo == "cargo":
                cargos.append(normalizar(linha))
            elif modo == "area":
                areas.append(normalizar(linha))
    
    return set(cargos), areas

def selecionar_arquivo_sici_interface():
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha extraída do SICI que contém os dados novos.")
    return filedialog.askopenfilename(
        title="1. Selecione a planilha EXTRAÍDA DO SICI",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )

def selecionar_planilha_mfe_interface():
    messagebox.showinfo("Selecione um arquivo", "Agora, selecione a planilha do MFE que será ATUALIZADA.")
    return filedialog.askopenfilename(
        title="2. Selecione a planilha do MFE",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )

# ---------------- LÓGICA PRINCIPAL ----------------
def atualizar_planilha_mfe(dados_sici):
    
    root = inicializar_tkinter()
    arquivo_mfe = selecionar_planilha_mfe_interface()
    
    if not arquivo_mfe:
        print("[ALERTA] Nenhuma planilha MFE foi selecionada.")
        messagebox.showwarning("Aviso", "Nenhuma planilha MFE foi selecionada. Operação cancelada.")
        return 

    # --- 1. CARREGAR OS DADOS DO SICI ---
    if isinstance(dados_sici, str):
        print(f"[*] Carregando dados do arquivo SICI: {os.path.basename(dados_sici)}")
        df_sici = pd.read_excel(dados_sici)
    else:
        print("[*] Recebendo dados do SICI diretamente do fluxo principal...")
        df_sici = dados_sici

    if df_sici.empty:
        print("[ALERTA] Os dados do SICI estão vazios.")
        return

    # --- 2. CARREGAR OS DADOS DE ORDENADORES E EXCEÇÕES ---
    cargos_excecao, areas_excecao_contem = carregar_excecoes_poder_decisorio()
    
    verificar_ordenadores = messagebox.askyesno(
        "Ordenadores de Despesa", 
        "Deseja verificar por ordenadores de despesa? (Será necessário fornecer a base de dados)"
    )
    
    set_ordenadores = set()
    if verificar_ordenadores:
        messagebox.showinfo("Selecione um arquivo", "Selecione o arquivo que contém a lista de Ordenadores.")
        planilha_ordenadores = filedialog.askopenfilename(
            title="Selecione a base de Ordenadores",
            filetypes=[("Arquivos CSV", "*.csv"), ("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
        )
        if not planilha_ordenadores:
            messagebox.showwarning("Aviso", "Arquivo não selecionado. A verificação será pulada.")
            verificar_ordenadores = False
        else:
            try:
                _, ext = os.path.splitext(planilha_ordenadores)
                
                df_ord = None
                if ext.lower() == '.csv':
                    tentativas = [(';', 'utf-8'), (';', 'latin1'), (',', 'utf-8'), (',', 'latin1')]
                    for sep, enc in tentativas:
                        try:
                            tmp_df = pd.read_csv(planilha_ordenadores, sep=sep, encoding=enc)
                            if len(tmp_df.columns) > 1:
                                df_ord = tmp_df
                                break
                        except:
                            continue
                    if df_ord is None: 
                        df_ord = pd.read_csv(planilha_ordenadores, sep=';', on_bad_lines='skip')
                else:
                    df_ord = pd.read_excel(planilha_ordenadores, sheet_name=0)
                
                col_user = next((c for c in df_ord.columns if normalizar(str(c)) == 'usuario'), None)
                if not col_user:
                    col_user = df_ord.columns[2] if len(df_ord.columns) >= 3 else df_ord.columns[0]
                
                for val in df_ord[col_user].dropna():
                    nome_limpo = normalizar_nome(str(val))
                    if len(nome_limpo) > 2:
                        set_ordenadores.add(nome_limpo)
                        
                print(f"[*] Base de Ordenadores carregada com {len(set_ordenadores)} usuários válidos.")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao processar arquivo de ordenadores:\n{e}")
                verificar_ordenadores = False

    # --- 3. MACHINE LEARNING (Predição em Lote) ---
    print("[*] Acionando a Inteligência Artificial para as Áreas de Negócio...")
    areas_unicas_originais = df_sici['área'].fillna("").unique().tolist()
    areas_negocio_previstas = area_negocio_ml.prever_area_negocio(areas_unicas_originais)
    
    # Cria um de-para do modelo: { "Área original": "Área Prevista ML" }
    dic_ml_areas = dict(zip(areas_unicas_originais, areas_negocio_previstas))

    # --- 4. AVALIAÇÃO E INDEXAÇÃO SICI ---
    sici_keys = {}
    lixos = {'vago', 'vaga', 'nao informado', 'sem titular', '-'}
    
    for _, rs in df_sici.iterrows():
        org_original = str(rs.get('órgão', ''))
        org = normalizar(org_original)
        
        esc = normalizar(str(rs.get('escalão', '')))
        
        area_original = str(rs.get('área', ''))
        area = normalizar(area_original)
        
        cargo = normalizar(str(rs.get('cargo', '')))
        
        titular_original = str(rs.get('titular', '')).strip()
        titular_norm = normalizar_nome(titular_original)
        
        chave_si = f"{org}|{esc}|{area}|{cargo}|{titular_norm}"
        
        is_ordenador = False
        if verificar_ordenadores and titular_norm and titular_norm not in lixos and len(titular_norm) > 2:
            is_ordenador = titular_norm in set_ordenadores
            
        texto_ordenador = "2 - Sim" if is_ordenador else "1 - Não"
        
        is_excecao_poder = False
        if cargo in cargos_excecao:
            is_excecao_poder = True
        else:
            for area_excecao in areas_excecao_contem:
                if area_excecao in area: 
                    is_excecao_poder = True
                    break

        if is_ordenador or is_excecao_poder:
            texto_poder_decisao = "2 - Possui poder de decisão sobre alocação de recursos orçamentários no órgão"
        else:
            texto_poder_decisao = "1 - Não possui poder de decisão sobre alocação de recursos orçamentários no órgão"

        tipo_cargo_classificado = DIC_TIPOS.get(cargo, "")
        macro_area_classificada = DIC_MACROAREA.get(org, "")
        
        # Resgata a área classificada pela IA no Dicionário
        area_negocio_classificada = dic_ml_areas.get(area_original, "")

        sici_keys[chave_si] = {
            "orgao": org_original,
            "escalao": str(rs.get('escalão', '')),
            "area": area_original,
            "cargo": str(rs.get('cargo', '')),
            "titular": titular_original,
            "texto_ordenador": texto_ordenador,
            "texto_poder_decisao": texto_poder_decisao,
            "tipo_cargo": tipo_cargo_classificado,
            "macro_area": macro_area_classificada,
            "area_negocio": area_negocio_classificada 
        }

    # --- 5. VISITAR MFE E MAPEAMENTO ---
    print(f"[*] Lendo a planilha local '{os.path.basename(arquivo_mfe)}'...")
    try:
        df_mfe = pd.read_excel(arquivo_mfe, sheet_name=NOME_ABA)
    except Exception as e:
        messagebox.showerror("Erro de Arquivo", f"Falha ao ler MFE:\n{e}")
        return

    orgaos_presentes_sici = df_sici['órgão'].dropna().unique().tolist()
    orgaos_normalizados_sici = [normalizar(org) for org in orgaos_presentes_sici]

    mfe_keys = {}
    for idx, row in df_mfe.iterrows():
        orgao_ex = str(row.iloc[1]) if pd.notna(row.iloc[1]) else "" 
        if normalizar(orgao_ex) not in orgaos_normalizados_sici:
            continue

        escalao_ex = str(row.iloc[2]) if pd.notna(row.iloc[2]) else "" 
        area_ex = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""  
        cargo_ex = str(row.iloc[4]) if pd.notna(row.iloc[4]) else "" 
        
        if not normalizar(area_ex) and not normalizar(cargo_ex):
            continue
            
        titular_ex = ""
        if df_mfe.shape[1] > 12: 
            tit_val = row.iloc[12]
            if pd.notna(tit_val):
                titular_ex = str(tit_val).strip()
                
        titular_norm_ex = normalizar_nome(titular_ex)
            
        chave_ex = f"{normalizar(orgao_ex)}|{normalizar(escalao_ex)}|{normalizar(area_ex)}|{normalizar(cargo_ex)}|{titular_norm_ex}"
        mfe_keys[chave_ex] = {"linha": idx + 2}

    # MAPEAR AÇÕES
    linhas_para_excluir = []
    dados_removidos = [] 
    novos_registros = [] 
    dados_adicionados = [] 
    linhas_para_atualizar = [] 

    for chave_ex, dados_ex in mfe_keys.items():
        if chave_ex not in sici_keys:
            linhas_para_excluir.append(dados_ex['linha'])
            linha_real = dados_ex['linha'] - 2
            
            titular_removido = str(df_mfe.iloc[linha_real, 12]) if df_mfe.shape[1] > 12 else ""
            dados_removidos.append({
                "orgao": str(df_mfe.iloc[linha_real, 1]),
                "escalao": str(df_mfe.iloc[linha_real, 2]),
                "area": str(df_mfe.iloc[linha_real, 3]),
                "cargo": str(df_mfe.iloc[linha_real, 4]),
                "titular": titular_removido
            })

    for chave_si, dados_si in sici_keys.items():
        if chave_si not in mfe_keys:
            nova_linha = [""] * 13 
            nova_linha[1] = dados_si['orgao']  
            nova_linha[2] = dados_si['escalao'] 
            nova_linha[3] = dados_si['area']    
            nova_linha[4] = dados_si['cargo']   
            nova_linha[5] = dados_si['tipo_cargo']            # Coluna F 
            nova_linha[6] = dados_si['area_negocio']         # Coluna G (ML)
            nova_linha[7] = dados_si['macro_area']            # Coluna H 
            nova_linha[9] = dados_si['texto_ordenador']       # Coluna J
            nova_linha[11] = dados_si['texto_poder_decisao']  # Coluna L
            nova_linha[12] = dados_si['titular']              # Coluna M 
            
            novos_registros.append(nova_linha)
            dados_adicionados.append(dados_si)
        else:
            linhas_para_atualizar.append({
                'linha': mfe_keys[chave_si]['linha'],
                'tipo_cargo': dados_si['tipo_cargo'],
                'macro_area': dados_si['macro_area'],
                'area_negocio': dados_si['area_negocio'],
                'texto_ordenador': dados_si['texto_ordenador'],
                'texto_poder_decisao': dados_si['texto_poder_decisao'],
                'titular': dados_si['titular']
            })

    # --- 6. ATUALIZAÇÃO FÍSICA NO EXCEL ---
    print(f"\n[*] Aplicando alterações no arquivo '{arquivo_mfe}'...")
    try:
        wb = openpyxl.load_workbook(arquivo_mfe)
        ws = wb[NOME_ABA]
        
        cel_cabecalho_13 = ws.cell(row=1, column=13)
        if not cel_cabecalho_13.value:
            cel_cabecalho_13.value = "Titular"
        
        # 1. ATUALIZAÇÕES
        if linhas_para_atualizar:
            for item in linhas_para_atualizar:
                ws.cell(row=item['linha'], column=13, value=item['titular'])
                
                if item['tipo_cargo']:
                    ws.cell(row=item['linha'], column=6, value=item['tipo_cargo'])
                if item['macro_area']:
                    ws.cell(row=item['linha'], column=8, value=item['macro_area'])
                    
                # Injeta a Área de Negócio da Inteligência Artificial (G = 7)
                cel_k = ws.cell(row=item['linha'], column=7, value=item['area_negocio'])
                if item['area_negocio'].startswith("⚠️"):
                    cel_k.fill = PatternFill(start_color=COR_ALERTA, end_color=COR_ALERTA, fill_type="solid")
                else:
                    cel_k.fill = PatternFill(fill_type=None)
                
                if verificar_ordenadores:
                    ws.cell(row=item['linha'], column=10, value=item['texto_ordenador'])
                    ws.cell(row=item['linha'], column=12, value=item['texto_poder_decisao'])

        # 2. EXCLUSÕES
        if linhas_para_excluir:
            linhas_para_excluir.sort(reverse=True)
            for linha in linhas_para_excluir:
                ws.delete_rows(linha)

        # 3. ADIÇÕES
        if novos_registros:
            ultima_linha = ws.max_row
            while ultima_linha > 1 and ws.cell(row=ultima_linha, column=2).value is None:
                ultima_linha -= 1
            
            linha_alvo = ultima_linha + 1
            for registro in novos_registros:
                for col_idx, valor in enumerate(registro, start=1):
                    if valor: 
                        cel_add = ws.cell(row=linha_alvo, column=col_idx, value=valor)
                        # Pinta a Coluna 7 (G) de Amarelo se o ML der alerta em novos registros
                        if col_idx == 7 and str(valor).startswith("⚠️"):
                            cel_add.fill = PatternFill(start_color=COR_ALERTA, end_color=COR_ALERTA, fill_type="solid")
                            
                linha_alvo += 1

        wb.save(arquivo_mfe)
        print("\n[!] Planilha MFE atualizada salva com sucesso!")
        
    except PermissionError:
        messagebox.showerror("Erro: Arquivo aberto", f"O arquivo {os.path.basename(arquivo_mfe)} está aberto no Excel, feche-o e tente novamente.")
        return
    except Exception as e:
        messagebox.showerror("Erro: openpyxl", f"Falha ao manipular o arquivo via openpyxl:\n {e}")
        return

    # --- 7. SALVAR BACKUP DE AUDITORIA ---
    if dados_removidos or dados_adicionados:
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        registros_alterados = f"alterados_MFE_{agora}.xlsx"
        
        with pd.ExcelWriter(registros_alterados, engine='openpyxl') as writer:
            if dados_removidos:
                df_removidos = pd.DataFrame(dados_removidos)
                df_removidos = df_removidos[['orgao', 'escalao', 'area', 'cargo', 'titular']]
                df_removidos.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo', 'titular': 'Titular'}, inplace=True)
                df_removidos.to_excel(writer, sheet_name='Exclusões', index=False)
                
            if dados_adicionados:
                df_adicionados = pd.DataFrame(dados_adicionados)
                df_adicionados = df_adicionados[['orgao', 'escalao', 'area', 'cargo', 'titular']]
                df_adicionados.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo', 'titular': 'Titular'}, inplace=True)
                df_adicionados.to_excel(writer, sheet_name='Adições', index=False)

    mensagem_resumo = f"Processo finalizado com sucesso!\n\n✅ Adições realizadas: {len(novos_registros)}\n❌ Exclusões realizadas: {len(linhas_para_excluir)}"
    mensagem_resumo += f"\n\n⚙️ A coluna K (Área de Negócio) foi preenchida utilizando Inteligência Artificial."
    
    if verificar_ordenadores:
        mensagem_resumo += f"\n⚙️ As colunas J e L foram validadas conforme a capacidade de alocar/gerir despesas para cada titular."

    messagebox.showinfo("Atualização Concluída", mensagem_resumo)

if __name__ == "__main__":
    root = inicializar_tkinter()
    arquivo_selecionado = selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        atualizar_planilha_mfe(arquivo_selecionado)