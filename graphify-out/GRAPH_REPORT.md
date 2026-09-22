# Graph Report - webscrapper-SICI  (2026-09-22)

## Corpus Check
- Corpus is ~18,961 words - fits in a single context window. You may not need a graph.

## Summary
- 152 nodes · 244 edges · 11 communities
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 14 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- MFE Classification Pipeline
- Project Architecture and Dependencies
- Leadership Matching Workflow
- Budget Tercile Calculation
- Configuration and Packaging
- Team Management Matching
- SICI Web Scraping
- Budget Relevance Criteria
- Configuration File Management
- Application Visual Identity
- Team Management Source Data

## God Nodes (most connected - your core abstractions)
1. `iniciar_raspagem()` - 13 edges
2. `atualizar_planilha_mfe()` - 9 edges
3. `gerar_dataframe_empenhos()` - 9 edges
4. `Dependências Python Fixadas` - 9 edges
5. `Inteligência Externa por Arquivos de Configuração` - 8 edges
6. `cruzar_planilhas()` - 7 edges
7. `ler_config()` - 6 edges
8. `Configurações Gerais do Robô SICI e Atualizador MFE` - 6 edges
9. `painel_principal.py — Orquestrador Central` - 6 edges
10. `atualizador_MFE.py — Atualização do MFE` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Configuração e Planilhas Externamente Editáveis` --semantically_similar_to--> `Inteligência Externa por Arquivos de Configuração`  [INFERRED] [semantically similar]
  gerar exe.txt → readme.md
- `Planilha Extraída do SICI` --semantically_similar_to--> `sici_extracao_completa_YYYYMMDD_HHMM.xlsx`  [INFERRED] [semantically similar]
  Rascunhos acerca da automatizacao.md → readme.md
- `Magnitude do Orçamento em Três Níveis` --semantically_similar_to--> `calculadora_tercis.py — Cálculo do Poder Orçamentário`  [INFERRED] [semantically similar]
  Rascunhos acerca da automatizacao.md → readme.md
- `executar_somente_mfe()` --calls--> `selecionar_arquivo_sici_interface()`  [EXTRACTED]
  painel_principal.py → atualizador_MFE.py
- `atualizar_planilha_mfe()` --calls--> `gerar_dataframe_empenhos()`  [EXTRACTED]
  atualizador_MFE.py → calculadora_tercis.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Fontes e Regras do Critério Orçamentário** — rascunhos_acerca_da_automatizacao_siafic, rascunhos_acerca_da_automatizacao_supor, rascunhos_acerca_da_automatizacao_funcoes_rgcaf, rascunhos_acerca_da_automatizacao_ordenadores_despesa, rascunhos_acerca_da_automatizacao_relevancia_orcamentaria [EXTRACTED 1.00]
- **Sistema de Regras Configuráveis do MFE** — config_cargo_exato, config_area_contem, config_tipos_cargo, config_macro_areas [EXTRACTED 1.00]
- **Pipeline Central da Automação SICI** — readme_painel_principal, readme_scraper_sici_nome, readme_atualizador_mfe, readme_match_lideres [EXTRACTED 1.00]
- **Webscraper SICI Visual Identity** — webscraper_icon_nobg_robot, webscraper_icon_nobg_wrench, webscraper_icon_nobg_crest, webscraper_icon_nobg_blue_badge [EXTRACTED 1.00]

## Communities (11 total, 0 thin omitted)

### Community 0 - "MFE Classification Pipeline"
Cohesion: 0.10
Nodes (30): _carregar_modelos(), clean_text(), obter_caminho(), prever_area_negocio(), Retorna o caminho absoluto do arquivo. Funciona tanto rodando o .py normal…, Garante que os arquivos .pkl sejam carregados na memória de forma otimizada., Limpa a string de área padronizando para o modelo., Função principal: Recebe uma lista de strings e retorna a Área de Negócio… (+22 more)

### Community 1 - "Project Architecture and Dependencies"
Cohesion: 0.09
Nodes (28): Empacotamento PyInstaller em Modo onedir, Ordenadores de Despesa, Planilha Extraída do SICI, Sistema Único e Integrado de Execução Orçamentária, Administração Financeira e Controle (SIAFIC), area_negocio_ml.py — Classificação de Área de Negócio, atualizador_MFE.py — Atualização do MFE, Automação SICI da Prefeitura do Rio, planilha_cruzamento_PLC/PRLF.xlsx (+20 more)

### Community 2 - "Leadership Matching Workflow"
Cohesion: 0.18
Nodes (17): cruzar_planilhas(), inicializar_tkinter(), normalizar_nome(), Deixa em minúsculo, remove acentos e espaços extras, selecionar_arquivo_sici(), selecionar_planilha_minibios(), desabilitar_botoes(), executar_raspagem_completa() (+9 more)

### Community 3 - "Budget Tercile Calculation"
Cohesion: 0.22
Nodes (14): cruzar_sici_com_tercis(), extrair_nome_sem_cpf(), formatar_reais(), gerar_dataframe_empenhos(), limpar_coluna_financeira(), normalizar_nome(), obter_coluna(), 1. Gera planilha intermediária. 2. Lê o SICI e identifica a coluna (aceita… (+6 more)

### Community 4 - "Configuration and Packaging"
Cohesion: 0.27
Nodes (11): Regras de Área Contendo Texto, Regras de Cargo Exato, Configurações Gerais do Robô SICI e Atualizador MFE, Dicionário de Macro Áreas, Regras de Palavras Ignoradas, Dicionário de Tipos de Cargo, Configuração e Planilhas Externamente Editáveis, Modelos de Machine Learning e Ícone Encapsulados (+3 more)

### Community 5 - "Team Management Matching"
Cohesion: 0.33
Nodes (9): cruzar_planilhas(), iniciar_painel(), acao_gerenciador(), acao_ordenador(), normalizar_nome(), Deixa em minúsculo, remove acentos e espaços extras, selecionar_arquivo_sici(), selecionar_planilha() (+1 more)

### Community 6 - "SICI Web Scraping"
Cohesion: 0.27
Nodes (7): exibir_alerta(), iniciar_raspagem(), clicar_por_id(), esperar_ajax(), expandir_por_id(), recolher_por_id(), 🔥 Toda a lógica principal foi embalada nesta função. O painel_principal.py…

### Community 7 - "Budget Relevance Criteria"
Cohesion: 0.22
Nodes (9): Automatização dos Critérios Gerenciais e de Relevância Orçamentária, Funções Regulamentadas pelo RGCAF, Magnitude do Orçamento em Três Níveis, Poder Decisório sobre Alocação Orçamentária, Relatório do MFE, Critério de Relevância Orçamentária, SUPOR, calculadora_tercis.py — Cálculo do Poder Orçamentário (+1 more)

### Community 8 - "Configuration File Management"
Cohesion: 0.29
Nodes (7): garantir_config_existe(), ler_config(), normalizar(), Garante que o arquivo config.txt exista, criando-o com os padrões se necessário., Lê o config.txt e retorna os dicionários e listas organizados., abrir_config_palavras(), Abre o arquivo config.txt

### Community 9 - "Application Visual Identity"
Cohesion: 0.47
Nodes (6): Automated Technical Service, Circular Blue Badge Design, Institutional Crest, Webscraper SICI Application Icon, Friendly Service Robot, Maintenance Wrench

### Community 10 - "Team Management Source Data"
Cohesion: 0.67
Nodes (3): Coordenadoria Geral de Gestão Institucional (CGGI), Coluna de Função Extraída do SICI, Status de Gestão de Equipes

## Ambiguous Edges - Review These
- `Institutional Crest` → `Automated Technical Service`  [AMBIGUOUS]
  webscraper icon-nobg.png · relation: conceptually_related_to

## Knowledge Gaps
- **14 isolated node(s):** `Coordenadoria Geral de Gestão Institucional (CGGI)`, `Coluna de Função Extraída do SICI`, `Sistema Único e Integrado de Execução Orçamentária, Administração Financeira e Controle (SIAFIC)`, `SUPOR`, `Relatório do MFE` (+9 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 50 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Institutional Crest` and `Automated Technical Service`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `iniciar_raspagem()` connect `SICI Web Scraping` to `MFE Classification Pipeline`, `Configuration File Management`, `Leadership Matching Workflow`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `atualizar_planilha_mfe()` connect `MFE Classification Pipeline` to `Configuration File Management`, `Budget Tercile Calculation`, `SICI Web Scraping`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `painel_principal.py — Orquestrador Central` connect `Project Architecture and Dependencies` to `Configuration and Packaging`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `gerar_dataframe_empenhos()` (e.g. with `extrair_nome_sem_cpf()` and `normalizar_nome()`) actually correct?**
  _`gerar_dataframe_empenhos()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Coordenadoria Geral de Gestão Institucional (CGGI)`, `Coluna de Função Extraída do SICI`, `Sistema Único e Integrado de Execução Orçamentária, Administração Financeira e Controle (SIAFIC)` to the rest of the system?**
  _14 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `MFE Classification Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.0962566844919786 - nodes in this community are weakly interconnected._