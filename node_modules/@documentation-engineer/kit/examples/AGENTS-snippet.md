<!-- Opcional: acrescente ao AGENTS.md de cada repositório, preservando instruções existentes. -->
## Documentação de engenharia

Documentação: `docs/index.md`, `docs/data-lineage.md`, `docs/architecture.md`.
Antes de alterar regra de negócio, consulte as seções relacionadas. Depois execute `python scripts/docs-update.py prepare` e só atualize os documentos se houver impacto real; preservar títulos, cores e diagramas. O relatório `docs/technical-review.md` é auditoria inicial, não reescrever automaticamente. Use `@documentation-engineer` com skill `system-documentation` para revisão semântica. Não execute integração externa sem autorização.
