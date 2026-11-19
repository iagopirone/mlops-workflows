---
type: Diagram
title: Pipeline atual e fluxo-alvo
description: Fluxo implementado e verificado, fluxo-alvo do desafio MIRAGE e mapa dos diagramas do ADR 001.
tags:
- mermaid
- architecture
- workflow
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, proposal]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Diagramas do ADR 001

| Arquivo | Finalidade | Situação |
|---|---|---|
| [Fluxo do workflow](workflow-flow.md) (antes `01-flow.mmd`) | Seleção de pipeline, execução das etapas e finalização | Arquitetura proposta; orquestrador não implementado |
| [Modelo de classes](class-model.md) (antes `02-class-diagram.mmd`) | Entidades e contratos | **Desatualizado.** Mostra um `Artifact` único, sem `ArtifactContent` nem os componentes reais |
| [Sequência de execução](execution-sequence.md) (antes `03-sequence-diagram.mmd`) | Sequência prevista | Já separa `ArtifactContent`; o orquestrador não foi implementado |

Esses diagramas ainda não foram alterados; em 18/11/2026 só foram movidos de `docs/diagrams/*.mmd` para documentos `Diagram`, com o Mermaid idêntico. Atualizá-los está no [roadmap](../plans/2026-11-17-plan-mirage-integration.md).

## Fluxo implementado e verificado (17/11/2026)

```mermaid
flowchart LR
  I[ImageReference] --> D[ObjectDetectionComponent<br/>YoloDetector]
  D --> J[DetectionReference / JSON]
  I --> V[DetectionVisualizationComponent]
  J --> V
  V --> A[ImageReference anotada]
  I --> Q[VisualQuestionAnsweringComponent<br/>FakeAnswerer]
  P[TextReference prompt] --> Q
  Q --> R[TextReference resposta]
  R --> T[TextDetectionParsingComponent]
  I --> T
  T --> J
```

O VQA e o parser foram verificados só com `FakeAnswerer`.

## Fluxo-alvo do desafio MIRAGE (planejado, não implementado)

```mermaid
flowchart LR
  I[ImageReference] --> Q[VQA component<br/>MirageAnswerer - futuro]
  P[TextReference prompt] --> Q
  Q --> R[TextReference resposta]
  R --> T[TextDetectionParsingComponent - implementado]
  I --> T
  T --> K{JSON estruturalmente válido?}
  K -->|Sim| J[DetectionReference<br/>conf null - experimental]
  K -->|Não| E[Erro; nada é salvo]
  J --> V[DetectionVisualizationComponent]
  I --> V
  V --> A[ImageReference anotada]
```

- **Validade estrutural não é precisão espacial**: a precisão só será conhecida medindo com inferência real.
- **Alternativa para as caixas:** um detector guiado por texto (OWLv2, Grounding DINO) implementando `ObjectDetector`. Ele se encaixaria no primeiro fluxo sem mudar nenhuma interface.
