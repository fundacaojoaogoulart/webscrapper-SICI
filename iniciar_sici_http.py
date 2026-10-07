"""Entrada interativa do executável experimental SICI HTTP.

Compilar: python -m PyInstaller --clean --noconfirm --onefile --console
    --name SICI_HTTP_Paralelo --icon icon.ico iniciar_sici_http.py
Distribua também o config.txt atual ao lado do executável.
"""

import sys
import traceback
import tkinter as tk
from tkinter import filedialog

from scraper_sici_http import main


def selecionar_planilha(titulo):
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askopenfilename(
            parent=root, title=titulo,
            filetypes=[("Planilha Excel", "*.xlsx")],
        )
    finally:
        root.destroy()


def iniciar():
    # Mantém a linha de comando disponível para testes e automações.
    if len(sys.argv) > 1:
        return main(sys.argv[1:])
    codigo = 0
    try:
        print("SICI HTTP - EXTRACAO PARALELA (4 trabalhadores)\n")
        print("1 - Extrair órgãos da administração direta")
        print("2 - Extrair órgãos da administração indireta")
        print("3 - Extrair os dois grupos")
        print("4 - Extrair administração direta e comparar com Excel do Selenium")
        print("5 - Comparar dois arquivos já extraídos")
        print("0 - Sair\n")
        opcao = input("Escolha uma opcao: ").strip()
        if opcao == "0":
            return 0
        if opcao not in {"1", "2", "3", "4", "5"}:
            print("Opcao invalida.")
            return 1
        argumentos = []
        if opcao in {"2", "3"}:
            argumentos.extend(["--administracao", "indireta" if opcao == "2" else "ambas"])
        if opcao in {"4", "5"}:
            referencia = selecionar_planilha("Selecione a extracao ORIGINAL do Selenium")
            if not referencia:
                print("Operacao cancelada.")
                return 0
            argumentos.extend(["--comparar", referencia])
        if opcao == "5":
            http = selecionar_planilha("Selecione a extracao HTTP para comparar")
            if not http:
                print("Operacao cancelada.")
                return 0
            argumentos.extend(["--somente-comparar", http])
        print("\nResultados na pasta resultados_http, ao lado do programa.")
        print("Use o mesmo config.txt nas duas coletas e uma referencia recente.\n")
        codigo = main(argumentos)
    except KeyboardInterrupt:
        print("\nOperacao interrompida.")
        codigo = 1
    except Exception:
        traceback.print_exc()
        codigo = 1
    finally:
        try:
            input("\nPressione Enter para fechar...")
        except (EOFError, KeyboardInterrupt):
            pass
    return codigo


if __name__ == "__main__":
    raise SystemExit(iniciar())
