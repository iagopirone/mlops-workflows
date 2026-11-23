---
type: Playbook
title: Testar e executar localmente
description: Instalação, lint, testes (com e sem ONNX real), testes do experimento, validação da documentação e demo.
tags:
- setup
- python
- uv
- cli
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
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Ambiente

Ambiente verificado em 17/11/2026: Python 3.12.14, uv 0.12.5, numpy 2.5.4, opencv-python-headless 5.0.0.93, onnxruntime 1.31.1, pydantic 2.14.1, pytest 9.1.1, ruff 0.17.0. O `pyproject.toml` informa `requires-python = ">=3.12"` e dependências `numpy`, `onnxruntime`, `opencv-python-headless`, `pydantic` (2.x). O fluxo de trabalho usa `uv` e `pytest`.

## Instalação

```bash
git clone https://github.com/iagopirone/mlops-workflows.git
cd mlops-workflows
uv sync
```

Para trabalhar em branch específica, faça checkout conscientemente e verifique `git status`. Modelos `.onnx` e imagens de teste precisam ser fornecidos localmente; não acompanham necessariamente o repositório.

## Comandos úteis

```bash
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q
uv run python -m pytest -q -rs
```

`ruff format --check .` também verifica blocos de código Python dentro dos `.md` desta documentação. Escreva os exemplos já formatados.

Agentes devem seguir `CLAUDE.md`, na raiz, e começar a sessão por [handoff](../handoff.md).

### Testar o experimento MIRAGE (fora da suíte principal)

```bash
uv run python -m pytest -q experiments/mirage/tests
# Compatibilidade com Python 3.10, sem tocar no .venv:
uv run --no-project --python 3.10 --with pytest --with "pydantic>=2,<3" \
  python -m pytest -q experiments/mirage/tests
```

### Testar os drivers de ponta a ponta (fora da suíte principal)

```bash
uv run python -m pytest -q -rs experiments/e2e/tests
```

O teste com o YOLO real só roda com `DETECTION_MODEL_PATH`, `DETECTION_IMAGE_PATH` **e** `E2E_ALLOW_REAL_MODELS=1`; sem isso, é pulado. O MIRAGE nunca é carregado. Detalhes em [relatório e drivers](../references/artifact-execution-report.md).

### Testar o adaptador do Florence-2 (sem carregar o modelo)

```bash
uv run python -m pytest -q experiments/florence2/tests
```

A inferência real roda num `venv` próprio; veja [Florence-2](../references/florence2.md).

### Testar o adaptador do Qwen3-VL (sem carregar o modelo)

```bash
uv run python -m pytest -q experiments/qwen3vl/tests
```

A inferência real exige o teto de memória; veja [Qwen3-VL](../references/qwen3vl.md).

### Validar a documentação

```bash
uv run python scripts/okf_lint.py
```

O que o validador verifica está em [diretrizes OKF](../references/okf-guidelines.md#validador-local).

### Testar com o ONNX real

```bash
DETECTION_MODEL_PATH="/caminho/para/best.onnx" \
DETECTION_IMAGE_PATH="/caminho/para/imagem.jpg" \
uv run python -m pytest -q -rs
```

Os caminhos são **exemplos**: adaptação à máquina é obrigatória. Última execução verificada (18/11/2026): `277 passed, 1 skipped` sem os caminhos (com o artefato de relatório). Com os caminhos, a última execução foi `253 passed`, antes do artefato. Em 17/11/2026 eram 218 e 217 + 1 skipped; os +35 são os testes do validador. Os testes de `experiments/mirage/tests` rodam à parte: ~~22 passed~~ ~~69 passed~~ **81 passed** desde a validação do nome do checkpoint (18/11/2026); veja [suíte de testes](../references/test-suite.md).

## Demo

```bash
uv run python -m examples.demo_detection \
  --model /caminho/para/best.onnx \
  --image /caminho/para/imagem.jpg \
  --output-dir outputs
```

Contagem de classes a partir de um JSON de detecções de qualquer fonte (não executa modelo; detalhes em [contagem](../references/component-class-counting.md#exemplo-executável)):

```bash
uv run python -m examples.demo_class_counting \
  --detections /caminho/para/detections.json \
  --classes RBC WBC Platelets \
  --output-dir outputs/class_counting
```

Saídas esperadas da demonstração de detecção: JSON de detecções e imagem anotada. Para consumir essas detecções através do novo componente de visualização, ver [demonstração e pipeline](../reports/2026-11-16-yolo-visualization-demo.md).
