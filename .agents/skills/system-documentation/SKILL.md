---
name: system-documentation
description: Skill para OpenCode de auditoria e documentação de sistemas, regras de negócio e linhagem de dados, com visualização MkDocs, atualização incremental via Git diff e CI GitHub Actions opt-in.
compatibility: OpenCode; Python 3.9+, Git; MkDocs Material para build. CI opcional apenas GitHub Actions.
metadata:
  version: "2.0.0"
  language: pt-BR
---

# System Documentation

**Método aqui, fatos no repositório.** Use `documentation-engineer` para `init`, `update` e `setup-ci`. Leia apenas a referência do modo ativo. Não execute aplicativos reais, scrapers, planilhas ou deploys sem autorização específica.

## `init`

Leia `references/initial-audit.md` e `references/documentation-standards.md`. Antes de configurar o MkDocs, **pergunte obrigatoriamente** fonte principal, cor primária, cor secundária e cor do texto. Uma única vez por repositório; reutilize configuração nas próximas execuções. Confirme CI antes de instalar.

Faça inventário seletivo e gere apenas `docs/index.md`, `docs/architecture.md`, `docs/data-lineage.md`, `docs/technical-review.md`, `docs/documentation-maintenance.md`. Priorize regras de negócio (inclusive limitações tabeladas), fluxo de dados manual/automático e arquitetura em nível adequado. Não gerar documentação secundária extensa. O mapa JSON e scripts pertencem a `scripts/`, não a `docs/`.

Leia `templates/diagram-style.md` para diagramas verticais preferenciais, formas, cores e subgraphs. Use `templates/mkdocs.yml` com saída `.docs/mkdoc`; personalize tema e copie `templates/extra.css` para `docs/stylesheets/extra.css` com a cor do texto escolhida sem modificar as cores semânticas. Adicione ao `.gitignore` a saída e `.docs-update/`. Copie scripts templates para `scripts/`, preserve arquivos existentes, ajuste mapa a globs verificados. Atualize seção curta do README do projeto (comandos locais e status real do CI); não sobrescrever README.

O texto de `documentation-maintenance.md` deve seguir `templates/documentation-maintenance.template.md`, mas incluir APENAS capacidades instaladas e comandos verificados. Validar build/diagrama conforme ferramentas disponíveis; reportar limitações reais.

## `update`

Leia `references/incremental-update.md`. Execute `python scripts/docs-update.py prepare` primeiro; seu resultado **não usa LLM** e fica em `.docs-update/review-context.json`. `skip` não altera nada; `regenerate` valida/builda; `review_ai` exige inspeção apenas do diff e seções relevantes; `manual_review` não autoriza inventar regras. Alterações mínimas, preservar estilo e paleta; nunca reescrever `technical-review.md` automaticamente.

## `setup-ci`

Leia `references/setup-ci.md`. Pergunte se não houver CI: **“Foi identificado que ainda não existe CI nesse projeto, deseja implementar um CI com GitHub Actions?”**. Só após resposta afirmativa criar/adaptar `.github/workflows/documentation.yml` a partir do template. Se houver CI, pedir autorização antes de integrar sem sobrescrever deploys. Documentar artefatos, status de IA, requisitos do OpenCode no PATH, seleção de modelo e opção de revisão manual no README e em `documentation-maintenance.md`.

## Economia, privacidade e honestidade

Não varra `node_modules`, `.git`, caches, build, exports de planilha nem arquivos binários. Não leia segredos nem registros pessoais. Registre lacunas como pendências. Git não observa Sheets/sites/bancos remotos. **Skill não disponibiliza modelo, credenciais, acesso remoto, CI ou execução automática local de IA por si só.** Não afirmar que validou visualmente diagramas sem navegador. Não modifique código de produção nem regras de negócio.

<!-- EXEMPLOS DE PROMPTS: veja examples/prompts.md na raiz do kit. -->
