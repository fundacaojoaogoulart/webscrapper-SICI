import tkinter as tk
from tkinter import messagebox
import threading
import os
from tkinter import filedialog
import calculadora_tercis
import scraper_sici_nome
import atualizador_MFE
import match_lideres

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


def executar_cruzamento_empenhos():
    # Pede o arquivo SICI
    caminho_sici = filedialog.askopenfilename(
        title="1º Passo: Selecione a planilha do SICI",
        filetypes=[("Arquivos Excel", "*.xlsx *.xls")]
    )
    if not caminho_sici:
        lbl_status.config(text="Status: Operação Cancelada (SICI não selecionado).", fg="orange")
        return

    # Pede o arquivo de Empenhos
    caminho_empenhos = filedialog.askopenfilename(
        title="2º Passo: Selecione a planilha de Valor Empenhado",
        filetypes=[("Arquivos Excel/CSV", "*.xlsx *.xls *.csv")]
    )
    if not caminho_empenhos:
        lbl_status.config(text="Status: Operação Cancelada (Empenhos não selecionados).", fg="orange")
        return

    caminho_saida = "SICI_Atualizado_com_Tercis.xlsx"

    def tarefa_cruzamento():
        desabilitar_botoes()
        lbl_status.config(text="Status: Processando Empenhos e Cruzando Dados...", fg="blue")
        try:
            sucesso, relat_inter = calculadora_tercis.cruzar_sici_com_tercis(caminho_sici, caminho_empenhos, caminho_saida)
            if sucesso:
                msg = f"Status: Concluído! Salvo em '{caminho_saida}' (Intermediário: '{relat_inter}')"
                lbl_status.config(text=msg, fg="green")
        except Exception as e:
            lbl_status.config(text=f"Status: Erro - {str(e)}", fg="red")
            messagebox.showerror("Erro de Processamento", f"Falha ao cruzar dados:\n{str(e)}")
        finally:
            habilitar_botoes()
    threading.Thread(target=tarefa_cruzamento).start()


def abrir_config_palavras():
    """Abre o arquivo config.txt"""
    scraper_sici_nome.carregar_palavras_ignoradas() 
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
btn_tercis = tk.Button(root, text="5. Calcular Critério de Magnitude do Orçamento", font=("Arial", 10, "bold"), bg="#d1c4e9", command=executar_cruzamento_empenhos, width=45)
btn_tercis.pack(pady=3)

# --- CONFIGURAÇÕES ---
btn5 = tk.Button(root, text="⚙️ Editar Filtro de Palavras Ignoradas", font=("Arial", 9), fg="#333", bg="#f5f5f5", command=abrir_config_palavras, width=45)
btn5.pack(pady=(15, 0))

botoes.extend([btn1, btn2, btn3, btn4, btn_tercis, btn5])

lbl_status = tk.Label(root, text="Status: Aguardando comando...", font=("Arial", 9, "italic"), fg="gray")
lbl_status.pack(pady=(10, 0))

root.mainloop()