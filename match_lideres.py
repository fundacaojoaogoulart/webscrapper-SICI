import pandas as pd
import unicodedata
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import os

# ---------------- CONFIGURAÇÕES ----------------
ARQUIVO_C = "planilha_cruzamento.xlsx"

# ---------------- UTILITÁRIOS ----------------
def normalizar_nome(texto):
    """ Deixa em minúsculo, remove acentos e espaços extras """
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

def selecionar_arquivo_sici():
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha extraída do SICI que contém os dados das funções.")
    caminho_arquivo = filedialog.askopenfilename(
        title="1. Selecione a planilha EXTRAÍDA DO SICI",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

def selecionar_planilha_minibios():
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha de Lideranças para fazer o cruzamento.")
    caminho_arquivo = filedialog.askopenfilename(
        title="2. Selecione a planilha de Lideranças",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

# ---------------- LÓGICA PRINCIPAL ----------------
def cruzar_planilhas(dados_sici,tarefa = ""):
    print("[*] Carregando as planilhas...")
    
    try:
        root = inicializar_tkinter()
        
        planilha_a = selecionar_planilha_minibios()
        if not planilha_a:
            print("[ALERTA] Nenhuma planilha de lideranças foi selecionada.")
            messagebox.showwarning("Aviso", "Nenhuma planilha de lideranças foi selecionada. Operação cancelada.")
            return False
        
        if isinstance(dados_sici, str):
            print(f"[*] Carregando dados do arquivo SICI: {os.path.basename(dados_sici)}")
            df_b = pd.read_excel(dados_sici, sheet_name=0)
        else:
            print("[*] Recebendo dados do SICI diretamente do fluxo principal...")
            df_b = dados_sici

        if df_b is None or df_b.empty:
            print("[ALERTA] Os dados do SICI estão vazios.")
            messagebox.showwarning("Aviso", "A base do SICI está vazia. Operação cancelada.")
            return False

        df_a = pd.read_excel(planilha_a, sheet_name=0)
        
    except FileNotFoundError as e:
        messagebox.showerror("Erro de Arquivo", f"Arquivo não encontrado:\n{e}")
        return False
    except Exception as e:
        messagebox.showerror("Erro de Leitura", f"Falha ao ler os arquivos:\n{e}")
        return False
    
    if tarefa == "PLC":
        ARQUIVO_C = "planilha_cruzamento_PLC.xlsx"
    elif tarefa == "PRLF":
        ARQUIVO_C = "planilha_cruzamento_PRLF.xlsx"

    # 🔥 PORTA DE VALIDAÇÃO: Verifica se as colunas obrigatórias existem antes de prosseguir
    if 'NOME' not in df_a.columns:
        erro_msg = "A planilha de Líderanças selecionada não possui a coluna 'NOME'.\n\nVerifique o cabeçalho do arquivo e tente novamente."
        print(f"[ERRO] {erro_msg}")
        messagebox.showerror("Erro de Formato", erro_msg)
        return False
        
    for col in ['titular', 'área', 'cargo']:
        if col not in df_b.columns:
            erro_msg = f"A planilha do SICI não possui a coluna obrigatória '{col}'.\n\nVerifique se você gerou o SICI completo e tente novamente."
            print(f"[ERRO] {erro_msg}")
            messagebox.showerror("Erro de Formato", erro_msg)
            return False

    print("[*] Normalizando os nomes para comparação...")
    
    try:
        df_a['chave_nome_a'] = df_a['NOME'].apply(normalizar_nome)
        df_b['chave_nome_b'] = df_b['titular'].apply(normalizar_nome)
    except Exception as e:
        messagebox.showerror("Erro na Normalização", f"Falha ao processar os nomes:\n{e}")
        return False

    df_b_filtrado = df_b[['chave_nome_b', 'área', 'cargo']].drop_duplicates(subset=['chave_nome_b'])

    print("[*] Cruzando os dados (Left Join)...")
    
    df_c = pd.merge(
        df_a, 
        df_b_filtrado, 
        how='left', 
        left_on='chave_nome_a', 
        right_on='chave_nome_b'
    )

    print("[*] Gerando a coluna de status...")
    if tarefa == "PLC":
        df_c['status'] = np.where(
            df_c['chave_nome_b'].notna(), 
            "Líder em cargo comissionado", 
            "Não está em cargo comissionado"
        )
    elif tarefa == "PRLF":
            df_c['status'] = np.where(
            df_c['chave_nome_b'].notna(), 
            "Liderança feminina em cargo comissionado", 
            "Não está em cargo comissionado"
        )
    df_c = df_c.drop(columns=['chave_nome_a', 'chave_nome_b'])

    colunas_originais_a = [col for col in df_a.columns if col != 'chave_nome_a']
    nova_ordem = colunas_originais_a + ['status', 'área', 'cargo']
    df_c = df_c[nova_ordem]

    print(f"[*] Salvando o resultado final em '{ARQUIVO_C}'...")
    try:
        df_c.to_excel(ARQUIVO_C, index=False)
    except PermissionError:
        print(f"\n[ERRO FATAL] O arquivo '{ARQUIVO_C}' está aberto.")
        messagebox.showerror("Arquivo Aberto", f"O arquivo '{ARQUIVO_C}' está aberto no Excel. Feche-o e tente novamente.")
        return False 
    except Exception as e:
        messagebox.showerror("Erro Crítico", f"Falha ao salvar a planilha:\n{e}")
        return False
    
    total_lideres = len(df_c)
    if tarefa == "PLC":
        total_comissionados = len(df_c[df_c['status'] == "líder em cargo comissionado"]) 
    elif tarefa == "PRLF":
        total_comissionados = len(df_c[df_c['status'] == "liderança feminina em cargo comissionado"])
    
    resumo_msg = f"✅ Cruzamento Concluído!\n\nTotal de líderes validados: {total_lideres}\nEncontrados em cargos comissionados: {total_comissionados}\n\nArquivo '{ARQUIVO_C}' salvo com sucesso!"
    
    messagebox.showinfo("Match concluído!", resumo_msg)
    print(f"\n✅ Concluído!")
    return True # 🔥 Retorna verdadeiro se tudo der certo

if __name__ == "__main__":
    root = inicializar_tkinter()
    arquivo_selecionado = selecionar_arquivo_sici()

    if arquivo_selecionado:
        cruzar_planilhas(arquivo_selecionado)
    else:
        messagebox.showwarning('Cancelado', 'Nenhum arquivo SICI foi selecionado. Encerrando aplicação.')