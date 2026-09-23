# AGENTS.md

Instruções permanentes para agentes que trabalham neste repositório.

## Onde está a documentação

- `docs/data-lineage.md` — fluxo e rastreabilidade dos dados (origem → transformação → destino).
- `docs/architecture.md` — arquitetura, módulos e execução do sistema.
- `docs/technical-review.md` — registro da auditoria inicial (não reescrever).
- `docs/documentation-maintenance.md` — procedimento de manutenção incremental.

## Quando consultar cada documento

- Mudança em scraping, classificação, regras, transformações ou planilhas → `data-lineage.md`.
- Mudança em componentes, responsabilidades, dependências ou no `.exe` → `architecture.md`.
- Manter a documentação em dia após mudança de código → siga `documentation-maintenance.md`.

## Manutenção incremental (sempre manual)

Rode com o Python da `.venv-docs` (`.\.venv-docs\Scripts\python.exe`), que contém MkDocs e Selenium.

1. `python scripts/docs-impact.py` — triagem determinística (sem IA).
2. Se `needsAgent: true`, `python scripts/docs-update.py` (aciona `opencode run`).
3. Valide com `python scripts/docs-validate.py`.

## Regras de preservação

- Modifique somente os trechos afetados; preserve títulos, terminologia e diagramas Mermaid.
- Não remova informação válida; não substitua regras internas por interpretações próprias.
- Não altere informações marcadas como "externo não verificado".
- Não regenere `technical-review.md`. Se a documentação já estiver correta, não altere nada.

## Validação

- `python scripts/docs-validate.py`
- `python scripts/docs-impact.py --test`
