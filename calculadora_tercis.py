import pandas as pd
import numpy as np
import unicodedata
import os
import re

def normalizar_nome(texto):
    """Padroniza os nomes e colunas ignorando acentos, maiúsculas e espaços extras."""
    if pd.isna(texto) or not str(texto).strip(): 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return " ".join(texto.split())

def extrair_nome_sem_cpf(texto):
    """
    Remove o padrão de CPF/CNPJ no início da string, com ou sem traço.
    Exemplo: '123.456.789-00 - JOAO' ou '12345678900 JOAO' viram apenas 'JOAO'
    """
    if pd.isna(texto): 
        return ""
    texto = str(texto).strip()
    # Remove blocos de números/pontos no começo, engolindo o hífen separador se houver
    texto_limpo = re.sub(r'^[\d\.\-\*]+\s*(?:-|–)?\s*', '', texto)
    return texto_limpo.strip()

def obter_coluna(df, nomes_alvo):
    """Busca dinamicamente a coluna no dataframe. Aceita uma lista de nomes possíveis."""
    if isinstance(nomes_alvo, str):
        nomes_alvo = [nomes_alvo]
        
    for alvo in nomes_alvo:
        alvo_norm = normalizar_nome(alvo)
        for col in df.columns:
            if normalizar_nome(str(col)) == alvo_norm:
                return col
    raise KeyError(f"[ERRO FATAL] Nenhuma das colunas {nomes_alvo} foi encontrada na planilha.")

def formatar_reais(valor):
    """Formata um float para o padrão de moeda brasileiro."""
    if pd.isna(valor): return "0,00"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def limpar_coluna_financeira(serie):
    """Limpeza BLINDADA para finanças brasileiras: garante que vire número de verdade."""
    # Se o Pandas já leu como número, ótimo, só preenche os vazios
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0.0)
    
    # Se for texto, força conversão para string, tira pontos e ajusta a vírgula
    serie_str = serie.astype(str).str.strip()
    serie_str = serie_str.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    
    # 'coerce' força qualquer erro (texto não numérico) a virar NaN, depois botamos 0.0
    return pd.to_numeric(serie_str, errors='coerce').fillna(0.0)

def gerar_dataframe_empenhos(caminho_empenhos):
    """
    Lê o arquivo de empenhos, limpa o CPF, calcula os tercis e retorna o DataFrame agrupado.
    """
    try:
        if caminho_empenhos.endswith(('.xlsx', '.xls')):
            df_empenhos = pd.read_excel(caminho_empenhos)
        else:
            df_empenhos = pd.read_csv(caminho_empenhos, sep=';', encoding='latin1', on_bad_lines='skip')
    except Exception as e:
        raise Exception(f"Falha ao ler o arquivo de empenhos: {e}")

    col_assinatura = obter_coluna(df_empenhos, 'Unidade Gestora / Assinatura Empenho')
    col_valor = obter_coluna(df_empenhos, 'Valor Empenhado')

    # 1. Extrair nome (remover CPF) e normalizar
    df_empenhos['Nome_Sem_CPF'] = df_empenhos[col_assinatura].apply(extrair_nome_sem_cpf)
    df_empenhos['Assinatura_Norm'] = df_empenhos['Nome_Sem_CPF'].apply(normalizar_nome)
    
    # 2. Aplicar a limpeza blindada de valores
    df_empenhos['Valor_Real'] = limpar_coluna_financeira(df_empenhos[col_valor])

    # 3. Agrupamento e Soma
    df_agrupado = df_empenhos.groupby('Assinatura_Norm').agg(
        Nome_Original=('Nome_Sem_CPF', 'first'),
        Valor_Total_Empenhado=('Valor_Real', 'sum'),
        Qtd_Empenhos=('Assinatura_Norm', 'count')
    ).reset_index()
    
    # Agora a comparação > 0.0 funcionará perfeitamente
    df_calc = df_agrupado[df_agrupado['Valor_Total_Empenhado'] > 0.0].copy()

    if df_calc.empty:
        raise Exception("Nenhum 'Valor Empenhado' maior que zero foi encontrado. Verifique a planilha.")

    tercil_1 = df_calc['Valor_Total_Empenhado'].quantile(0.333333)
    tercil_2 = df_calc['Valor_Total_Empenhado'].quantile(0.666666)
    txt_t1, txt_t2 = formatar_reais(tercil_1), formatar_reais(tercil_2)

    labels_tercis = [
        f"2 - Ordena na faixa do 1º Tercil (R$ 0,01 a R$ {txt_t1})",
        f"3 - Ordena na faixa do 2º Tercil (R$ {txt_t1} a R$ {txt_t2})",
        f"4 - Ordena na faixa do 3º Tercil (Acima de R$ {txt_t2})"
    ]

    df_calc['Classificacao'] = pd.cut(
        df_calc['Valor_Total_Empenhado'],
        bins=[-np.inf, tercil_1, tercil_2, np.inf],
        labels=labels_tercis
    )

    df_agrupado = pd.merge(df_agrupado, df_calc[['Assinatura_Norm', 'Classificacao']], on='Assinatura_Norm', how='left')
    
    if isinstance(df_agrupado['Classificacao'].dtype, pd.CategoricalDtype):
        df_agrupado['Classificacao'] = df_agrupado['Classificacao'].cat.add_categories(["1 - Não ordena despesa"])
    df_agrupado['Classificacao'] = df_agrupado['Classificacao'].fillna("1 - Não ordena despesa")

    df_agrupado['Texto_Final_Tercis'] = df_agrupado['Classificacao'].astype(str) + " | " + df_agrupado['Qtd_Empenhos'].astype(str) + " empenho(s)"

    return df_agrupado


def cruzar_sici_com_tercis(caminho_sici, caminho_empenhos, caminho_saida):
    """
    1. Gera planilha intermediária.
    2. Lê o SICI e identifica a coluna (aceita 'titular' ou 'titula').
    3. Faz o LEFT JOIN e salva.
    """
    df_empenhos_agrupados = gerar_dataframe_empenhos(caminho_empenhos)
    nome_intermediario = "Relatorio_Intermediario_Tercis.xlsx"
    df_empenhos_agrupados[['Nome_Original', 'Valor_Total_Empenhado', 'Qtd_Empenhos', 'Texto_Final_Tercis']].to_excel(nome_intermediario, index=False)
    
    df_sici = pd.read_excel(caminho_sici)
    
    # Busca a coluna tanto se ela for "Titular" quanto "Titula" (Prevenção de erros)
    col_titular_sici = obter_coluna(df_sici, ['titular', 'titula'])
    
    df_sici['chave_join_sici'] = df_sici[col_titular_sici].apply(normalizar_nome)

    # LEFT JOIN
    df_final = pd.merge(
        df_sici, 
        df_empenhos_agrupados[['Assinatura_Norm', 'Valor_Total_Empenhado', 'Texto_Final_Tercis']], 
        left_on='chave_join_sici', 
        right_on='Assinatura_Norm', 
        how='left'
    )

    df_final.drop(columns=['chave_join_sici', 'Assinatura_Norm'], inplace=True)
    df_final['Valor_Total_Empenhado'] = df_final['Valor_Total_Empenhado'].fillna(0.0)
    df_final['Texto_Final_Tercis'] = df_final['Texto_Final_Tercis'].fillna("1 - Não ordena despesa | 0 empenho(s)")

    df_final.to_excel(caminho_saida, index=False)
    return True, nome_intermediario