import pandas as pd
import numpy as np
import re
import joblib
import os
import sys 

# ---------------- CONFIGURAÇÕES ----------------
MODEL_FILE = 'model_fjg.pkl'
VECTORIZER_FILE = 'vectorizer_fjg.pkl'

STOPWORDS_RIO = [
    'coordenadoria', 'gerencia', 'assessoria', 'nucleo', 'escritorio',
    'diretoria', 'subsecretaria', 'secretaria', 'geral', 'especial',
    'tecnica', 'de', 'da', 'do', 'das', 'dos', 'e', 'para', 'com'
]

# Variáveis globais para armazenar os modelos em memória
_model = None
_vectorizer = None

def obter_caminho(nome_arquivo):
    """
    Retorna o caminho absoluto do arquivo. 
    Funciona tanto rodando o .py normal quanto rodando o .exe compilado.
    Procura tanto na pasta temporária (se embutido) quanto ao lado do .exe.
    """
    caminhos_tentativas = []
    
    if getattr(sys, 'frozen', False):
        # Se for um .exe gerado pelo PyInstaller
        # 1. Pasta temporária do PyInstaller (caso o arquivo tenha sido embutido no exe)
        if hasattr(sys, '_MEIPASS'):
            caminhos_tentativas.append(sys._MEIPASS)
        # 2. Pasta onde o arquivo .exe está localizado (caso o arquivo esteja solto ao lado)
        caminhos_tentativas.append(os.path.dirname(sys.executable))
    else:
        # Se estiver rodando o script .py direto no editor (VSCode)
        caminhos_tentativas.append(os.path.dirname(os.path.abspath(__file__)))
        caminhos_tentativas.append(os.path.abspath("."))

    # Retorna o primeiro caminho onde o arquivo de fato existe
    for base_path in caminhos_tentativas:
        caminho_completo = os.path.join(base_path, nome_arquivo)
        if os.path.exists(caminho_completo):
            return caminho_completo
            
    # Se não encontrar em nenhum lugar, retorna o caminho base padrão para estourar o erro previsto
    if caminhos_tentativas:
        return os.path.join(caminhos_tentativas[-1], nome_arquivo)
    return nome_arquivo

def _carregar_modelos():
    """Garante que os arquivos .pkl sejam carregados na memória de forma otimizada."""
    global _model, _vectorizer
    
    if _model is not None and _vectorizer is not None:
        return True
        
    # Usa a nossa nova função para descobrir onde os arquivos estão
    caminho_modelo = obter_caminho(MODEL_FILE)
    caminho_vetorizador = obter_caminho(VECTORIZER_FILE)
        
    if not os.path.exists(caminho_modelo) or not os.path.exists(caminho_vetorizador):
        print(f"[AVISO] Arquivos de Machine Learning não encontrados. A classificação da Área de Negócio será pulada.")
        return False
        
    try:
        # Carrega usando o caminho completo corrigido
        _model = joblib.load(caminho_modelo)
        _vectorizer = joblib.load(caminho_vetorizador)
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao carregar os modelos de Machine Learning: {e}")
        return False
def clean_text(text):
    """Limpa a string de área padronizando para o modelo."""
    if not isinstance(text, str): 
        return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    tokens = text.split()
    return " ".join([w for w in tokens if w not in STOPWORDS_RIO])

def prever_area_negocio(lista_areas):
    """
    Função principal: Recebe uma lista de strings e retorna a Área de Negócio prevista.
    Injeta um alerta de Revisão Manual caso a confiança do modelo seja baixa.
    """
    if not _carregar_modelos():
        return [""] * len(lista_areas)
        
    areas_limpas = [clean_text(area) for area in lista_areas]
    
    try:
        X_vect = _vectorizer.transform(areas_limpas)
        predicoes = _model.predict(X_vect)
        probs = _model.predict_proba(X_vect)
        
        # Isola a confiança (probabilidade máxima encontrada)
        confiancas = (np.max(probs, axis=1) * 100).round(2)
        
        resultados = []
        for pred, conf in zip(predicoes, confiancas):
            if conf < 75.0:
                resultados.append(f"⚠️ REVISÃO MANUAL ({conf}% de Confiança): {pred}")
            else:
                resultados.append(pred)
                
        return resultados
        
    except Exception as e:
        print(f"[ERRO] Falha durante a predição via Inteligência Artificial: {e}")
        return [""] * len(lista_areas)