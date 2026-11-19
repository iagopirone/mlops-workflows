---
type: Reference
title: Invariantes do projeto
description: Regras rígidas que nenhuma mudança pode violar sem uma decisão nova registrada em ADR.
tags:
- invariants
- architecture
- rules
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified]
---

# Invariantes

Cada regra tem a origem (ADR, decisão no log ou código). Para mudar uma invariante, registre um ADR novo e atualize esta página na mesma mudança.

## Arquitetura

| # | Invariante | Origem |
|---|---|---|
| I1 | Dados trafegam entre componentes como **referências** (`ArtifactReference`) e são carregados como **conteúdos** (`ArtifactContent`). `materialize()` carrega; `dematerialize(reference)` grava e devolve o local | Código (`artifacts/interface.py`, `artifacts/content.py`); [contratos](contracts.md) |
| I2 | `Component.prepare()` devolve **conteúdos de artefatos**, não `.data`; o `.data` só é lido dentro de `execute()`. Exceção conhecida e registrada: `ObjectDetectionComponent` | [ADR 002](../adr/002-prepare-returns-artifact-contents.md) |
| I3 | `Component.execute()` devolve `list[ArtifactReference]` com as saídas gravadas | Código (`components/interface.py`) |
| I4 | Modelos ficam atrás de interfaces injetadas no construtor (`ObjectDetector`, `VisualQuestionAnswerer`); componentes não instanciam modelos | [injeção de dependências](dependency-injection.md) |
| I5 | Testes automatizados usam simuladores (`Fake*`). Modelos reais só em testes pulados quando não configurados (como o ONNX); **o MIRAGE nunca é carregado em testes** | [suíte de testes](test-suite.md) |
| I6 | Classes Pydantic dos artefatos usam `strict=True` e `extra="forbid"` | Código |

## Dados e detecções

| # | Invariante | Origem |
|---|---|---|
| I7 | **Nunca inventar** coordenadas, classes ou confiança para preencher `DetectionContent` | Decisão do usuário (log, 17/11/2026) |
| I8 | `Detection.conf` é `float` entre 0 e 1 **ou** `null`; `null` significa que a fonte não dá confiança | [ADR 003](../adr/003-nullable-detection-confidence.md) |
| I9 | `Detection.box` é `[x1, y1, x2, y2]` em pixels da imagem original | [artefato de detecção](artifact-detection.md) |
| I10 | Imagens são `np.ndarray` em BGR (OpenCV) | [artefato de imagem](artifact-image.md) |
| I11 | Respostas textuais só viram detecções pelo `TextDetectionParser`: JSON puro, convenção de coordenadas explícita, rejeição total se algum item for inválido | [ADR 005](../adr/005-strict-json-text-detection-parsing.md) |
| I12 | Respostas textuais (VQA) e detecções estruturadas são coisas diferentes e ficam em artefatos diferentes (`TextContent` × `DetectionContent`) | Decisão do usuário (log, 17/11/2026) |

## MIRAGE e experimentos

| # | Invariante | Origem |
|---|---|---|
| I13 | O MIRAGE roda **fora do processo** e fora do ambiente principal; suas dependências nunca entram no `pyproject.toml` | [ADR 004](../adr/004-mirage-out-of-process.md) |
| I14 | `experiments/mirage/run_poc.py` usa só a biblioteca padrão e é compatível com Python 3.10 | [ADR 004](../adr/004-mirage-out-of-process.md) |
| I15 | Na avaliação, respostas inválidas ou ausentes contam como FN e **nunca** são excluídas; sem AP/mAP | [ADR 006](../adr/006-offline-detection-evaluation.md) |

## Processo

| # | Invariante | Origem |
|---|---|---|
| I16 | Planejar → aprovação → executar → validar → documentar. Nada de commit, push, reset, clean, rebase ou troca de branch sem autorização | `CLAUDE.md`; [ADR 007](../adr/007-okf-documentation-structure.md) |
| I17 | Não instalar dependências, não baixar pesos e não mudar versões do ambiente sem aprovação | `CLAUDE.md` |
| I18 | Toda etapa atualiza a página técnica, o `log.md`, o `status` e o `handoff.md` | [ADR 007](../adr/007-okf-documentation-structure.md) |
