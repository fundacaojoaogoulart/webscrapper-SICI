# Convenção visual Mermaid (obrigatória em diagramas novos)

- Preferir `flowchart TB` (vertical). Usar LR apenas se o vertical reduzir a legibilidade; jamais forçar um diagrama ilegível.
- Formas: dados/planilhas `[(...)]`; tarefa `[ ... ]`; decisão `{ ... }` com arestas nomeadas; código `[[ ... ]]` (subprocesso com bordas laterais); documentos `[/ ... /]`; serviço externo retângulo tracejado (`classDef external ...stroke-dasharray: 5 3`).
- Cores semânticas fixas independentemente das cores do tema: Google Sheets verde `#E4F5E8/#20864B`; documentos estáticos roxo `#EAE3FA/#8760C8`; tarefas azul `#E3EDFF/#4A7BE8`; serviços/ferramentas amarelo `#FFF7D8/#C9AC2D`. Banco não-Sheets: azul suave ou cor contextual distinta; checar contraste. Código: violeta suave, diferenciar de documento pela forma. Decisão: neutra ou laranja, não confundir com serviços.
- Agrupar com `subgraph` quando houver fronteira lógica clara (Firebase, Serviços Google, Apps Script). A posição dos nós em subgraphs depende do renderizador; inspecionar resultado. Preferir nomes curtos; usar novo diagrama se ultrapassar a leitura confortável.
- Sem emojis como símbolos principais; símbolos nativos Mermaid são mais portáveis. As imagens fornecidas pelo usuário são referências visuais, não fontes de fatos do repositório.

```mermaid
flowchart TB
  subgraph Google[Serviços Google]
    sheet[(Google Sheets)]:::sheet
  end
  subgraph App[Aplicação]
    code[[import.js]]:::code
    step[Normalizar dados]:::task
    decision{Registro válido?}:::decision
  end
  external[Serviço externo]:::external
  doc[/Relatório.pdf/]:::document
  sheet --> code --> step --> decision
  decision -->|Sim| doc
  decision -->|Não| external
  classDef sheet fill:#E4F5E8,stroke:#20864B,color:#153A23;
  classDef document fill:#EAE3FA,stroke:#8760C8,color:#30204E;
  classDef task fill:#E3EDFF,stroke:#4A7BE8,color:#173467;
  classDef code fill:#F0EAFE,stroke:#7554B9,color:#30204E;
  classDef decision fill:#FFF0DF,stroke:#B77928,color:#50370D;
  classDef external fill:#FFF7D8,stroke:#C9AC2D,color:#4B3D0C,stroke-dasharray:5 3;
```
