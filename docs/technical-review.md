# Avaliação técnica

Avaliação objetiva da estrutura atual, separando **problemas comprovados**, **riscos potenciais** e **melhorias opcionais**. Cada problema traz evidência no código, impacto e possível solução.

## Sumário executivo

O sistema cumpre o objetivo com uma arquitetura simples e adequada ao porte: um orquestrador (painel), um scraper e um atualizador, com regras externalizadas em `config.txt`. Os principais riscos concentram-se em **integridade de dados** (sobrescrita de edições e ausência de auditoria diferencial), **recuperação de falhas** (coleta parcial reportada como sucesso) e **testabilidade** (sem testes).

---

## 1. Problemas comprovados (evidência direta no código)

### P1. Regeneração do MFE descarta edições manuais anteriores

- **Evidência:** `atualizador_MFE.py:302-332` faz `shutil.copy(arquivo_base, arquivo_saida)`, depois `ws.delete_rows(2, ws.max_row - 1)` e reescreve os registros. A saída é derivada de `MFE_Base.xlsx`, nunca da `MFE_Atualizada.xlsx` anterior.
- **Impacto:** qualquer revisão/preenchimento manual feito na saída anterior é perdido na próxima execução. Não há como reaproveitar trabalho humano.
- **Solução possível:** ler a `MFE_Atualizada.xlsx` anterior como base, aplicar um diff por chave composta e preservar colunas editadas manualmente; ou gerar um arquivo de auditoria das diferenças.

### P2. Coluna A ("ID automático") nunca é preenchida

- **Evidência:** `nova_linha = [""] * 13` e o preenchimento começa no índice 1 (`atualizador_MFE.py:285-298`). O cabeçalho da base declara "ID (automático)", mas não há fórmula nem valor.
- **Impacto:** o identificador de cada registro fica vazio no arquivo gerado, fragilizando rastreabilidade e referências cruzadas.
- **Solução possível:** preencher um ID sequencial/estável derivado da chave composta, ou restaurar a fórmula do Excel na base.

### P3. Cruzamento de lideranças pós-raspagem omite a tarefa e pode falhar

- **Evidência:** o scraper chama `match_lideres.cruzar_planilhas(df)` sem `tarefa` (`scraper_sici_nome.py:354`). Em `match_lideres.py`, `ARQUIVO_C` só é definido para `PLC`/`PRLF` (`:87-90`) e `status` só é criado nesses casos (`:128-139`); a seleção de colunas em `:148` exige `status`.
- **Impacto:** no fluxo integrado, a etapa "Etapa 3: Match de Líderes" pode lançar `KeyError` ou falhar ao salvar. Os botões offline funcionam porque passam a tarefa.
- **Solução possível:** passar a tarefa explicitamente no scraper (perguntando PLC/PRLF) ou tornar `cruzar_planilhas` resiliente à tarefa vazia.

### P4. Coleta interrompida ainda reporta sucesso e oferece próximos passos

- **Evidência:** o laço é envolvido em `try/except` que apenas exibe alerta de erro (`scraper_sici_nome.py:303-306`); o `finally` salva os resultados parciais e dispara as confirmações de MFE/Líderes (`:308-354`).
- **Impacto:** dados incompletos podem ser gravados e encaminhados como se a extração estivesse completa, sem indicador claro de parcialidade.
- **Solução possível:** registrar explicitamente que a extração foi parcial e bloquear as etapas seguintes sem confirmação adicional.

### P5. Ausência de verificação de ordenadores vira "1 - Não" silenciosamente

- **Evidência:** se o usuário responde "não" à verificação, `set_ordenadores` permanece vazio e a coluna J recebe `"1 - Não"` para todos (`atualizador_MFE.py:129-135,234-252`).
- **Impacto:** "não verificado" fica indistinguível de "não é ordenador", contaminando a coluna L (Poder de Decisão) para os cargos que dependem dessa informação.
- **Solução possível:** usar um terceiro estado (ex.: "não informado") quando a verificação for omitida.

### P6. Retorno do atualizador não confirma gravação; o painel trata ausência de exceção como sucesso

- **Evidência:** `atualizar_planilha_mfe` retorna sem valor em vários erros (`atualizador_MFE.py:335-340`); o painel apenas atualiza o status para "Concluída" após a chamada (`painel_principal.py:34-36`).
- **Impacto:** a interface pode indicar sucesso mesmo quando a gravação falhou (ex.: arquivo aberto no Excel).
- **Solução possível:** retornar booleano/sumário e refletir o resultado real no status do painel.

### P7. Correspondência por nome sem identificador único

- **Evidência:** ordenadores, lideranças e tercis usam apenas o nome normalizado (`normalizar_nome`) como chave — `atualizador_MFE.py:234-236`, `match_lideres.py:106-125`, `calculadora_tercis.py:73-84`.
- **Impacto:** homônimos colidem; variações de grafia/abreviações geram falsos negativos; o CPF (quando presente nos empenhos) é removido em vez de usado como chave.
- **Solução possível:** usar CPF/identificador estável quando disponível; manter nome como fallback com tratamento de ambiguidade.

