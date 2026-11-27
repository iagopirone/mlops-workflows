---
type: ADR
title: "ADR 012 — Pipeline em pasta própria, imutável e validado na criação"
description: Step e Pipeline vão para mlops_workflows/pipeline/, ficam imutáveis, referenciam dependências por identificador e rejeitam na criação IDs duplicados ou vazios, dependências externas, ciclos e finalização inconsistente.
tags:
- adr
- pipeline
- architecture
- validation
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-26T15:54:23-03:00"
evidence_basis: [approved, verified]
sources:
- id: jira-visres-305
  resource: https://visio-ai.atlassian.net/browse/VISRES-305 (lida em 26/11/2026)
  title: "VISRES-305 — Organizar a definição dos pipelines - Pipeline"
---

# ADR 012 — Pipeline em pasta própria, imutável e validado na criação

- **Status:** Aceito. Implementado e testado em 26/11/2026; decisões 1–7 aprovadas no plano e 8–11 aprovadas pelo usuário em 26/11/2026, junto com a imutabilidade limitada à estrutura. O código aguarda a revisão final do usuário e não foi commitado.
- **Tarefa:** VISRES-305, lida no Jira em 26/11/2026.

## Contexto

- **Tarefa no Jira:**
  - colocar o `Pipeline` numa pasta própria;
  - validar a estrutura: IDs de etapa duplicados, dependências externas ao pipeline e dependências circulares;
  - representar a finalização como uma etapa com pré-requisitos;
  - **critério de conclusão:** pipeline de exemplo com finalização e testes que aceitam a estrutura válida e rejeitam as inconsistências.
- **Código anterior** (`mlops_workflows/domain.py`): `Step` e `Pipeline` eram dataclasses mutáveis, sem nenhuma validação, e `Step.depends_on` guardava objetos `Step`. Nenhum módulo importava `domain.py`.
- **O que o [ADR 001](001-workflow-architecture.md) prevê:**
  - pipelines guardados num repositório e definidos por configuração;
  - coordenação em outra máquina, que troca referências por mensagens;
  - etapas compartilhadas entre execuções, que não podem ser alteradas por nenhuma delas;
  - finalização no mesmo ciclo das outras etapas, cujas dependências garantem que ela seja a última.

## Decisão

**Aprovado pelo usuário em 26/11/2026 (plano da tarefa):**

1. **Pasta própria:** `mlops_workflows/pipeline/`, com:
   - `step.py` (`Step`);
   - `pipeline.py` (`Pipeline`);
   - `invalid_pipeline_error.py` (`InvalidPipelineError`, subclasse de `ValueError`).

   `domain.py` passa a importar `Step` e `Pipeline` de lá. `Event`, `PipelineRepository` e os esqueletos do orquestrador ficam sem alteração.
2. **Dependências por identificador:** `Step.depends_on: tuple[str, ...]`, com os `step_name` das etapas.
3. **Estruturas imutáveis:** `@dataclass(frozen=True)` e tuplas em `depends_on`, `input_artifacts`, `output_artifacts` e `steps`.
4. **Finalização num campo separado:** `Pipeline(pipeline_id, steps, finalization)`.
   - Há exatamente uma finalização, garantida pelo tipo do campo.
   - Ela é um `Step` comum, sem dependentes, e toda etapa de processamento tem caminho até ela.
   - `all_steps` devolve as etapas de processamento seguidas da finalização, para que todas sejam percorridas no mesmo ciclo.
5. **Validação na criação:** um pipeline inválido não chega a existir. As regras recusam:
   - IDs duplicados;
   - dependências externas;
   - ciclos;
   - IDs vazios;
   - autodependência;
   - dependência repetida;
   - ausência de etapas de processamento;
   - dependência da finalização;
   - etapa sem caminho até a finalização.
6. **Pipeline de exemplo só estrutural**, num teste:
   - detecção → visualização + contagem de classes → finalização;
   - usa os componentes reais, com um `FakeDetector`;
   - a finalização usa um componente simulado;
   - nenhum modelo é instanciado e nada é executado.
7. **Sem novas abstrações:** nenhuma classe validadora separada e nenhum componente concreto de finalização. Componentes existentes e esqueletos do orquestrador sem alteração.

**Escolhas de implementação (propostas e aprovadas pelo usuário em 26/11/2026):**

8. **Onde cada regra fica:**
   - as regras que dependem só da etapa (nome vazio, autodependência, dependência repetida) ficam em `Step.__post_init__`, então nem uma etapa isolada pode ser criada inválida;
   - as que dependem do conjunto ficam em `Pipeline.__post_init__`.
9. **Verificações de tipo em tempo de execução, com `TypeError`:**
   - listas no lugar de tuplas (sem isso a imutabilidade do item 3 não valeria);
   - IDs ou dependências que não são texto;
   - itens que não são `Step`.

   Erros de estrutura usam `InvalidPipelineError`.
