---
type: Reference
title: Pipeline e etapas
description: Step e Pipeline em mlops_workflows/pipeline/ — campos, imutabilidade, finalização, regras de validação da estrutura, pipeline de exemplo e testes.
tags:
- pipeline
- architecture
- validation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-26T15:54:23-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/organizar-pipeline (a partir de dd2b50e, alterações não commitadas), inspecionado e testado em 26/11/2026
  title: Código, testes e execuções locais
---

# Pipeline e etapas

Implementado na VISRES-305 (26/11/2026). As decisões e os porquês estão no [ADR 012](../adr/012-pipeline-structure-validation.md), aceito em 26/11/2026. **O código ainda não foi commitado** e aguarda a revisão final do usuário.

Este módulo **define e valida** a estrutura de um pipeline. Ele não executa nada: `StepSelector`, `WorkflowRunner` e os outros elementos do orquestrador continuam como esqueletos em `mlops_workflows/domain.py` ([ADR 001](../adr/001-workflow-architecture.md)).

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `mlops_workflows/pipeline/step.py` | `Step`: uso de um componente no pipeline |
| `mlops_workflows/pipeline/pipeline.py` | `Pipeline`: etapas de processamento + finalização, validadas na criação |
| `mlops_workflows/pipeline/invalid_pipeline_error.py` | `InvalidPipelineError(ValueError)` |
| `mlops_workflows/domain.py` | Importa `Step` e `Pipeline` de `pipeline/`; o resto não mudou |

## `Step`

```python
@dataclass(frozen=True)
class Step:
    step_name: str
    component: Component
    depends_on: tuple[str, ...] = ()
    input_artifacts: tuple[ArtifactReference, ...] = ()
    output_artifacts: tuple[ArtifactReference, ...] = ()
```

- `step_name` identifica a etapa dentro do pipeline.
- `depends_on` lista os `step_name` das etapas que precisam terminar antes desta começar.
- A etapa é imutável **na estrutura**: nome, dependências e as tuplas de artefatos. A imutabilidade é rasa: as referências de artefatos e o componente guardados nela continuam mutáveis (ADR 012).
- **Recusa:**
  - `component` que não é instância de `Component` (`TypeError`);
  - item de `input_artifacts` ou `output_artifacts` que não é `ArtifactReference` (`TypeError`);
  - nome que não é texto (`TypeError`);
  - nome vazio ou em branco (`InvalidPipelineError`);
  - autodependência (`InvalidPipelineError`);
  - dependência repetida (`InvalidPipelineError`);
  - lista no lugar de tupla (`TypeError`);
  - dependência que não é texto (`TypeError`).

## `Pipeline`

```python
@dataclass(frozen=True)
class Pipeline:
    pipeline_id: str
    steps: tuple[Step, ...]
    finalization: Step
```

- `steps` contém as etapas de processamento; `finalization` é a etapa de finalização, um `Step` comum.
- `all_steps` devolve `(*steps, finalization)`.
- **Regras verificadas na criação, nesta ordem.** A primeira que falhar gera o erro, com os nomes envolvidos.

| # | Regra | Exemplo de mensagem |
|---|---|---|
| 1 | `steps` é tupla de `Step` e `finalization` é `Step` (`TypeError`) | `Expected a tuple of steps.` |
| 2 | `pipeline_id` é texto (`TypeError`) e não vazio | `The pipeline id must not be empty.` |
| 3 | Pelo menos uma etapa de processamento | `The pipeline needs at least one processing step.` |
| 4 | Nomes únicos, inclusive o da finalização | `Duplicated step names: a.` |
| 5 | Toda dependência existe no pipeline | `Dependencies outside the pipeline: b -> missing.` |
| 6 | Nenhuma etapa depende da finalização | `Steps depending on the finalization: b.` |
| 7 | Sem ciclos | `Circular dependency: a -> c -> b -> a.` |
| 8 | Toda etapa de processamento tem caminho até a finalização | `Steps without a path to the finalization: c.` |

- As regras 6 e 8 juntas garantem que a finalização seja a **última** etapa e espere todas as outras.
- A regra 8 também recusa uma finalização sem pré-requisitos.

**O que não é verificado:**
- quantidade mínima de entradas e saídas de cada etapa;
- ligação entre a saída de uma etapa e a entrada de outra;
- tipo concreto do componente de finalização.

Esses pontos continuam em aberto no ADR 001.

## Limitações

Aprovadas ou registradas pelo usuário em 26/11/2026 (ADR 012):

- **Imutabilidade só da estrutura.** Nome, dependências, lista de etapas e as tuplas de artefatos não mudam. Mas:
  - as referências de artefatos aceitam atribuição, então `step.input_artifacts[0].location = "x"` funciona;
  - os atributos dos componentes também podem ser alterados, como `ClassCountingComponent.classes`.

  Uma execução ainda pode alterar uma referência ou um componente compartilhado.
- **Sem `hash` com artefatos:** um `Step` que guarda referências de artefatos não pode ser chave de `dict` ou `set`. Um futuro `StepSelector` deve acompanhar as etapas pelo `step_name`.
- **Nomes não normalizados:** `"a"` e `" a"` são etapas diferentes.
- **Busca de ciclos recursiva:** em cadeias muito longas, da ordem de mil etapas, deve falhar. Isso é **hipótese**, não testada.

## Pipeline de exemplo

Definido em `tests/unit/pipeline/test_example_pipeline.py` (`build_example_pipeline`). Ele só é construído e validado: nada é executado e nenhum arquivo é lido ou gravado.

```text
detect ──┬──> visualize ──┐
         └──> count ──────┴──> finalize
```

| Etapa | Componente | Entradas | Saídas |
|---|---|---|---|
| `detect` | `ObjectDetectionComponent(FakeDetector())` | imagem | detecções |
| `visualize` | `DetectionVisualizationComponent` | imagem, detecções | imagem anotada |
| `count` | `ClassCountingComponent(["RBC", "WBC", "Platelets"])` | detecções | contagem |
| `finalize` | componente simulado (não existe finalização concreta) | imagem anotada, contagem | — |

## Testes (verificados em 26/11/2026)

| Arquivo | Testes | O que cobre |
|---|---:|---|
| `tests/unit/pipeline/test_step.py` | 16 | campos e padrões; `component` que não é `Component`; artefatos que não são `ArtifactReference` (cada campo e tupla mista); nome que não é texto; nome vazio; autodependência; dependência repetida; listas; dependência que não é texto; imutabilidade |
| `tests/unit/pipeline/test_pipeline.py` | 19 | pipelines sequencial, paralelo e indireto aceitos; cada regra da tabela; imutabilidade |
| `tests/unit/pipeline/test_example_pipeline.py` | 2 | exemplo aceito; finalização depende das etapas que produzem as saídas finais |

`tests/unit/pipeline/conftest.py` fornece um `PlaceholderComponent`, que só preenche o campo `component`.
