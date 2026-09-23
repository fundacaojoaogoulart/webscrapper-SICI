# Manutenção incremental da documentação

## Objetivo

O fluxo local identifica, por Git diff e regras determinísticas, se uma alteração pode afetar a arquitetura ou a linhagem dos dados. Ele evita usar IA como etapa de classificação e prepara contexto mínimo apenas quando houver possível impacto semântico.

`technical-review.md` é o registro da auditoria inicial. Não é reescrito por este fluxo; nova revisão técnica depende de solicitação explícita ou de uma alteração relevante que precise de validação humana.

## Ambiente

As ferramentas rodam com o Python da `.venv-docs`, que contém MkDocs, Selenium e openpyxl:

```powershell
python -m venv .venv-docs
.\.venv-docs\Scripts\python.exe -m pip install -r requirements-docs.txt
```

Nos exemplos abaixo, `python` significa o Python da `.venv-docs` (`.\.venv-docs\Scripts\python.exe` no Windows). A validação precisa dessa venv para renderizar os diagramas com Chrome/Edge e para o `mkdocs build`.

## Triagem

```powershell
python scripts/docs-impact.py
```

Por padrão, compara a árvore de trabalho com `HEAD`, incluindo arquivos não rastreados que não estejam ignorados. Para outros cenários:

```powershell
python scripts/docs-impact.py --staged
python scripts/docs-impact.py --base origin/main --head HEAD
```

O resultado é impresso em JSON e salvo localmente em `.docs-impact/impact.json`. Quando houver impacto possível, `.docs-impact/context.md` contém somente o diff relevante, os documentos candidatos e as convenções de atualização. O diretório é ignorado pelo Git.

O mapeamento versionado fica em `scripts/docs-dependencies.json`. Ele associa módulos a arquitetura e linhagem, e deve ser atualizado quando uma fonte, destino de dados, integração ou módulo novo for confirmado.

### Decisão

- `needsAgent: false`: somente arquivos ignorados ou sem impacto conhecido foram alterados; não atualize a documentação.
- `needsAgent: true`: a alteração pode ter impacto. Revise o pacote de contexto e faça uma atualização localizada, ou conclua que a documentação permanece correta.
- `requiresHumanReview: true`: schema de planilha, binários de modelo (`.pkl`), configuração de runtime ou módulo novo/desconhecido exigem decisão humana antes de registrar um novo comportamento como confirmado.

Alterações em componentes internos não são descartadas apenas pelo tamanho: elas seguem para avaliação quando pertencem a áreas mapeadas. Arquivos novos de código também são conservadoramente sinalizados.

## Atualização com agente

O comando local integrado é:

```powershell
python scripts/docs-update.py
python scripts/docs-update.py --model "provedor/modelo"
```

Ele executa a triagem, encerra sem chamar IA quando `needsAgent` for `false` e, havendo impacto, chama `opencode run`. O modelo é opcional: sem `--model`, o OpenCode usa o padrão configurado pelo usuário; com ele, a escolha vale somente para aquela execução. Nenhuma conta, provedor, modelo ou credencial é versionado no repositório.

Cada pessoa deve instalar a CLI OpenCode, conectar sua própria conta e escolher os modelos disponíveis localmente. Por exemplo, execute `opencode auth login <provedor>` (ex.: `openai`) e use `/models` para conferir os identificadores aceitos. O comando não tenta autenticar, salvar credenciais nem instalar a CLI. Se ela não estiver disponível, o contexto permanece em `.docs-impact/context.md` para execução manual.

Por segurança, a execução automática interrompe quando a triagem exige revisão humana. Após revisar o contexto, use `python scripts/docs-update.py --allow-review` para permitir que a IA documente somente fatos comprovados, preservando a incerteza. Use `--dry-run` para preparar e inspecionar o contexto sem chamar o modelo.

O agente recebe apenas a instrução para ler o pacote local e pode modificar exclusivamente os documentos afetados e, se necessário, `scripts/docs-dependencies.json`. O orquestrador calcula hashes antes e depois, preserva qualquer alteração fora do escopo para revisão e falha sem revertê-la. Em caso de êxito, executa a validação documental.

### Disparo manual e sinalização

O fluxo é **sempre manual**: nada é acionado automaticamente por hook de Git ou pipeline. Após alterar código que possa afetar a documentação, execute `python scripts/docs-update.py`.

Quando há impacto mas a CLI `opencode` não está no `PATH`, o comando emite o alerta **“IA não acionada para ajustes na documentação por falta de 'opencode' no PATH”**, informa os documentos afetados, preserva `.docs-impact/context.md` e encerra com código de saída `3`. O motivo também é gravado de forma estruturada em `.docs-impact/impact.json`, no campo `aiAction`, para ser lido por scripts ou CI. Os estados possíveis são:

| `aiAction.status` | Significado | Código de saída |
|---|---|---|
| `not-needed` | Sem impacto; IA não acionada | 0 |
| `human-review-required` | Triagem exige revisão humana | 2 |
| `dry-run` | Somente preparação; IA não acionada | 0 |
| `not-run` (`reason: opencode-missing`) | Impacto detectado, mas CLI ausente | 3 |
| `failed` | A execução da IA falhou | 4 |
| `out-of-scope` | A IA alterou arquivos fora do escopo | 5 |
| `validation-failed` | Validação documental reprovada | 6 |
| `completed` | Atualização concluída e validada | 0 |

## Validação

```powershell
python scripts/docs-validate.py
python scripts/docs-impact.py --test
```

`docs-validate.py` verifica cercas Markdown, links e âncoras locais, valida a sintaxe estrutural de cada diagrama Mermaid, renderiza os diagramas usando o bundle local `docs/assets/mermaid.min.js` quando um navegador Chrome/Edge está disponível e executa `mkdocs build --strict`. Quando existe `.docs-impact/impact.json`, também aponta mudanças documentais fora do escopo indicado pela triagem.

Para tornar a renderização obrigatória:

```powershell
python scripts/docs-validate.py --require-render
```

Defina `CHROME_PATH` se o navegador não estiver em um caminho conhecido. Sem navegador, a validação informa que a renderização foi ignorada; a sintaxe Mermaid e o build MkDocs continuam verificados.

Os testes sintéticos (`docs-impact.py --test`) não usam Selenium, planilhas reais ou outros recursos externos. Eles cobrem alteração sem impacto, seletor/campo do scraper, regra de correspondência, schema de planilha, geração do `.exe`, mudança que requer revisão humana e alteração de dados externos sem mudança de funcionamento.

## Fontes externas

O Git não observa mudanças diretas no Portal SICI nem nas bases externas (Ordenadores, Empenhos, lideranças). O repositório versiona os schemas conhecidos (`MFE_Base.xlsx` e o mapeamento), que já são cobertos pela triagem. Não foi implementado monitoramento externo porque não há necessidade demonstrada nem acesso autorizado. Se isso mudar, a verificação deve comparar somente metadados de abas e cabeçalhos esperados — nunca importar todos os registros — e exigir autorização explícita.