10. **Só o primeiro problema é informado.** As regras rodam numa ordem fixa, e a primeira que falha gera o erro com **todos** os nomes envolvidos nela. Um problema de um tipo pode esconder outro de tipo diferente, mas a busca de ciclos depende de nomes únicos e de dependências existentes, que são verificados antes.
11. **Dataclass, não Pydantic**, ao contrário do `Event` no mesmo `domain.py`: `Step` guarda uma instância de `Component`, e com Pydantic as exceções levantadas nos validadores chegariam embrulhadas em `ValidationError`.

## Por quê

- **Identificadores em texto:**
  - Com objetos imutáveis, uma etapa só pode citar outra que já exista. Um ciclo seria impossível de montar, e o teste de dependência circular exigido pela tarefa não testaria nada.
  - Com objetos mutáveis, o ciclo só surgiria alterando etapas compartilhadas, o que o ADR 001 proíbe.
  - Texto torna as três verificações da tarefa diretas (ID repetido, ID desconhecido, ciclo) e é serializável para o repositório de pipelines e para a coordenação remota.
- **Imutabilidade (rasa):** a validação só vale enquanto a estrutura não muda. O `frozen` e as tuplas fixam a estrutura validada: nomes, dependências, quais etapas existem e quais artefatos cada uma cita. **Não** fixam os objetos guardados dentro das etapas:
  - `ArtifactReference` aceita atribuição (`validate_assignment=True`, sem `frozen`), então `step.input_artifacts[0].location = "x"` funciona (verificado em 26/11/2026);
  - os componentes têm atributos comuns, como `ClassCountingComponent.classes`, que também podem ser alterados.

  Isso não afeta as regras validadas, mas uma execução ainda pode alterar uma referência ou um componente compartilhado. A preocupação do ADR 001 com etapas compartilhadas **só está resolvida no nível da estrutura**.
- **Validação dentro das classes, não num validador à parte:** as regras são invariantes do próprio `Pipeline`, como a validação Pydantic dos artefatos. Uma classe separada criaria um estado intermediário, de pipeline ainda não validado, sem nenhum uso hoje (YAGNI).
- **Finalização num campo:** fica explícita e tipada, e é impossível ter zero ou duas. "Sem dependentes" e "toda etapa leva a ela" garantem que ela seja a última, como diz o ADR 001.

## Atualização de 26/11/2026 (aprovação do usuário)

- Itens 8–11 aprovados.
- **Imutabilidade limitada à estrutura aprovada para esta etapa**, com a condição de que a limitação fique documentada. Ela está registrada em "Por quê", em "Consequências" e em [pipeline e etapas](../references/pipeline.md#limitações).
- **Achados da revisão final**, só documentados e sem mudança de comportamento:
  - `component` e os itens das tuplas de artefatos não têm o tipo verificado;
  - um `Step` que guarda referências de artefatos não pode ser usado como chave de `dict` ou `set` (`hash` falha, porque as referências Pydantic não são *hashable*);
  - nomes não são normalizados: `"a"` e `" a"` são etapas diferentes.
- A docstring de `Step` foi corrigida para dizer que só a estrutura é imutável.

## Atualização de 26/11/2026 (ajuste pedido na revisão final)

- O usuário aprovou a arquitetura e pediu um ajuste: o `Step` agora verifica que `component` é uma instância de `Component` e que todos os itens de `input_artifacts` e `output_artifacts` são `ArtifactReference`, levantando `TypeError` (convenção do item 9).
- Isso resolve o primeiro achado da revisão final.
- **Mantidos por decisão do usuário:**
  - imutabilidade só da estrutura;
  - sem normalizar nomes;
  - `Step` sem `hash`;
  - sem validar a ligação entre as saídas e as entradas das etapas.
- +4 testes em `tests/unit/pipeline/test_step.py`.

## Consequências

- **Mudou o contrato:** `Step.depends_on` era `list[Step]` e passou a `tuple[str, ...]`. Como ninguém usava `domain.py`, nenhum outro código precisou mudar.
- **O que continua sem regra** (decisões pendentes do ADR 001):
  - quantas entradas e saídas uma etapa precisa ter (`0..*` × `1..*`): coleções vazias são aceitas;
  - qual saída alimenta cada entrada: as dependências dizem a ordem, não o fluxo de artefatos.
- **O que não existe ainda:**
  - o componente concreto de finalização;
  - o `StepSelector` e o `WorkflowRunner`.
- **Recursão no ciclo:** a busca de ciclos é recursiva. Pelo limite padrão de recursão do Python, uma cadeia de dependências muito longa (da ordem de mil etapas) deve falhar. Isso é **hipótese**, não testada.
- **Imutabilidade rasa:** referências de artefatos e componentes dentro das etapas continuam mutáveis (veja "Por quê").
- **Detalhes:** [Pipeline e etapas](../references/pipeline.md).
