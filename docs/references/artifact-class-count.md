---
type: Reference
title: Artefato de contagem de classes
description: ClassCount, ClassCountContent e ClassCountReference — esquema, validações de consistência e persistência em JSON da saída do ClassCountingComponent.
tags:
- artifacts
- counting
- json
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-23T13:24:49-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d3c737c + alterações não commitadas), inspecionado e testado em 23/11/2026
  title: Código, testes e execuções locais
---

# Artefato de contagem de classes

Pasta: `mlops_workflows/artifacts/class_count/` (não commitado). Produzido pelo [ClassCountingComponent](component-class-counting.md). Por que existe um tipo novo: [ADR 011](../adr/011-class-counting-component.md).

## Classes

| Classe | Arquivo | Papel |
|---|---|---|
| `ClassCount` | `class_count.py` | Modelo Pydantic (`strict`, `extra="forbid"`) com a contagem e as regras de consistência |
| `ClassCountContent` | `class_count_content.py` | `data: ClassCount`; `dematerialize(reference)` grava JSON UTF-8 (indentado, com quebra de linha final), cria as pastas e devolve o local |
| `ClassCountReference` | `class_count_reference.py` | `materialize()` lê o JSON com `ClassCount.model_validate_json` (**revalida** tudo) e devolve um `ClassCountContent`; `FileNotFoundError` se o arquivo não existir |

Mesmo padrão do [relatório de execução](artifact-execution-report.md).

## Esquema

| Campo | Tipo | Significado |
|---|---|---|
| `classes` | `list[str] \| null` | Domínio configurado; `null` = modo genérico |
| `counts` | `dict[str, int ≥ 0]` | Classes contabilizadas |
| `total` | `int ≥ 0` | Soma de `counts` |
| `excluded` | `dict[str, int ≥ 1]` | Classes detectadas fora do domínio |
| `detection_count` | `int ≥ 0` | Detecções recebidas |

## Regras de consistência (validadas na criação e na leitura)

- `total == soma(counts)`.
- `detection_count == total + soma(excluded)`.
- Modo genérico (`classes: null`): `excluded` vazio e nenhuma contagem zero em `counts` (só aparecem classes detectadas).
- Modo restrito: `classes` sem repetições; as chaves de `counts` são **exatamente** `classes`, na mesma ordem; nenhuma chave de `excluded` está em `classes`.
- Tipos estritos: `"2"` não vira `2`, tupla não vira lista, campo desconhecido é rejeitado.
- Os nomes das classes são guardados como recebidos.

A ordem das chaves é preservada no JSON e na leitura.

## Testes (verificados em 23/11/2026)

`tests/unit/artifacts/class_count/`, um arquivo por classe:

- `test_class_count.py` (15): modos genérico, restrito e vazio aceitos; 11 combinações inconsistentes rejeitadas; tipos estritos e campo extra.
- `test_class_count_content.py` (3): `data` precisa ser `ClassCount`; grava todos os campos, na ordem, criando pastas; grava `classes: null`.
- `test_class_count_reference.py` (6): ida e volta nos três modos, preservando a ordem; arquivo ausente; arquivo inconsistente rejeitado na leitura; `name`/`location` vazios.

## Limitações

- Não guarda de qual `DetectionReference` veio a contagem; quem chama conhece a ligação.
- Não guarda a imagem nem as caixas: só números por classe.
- **Chave repetida no JSON é aceita na leitura** (o último valor vence) quando as somas batem. O componente nunca grava chaves repetidas; só um arquivo editado à mão ou corrompido chega a esse caso. Não corrigido por decisão do usuário (23/11/2026, [ADR 011](../adr/011-class-counting-component.md#atualização-de-23112026-revisão-do-usuário)).
- **`ClassCount` é mutável depois de criado**, sem revalidação na atribuição, como o `ExecutionReport` e o `Detection`; a leitura revalida. Mantido por decisão do usuário (23/11/2026).
