import pandas as pd
import unicodedata
import numpy as np
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import os

# ---------------- UTILITÁRIOS ----------------
def normalizar_nome(texto):
    """ Deixa em minúsculo, remove acentos e espaços extras """
    if pd.isna(texto) or not str(texto).strip():
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = " ".join(texto.split())
    return texto

def selecionar_arquivo_sici():
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha BASE (que contém os dados de titular, área e cargo).")
    caminho_arquivo = filedialog.askopenfilename(
        title="1. Selecione a planilha BASE",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

def selecionar_planilha():
    messagebox.showinfo("Selecione um arquivo", "Selecione a planilha com os NOMES (CGGI) para fazer o cruzamento.")
    caminho_arquivo = filedialog.askopenfilename(
        title="2. Selecione a planilha da CGGI",
        filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os Arquivos", "*.*")]
    )
    return caminho_arquivo

# ---------------- LÓGICA PRINCIPAL ----------------
def cruzar_planilhas(dados_sici, tarefa=""):
    print(f"[*] Iniciando cruzamento para: {tarefa}")
    
    # Define o nome do arquivo de saída com base na tarefa
    arquivo_saida = f"resultado_cruzamento_{tarefa}.xlsx"
    
    try:
        planilha_a = selecionar_planilha()
        if not planilha_a:
            print("[ALERTA] Nenhuma planilha foi selecionada.")
            messagebox.showwarning("Aviso", "Nenhuma planilha da CGGI foi selecionada. Operação cancelada.")
            return False
        
        if isinstance(dados_sici, str):
            print(f"[*] Carregando dados do arquivo SICI: {os.path.basename(dados_sici)}")
            df_b = pd.read_excel(dados_sici, sheet_name=0)
        else:
            print("[*] Recebendo dados do SICI diretamente do fluxo principal...")
            df_b = dados_sici

        if df_b is None or df_b.empty:
            print("[ALERTA] Os dados do SICI estão vazios.")
            messagebox.showwarning("Aviso", "A base fornecida está vazia. Operação cancelada.")
            return False

        df_a = pd.read_excel(planilha_a, sheet_name=0)
        
    except FileNotFoundError as e:
        messagebox.showerror("Erro de Arquivo", f"Arquivo não encontrado:\n{e}")
        return False
    except Exception as e:
        messagebox.showerror("Erro de Leitura", f"Falha ao ler os arquivos:\n{e}")
        return False

    # 🔥 PORTA DE VALIDAÇÃO
    if 'NOME' not in df_a.columns:
        erro_msg = "A planilha da CGGI não possui a coluna 'NOME'.\n\nVerifique o cabeçalho do arquivo e tente novamente."
        print(f"[ERRO] {erro_msg}")
        messagebox.showerror("Erro de Formato", erro_msg)
        return False
        
    for col in ['titular', 'área', 'cargo']:
        if col not in df_b.columns:
            erro_msg = f"A planilha base não possui a coluna obrigatória '{col}'.\n\nVerifique o arquivo e tente novamente."
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
    
    # Define os textos dinamicamente com base na tarefa
    if tarefa == "gerenciador":
        texto_positivo = "líder em cargo de gerencia de equipes"
        texto_negativo = "Não está em cargo de gerencia de equipes"
    else: # ordenador
        texto_positivo = "líder em cargo de ordenação de despesas"
        texto_negativo = "Não está em cargo de ordenação de despesas"

    df_c['status'] = np.where(
        df_c['chave_nome_b'].notna(), 
        texto_positivo, 
        texto_negativo
    )

    df_c = df_c.drop(columns=['chave_nome_a', 'chave_nome_b'])

    colunas_originais_a = [col for col in df_a.columns if col != 'chave_nome_a']
    nova_ordem = colunas_originais_a + ['status', 'área', 'cargo']
    df_c = df_c[nova_ordem]

    print(f"[*] Salvando o resultado final em '{arquivo_saida}'...")
    try:
        df_c.to_excel(arquivo_saida, index=False)
    except PermissionError:
        print(f"\n[ERRO FATAL] O arquivo '{arquivo_saida}' está aberto.")
        messagebox.showerror("Arquivo Aberto", f"O arquivo '{arquivo_saida}' está aberto no Excel. Feche-o e tente novamente.")
        return False 
    except Exception as e:
        messagebox.showerror("Erro Crítico", f"Falha ao salvar a planilha:\n{e}")
        return False
    
    total_lideres = len(df_c)
    total_comissionados = len(df_c[df_c['status'] == texto_positivo])

    resumo_msg = f"✅ Cruzamento Concluído!\n\nTotal analisado: {total_lideres}\nEncontrados ({tarefa}): {total_comissionados}\n\nArquivo '{arquivo_saida}' salvo com sucesso!"
    
    messagebox.showinfo("Match concluído!", resumo_msg)
    print(f"\n✅ Concluído!")
    return True

# ---------------- MONTAGEM DA JANELA (TKINTER) ----------------
def iniciar_painel():
    root = tk.Tk()
    root.title("Conferências CGGI - Equipes e Despesas")
    root.geometry("450x300")
    root.eval('tk::PlaceWindow . center') 
    root.resizable(False, False)

    # Funções "Wrapper" para os botões não executarem sozinhos
    def acao_gerenciador():
        arquivo = selecionar_arquivo_sici()
        if arquivo:
            lbl_status.config(text="Status: Processando Gerenciadores...", fg="blue")
            sucesso = cruzar_planilhas(arquivo, "gerenciador")
            if sucesso:
                lbl_status.config(text="Status: Processo Finalizado!", fg="green")
            else:
                lbl_status.config(text="Status: Operação Cancelada/Erro.", fg="red")

    def acao_ordenador():
        arquivo = selecionar_arquivo_sici()
        if arquivo:
            lbl_status.config(text="Status: Processando Ordenadores...", fg="blue")
            sucesso = cruzar_planilhas(arquivo, "ordenador")
            if sucesso:
                lbl_status.config(text="Status: Processo Finalizado!", fg="green")
            else:
                lbl_status.config(text="Status: Operação Cancelada/Erro.", fg="red")

    tk.Label(root, text="Painel de Controle CGGI", font=("Arial", 14, "bold")).pack(pady=(15, 15))

    btn1 = tk.Button(root, text="1. Checar Gestores de Equipe", font=("Arial", 11, "bold"), bg="#e1f5fe", command=acao_gerenciador, width=40, height=2)
    btn1.pack(pady=5)

    btn2 = tk.Button(root, text="2. Checar Ordenadores de Despesa", font=("Arial", 11, "bold"), bg="#f1f8e9", command=acao_ordenador, width=40, height=2)
    btn2.pack(pady=5)

    lbl_status = tk.Label(root, text="Status: Aguardando comando...", font=("Arial", 9, "italic"), fg="gray")
    lbl_status.pack(pady=(15, 0))

    root.mainloop()

# ---------------- EXECUÇÃO ----------------
if __name__ == "__main__":
    iniciar_painel()