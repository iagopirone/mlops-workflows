---
type: Playbook
title: "Criar um tipo de artefato"
description: Passo a passo para adicionar um par Reference/Content novo, seguindo o padrão de TextReference/TextContent.
tags:
- playbook
- artifacts
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [verified]
---

# Criar um tipo de artefato

Modelo real a copiar: `mlops_workflows/artifacts/text/` (o artefato mais simples). Contratos em [contratos](../references/contracts.md) e [ciclo de vida](../references/artifact-lifecycle.md).

## Antes de começar

- Apresente o plano e espere aprovação ([documentar uma mudança](document-a-change.md)).
- Confira se um artefato existente não resolve (YAGNI).

## Passos

1. Crie `mlops_workflows/artifacts/<tipo>/` com `__init__.py`, `<tipo>_content.py` e `<tipo>_reference.py`.
2. **Content:** herda de `ArtifactContent`, declara `data` com o tipo concreto e implementa `dematerialize(reference) -> str`, que grava em `reference.location` (criando as pastas) e devolve o local.
3. **Reference:** herda de `ArtifactReference` e implementa `materialize()`, que lê de `self.location`, lança `FileNotFoundError` se o arquivo não existir e devolve o Content.
4. Não mude `model_config`: as classes base já usam `strict=True`, `extra="forbid"` e `validate_assignment=True`.
5. Testes:
   - unitários em `tests/unit/artifacts/<tipo>/test_<tipo>.py` (validação Pydantic, ida e volta, erros);
   - de integração com `tmp_path` em `tests/integration/artifacts/` quando houver arquivo real;
   - sem `__init__.py` nos testes (o pytest usa `--import-mode=importlib`).
6. Valide com o playbook [testar localmente](test-locally.md).

## Documentar

- Nova página `references/artifact-<tipo>.md` e uma linha em `references/index.md`.
- Atualize [artefatos](../references/artifacts.md), [estrutura do repositório](../references/repository-structure.md), [suíte de testes](../references/test-suite.md), `log.md`, [status](../references/status.md) e `handoff.md`.
