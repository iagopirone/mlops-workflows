---
type: Reference
title: Referências de código e documentação
description: Relação de fontes úteis para manutenção dos conceitos e guias.
tags:
- references
- links
- tools
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: mirage-repo
  resource: https://github.com/visual-haystacks/mirage
  title: Repositório oficial MIRAGE
- id: okf-spec
  resource: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md
  title: Especificação OKF 0.2
---

# Repositório e decisões

- Código: https://github.com/iagopirone/mlops-workflows
- Branch documentada: `feature/implementar-componentes` (fonte antiga do ZIP).
- ADR: [ADR 001](../adr/001-workflow-architecture.md) (até 18/11/2026 em `docs/ADR-001-workflow-architecture.md`).
- Diagramas: [diagramas](../diagrams/index.md) (até 18/11/2026 em `docs/diagrams/01-flow.mmd`, `02-class-diagram.mmd`, `03-sequence-diagram.mmd`).
- Padrão de documentação: https://github.com/Visio-ai/new-visio-research-models (bundle OKF em `docs/`), adaptado em [diretrizes OKF](okf-guidelines.md).
- PR #3 (aberto, verificado com `gh` em 17/11/2026): https://github.com/iagopirone/mlops-workflows/pull/3

# Modelos e formatos

- MIRAGE: https://github.com/visual-haystacks/mirage
- Checkpoint: https://huggingface.co/tsunghanwu/mirage-llama3.1-8.3B
- Paper (Visual Haystacks, ICLR 2025): https://arxiv.org/abs/2407.13766
- Conjunto de treino: https://huggingface.co/datasets/tsunghanwu/MIRAGE-training-set
- Alternativas para detecção guiada por texto (não avaliadas): OWLv2 (Hugging Face Transformers) e Grounding DINO.
- OKF v0.2: https://github.com/devlooped/okf/blob/main/specs/okf-0.2.md

# Ferramentas

- `uv`: https://docs.astral.sh/uv/
- Ruff: https://docs.astral.sh/ruff/
- pytest: https://docs.pytest.org/
- Pydantic: https://docs.pydantic.dev/
- ONNX Runtime: https://onnxruntime.ai/

Os links externos são indicados para consulta. A origem de cada página (snapshot, relato ou código local) está em [proveniência](provenance.md).
