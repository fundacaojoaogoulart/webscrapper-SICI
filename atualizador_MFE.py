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

# ---------------- CONFIGURAÇÕES ----------------
NOME_ABA = "Todas as Funções (Editável)"
COR_ALERTA = "FFFF00" # Amarelo para revisão manual

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
    """Lê as exceções de Coluna L a partir de um txt. Se não existir, cria com o padrão."""
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

    # --- 3. AGRUPAMENTO SICI (Identificar Cargos Mistos) ---
    sici_keys = {}
    lixos = {'vago', 'vaga', 'nao informado', 'sem titular', '-'}
    
    for _, rs in df_sici.iterrows():
        org = normalizar(str(rs.get('órgão', '')))
        esc = normalizar(str(rs.get('escalão', '')))
        area = normalizar(str(rs.get('área', '')))
        cargo = normalizar(str(rs.get('cargo', '')))
        titular = normalizar_nome(str(rs.get('titular', '')))
        
        chave_si = f"{org}|{esc}|{area}|{cargo}"
        
        if chave_si not in sici_keys:
            sici_keys[chave_si] = {
                "orgao": str(rs.get('órgão', '')),
                "escalao": str(rs.get('escalão', '')),
                "area": str(rs.get('área', '')),
                "cargo": str(rs.get('cargo', '')),
                "titulares": set() 
            }
            
        if titular and len(titular) > 2 and titular not in lixos:
            sici_keys[chave_si]["titulares"].add(titular)

    # --- 4. AVALIAÇÃO DE ORDENADORES, PODER DE DECISÃO E CORES ---
    qtd_alertas = 0
    texto_poder_sim = "2 - Possui poder de decisão sobre alocação de recursos orçamentários no órgão"
    texto_poder_nao = "1 - Não possui poder de decisão sobre alocação de recursos orçamentários no órgão"

    for chave_si, dados_si in sici_keys.items():
        titulares_do_cargo = dados_si["titulares"]
        total_pessoas = len(titulares_do_cargo)
        total_ordenadores = 0
        
        if verificar_ordenadores:
            total_ordenadores = sum(1 for t in titulares_do_cargo if t in set_ordenadores)
            
        # Regras de preenchimento e cor (Coluna 10 / J)
        cor_fundo = None
        if not verificar_ordenadores or total_pessoas == 0 or total_ordenadores == 0:
            texto_ordenador = "1 - Não"
        elif total_ordenadores == total_pessoas:
            texto_ordenador = "2 - Sim"
        else:
            texto_ordenador = "⚠️ REVISÃO MANUAL: Cargo possui titulares com e sem poder de ordenação"
            cor_fundo = COR_ALERTA
            qtd_alertas += 1
            
        # Regras de preenchimento do Poder de Decisão (Coluna 12 / L)
        cargo_norm = normalizar(dados_si['cargo'])
        area_norm = normalizar(dados_si['area'])
        
        is_excecao_poder = False
        if cargo_norm in cargos_excecao:
            is_excecao_poder = True
        else:
            for area_excecao in areas_excecao_contem:
                if area_excecao in area_norm: # Verifica se a string exigida está contida na Área
                    is_excecao_poder = True
                    break

        if texto_ordenador == "2 - Sim" or is_excecao_poder:
            texto_poder_decisao = texto_poder_sim
        elif texto_ordenador.startswith("⚠️"):
            # Se for misto, repassa o alerta também para a L, mas se for exceção, a exceção salva e recebe 2!
            texto_poder_decisao = "⚠️ REVISÃO MANUAL: Avalie o poder de decisão deste cargo (titulares mistos)"
        else:
            texto_poder_decisao = texto_poder_nao

        dados_si['texto_ordenador'] = texto_ordenador
        dados_si['texto_poder_decisao'] = texto_poder_decisao
        dados_si['cor_fundo'] = cor_fundo

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
            
        chave_ex = f"{normalizar(orgao_ex)}|{normalizar(escalao_ex)}|{normalizar(area_ex)}|{normalizar(cargo_ex)}"
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
            dados_removidos.append({
                "orgao": str(df_mfe.iloc[linha_real, 1]),
                "escalao": str(df_mfe.iloc[linha_real, 2]),
                "area": str(df_mfe.iloc[linha_real, 3]),
                "cargo": str(df_mfe.iloc[linha_real, 4])
            })

    for chave_si, dados_si in sici_keys.items():
        if chave_si not in mfe_keys:
            nova_linha = [""] * 12
            nova_linha[1] = dados_si['orgao']  
            nova_linha[2] = dados_si['escalao'] 
            nova_linha[3] = dados_si['area']    
            nova_linha[4] = dados_si['cargo']   
            nova_linha[9] = dados_si['texto_ordenador']   # Coluna J
            nova_linha[11] = dados_si['texto_poder_decisao'] # Coluna L
            
            novos_registros.append({"dados": nova_linha, "cor": dados_si['cor_fundo']})
            dados_adicionados.append(dados_si)
        else:
            linhas_para_atualizar.append({
                'linha': mfe_keys[chave_si]['linha'],
                'texto_ordenador': dados_si['texto_ordenador'],
                'texto_poder_decisao': dados_si['texto_poder_decisao'],
                'cor': dados_si['cor_fundo']
            })

    # --- 6. ATUALIZAÇÃO FÍSICA NO EXCEL ---
    print(f"\n[*] Aplicando alterações no arquivo '{arquivo_mfe}'...")
    try:
        wb = openpyxl.load_workbook(arquivo_mfe)
        ws = wb[NOME_ABA]
        
        # 1. ATUALIZAÇÕES e PINTURA
        if linhas_para_atualizar and verificar_ordenadores:
            for item in linhas_para_atualizar:
                cel_j = ws.cell(row=item['linha'], column=10, value=item['texto_ordenador'])
                cel_l = ws.cell(row=item['linha'], column=12, value=item['texto_poder_decisao'])
                
                if item['cor']:
                    cel_j.fill = PatternFill(start_color=item['cor'], end_color=item['cor'], fill_type="solid")
                    cel_l.fill = PatternFill(start_color=item['cor'], end_color=item['cor'], fill_type="solid")
                else:
                    cel_j.fill = PatternFill(fill_type=None) 
                    cel_l.fill = PatternFill(fill_type=None)

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
                for col_idx, valor in enumerate(registro["dados"], start=1):
                    if valor: 
                        cel_add = ws.cell(row=linha_alvo, column=col_idx, value=valor)
                        if (col_idx == 10 or col_idx == 12) and registro["cor"]:
                            cel_add.fill = PatternFill(start_color=registro["cor"], end_color=registro["cor"], fill_type="solid")
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
        if qtd_alertas > 0:
            mensagem_resumo += f"\n\n⚠️ {qtd_alertas} cargos apresentaram ordenação mista e foram marcados em AMARELO na planilha para sua revisão manual."
        else:
            mensagem_resumo += f"\n\n⚙️ As colunas J e L foram calibradas com base nas regras e no arquivo de exceções."

    messagebox.showinfo("Atualização Concluída", mensagem_resumo)

if __name__ == "__main__":
    root = inicializar_tkinter()
    arquivo_selecionado = selecionar_arquivo_sici_interface()
    
    if arquivo_selecionado:
        atualizar_planilha_mfe(arquivo_selecionado)