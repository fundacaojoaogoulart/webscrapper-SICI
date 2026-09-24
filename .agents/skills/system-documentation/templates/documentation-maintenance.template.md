# Manutenção incremental da documentação

## Objetivo

Descreva o fluxo real: triagem Git determinística → contexto mínimo → revisão semântica somente quando necessária → validação. `technical-review.md` é auditoria inicial, não é reescrito em updates habituais.

## Ambiente

Liste o comando para criar/usar venv APENAS se instalada e exigida. Dependências em `requirements-docs.txt` e versões de Python/MkDocs usadas. Não alegue Playwright/navegador obrigatório se não estiver instalado. MkDocs local (`site_dir: .docs/mkdoc`), não publicação pública.

## Triagem

`python scripts/docs-update.py prepare` compara HEAD com working tree; `--base origin/main --target HEAD` compara revisões via merge-base. Inclui não rastreados não ignorados. Resultado: `.docs-update/result.json` e `review-context.json` (local, ignorado; diffs limitados e sem credenciais conhecidas). Mapeamento: `scripts/docs-dependencies.json`. Explique que classificação não prova ausência de alteração semântica.

### Decisão

| Classificação | Ação |
|---|---|
| `skip` | Sem impacto conhecido; não atualizar/buildar. |
| `regenerate` | Validar/reconstruir sem IA. |
| `review_ai` | Agente examina contexto mínimo e propõe patch ou zero mudança. |
| `manual_review` | Exige validação humana antes de documentar. |

## Atualização com agente

`python scripts/docs-update.py update` **não chama LLM**: prepara e valida em `regenerate`; para casos semânticos entrega JSON de revisão. Descreva como selecionar `documentation-engineer`/skill no OpenCode e usar `review-context.json`. Se integração automática foi configurada no CI, explique os requisitos e o comportamento específico, sem prometer execução autônoma local.

### Disparo manual e CI

Documente a situação real: CI ausente, CI somente triagem, ou CI com opção manual de IA. Se GitHub Actions instalado, cite workflow, triggers e artefatos, configuração do OpenCode no PATH, modelo (`DOCS_AI_MODEL`) e credenciais do provider. A opção de IA em CI deve ser autorizada/configurada; não executá-la automaticamente em PR não confiável nem commitar na main. Quando o JSON sinaliza `review_ai` ou `manual_review`, explique como executar o comando manual do OpenCode ou validar manualmente. Não invente secrets ou jobs de deploy.

## Validação

`python scripts/docs-update.py validate` realiza verificações Markdown/links/estrutura Mermaid e MkDocs build strict. Verificação visual opcional: `python scripts/docs-validate.py --repo . --visual`, que exige Playwright e navegador Chromium/Chrome/Edge; só declare renderização validada depois de executá-la com sucesso. Liste testes disponíveis; não alegar cobertura inexistente.

## Fontes externas

Git não detecta alterações diretamente em Google Sheets, sites, ERGON ou banco remoto. Registros individuais não exigem necessariamente alterar documentação técnica. Se schema externo puder afetar o fluxo, indique revisão de metadados autorizada (abas/cabeçalhos), sem importar dados pessoais.
