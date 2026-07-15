import os
import sys
import re
import unicodedata

if getattr(sys, 'frozen', False):
    app_path = os.path.dirname(sys.executable)
else:
    app_path = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(app_path, "config.txt")

CONFIG_DEFAULT = """# =========================================================================
# CONFIGURAÇÕES GERAIS DO ROBÔ SICI E ATUALIZADOR MFE
# =========================================================================
#
# COMO EDITAR ESTE ARQUIVO:
# 1. As linhas que começam com '#' são apenas comentários de ajuda.
# 2. Respeite os cabeçalhos entre colchetes, como [PALAVRAS_IGNORADAS]. Não os apague.
# 3. Logo abaixo de cada cabeçalho, adicione as regras correspondentes.
# 4. Salve o arquivo após fazer qualquer edição e reinicie o programa.
#
# =========================================================================

[PALAVRAS_IGNORADAS]
# Adicione abaixo as palavras ou siglas que o robô deve ignorar na raspagem SICI.
# Coloque apenas uma palavra por linha. Maiúsculas/minúsculas não importam.
escola 
ciep
creche
centro de educação de jovens e adultos
edi 
c.m.
e.m.
espaço de desenvolvimento infantil
biblioteca escolar
centro de desenvolvimento de educação integrada
hospital
gerência do parque
centro de referência de assistência social
centro de referência da assistência social
centro de referência especializado de assistência social
centro de referência especializado da assistência social
centro municipal de referência
fundo municipal
unidade municipal de reinserção
central de recepção
centro de cidadania
conselho
comitê
fundo
comissão
vila olímpica
casa viva
centro esportivo
junta especial
juntas
museu histórico

[CARGO_EXATO]
# Define regras extras para a coluna de Poder de Decisão (Coluna L) baseadas no cargo EXATO (Coluna E).
# Coloque um cargo por linha.
Chefe de Gabinete
Procurador Geral do Município
Subprocurador Geral do Município
Controlador Geral
Secretário Especial
Secretário Municipal
Subsecretário
Inspetor Geral
Presidente de Autarquia
Subcontrolador

[AREA_CONTEM]
# Define regras extras para a coluna de Poder de Decisão (Coluna L) se o nome da ÁREA CONTIVER o texto abaixo.
# Coloque um texto por linha.
Coordenadoria Regional de Educação

[TIPOS_CARGO]
# Dicionário de Tipos de Cargo: "Nome do Cargo (Coluna E) = Tipo de Cargo (Coluna F)"
Assessor Chefe = Assessor(a)
Assessor Chefe Especial = Assessor(a)
Assessor Chefe Especial I = Assessor(a)
Assessor Chefe I = Assessor(a)
Assessor Chefe Técnico = Assessor(a)
Assessor Chefe Técnico Especial = Assessor(a)
Consultor Jurídico = Assessor(a)
Chefe da Casa Militar = Chefe
Chefe de Gabinete = Chefe
Chefe Executivo = Chefe
Chefe Executivo de Resiliência e Operações = Chefe
Auditor Chefe = Coordenador(a)
Auditor Geral = Coordenador(a)
Contador Geral = Coordenador(a)
Coordenador Especial = Coordenador(a)
Coordenador Especial "Subprefeito" = Coordenador(a)
Coordenador Especial do Gabinete do Prefeito = Coordenador(a)
Coordenador Geral = Coordenador(a)
Coordenador I = Coordenador(a)
Coordenador II = Coordenador(a)
Coordenador Técnico = Coordenador(a)
Corregedor = Coordenador(a)
Inspetor Corregedor = Coordenador(a)
Secretário Executivo III = Coordenador(a)
Subdiretor Técnico = Coordenador(a)
Diretor de Diretoria de Autarquia = Diretor(a)
Diretor Executivo = Diretor(a)
Diretor Executivo II = Diretor(a)
Diretor I = Diretor(a)
Diretor II = Diretor(a)
Diretor III = Diretor(a)
Diretor IV = Diretor(a)
Procurador Chefe = Diretor(a)
Procurador Corregedor = Diretor(a)
Gerente de Processo III = Gerente
Gerente I = Gerente
Gerente II = Gerente
Gerente III = Gerente
Gerente IV = Gerente
Ouvidor = Ouvidor(a)
Ouvidor de Núcleo I = Ouvidor(a)
Ouvidor de Núcleo II = Ouvidor(a)
Presidente = Presidente
Presidente de Autarquia = Presidente
Presidente II = Presidente
Controlador Geral = Secretário(a)
Inspetor Geral = Secretário(a)
Procurador Geral do Município = Secretário(a)
Secretário Especial = Secretário(a)
Secretário Municipal = Secretário(a)
Auditor Chefe da Receita Municipal = Subsecretário(a)
Subcontrolador = Subsecretário(a)
Subprocurador Geral do Município = Subsecretário(a)
Subsecretário = Subsecretário(a)
Vice-Presidente = Subsecretário(a)
Superintendente = Superintendente
Superintendente Executivo = Superintendente
Superintendente Técnico = Superintendente

[MACRO_AREAS]
# Dicionário de Macro Áreas: "Órgão = Macro Área (COLUNA H)"
casacivil = Gestão
cgm = Gestão
cgmrio = Gestão
gbp = Gestão
gmrio = Planejamento Urbano e Econômico
gvp = Gestão
ipp = Gestão
juvrio = Social
pgm = Gestão
previrio = Gestão
seacrio = Social
secid = Social
seconserva = Infraestrutura e Logística Urbana
sedecon = Social
sedhir = Social
segur = Planejamento Urbano e Econômico
seim = Planejamento Urbano e Econômico
semesqv = Social
seop = Planejamento Urbano e Econômico
sesrio = Social
sincrio = Social
sma = Gestão
smac = Planejamento Urbano e Econômico
smas = Social
smc = Social
smcg = Gestão
smct = Planejamento Urbano e Econômico
smde = Planejamento Urbano e Econômico
smdu = Planejamento Urbano e Econômico
sme = Social
smel = Social
smg = Gestão
smh = Social
smi = Infraestrutura e Logística Urbana
smit = Gestão
smpd = Social
smpda = Social
sms = Social
smte = Social
smtr = Planejamento Urbano e Econômico
smturrio = Planejamento Urbano e Econômico
spmrio = Social
smf = Gestão
"""

