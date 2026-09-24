# Padrões: documentação curta, factual e visual

Somente cinco páginas Markdown no diretório `docs/`:

- `index.md`: o que faz, entradas/saídas, resumo do fluxo e links. Não copiar tabelas.
- `data-lineage.md`: documento principal com origem → extração → revisão/normalização → destino → consumidores; campos atualizados automaticamente versus manualmente, regras de negócio, prioridade das regras tabeladas, casos sem correspondência, exceções e limitações comprovadas. Tabelas sucintas e rastreabilidade até função/arquivo quando relevante.
- `architecture.md`: diagrama agrupado, responsabilidade de cada módulo/arquivo relevante, entrada/serviços externos. Sem lista de todas as funções ou dependências triviais.
- `technical-review.md`: achados com evidência, impacto e melhoria possível; separar problema, risco e opção. Congelar após auditoria inicial.
- `documentation-maintenance.md`: comandos realmente instalados, classificação, acionamento do OpenCode quando configurado, CI existente ou não, validação e fontes externas.

Diagramas: seguir `templates/diagram-style.md`. Preferir direção vertical, grouping e cores semânticas fixas; não confundir paleta do tema com paleta dos dados. Não inventar campos nem dados sensíveis. Sempre tentar preservar o conteúdo válido ao atualizar.
