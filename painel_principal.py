import tkinter as tk
from tkinter import messagebox
import threading
import os # 🔥 Import necessário para abrir arquivos do Windows

import scraper_sici
import atualizador_MFE

def executar_fluxo_completo():
    """Roda a raspagem e em seguida a atualização (Opção 1)"""
    def tarefa():
        btn_completo.config(state=tk.DISABLED)
        btn_somente_mfe.config(state=tk.DISABLED)
        btn_config.config(state=tk.DISABLED)
        lbl_status.config(text="Status: Raspando o SICI... Aguarde.", fg="blue")
        try:
            scraper_sici.iniciar_raspagem()
            lbl_status.config(text="Status: Processo Finalizado!", fg="green")
        except Exception as e:
            lbl_status.config(text="Status: Erro durante o processo.", fg="red")
        finally:
            btn_completo.config(state=tk.NORMAL)
            btn_somente_mfe.config(state=tk.NORMAL)
            btn_config.config(state=tk.NORMAL)
            
    thread = threading.Thread(target=tarefa)
    thread.start()

def executar_somente_mfe():
    """Roda apenas a atualização a partir de um Excel já existente (Opção 2)"""
    root_aux = atualizador_MFE.inicializar_tkinter()
    arquivo_selecionado = atualizador_MFE.selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        lbl_status.config(text="Status: Atualizando Planilha MFE...", fg="blue")
        atualizador_MFE.atualizar_planilha_mfe(arquivo_selecionado)
        lbl_status.config(text="Status: Atualização MFE Concluída!", fg="green")
    else:
        messagebox.showwarning('Cancelado', 'Nenhum arquivo SICI foi selecionado. Operação cancelada.')
        lbl_status.config(text="Status: Operação Cancelada.", fg="orange")

def abrir_config_palavras():
    """Abre o arquivo config.txt no Bloco de Notas (Opção 3)"""
    # Chama a função do scraper só para garantir que o arquivo seja criado caso não exista
    scraper_sici.carregar_palavras_ignoradas()
    
    try:
        if os.name == 'nt': # Se for Windows
            os.startfile("config.txt")
        else: # Se for Mac/Linux
            import subprocess
            subprocess.call(['open', 'config.txt'])
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo config.txt:\n{e}")

# ---------------- MONTAGEM DA JANELA (TKINTER) ----------------
root = tk.Tk()
root.title("Robô SICI & MFE - Prefeitura do Rio")
root.geometry("450x320") # 🔥 Aumentei a altura para caber o novo botão
root.eval('tk::PlaceWindow . center') 
root.resizable(False, False)

tk.Label(
    root, 
    text="Painel de Controle SICI/MFE", 
    font=("Arial", 14, "bold")
).pack(pady=(20, 10))

# Botão 1
btn_completo = tk.Button(
    root, 
    text="1. Iniciar Raspagem no SICI (+ Atualizar MFE)", 
    font=("Arial", 11), 
    bg="#e1f5fe",
    command=executar_fluxo_completo, 
    width=40, height=2
)
btn_completo.pack(pady=5)

# Botão 2
btn_somente_mfe = tk.Button(
    root, 
    text="2. Apenas Atualizar MFE (Já tenho a planilha)", 
    font=("Arial", 11), 
    bg="#f1f8e9",
    command=executar_somente_mfe, 
    width=40, height=2
)
btn_somente_mfe.pack(pady=5)

# Botão 3 - 🔥 NOVO BOTÃO
btn_config = tk.Button(
    root, 
    text="3. Editar Palavras Ignoradas (Filtro)", 
    font=("Arial", 11), 
    bg="#fff9c4", # Cor de fundo amarelinha clara
    command=abrir_config_palavras, 
    width=40, height=2
)
btn_config.pack(pady=5)

# Label de Status
lbl_status = tk.Label(root, text="Status: Aguardando comando...", font=("Arial", 9, "italic"), fg="gray")
lbl_status.pack(pady=(15, 0))

root.mainloop()