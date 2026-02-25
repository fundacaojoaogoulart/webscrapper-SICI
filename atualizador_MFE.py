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
    """ Exige 100% de match ignorando apenas maiúsculas e acentos """
    if pd.isna(texto) or not texto: 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto.strip()

def inicializar_tkinter():
    """Garante que a raiz do Tkinter seja criada apenas uma vez e fique invisível"""
    root = tk._default_root
    if root is None:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
    return root

def selecionar_arquivo_sici_interface():
    """Abre uma janela para o usuário escolher o arquivo SICI gerado"""
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha extraída do SICI que contém os dados novos.")
    caminho_arquivo = filedialog.askopenfilename(
        title="1. Selecione a planilha EXTRAÍDA DO SICI",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

def selecionar_planilha_mfe_interface():
    """Abre uma janela para o usuário escolher a planilha MFE"""
    messagebox.showinfo("Selecione um arquivo", "Agora, selecione a planilha do MFE que será ATUALIZADA.")
    caminho_arquivo = filedialog.askopenfilename(
        title="2. Selecione a planilha do MFE",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

# ---------------- LÓGICA PRINCIPAL ----------------
def atualizar_planilha_mfe(dados_sici):
    """
    Função principal que pode receber tanto um caminho de arquivo (string)
    quanto um DataFrame do Pandas (quando invocada por outro script).
    """
    
    root = inicializar_tkinter()
    arquivo_mfe = selecionar_planilha_mfe_interface()
    
    if not arquivo_mfe:
        print("[ALERTA] Nenhuma planilha MFE foi selecionada. Operação cancelada.")
        messagebox.showwarning("Aviso: Nenhuma planilha selecionada",f'Nenhuma planilha MFE foi selecionada. Operação cancelada.')
        return 

    # 1. Carregar os dados do SICI
    if isinstance(dados_sici, str):
        print(f"[*] Carregando dados do arquivo SICI: {os.path.basename(dados_sici)}")
        df_sici = pd.read_excel(dados_sici)
    else:
        print("[*] Recebendo dados do SICI diretamente do Web Scraper...")
        df_sici = dados_sici

    if df_sici.empty:
        print("[ALERTA] Os dados do SICI estão vazios. Nenhuma atualização será feita.")
        return

    # 2. Carregar a planilha MFE
    print(f"[*] Lendo a planilha local '{os.path.basename(arquivo_mfe)}'...")
    try:
        df_mfe = pd.read_excel(arquivo_mfe, sheet_name=NOME_ABA)
    except FileNotFoundError:
        print(f"[ERRO] O arquivo '{arquivo_mfe}' não foi encontrado.")
        messagebox.showerror("Erro: Arquivo não encontrado",f'Falha ao localizar arquivo {arquivo_mfe}')
        return
    except ValueError:
        print(f"[ERRO] A aba '{NOME_ABA}' não existe neste arquivo.")
        messagebox.showerror("Erro: Aba não encontrada",f'Certifique-se de que o arquivo MFE contém a aba {NOME_ABA}')
        return

    # 3. Identificar os órgãos que foram raspados no SICI para filtrar a MFE
    orgaos_presentes_sici = df_sici['órgão'].dropna().unique().tolist()
    orgaos_normalizados_sici = [normalizar(org) for org in orgaos_presentes_sici]

    print(f"[*] Cruzando dados para {len(orgaos_presentes_sici)} órgão(s) com 100% de precisão...")

    # 4. Indexar dados do SICI (Chave Única: Órgão + Escalão + Área + Cargo)
    sici_keys = {}
    for _, rs in df_sici.iterrows():
        orgao_si = str(rs['órgão']) if pd.notna(rs['órgão']) else ""
        area_si = str(rs['área']) if pd.notna(rs['área']) else ""
        cargo_si = str(rs['cargo']) if pd.notna(rs['cargo']) else ""
        escalao_si = str(rs['escalão']) if 'escalão' in df_sici.columns and pd.notna(rs['escalão']) else ""
        
        # 🔥 A CHAVE AGORA OBRIGA O ESCALÃO A BATER TAMBÉM
        chave_si = f"{normalizar(orgao_si)}|{normalizar(escalao_si)}|{normalizar(area_si)}|{normalizar(cargo_si)}"
        sici_keys[chave_si] = {"orgao": orgao_si, "escalao": escalao_si, "area": area_si, "cargo": cargo_si}

    # 5. Indexar dados da Planilha MFE (Apenas dos órgãos pertinentes)
    mfe_keys = {}
    for idx, row in df_mfe.iterrows():
        orgao_ex = str(row.iloc[1]) if pd.notna(row.iloc[1]) else "" # Coluna B
        
        if normalizar(orgao_ex) not in orgaos_normalizados_sici:
            continue

        escalao_ex = str(row.iloc[2]) if pd.notna(row.iloc[2]) else "" # Coluna C
        area_ex = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""  # Coluna D
        cargo_ex = str(row.iloc[4]) if pd.notna(row.iloc[4]) else "" # Coluna E
        
        if not normalizar(area_ex) and not normalizar(cargo_ex):
            continue
            
        # 🔥 CHAVE ATUALIZADA COM O ESCALÃO DO MFE
        chave_ex = f"{normalizar(orgao_ex)}|{normalizar(escalao_ex)}|{normalizar(area_ex)}|{normalizar(cargo_ex)}"
        mfe_keys[chave_ex] = {"orgao": orgao_ex, "escalao": escalao_ex, "area": area_ex, "cargo": cargo_ex, "linha": idx + 2}

    # 6. Mapear Ações (Exclusões e Adições)
    linhas_para_excluir = []
    dados_removidos = [] 
    
    novos_registros = [] 
    dados_adicionados = [] 

    # Varredura: DELETAR (Está na MFE mas NÃO está no SICI)
    for chave_ex, dados_ex in mfe_keys.items():
        if chave_ex not in sici_keys:
            linhas_para_excluir.append(dados_ex['linha'])
            dados_removidos.append(dados_ex)
            # Imprime o escalão removido também no log
            print(f"    [-] EXCLUSÃO -> Órgão: '{dados_ex['orgao']}' | Escalão: '{dados_ex['escalao']}' | Área: '{dados_ex['area']}' | Cargo: '{dados_ex['cargo']}' (Linha {dados_ex['linha']})")

    # Varredura: ADICIONAR (Está no SICI mas NÃO está na MFE)
    for chave_si, dados_si in sici_keys.items():
        if chave_si not in mfe_keys:
            nova_linha = ["", dados_si['orgao'], dados_si['escalao'], dados_si['area'], dados_si['cargo'], ""]
            
            novos_registros.append(nova_linha)
            dados_adicionados.append(dados_si)
            
            print(f"    [+] ADIÇÃO -> Órgão: '{dados_si['orgao']}' | Escalão: '{dados_si['escalao']}' | Área: '{dados_si['area']}' | Cargo: '{dados_si['cargo']}'")

    # 7. APLICAÇÃO FÍSICA NO EXCEL MFE
    print(f"\n[*] Aplicando alterações no arquivo '{arquivo_mfe}'...")
    try:
        wb = openpyxl.load_workbook(arquivo_mfe)
        ws = wb[NOME_ABA]
        
        if linhas_para_excluir:
            linhas_para_excluir.sort(reverse=True)
            for linha in linhas_para_excluir:
                ws.delete_rows(linha)
            print(f"    [✓] {len(linhas_para_excluir)} cargos excluídos fisicamente da MFE.")
        else:
            print("    [✓] Nenhum cargo pendente de exclusão na MFE.")

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
            print(f"    [✓] {len(novos_registros)} novos cargos injetados.")
        else:
            print("    [✓] Nenhum cargo novo para adicionar.")

        wb.save(arquivo_mfe)
        print("\n[!] Planilha MFE atualizada salva com sucesso!")
        

    except PermissionError:
        print(f"\n[ERRO FATAL] O arquivo '{arquivo_mfe}' está aberto no Excel. Feche-o e tente novamente.")
        messagebox.showerror("Erro: Arquivo aberto",f'O arquivo {os.path.basename(arquivo_mfe)} está aberto, feche-o e tente novamente.')
        return
    except Exception as e:
        print(f"\n[ERRO] Falha ao manipular o arquivo via openpyxl: {e}")
        messagebox.showerror("Erro: openpyxl",f'Falha ao manipular o arquivo via openpyxl:\n {e}')
        return

    # 8. SALVAR BACKUP DOS REMOVIDOS E ADICIONADOS
    if dados_removidos or dados_adicionados:
        agora = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        registros_alterados = f"alterados_MFE_{agora}.xlsx"
        
        with pd.ExcelWriter(registros_alterados, engine='openpyxl') as writer:
            
            # Aba de Exclusões
            if dados_removidos:
                df_removidos = pd.DataFrame(dados_removidos)
                # 🔥 INCLUINDO A COLUNA 'escalao' AQUI
                df_removidos = df_removidos[['orgao', 'escalao', 'area', 'cargo']]
                df_removidos.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo'}, inplace=True)
                df_removidos.to_excel(writer, sheet_name='Exclusões', index=False)
                
            # Aba de Adições
            if dados_adicionados:
                df_adicionados = pd.DataFrame(dados_adicionados)
                # 🔥 INCLUINDO A COLUNA 'escalao' AQUI
                df_adicionados = df_adicionados[['orgao', 'escalao', 'area', 'cargo']]
                df_adicionados.rename(columns={'orgao': 'Órgão', 'escalao': 'Escalão', 'area': 'Área/Título', 'cargo': 'Cargo'}, inplace=True)
                df_adicionados.to_excel(writer, sheet_name='Adições', index=False)
                
        print(f"\n[!] Planilha de auditoria '{registros_alterados}' gerada com sucesso!")

    mensagem_resumo = f"Processo finalizado com sucesso!\n\n"
    mensagem_resumo += f"✅ Adições realizadas: {len(novos_registros)}\n"
    mensagem_resumo += f"❌ Exclusões realizadas: {len(linhas_para_excluir)}"
    
    if dados_removidos or dados_adicionados:
        mensagem_resumo += f"\n\nUm arquivo de auditoria foi gerado com os detalhes."
        
    messagebox.showinfo("Atualização Concluída", mensagem_resumo)

# ---------------- EXECUÇÃO DIRETA ----------------
if __name__ == "__main__":
    root = inicializar_tkinter()
    
    arquivo_selecionado = selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        atualizar_planilha_mfe(arquivo_selecionado)
    else:
        messagebox.showerror('Erro','Nenhum arquivo SICI foi selecionado. Encerrando aplicação.')
        print("Operação cancelada. Nenhum arquivo SICI foi selecionado.")