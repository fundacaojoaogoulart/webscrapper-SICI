# Arquitetura e fluxos — guia para desenvolvedores

Três visões complementares do código atual. Abra os HTMLs em um navegador; cada arquivo contém CSS e SVG, navegação entre os diagramas e notas de implementação. No GitHub, baixe ou abra os arquivos localmente para visualizar o HTML renderizado.

| Diagrama | Pergunta | Arquivo |
|---|---|---|
| Arquitetura | Quais módulos existem e quais responsabilidades têm? | [arquitetura.html](diagramas/arquitetura.html) |
| Fluxo de dados | Quais entradas são transformadas em quais saídas? | [fluxo-dados.html](diagramas/fluxo-dados.html) |
| Sequência | Em que ordem acontece uma raspagem iniciada no painel? | [sequencia.html](diagramas/sequencia.html) |

## Fonte e escopo

Conferido no código em **22/09/2026**. O grafo `graphify-out/graph.json` foi consultado como índice de navegação; chamadas, condições e nomes de arquivos foram validados diretamente nos módulos. Os diagramas descrevem o estado atual, com as limitações abaixo.

- Tema padrão da skill Diagram Design, fundo claro; formato `doc-wide` (1280 × 720), estático e em português.
- O fluxo de dados usa a disposição técnica de componentes da referência de arquitetura. Não há raias de papéis organizacionais, pois o código não define essa divisão.
- A arquitetura destaca as chamadas principais; os atalhos offline e a inicialização de configuração aparecem nas notas.
- A sequência agrupa painel e tarefa em uma coluna; MFE e match em outra. Mostra o cenário com registros e dois blocos opcionais sucessivos. Chamadas internas, seleção de arquivos e detalhes de coleta estão nas referências.
- Fontes Google são opcionais; sem rede, o navegador usa fontes locais de fallback.

## Mapa de implementação

| Responsabilidade | Fonte verificável |
|---|---|
| Interface, thread e atalhos offline | [`painel_principal.py`](../painel_principal.py), L14–74, L95–126 |
| Configuração, navegação, coleta e próximos passos | [`scraper_sici_nome.py`](../scraper_sici_nome.py), L47–69, L140–155, L303–358 |
| Regras, ordenadores, empenhos, ML e escrita MFE | [`atualizador_MFE.py`](../atualizador_MFE.py), L62–127, L129–205, L281–332 |
| Normalização e cálculo dos tercis | [`calculadora_tercis.py`](../calculadora_tercis.py), L57–116 |
| Modelos e predição de áreas | [`area_negocio_ml.py`](../area_negocio_ml.py), L9–10, L53–85 em diante |
| Cruzamento e filtro de lideranças | [`match_lideres.py`](../match_lideres.py), L54–180 |
| Leitura e criação de configuração | [`config_manager.py`](../config_manager.py), `garantir_config_existe()` e `ler_config()` |
| Janela independente CGGI | [`gestores_equipes.py`](../gestores_equipes.py), L146–189 |

## Contratos e detalhes importantes

### SICI e MFE

A raspagem gera `órgão`, `escalão`, `área`, `cargo`, `titular` e `data_extracao`, salvando `sici_extracao_YYYYMMDD_HHMM.xlsx` ao lado do script/executável. Esse é o nome usado pelo código, diferente do nome com `completa` citado no README antigo e no grafo.

MFE recebe um DataFrame ou um caminho de Excel, lê `config.txt` e usa `model_fjg.pkl` e `vectorizer_fjg.pkl` para classificação. Ordenadores e empenhos são entradas opcionais, selecionadas pelo usuário. A saída `MFE_Atualizada.xlsx` é produzida copiando `MFE_Base.xlsx`, removendo linhas de dados e preenchendo 13 posições de coluna; não representa uma atualização diferencial célula a célula.

O fluxo integrado chama `gerar_dataframe_empenhos()` e recebe o resultado em memória. A geração de `Relatorio_Intermediario_Tercis.xlsx` está no helper separado `cruzar_sici_com_tercis()` e não deve ser presumida em toda atualização MFE.

### Lideranças e chamada pós-raspagem

Os botões offline passam `tarefa="PLC"` ou `tarefa="PRLF"`. O cruzamento usa a coluna `NOME` da base de lideranças e `titular`, `área`, `cargo` do SICI, normaliza nomes, faz left join e filtra os encontrados. As saídas desses modos são `planilha_cruzamento_PLC.xlsx` e `planilha_cruzamento_PRLF.xlsx`, relativas ao diretório de execução.

**Inconsistência observada no código:** o scraper chama `cruzar_planilhas(df)` sem tarefa. O valor padrão vazio não cria a coluna `status` nem define `ARQUIVO_C` local. Com entradas usuais válidas, a seleção de colunas em L148 pode lançar `KeyError` por ausência de `status`; se a entrada já contiver essa coluna, o uso posterior de `ARQUIVO_C` ainda pode falhar. Por isso, a sequência registra “retorno ou exceção”, sem prometer geração do relatório nesse caminho. Essa observação é análise estática, não uma execução do robô.

### Thread e encerramento

`executar_raspagem_completa()` inicia uma thread. A tarefa altera os controles Tkinter, executa o scraper e reabilita os botões no `finally`. As confirmações e os pós-processamentos ocorrem dentro da execução do scraper. O status final do painel não é uma validação de cada artefato: há erros tratados internamente que retornam normalmente.

## Manutenção dos diagramas

A fonte editável é [`diagramas/gerar.py`](diagramas/gerar.py), com conteúdo, coordenadas e estilos explícitos; não exige bibliotecas adicionais nem importa os módulos da aplicação.

```powershell
python docs/diagramas/gerar.py
python .agents/skills/diagram-design/scripts/self_check.py docs/diagramas/arquitetura.html
python .agents/skills/diagram-design/scripts/self_check.py docs/diagramas/fluxo-dados.html
python .agents/skills/diagram-design/scripts/self_check.py docs/diagramas/sequencia.html
```

Ao alterar chamadas, tarefas, entradas ou nomes de saídas, atualize a fonte, regenere os três HTMLs e confira as referências de linha. Versione o gerador e os arquivos gerados juntos.