### P8. README descreve auditoria de "adicionados/excluídos" que não existe no código

- **Evidência:** o README afirma geração de "planilhas de auditoria sobre os dados adicionados e excluídos", mas o atualizador regenera a aba sem calcular diferenças (`atualizador_MFE.py:302-332`).
- **Impacto:** expectativa incorreta de rastreabilidade; risco de uso indevido do produto.
- **Solução possível:** implementar a auditoria diferencial ou corrigir a documentação.

---

## 2. Riscos potenciais

### R1. Fragilidade diante de mudanças no portal

- **Evidência:** a raspagem depende de IDs e URLs fixos de ASP.NET WebForms (`ContentPlaceHolder1_lblNomeUnidadeGestaoSelecionada`, `ua_treeviewt`, `-A.gif`/`-D.gif`, `Sys.WebForms.PageRequestManager`) — `scraper_sici_nome.py:73-74,85-89,140,157,185-186`.
- **Impacto:** qualquer alteração no portal interrompe a extração, sem mecanismo de detecção de mudança de layout.
- **Solução possível:** centralizar os seletores em configuração e adicionar verificação de sanidade da página antes de iterar.

### R2. Chamadas à GUI (Tkinter) a partir de uma thread de trabalho

- **Evidência:** a raspagem roda em `threading.Thread` (`painel_principal.py:26`) e, dentro dela, o scraper usa `messagebox`/`askyesno` (`scraper_sici_nome.py:340-354`).
- **Impacto:** Tkinter não é thread-safe; o comportamento pode ser instável em alguns ambientes (embora funcione em muitos casos no Windows).
- **Solução possível:** mover os diálogos para a thread principal via fila/`after`.

### R3. Proveniência e versionamento dos modelos de ML

- **Evidência:** `model_fjg.pkl` e `vectorizer_fjg.pkl` são binários sem registro de treinamento, versão, métricas ou dados de origem (`area_negocio_ml.py:9-10`).
- **Impacto:** impossível reproduzir ou auditar a classificação; a qualidade é desconhecida.
- **Solução possível:** documentar/versionar o pipeline de treinamento e as métricas.

### R4. Caminhos de configuração/recursos resolvidos em tempo de importação

- **Evidência:** `CONFIG_FILE` é calculado no topo de `config_manager.py:6-11` com base em `sys.executable` ou `__file__`.
- **Impacto:** se o diretório de trabalho mudar ou o executável for movido, a localização de `config.txt` pode divergir do esperado.
- **Solução possível:** resolver caminhos no momento do uso e/ou expor claramente o diretório de dados.

---

## 3. Melhorias opcionais

- **Testes automatizados:** não há nenhum. Extrair `normalizar*`, `gerar_dataframe_empenhos`, `prever_area_negocio` e a montagem dos registros para funções puras e cobri-las com `pytest` aumentaria a confiança.
- **CI:** adicionar lint e testes em push (GitHub Actions), separando o que é documental do que é lógica.
- **Logging estruturado:** substituir `print` por `logging`, com arquivo de log que registre coleta parcial, erros e caminhos.
- **Configuração tipada:** substituir `config.txt` por um formato validado (ex.: TOML/YAML com schema) para detectar erros de edição manual.
- **Saída de auditoria:** gerar um arquivo com as diferenças entre a saída anterior e a nova (adicionados/removidos/alterados).
- **Separar GUI da lógica:** isolar as funções de processamento dos diálogos Tkinter para permitir uso headless e testes.

---

## 4. Avaliação dos artefatos existentes

### Graphify (`graphify-out/`)

- **Utilidade:** o `GRAPH_REPORT.md` e o `graph.json` são um bom índice de navegação (funções, módulos e comunidades), confirmando a organização em torno de `iniciar_raspagem()` e `atualizar_planilha_mfe()`.
- **Limitações:** mistura fatos extraídos de código, README e rascunhos com relações **inferidas** (algumas marcadas como `INFERRED`/`AMBIGUOUS`). Uma relação `EXTRACTED` não é, por si, prova de comportamento implementado. O relatório apresenta uma inconsistência entre o resumo (relações ambíguas) e a seção dedicada.
- **Veredito:** útil como índice, **não** como fonte primária de arquitetura.

### Diagram Design (`docs/diagramas/`)

- **Utilidade:** os três HTML (arquitetura, fluxo de dados, sequência) descrevem com precisão o que foi confirmado no código — incluindo a regeneração do MFE, o helper separado de tercis e a falha potencial do cruzamento pós-raspagem.
- **Veredito:** foram usados como referência e **reproduzidos em Mermaid** nesta documentação (componentes em `index.md`, fluxo em `data-lineage.md`, sequência em `architecture.md`). Os arquivos HTML/`gerar.py` permanecem no repositório, mas fora do build do MkDocs.

---

## 5. Não-problemas

- **Arquitetura simples** (sem microsserviços, banco de dados ou fila) é adequada ao escopo; não é tratada como deficiência.
- **Dependência de GUI e arquivos locais** é coerente com um utilitário de desktop de um único operador.
