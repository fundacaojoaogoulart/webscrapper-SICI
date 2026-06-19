# 🤖 Automação SICI - Prefeitura do Rio

Este projeto é um conjunto de ferramentas de Web Scraping e Processamento de Dados desenvolvido para automatizar a extração de dados do SICI, atualizar a planilha do MFE (Mapeamento de Funções Estratégicas) com os dados extraídos e validar a prevalencia de lideranças (Líderes Cariocas e Lideranças Femininas) em cargos, além de fornecer planilhas de auditoria sobre os dados adicionados e excuiídos da planilha do MFE.



---

## 🏗️ Visão Geral e Orquestração

O coração do projeto é o script **`painel_principal_com_nomes.py`**. Ele atua como o **Orquestrador Central** da aplicação, fornecendo uma Interface Gráfica (GUI) amigável (via Tkinter) para que o usuário interaja com os módulos subjacentes sem precisar executar linhas de código no terminal. 

O painel centraliza o acesso a três rotinas principais:
1. **Raspagem Web (`scraper_sici_nome.py`):** Navegação automatizada no site do SICI para extrair a árvore de cargos atualizada.
2. **Atualização do MFE (`atualizador_MFE.py`):** Injeção estrutural de adições, exclusões e regras de negócio na planilha do Mapeamento de Funções Estratégicas.
3. **Validação de Líderes (`match_lideres.py`):** Cruzamento de bases para identificar quais integrantes da Rede de Líderes Cariocas estão ocupando cargos comissionados.

---

## Como gerar um novo executável

Utilize o comando abaixo para gerar uma nova versão do webscraper do sici
```bash
pyinstaller --clean --onefile --windowed --collect-all selenium --icon=icon.ico painel_principal_com_nomes.py
```


## 🔄 Fluxo de Trabalho (Workflow)

O fluxo ideal de ponta a ponta projetado pela automação funciona da seguinte maneira:

1. O usuário abre o Painel Principal e clica em **Iniciar Raspagem Web**.
2. O robô (Selenium) abre o navegador, entra no SICI e começa a varrer todos os órgãos, ignorando os locais definidos no arquivo de filtro (`config.txt`), e salva uma planilha bruta extraída.
3. Ao término da raspagem, o sistema identifica que novos dados foram gerados e **pergunta proativamente** ao usuário se ele deseja seguir para as próximas etapas (MFE e/ou Líderes).
4. Se o usuário aceitar, os scripts de cruzamento são acionados em sequência, alimentando-se automaticamente da planilha recém-gerada, aplicando regras de negócio complexas, atualizando as planilhas finais e gerando relatórios de auditoria.

---

## 🎛️ Funcionalidades do Painel (Botões)

- **1. Iniciar Raspagem Web (SICI):** Executa o fluxo completo. Abre o navegador, realiza o web scraping no SICI, gera o arquivo Excel bruto com nomes dos titulares e encadeia (via pop-ups) as atualizações subsequentes.
- **2. Somente Atualizar MFE:** Rotina offline. Permite ao usuário pular a etapa do navegador e usar uma planilha do SICI já extraída anteriormente no seu computador para atualizar a planilha do MFE.
- **3. Somente Contabilizar Líderes Cariocas (Minibios):** Rotina offline. Cruza uma base do SICI já existente com uma planilha com nomes (exemplo: Minibios) para checar o *status* de comissionamento das lideranças.
- **4. Editar Filtro de Palavras Ignoradas:** Abre o bloco de notas de configuração (`config.txt`) permitindo adicionar ou remover siglas/palavras que o robô deve ignorar na hora de varrer o SICI.

---

## ⚠️ Requisitos e Padrões de Planilhas

Para que o cruzamento de dados via *Pandas* e a injeção via *Openpyxl* funcionem perfeitamente, as planilhas de entrada e saída possuem restrições rígidas.

### 1. Planilha MFE (Mapeamento de Funções Estratégicas)
A planilha MFE é o documento mais sensível do processo. O script edita diretamente a aba **"Todas as Funções (Editável)"**.
- **PROIBIDO ALTERAR A ORDEM DAS COLUNAS:** O script realiza injeções via mapeamento físico por índices. A estrutura *deve* respeitar a seguinte ordem para os cálculos automatizados:
  - **Coluna B (2):** Órgão
  - **Coluna C (3):** Escalão
  - **Coluna D (4):** Área
  - **Coluna E (5):** Nome do Cargo
  - **Coluna F (6):** Tipo de Cargo *(Alimentada via dicionário interno)*
  - **Coluna H (8):** Macro Área *(Alimentada via dicionário interno)*
  - **Coluna J (10):** Autonomia para ordenar despesa
  - **Coluna L (12):** Poder de Decisão sobre o Orçamento
  - **Coluna M (13):** Titular*

### 2. Planilha de Ordenadores de Despesa (CSV ou Excel)
Quando requisitada, esta planilha é usada para verificar o poder orçamentário.
- Deve possuir uma coluna chamada **"Usuário"**. Se não existir, o script tentará usar a terceira coluna (Índice C) ou a primeira coluna (Índice A) como plano de contingência.

### 3. Planilha com nomes para cruzamento SICI x LC ou PRLF
- Deve, obrigatoriamente, possuir uma coluna com o cabeçalho exato **`NOME`** na primeira aba. A falta dessa coluna aborta a operação.

---

## ⚙️ Arquivos de Configuração (.txt)

O sistema possui inteligência externa gerida por arquivos de texto, permitindo configurações sem necessidade de alterar o código-fonte (Python). **Se os arquivos não existirem na pasta, o script os cria automaticamente com os padrões de fábrica na primeira execução.**

- **`config.txt`:** Lista de palavras e siglas genéricas (ex: *escola, hospital, vila olímpica*). Qualquer ramo no SICI que contenha uma dessas palavras será ignorado pela raspagem para otimizar o tempo e focar nos cargos administrativos/liderança.
- **`excecoes_poder_decisorio.txt`:** Define regras rígidas para a Coluna L do MFE. Possui a tag `[CARGO_EXATO]` (onde o nome do cargo deve bater perfeitamente, ex: *Subsecretário*) e a tag `[AREA_CONTEM]` (onde basta que o termo esteja dentro do nome da área, ex: *Coordenadoria Regional de Educação*). Cargos enquadrados nestas regras recebem nota máxima em Poder de Decisão, independente de serem ordenadores ou não.

---

## 📤 Saídas e Resultados Gerados

A automação não sobrescreve os dados de maneira opaca. Toda execução gera rastreabilidade:

1. **`sici_extracao_completa_YYYYMMDD_HHMM.xlsx`:** O "banco de dados" puro e bruto raspado do portal SICI, servindo como fonte de verdade para o dia da execução.
2. **Atualização Direta no MFE:** A planilha MFE selecionada é salva com as linhas reordenadas, novas injeções nas colunas mencionadas e exclusões de cargos extintos.
3. **`alterados_MFE_YYYYMMDD_HHMM.xlsx`:** Uma planilha de **Auditoria**. Contém duas abas separadas ("Exclusões" e "Adições"), listando exatamente os cargos que o robô inseriu ou apagou do MFE, para que a equipe valide as alterações estruturais na prefeitura.
4. **`planilha_cruzamento.xlsx`:** Arquivo final resultante do script de líderes, adicionando as colunas `status`, `área` e `cargo` aos dados originais do Minibios.