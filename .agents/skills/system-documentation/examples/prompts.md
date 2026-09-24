# Prompts comentados para reutilizar com OpenCode

## 1. Primeira vez — `init`

<!-- Troque os itens entre colchetes. O agente obrigatoriamente perguntará fonte e cores uma vez e não deve pressupor escolhas. -->

```text
@documentation-engineer Use a skill system-documentation em modo init.
Priorize regras de negócio, fluxo de dados e arquitetura curta neste repositório.
Fontes e módulos mais relevantes: [caminhos conhecidos, se houver].
Não leia dados pessoais, credenciais, binários ou arquivos gerados.
Crie as cinco páginas padrão, configure MkDocs local em .docs/mkdoc e acrescente os comandos ao README existente.
Antes de configurar a aparência, me pergunte fonte principal, cor primária, cor secundária e cor do texto.
Não instale CI sem me consultar. Mostre o resumo da auditoria e eventuais lacunas.
```

## 2. Atualizar — `update`

<!-- Execute prepare primeiro para evitar ler o repositório inteiro; não chame IA para skip. -->

```text
@documentation-engineer Use a skill system-documentation em modo update.
Execute python scripts/docs-update.py prepare, leia apenas o contexto mínimo gerado e confirme impacto real.
Atualize apenas os trechos incorretos de regras, fluxo ou arquitetura. Preserve a estrutura/cores existentes.
Não altere technical-review.md nem código de produção.
```

## 3. Configurar CI — `setup-ci`

<!-- A instalação depende de autorização explícita, não ativa IA automaticamente em PR. -->

```text
@documentation-engineer Use a skill system-documentation em modo setup-ci.
Inspecione CI existente. Quero GitHub Actions com triagem determinística e artefato JSON.
Antes de modificar workflows, mostre o que será alterado e aguarde minha aprovação.
Explique o modo opcional de IA via dispatch manual, modelo/credenciais e revisão do patch.
```

## 4. Foco Firebase

```text
@documentation-engineer Use a skill system-documentation em modo init.
Foque no fluxo Google Sheets → validação → normalização → Firestore e nos serviços Firebase/Vercel.
Documente aba, coluna, transformação e coleção/campo; se não conseguir verificar, sinalize pendência.
```

## 5. Foco scraping

```text
@documentation-engineer Use a skill system-documentation em modo init.
Priorize origem do scraping, planilhas intermediárias, regras de mapeamento, etapas manuais/automáticas e arquivo final.
Use grafos/diagramas existentes somente como pistas verificáveis; não execute raspagem nem .exe.
```

## 6. Foco Apps Script

```text
@documentation-engineer Use a skill system-documentation em modo init.
Priorize estados e regras tabeladas do líder, aprovação/reprovação, processamento manual da fila e exatamente quais campos da aba Base mudam.
Arquitetura apenas no nível de arquivo/pasta; não execute funções que alterem planilhas.
```
