import tkinter as tk
from tkinter import messagebox
import threading
import os
from tkinter import filedialog
import config_manager
import scraper_sici_nome
import atualizador_MFE
import match_lideres

# Garante que o config.txt seja criado ao lado do executável na primeira inicialização
config_manager.garantir_config_existe()

def executar_raspagem_completa():
    """Roda a raspagem (O próprio scraper vai perguntar os próximos passos no final)"""
    def tarefa():
        desabilitar_botoes()
        lbl_status.config(text="Status: Raspando o SICI na web... Aguarde.", fg="blue")
        try:
            scraper_sici_nome.iniciar_raspagem()
            lbl_status.config(text="Status: Processo Finalizado!", fg="green")
        except Exception as e:
            lbl_status.config(text="Status: Erro durante o processo.", fg="red")
        finally:
            habilitar_botoes()
    threading.Thread(target=tarefa).start()

def executar_somente_mfe():
    """Roda apenas a atualização MFE a partir de um Excel já existente"""
    atualizador_MFE.inicializar_tkinter()
    arquivo_selecionado = atualizador_MFE.selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        lbl_status.config(text="Status: Atualizando Planilha MFE...", fg="blue")
        atualizador_MFE.atualizar_planilha_mfe(arquivo_selecionado)
        lbl_status.config(text="Status: Atualização MFE Concluída!", fg="green")
    else:
        lbl_status.config(text="Status: Operação Cancelada.", fg="orange")

def executar_somente_lideres():
    """Roda apenas o match de líderes a partir de um Excel SICI já existente"""
    match_lideres.inicializar_tkinter()
    arquivo_selecionado = match_lideres.selecionar_arquivo_sici()
    tarefa = "PLC"
    
    if arquivo_selecionado:
        lbl_status.config(text="Status: Cruzando dados de Líderes...", fg="blue")
        # 🔥 Verifica a resposta do script
        sucesso = match_lideres.cruzar_planilhas(arquivo_selecionado,tarefa)
        
        if sucesso:
            lbl_status.config(text="Status: Cruzamento Concluído!", fg="green")
        else:
            lbl_status.config(text="Status: Operação com Erro ou Cancelada.", fg="red")
    else:
        lbl_status.config(text="Status: Operação Cancelada.", fg="orange")

def executar_somente_lideranca_feminina():
    """Roda apenas o match de líderes a partir de um Excel SICI já existente"""
    match_lideres.inicializar_tkinter()
    arquivo_selecionado = match_lideres.selecionar_arquivo_sici()
    tarefa = "PRLF"
    
    if arquivo_selecionado:
        lbl_status.config(text="Status: Cruzando dados de Líderes...", fg="blue")
        # 🔥 Verifica a resposta do script
        sucesso = match_lideres.cruzar_planilhas(arquivo_selecionado,tarefa)
        
        if sucesso:
            lbl_status.config(text="Status: Cruzamento Concluído!", fg="green")
        else:
            lbl_status.config(text="Status: Operação com Erro ou Cancelada.", fg="red")
    else:
        lbl_status.config(text="Status: Operação Cancelada.", fg="orange")



def abrir_config_palavras():
    """Abre o arquivo config.txt"""
    config_manager.garantir_config_existe()
    try:
        os.startfile("config.txt")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível abrir o arquivo config.txt:\n{e}")

# --- Controles de Interface ---
botoes = []

def desabilitar_botoes():
    for btn in botoes: btn.config(state=tk.DISABLED)

def habilitar_botoes():
    for btn in botoes: btn.config(state=tk.NORMAL)

# ---------------- MONTAGEM DA JANELA (TKINTER) ----------------
root = tk.Tk()
root.title("Robô SICI - Prefeitura do Rio")
root.geometry("450x420")
root.eval('tk::PlaceWindow . center') 
root.resizable(False, False)

tk.Label(root, text="Painel de Controle SICI", font=("Arial", 14, "bold")).pack(pady=(15, 5))

# --- BLOCO PRINCIPAL ---
tk.Label(root, text="Extração de Dados", font=("Arial", 10, "bold"), fg="#555").pack(pady=(5, 0))
btn1 = tk.Button(root, text="1. Iniciar Raspagem Web (SICI)", font=("Arial", 11, "bold"), bg="#e1f5fe", command=executar_raspagem_completa, width=40, height=2)
btn1.pack(pady=5)

# --- BLOCO OFFLINE ---
tk.Label(root, text="Rotinas Offline (Usar Excel já existente)", font=("Arial", 10, "bold"), fg="#555").pack(pady=(15, 0))
btn2 = tk.Button(root, text="2. Somente Atualizar MFE", font=("Arial", 10), bg="#f1f8e9", command=executar_somente_mfe, width=45)
btn2.pack(pady=3)
btn3 = tk.Button(root, text="3. Somente Contabilizar Líderes Cariocas (Minibios)", font=("Arial", 10), bg="#fff3e0", command=executar_somente_lideres, width=45)
btn3.pack(pady=3)
btn4 = tk.Button(root, text="4. Somente Contabilizar Liderança Feminina", font=("Arial", 10), bg="#ffc4dd", command=executar_somente_lideranca_feminina, width=45)
btn4.pack(pady=3)
# --- CONFIGURAÇÕES ---
btn5 = tk.Button(root, text="⚙️ Editar Configurações Gerais (config.txt)", font=("Arial", 9), fg="#333", bg="#f5f5f5", command=abrir_config_palavras, width=45)
btn5.pack(pady=(15, 0))

botoes.extend([btn1, btn2, btn3, btn4, btn5])

lbl_status = tk.Label(root, text="Status: Aguardando comando...", font=("Arial", 9, "italic"), fg="gray")
lbl_status.pack(pady=(10, 0))

root.mainloop()