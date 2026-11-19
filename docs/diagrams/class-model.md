---
type: Diagram
title: "Modelo de classes (ADR 001)"
description: Classes propostas do orquestrador, artefatos e componentes, conforme o ADR 001.
tags:
- diagram
- adr
- classes
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:29:00-03:00"
evidence_basis: [proposal]
sources:
- id: adr-001
  resource: docs/diagrams/02-class-diagram.mmd, commit 6a30f8b (15/10/2026)
  title: Diagrama original do ADR 001
---

# Modelo de classes (ADR 001)

> **Origem:** `docs/diagrams/02-class-diagram.mmd` (commit `6a30f8b`), migrado em 18/11/2026 sem alterar o Mermaid. Representa a arquitetura **proposta** no [ADR 001](../adr/001-workflow-architecture.md); o orquestrador **não está implementado** (`domain.py` só tem esqueletos). Para o fluxo realmente implementado, veja [pipeline atual](current-pipeline.md).

```mermaid
classDiagram
    direction TB
    class WorkflowRunner {
        run(event, pipeline)
    }
    class ComponentExecutor {
        execute(component, contents)
    }
    class PipelineSelector {
        execute(event) Pipeline
    }
    class StepSelector {
        execute(pipeline)
    }
    class Event {
        pipeline_id
        sensor_data
        shop_id
        sensor_id
    }
    class PipelineRepository {
        get_by_id(pipeline_id)
    }
    class Pipeline {
        pipeline_id
        steps
    }
    class Step {
        step_name
        depends_on
        input_artifacts
        component
        output_artifacts
    }
    class Component {
        prepare(Artifact)
        execute(prepared_data) Artifact
    }
    class Artifact {
        name
        location
        materialize() content
        dematerialize(content)
    }
    WorkflowRunner ..> Event : utiliza
    WorkflowRunner ..> Pipeline : utiliza
    WorkflowRunner ..> ComponentExecutor : utiliza
    WorkflowRunner ..> StepSelector : utiliza
    PipelineSelector ..> WorkflowRunner : utiliza
    PipelineSelector ..> Event : lê
    PipelineSelector ..> PipelineRepository : consulta
    PipelineRepository --> "1..*" Pipeline : contém
    StepSelector ..> Pipeline : consulta
    StepSelector ..> Step : seleciona
    Pipeline --> "2..*" Step : contém
    Step --> "0..*" Step : depende
    Event --> "1" Artifact : sensor_data
    Step --> "1" Component : component
    Step --> "1..*" Artifact : input_artifacts
    Step --> "1..*" Artifact : output_artifacts
    ComponentExecutor ..> Component : utiliza
    Component ..> Artifact : utiliza
```
