---
type: Reference
title: Ciclo de vida dos artefatos e componentes
description: Materialização, preparação, execução e persistência das saídas.
tags:
- workflow
- data-flow
- artifacts
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Caminho dos dados

```mermaid
flowchart LR
  IR[ImageReference] --> P[prepare]
  DR[DetectionReference] --> P
  P --> IC[ImageContent]
  P --> DC[DetectionContent]
  IC --> EX[execute]
  DC --> EX
  EX --> OC[Novo ImageContent]
  OC --> DM[dematerialize]
  DM --> OR[ImageReference de saída]
```

- **Referência (`Reference`)**: aponta para um artefato; inclui `name` e `location`.
- **Materialização**: `reference.materialize()` carrega/valida e cria um `Content`.
- **Conteúdo (`Content`)**: objeto tipado representando dados na memória.
- **Preparação**: o componente converte referências em conteúdos prontos para processamento.
- **Execução**: recebe o retorno do `prepare()`, transforma-o e gera conteúdo de saída.
- **Desmaterialização**: `content.dematerialize(reference)` salva no destino.
- **Saída do componente**: lista de `ArtifactReference` para consumo posterior.

## Exemplo lógico

```python
prepared = component.prepare([image_reference, detection_reference])
output_refs = component.execute(prepared)
```

A composição é independente do detector que produziu as detecções. O objetivo é que **a fronteira entre componentes use referências de artefatos**, enquanto o processamento interno opere sobre conteúdos materializados.

## Cuidados

- Não extrair `.data` no `prepare()`: a convenção foi aplicada no visualizador e no VQA em 17/11/2026. `ObjectDetectionComponent` ainda retorna `np.ndarray`; veja [contratos](contracts.md).
- Não sobrescrever a imagem original: trabalhar com `image_content.data.copy()`.
- Preservar distinção entre imagem original e imagem anotada por referência de saída diferente.
- Não confundir estrutura Pydantic válida com coordenadas semanticamente corretas.
