import pandas as pd
import openpyxl
import unicodedata
import re
import datetime
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

# ---------------- CONFIGURAÇÕES ----------------
NOME_ABA = "Todas as Funções (Editável)"

# ---------------- UTILITÁRIOS ----------------
def normalizar(texto):
    """ Exige 100% de match eliminando tudo para Órgãos, Áreas e Cargos """
    if pd.isna(texto) or not str(texto).strip(): 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto.strip()

def normalizar_nome(texto):
    """ Normalização exclusiva para Nomes de Titulares (Preserva espaços) """
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

    # --- CARREGAMENTO DO SICI ---
    if isinstance(dados_sici, str):
        print(f"[*] Carregando dados do arquivo SICI: {os.path.basename(dados_sici)}")
        df_sici = pd.read_excel(dados_sici)
    else:
        print("[*] Recebendo dados do SICI diretamente do fluxo principal...")
        df_sici = dados_sici

    if df_sici.empty:
        print("[ALERTA] Os dados do SICI estão vazios.")
        return

    # --- VERIFICAÇÃO DE ORDENADORES ---
    verificar_ordenadores = messagebox.askyesno(
        "Ordenadores de Despesa", 
        "Deseja verificar por ordenadores de despesa? (Será necessário fornecer a base de dados em Excel/CSV)"
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
                
                # Inteligência de Dados: Scanner de Interseção
                titulares_sici = set(normalizar_nome(str(t)) for t in df_sici.get('titular', []).dropna())
                lixos = {'vago', 'vaga', 'nao informado', 'sem titular', '-'}
                titulares_sici = {t for t in titulares_sici if len(t) > 3 and t not in lixos}

                melhor_coluna = None
                maior_match = 0

                for col in df_ord.columns:
                    valores_col = set(normalizar_nome(str(v)) for v in df_ord[col].dropna())
                    valores_col = {v for v in valores_col if len(v) > 3}
                    
                    matches = len(titulares_sici.intersection(valores_col))
                    if matches > maior_match:
                        maior_match = matches
                        melhor_coluna = col

                if maior_match > 0 and melhor_coluna:
                    print(f"[*] Coluna '{melhor_coluna}' detectada pelo Scanner com {maior_match} nomes exatos.")
                    for val in df_ord[melhor_coluna].dropna():
                        nome_limpo = normalizar_nome(val)
                        if len(nome_limpo) > 3 and nome_limpo not in lixos:
                            set_ordenadores.add(nome_limpo)
                else:
                    print("[⚠️] AVISO: Nenhum cruzamento exato encontrado entre o SICI e a planilha de ordenadores.")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao processar arquivo de ordenadores:\n{e}")
                verificar_ordenadores = False

    # --- LEITURA DA MFE ---
    print(f"[*] Lendo a planilha local '{os.path.basename(arquivo_mfe)}'...")
    try:
        df_mfe = pd.read_excel(arquivo_mfe, sheet_name=NOME_ABA)
    except Exception as e:
        messagebox.showerror("Erro de Arquivo", f"Falha ao ler MFE:\n{e}")
        return

    orgaos_presentes_sici = df_sici['órgão'].dropna().unique().tolist()
    orgaos_normalizados_sici = [normalizar(org) for org in orgaos_presentes_sici]

    print(f"[*] Cruzando dados para {len(orgaos_presentes_sici)} órgão(s) com 100% de precisão...")

    # 🔥 CORREÇÃO: AVALIAÇÃO ESTRITA LINHA POR LINHA PELO TITULAR DA ÁREA
    sici_keys = {}
    for _, rs in df_sici.iterrows():
        orgao_si = str(rs.get('órgão', ''))
        area_si = str(rs.get('área', ''))
        cargo_si = str(rs.get('cargo', ''))
        escalao_si = str(rs.get('escalão', ''))
        
        # Isola o titular exato desta linha específica do SICI
        titular_si = normalizar_nome(str(rs.get('titular', '')))
        is_ordenador = False
        
        # Verifica se o nome EXATO desta pessoa está na base de ordenadores
        if verificar_ordenadores and titular_si and (titular_si in set_ordenadores):
            is_ordenador = True
            
        texto_ordenador = "2 - Possui poder de decisão sobre alocação de recursos orçamentários no órgão" if is_ordenador else "1 - Não possui poder de decisão sobre alocação de recursos orçamentários no órgão"
        
        chave_si = f"{normalizar(orgao_si)}|{normalizar(escalao_si)}|{normalizar(area_si)}|{normalizar(cargo_si)}"
        sici_keys[chave_si] = {
            "orgao": orgao_si, 
            "escalao": escalao_si, 
            "area": area_si, 
            "cargo": cargo_si,
            "texto_ordenador": texto_ordenador 
        }

    # INDEXAÇÃO DA PLANILHA MFE
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
            
        chave_ex = f"{normalizar(orgao_ex)}|{normalizar(escalao_ex)}|{normalizar(area_ex)}|{normalizar(cargo_ex)}"
        mfe_keys[chave_ex] = {"orgao": orgao_ex, "escalao": escalao_ex, "area": area_ex, "cargo": cargo_ex, "linha": idx + 2}

    # MAPEAR AÇÕES
    linhas_para_excluir = []
    dados_removidos = [] 
    novos_registros = [] 
    dados_adicionados = [] 
    linhas_para_atualizar = [] 

    # Varredura: DELETAR
    for chave_ex, dados_ex in mfe_keys.items():
        if chave_ex not in sici_keys:
            linhas_para_excluir.append(dados_ex['linha'])
            dados_removidos.append(dados_ex)

    # Varredura: ADICIONAR e ATUALIZAR COLUNA L
    for chave_si, dados_si in sici_keys.items():
        if chave_si not in mfe_keys:
            nova_linha = [""] * 12
            nova_linha[1] = dados_si['orgao']  
            nova_linha[2] = dados_si['escalao'] 
            nova_linha[3] = dados_si['area']    
            nova_linha[4] = dados_si['cargo']   
            nova_linha[11] = dados_si['texto_ordenador'] 
            
            novos_registros.append(nova_linha)
            dados_adicionados.append(dados_si)
        else:
            linhas_para_atualizar.append({
                'linha': mfe_keys[chave_si]['linha'],
                'texto_ordenador': dados_si['texto_ordenador']
            })

    # APLICAÇÃO NO EXCEL MFE
    print(f"\n[*] Aplicando alterações no arquivo '{arquivo_mfe}'...")
    try:
        wb = openpyxl.load_workbook(arquivo_mfe)
        ws = wb[NOME_ABA]
        
        if linhas_para_excluir:
            linhas_para_excluir.sort(reverse=True)
            for linha in linhas_para_excluir:
                ws.delete_rows(linha)

        if novos_registros:
            ultima_linha = ws.max_row
            while ultima_linha > 1 and ws.cell(row=ultima_linha, column=2).value is None:
                ultima_linha -= 1
            
            linha_alvo = ultima_linha + 1
            for registro in novos_registros:
                for col_idx, valor in enumerate(registro, start=1):
                    if valor: 
                        ws.cell(row=linha_alvo, column=col_idx, value=valor)
                linha_alvo += 1

        if linhas_para_atualizar and verificar_ordenadores:
            for item in linhas_para_atualizar:
                ws.cell(row=item['linha'], column=12, value=item['texto_ordenador'])

        wb.save(arquivo_mfe)
        print("\n[!] Planilha MFE atualizada salva com sucesso!")
        
    except PermissionError:
        messagebox.showerror("Erro: Arquivo aberto", f"O arquivo {os.path.basename(arquivo_mfe)} está aberto no Excel, feche-o e tente novamente.")
        return
    except Exception as e:
        messagebox.showerror("Erro: openpyxl", f"Falha ao manipular o arquivo via openpyxl:\n {e}")
        return

    # SALVAR BACKUP DE AUDITORIA
    if dados_removidos or dados_adicionados:
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        registros_alterados = f"alterados_MFE_{agora}.xlsx"
        
        with pd.ExcelWriter(registros_alterados, engine='openpyxl') as writer:
            if dados_removidos:
                df_removidos = pd.DataFrame(dados_removidos)
                df_removidos = df_removidos[['orgao', 'escalao', 'area', 'cargo']]
                df_removidos.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo'}, inplace=True)
                df_removidos.to_excel(writer, sheet_name='Exclusões', index=False)
                
            if dados_adicionados:
                df_adicionados = pd.DataFrame(dados_adicionados)
                df_adicionados = df_adicionados[['orgao', 'escalao', 'area', 'cargo']]
                df_adicionados.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo'}, inplace=True)
                df_adicionados.to_excel(writer, sheet_name='Adições', index=False)

    mensagem_resumo = f"Processo finalizado com sucesso!\n\n✅ Adições realizadas: {len(novos_registros)}\n❌ Exclusões realizadas: {len(linhas_para_excluir)}"
    
    if verificar_ordenadores:
        mensagem_resumo += f"\n\n⚙️ A coluna L foi calibrada individualmente para cada titular!"

    messagebox.showinfo("Atualização Concluída", mensagem_resumo)

if __name__ == "__main__":
    root = inicializar_tkinter()
    arquivo_selecionado = selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        atualizar_planilha_mfe(arquivo_selecionado)