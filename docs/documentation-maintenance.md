# Manutenção incremental da documentação

## Objetivo

O fluxo local segue: triagem Git determinística → contexto mínimo → revisão semântica somente quando necessária → validação. A triagem não usa IA e não prova, sozinha, a ausência de alteração semântica.

`technical-review.md` é a fotografia da auditoria inicial. Não é reescrito nas atualizações habituais.

## Ambiente

Use o Python da `.venv-docs` para instalar as dependências exclusivas da documentação:

```powershell
python -m venv .venv-docs
.\.venv-docs\Scripts\python.exe -m pip install -r requirements-docs.txt
```

Nos comandos a seguir, `python` representa esse interpretador. O site é local e privado, gerado em `.docs/mkdoc`.

Instale também o navegador usado na validação visual:

```powershell
python -m playwright install chromium
```

## Triagem

```powershell
python scripts/docs-update.py prepare
```

O comando compara `HEAD` com a árvore de trabalho, incluindo não rastreados não ignorados. Para comparar revisões, use `--base origin/main --target HEAD`; o cálculo usa o merge-base.

Os resultados locais e ignorados são `.docs-update/result.json` e `.docs-update/review-context.json`. O segundo contém apenas diffs de arquivos de código permitidos, com limites de tamanho e exclusão de caminhos de credenciais conhecidos. O mapeamento versionado fica em `scripts/docs-dependencies.json`.

### Decisão

| Classificação | Ação |
|---|---|
| `skip` | Sem impacto conhecido; não atualizar nem reconstruir. |
| `regenerate` | Validar e reconstruir sem IA. |
| `review_ai` | O agente examina o contexto mínimo e propõe patch localizado ou nenhuma mudança. |
| `manual_review` | Exige confirmação humana antes de documentar comportamento. |

## Atualização com agente

```powershell
python scripts/docs-update.py update
```

Esse comando **não chama LLM**. Ele prepara o contexto e valida quando a decisão é `regenerate`; nos casos `review_ai` e `manual_review`, informa que é necessária revisão localizada.

No OpenCode, selecione o agente `documentation-engineer`, use a skill `system-documentation` no modo `update` e solicite a revisão de `.docs-update/review-context.json`. O agente deve modificar apenas os documentos impactados e o mapa, quando necessário. Não são versionados modelo, conta, credenciais ou tokens.

### Disparo manual e CI

O workflow `.github/workflows/verify.yml` executa triagem e validação em pull requests e pushes na `main`, publicando `.docs-update/` como artefato `documentation-triage`.

A revisão por IA é opcional e fica disponível somente em `workflow_dispatch` com `run_ai=true`. Ela requer a variável `DOCS_AI_MODEL`, a credencial do provedor (`OPENAI_API_KEY` no template) e OpenCode no `PATH`. Não roda em PR não confiável, não faz commit automático e publica a proposta em `documentation-proposal.patch` como artefato.

## Validação

```powershell
python scripts/docs-update.py validate
```

Esse comando verifica as cinco páginas exigidas, links locais, cercas Markdown, estrutura Mermaid, mapa de dependências, executa `mkdocs build --strict` e renderiza os diagramas em Chromium com Playwright. A validação exige `playwright` e o navegador Chromium instalados.

## Fontes externas

Git não observa mudanças diretas no Portal SICI nem nas bases externas de ordenadores, empenhos e lideranças. Registros individuais não exigem, por si, alteração da documentação técnica. Se o schema externo puder afetar o fluxo, revise somente metadados autorizados, como abas e cabeçalhos, sem importar dados pessoais.