def garantir_config_existe():
    """Garante que o arquivo config.txt exista, criando-o com os padrões se necessário."""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(CONFIG_DEFAULT)

def normalizar(texto):
    import pandas as pd
    if pd.isna(texto) or not str(texto).strip(): 
        return ""
    texto = str(texto).lower()
    texto = "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^a-z0-9]', '', texto)
    return texto.strip()

def ler_config():
    """Lê o config.txt e retorna os dicionários e listas organizados."""
    garantir_config_existe()
    
    config_data = {
        'PALAVRAS_IGNORADAS': [],
        'CARGO_EXATO': set(),
        'AREA_CONTEM': [],
        'TIPOS_CARGO': {},
        'MACRO_AREAS': {}
    }
    
    secao_atual = None
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        for linha in f:
            linha = linha.strip()
            
            if not linha or linha.startswith("#"):
                continue
                
            if linha.startswith("[") and linha.endswith("]"):
                secao_atual = linha[1:-1]
                continue
                
            if secao_atual == 'PALAVRAS_IGNORADAS':
                config_data['PALAVRAS_IGNORADAS'].append(linha.lower())
                
            elif secao_atual == 'CARGO_EXATO':
                config_data['CARGO_EXATO'].add(normalizar(linha))
                
            elif secao_atual == 'AREA_CONTEM':
                config_data['AREA_CONTEM'].append(normalizar(linha))
                
            elif secao_atual == 'TIPOS_CARGO':
                if "=" in linha:
                    cargo, tipo = linha.split("=", 1)
                    config_data['TIPOS_CARGO'][normalizar(cargo)] = tipo.strip()
                    
            elif secao_atual == 'MACRO_AREAS':
                if "=" in linha:
                    orgao, macroarea = linha.split("=", 1)
                    config_data['MACRO_AREAS'][normalizar(orgao)] = macroarea.strip()
                    
    return config_data
