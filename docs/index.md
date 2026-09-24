# Documentação técnica

Documentação do **webscraper SICI** da Prefeitura do Rio: uma aplicação desktop em Python que extrai a árvore de cargos do Portal SICI, atualiza o Mapeamento de Funções Estratégicas (MFE) e executa cruzamentos de lideranças.

## Visão geral

O ponto de entrada é `painel_principal.py`. O usuário inicia uma raspagem web ou seleciona uma extração existente; o processamento interno classifica os dados e escreve arquivos locais. O pacote pode ser distribuído como executável `--onedir` via PyInstaller.

### Entradas, processamento e saídas

```mermaid
flowchart TB
    sici[Portal SICI]:::external
    input[(Extração SICI ou arquivo selecionado)]:::data
    panel[[painel_principal.py]]:::code
    process[Classificação e cruzamentos]:::task
    mfe[/MFE_Atualizada.xlsx/]:::document
    leaders[/Planilhas de cruzamento/]:::document

    sici --> panel --> input --> process
    process --> mfe
    process --> leaders

    classDef data fill:#E3EDFF,stroke:#4A7BE8,color:#173467;
    classDef document fill:#EAE3FA,stroke:#8760C8,color:#30204E;
    classDef task fill:#E3EDFF,stroke:#4A7BE8,color:#173467;
    classDef code fill:#F0EAFE,stroke:#7554B9,color:#30204E;
    classDef external fill:#FFF7D8,stroke:#C9AC2D,color:#4B3D0C,stroke-dasharray:5 3;
```

## O que você encontra aqui

| Página | Pergunta que responde |
|---|---|
| [Fluxo dos dados](data-lineage.md) | Como os dados chegam, são processados e chegam às planilhas? Quais campos são automáticos e quais são manuais? |
| [Arquitetura](architecture.md) | Quais módulos existem, como se relacionam e como o executável é construído? |
| [Avaliação técnica](technical-review.md) | Quais problemas, riscos e melhorias a implementação inicial apresenta? |
| [Manutenção](documentation-maintenance.md) | Como triar, revisar e validar alterações na documentação? |
