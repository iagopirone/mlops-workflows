---
type: Reference
title: Mecanismos transitórios
description: Registro do que é provisório no código ou na documentação, com o critério para remover ou consolidar cada item.
tags:
- transitional
- technical-debt
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [verified, approved]
---

# Mecanismos transitórios

Tudo o que existe "por enquanto" fica listado aqui. Quando o mecanismo for removido ou consolidado, apague a linha **e** a documentação ligada a ele na mesma mudança, e registre no [log](../log.md).

| Mecanismo | Onde | Por que existe | Critério de saída | Documentação ligada |
|---|---|---|---|---|
| Componente VQA **experimental** | `mlops_workflows/components/visual_question_answering/` | Etapa intermediária aprovada para testar imagem + prompt → texto antes de qualquer detecção | Decidir, com métricas reais, entre `MirageAnswerer` + parser ou um detector guiado por texto | [VQA](component-visual-question-answering.md) |
| Parser de texto em detecções **experimental** | `mlops_workflows/components/text_detection_parsing/` | Converte respostas textuais em `DetectionContent` para testar a hipótese do MIRAGE | Idem; se o MIRAGE for descartado, avaliar a remoção | [parser](component-text-detection-parsing.md) |
| `prepare()` divergente no `ObjectDetectionComponent` | `mlops_workflows/components/object_detection/object_detection_component.py` | Devolve `np.ndarray`, anterior à convenção do [ADR 002](../adr/002-prepare-returns-artifact-contents.md); alterar componente que funciona exige aprovação | Refatoração aprovada pelo usuário | [componente de detecção](component-object-detection.md) |
| Desenho de caixas duplicado | `examples/demo_detection.py` | O exemplo desenha as caixas por conta própria, repetindo o `DetectionVisualizationComponent` | Fazer o exemplo usar o visualizador (com aprovação) | [visualizador](component-detection-visualization.md) |
| Esqueletos do orquestrador | `mlops_workflows/domain.py` (`StepSelector`, `ComponentExecutor`, `WorkflowRunner`, `PipelineSelector`) | Modelam o [ADR 001](../adr/001-workflow-architecture.md); só lançam `NotImplementedError` | Implementar o orquestrador ou remover os esqueletos | [ADR 001](../adr/001-workflow-architecture.md), [diagramas](../diagrams/index.md) |
| Prova de conceito do MIRAGE | `experiments/mirage/` | Experimento isolado, com ambiente próprio, para testar a hipótese das caixas | Concluir a avaliação real e decidir o caminho; então mover para o pacote ou arquivar | [MIRAGE](mirage.md), [avaliador](mirage-evaluation.md) |
| Testes do experimento fora da suíte principal | `experiments/mirage/tests/` (o `pyproject.toml` tem `testpaths = ["tests"]`) | O experimento exige Python 3.10 e é isolado do pacote | Mesmo critério da prova de conceito | [suíte de testes](test-suite.md) |
| `ruff.toml` aninhado | `experiments/mirage/ruff.toml` | Alvo Python 3.10 e `src = ["../.."]` só nessa pasta | Mesmo critério da prova de conceito | [ferramentas](tooling.md) |
| Validador OKF local | `scripts/okf_lint.py` | O `okf-lint.py` oficial (`visio-research-context`) não está disponível nesta máquina | Usar o validador oficial quando estiver disponível | [diretrizes](okf-guidelines.md#validador-local) |
