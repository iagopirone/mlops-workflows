---
type: Diagram
title: "Fluxo do workflow (ADR 001)"
description: Fluxo proposto do pedido de processamento até a finalização, conforme o ADR 001.
tags:
- diagram
- adr
- flow
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:29:00-03:00"
evidence_basis: [proposal]
sources:
- id: adr-001
  resource: docs/diagrams/01-flow.mmd, commit 6a30f8b (15/10/2026)
  title: Diagrama original do ADR 001
---

# Fluxo do workflow (ADR 001)

> **Origem:** `docs/diagrams/01-flow.mmd` (commit `6a30f8b`), migrado em 18/11/2026 sem alterar o Mermaid. Representa a arquitetura **proposta** no [ADR 001](../adr/001-workflow-architecture.md); o orquestrador **não está implementado** (`domain.py` só tem esqueletos). Para o fluxo realmente implementado, veja [pipeline atual](current-pipeline.md).

```mermaid
flowchart TD
    entrada["Entrada genérica"] --> seletor["Escolhedor de pipeline"]
    seletor -. Consulta .-> repositorio["Repositório de pipelines"]
    repositorio -. Pipeline selecionado .-> seletor
    seletor -->|Pedido + pipeline| proxima
    subgraph workflow["Workflow"]
        proxima["Definir próxima etapa conforme os pré-requisitos"]
        subgraph ciclo["Execução de componentes — 1 a N"]
            buscar["Buscar e carregar artefatos"]
            executar["Preparar e executar componente"]
            registrar["Registrar saídas"]
            buscar --> executar --> registrar
        end
        proxima -->|Etapas prontas| buscar
        registrar -->|Resultado intermediário| proxima
        subgraph finalizacao["Componente de finalização"]
            finalizar["Organizar resultados finais e salvar/enviar"]
        end
        registrar -->|Saídas finais disponíveis e pré-requisitos atendidos| finalizar
    end
```
