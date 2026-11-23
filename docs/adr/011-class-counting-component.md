---
type: ADR
title: "ADR 011 — Componente de contagem de classes e artefato ClassCount"
description: O ClassCountingComponent conta detecções por cls nos modos genérico (None) e restrito (lista), e grava o resultado num artefato tipado ClassCountReference/ClassCountContent.
tags:
- adr
- components
- artifacts
- counting
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-23T13:24:49-03:00"
evidence_basis: [approved, verified]
---

# ADR 011 — Componente de contagem de classes e artefato ClassCount

- **Status:** Aceito. Implementado e testado em 23/11/2026; decisões 5–10 aprovadas pelo usuário em 23/11/2026, depois da revisão do código.
- **Tarefa:** VISRES-337. Os critérios usados foram os colados pelo usuário em 23/11/2026; o Jira não pôde ser lido nesta sessão (conector sem login).

## Contexto

- O projeto precisa contar objetos detectados por classe, a partir das detecções de **qualquer** detector.
- `Component.execute()` devolve `list[ArtifactReference]`: o resultado precisa ser persistido num artefato que outro componente consiga materializar.
- Nenhum artefato existente representa contagens: `DetectionContent` guarda caixas; um `TextContent` com JSON não validaria nada (mesmo argumento do [ADR 009](009-execution-report-artifact.md)).

## Decisão

**Aprovado pelo usuário (critérios da tarefa):**

1. `classes=None` conta todas as classes detectadas; `classes=[]` não contabiliza nenhuma.
2. Classes configuradas sem detecções aparecem com zero.
3. Detecções fora do domínio não entram no total e são registradas à parte (`excluded`).
4. Sem listas de classes embutidas, sem executar ou alterar o detector, sem filtro de confiança, sem normalizar nomes.

**Escolhas de implementação (propostas e aprovadas pelo usuário em 23/11/2026):**

5. Novo par mínimo em `mlops_workflows/artifacts/class_count/`: `ClassCount` (Pydantic estrito), `ClassCountContent` (grava JSON) e `ClassCountReference` (lê com `model_validate_json`, revalidando).
6. Campos: `classes`, `counts`, `total`, `excluded` e `detection_count`. O último permite verificar `total + soma(excluded) == detection_count`.
7. O modelo rejeita contagens incoerentes (somas, chaves fora do domínio, ordem diferente da configurada, exclusões no modo genérico), tanto ao gravar quanto ao ler.
8. Ordem determinística: no modo restrito, a ordem configurada; no genérico, a ordem da primeira ocorrência.
9. O construtor exige `None` ou `list[str]` sem repetições, e copia a lista.
10. A contagem fica num método privado do componente; não foi criada interface de "contador" injetável (YAGNI: uma única implementação, sem modelo envolvido).
11. Nenhum contrato existente foi alterado.

## Por quê

- **Tipagem e validação:** o artefato não pode ser gravado nem lido com números incoerentes.
- **`None` × `[]`:** são intenções diferentes (contar tudo × contar nada) e ficam explícitas no JSON (`null` × `[]`).
- **Sem normalização:** juntar `"RBC"` e `"rbc"` em silêncio esconderia diferenças entre detectores; a exclusão explícita deixa a divergência visível.

## Consequências

- Arquivos e testes listados em [ClassCountingComponent](../references/component-class-counting.md) e [artefato de contagem](../references/artifact-class-count.md).
- Exemplo: `examples/demo_class_counting.py`.
- Grafias diferentes entre detector e domínio resultam em zero + exclusão; um mapeamento de nomes, se for necessário, será outra decisão.

## Atualização de 23/11/2026 (revisão do usuário)

- As decisões 5–10 foram aprovadas: novo artefato, `detection_count`, ordem das classes e método privado de contagem.
- Duas limitações encontradas na revisão ficam **registradas, sem correção nesta tarefa** (decisão do usuário):
  1. **Chave repetida no JSON:** ao ler, `{"RBC": 1, "RBC": 2}` vira `{"RBC": 2}` (o último valor vence). Se as somas baterem, o arquivo é aceito. O componente nunca grava chaves repetidas, então só um arquivo editado à mão ou corrompido chega a esse caso; o `DetectionReference` se comporta igual.
  2. **`ClassCount` mutável:** atribuir um campo depois de criado (por exemplo, `total = 99`) não é revalidado, como no `ExecutionReport` e no `Detection`. A validação volta a rodar na leitura do arquivo.
