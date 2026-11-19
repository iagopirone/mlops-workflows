---
type: Reference
title: Testes automatizados
description: Suítes, organização, comandos e resultados reais.
tags:
- tests
- pytest
- quality
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Organização

- **`tests/unit/`:** classes e métodos isolados (Pydantic, arquivos, caixas, erros), com simuladores (`Fake*`) no lugar dos modelos.
- **`tests/integration/`:** artefatos com arquivos reais (`tmp_path`) e componentes encadeados.
- **Teste com ONNX real:** pulado se `DETECTION_MODEL_PATH` e `DETECTION_IMAGE_PATH` não estiverem definidas.
- **Configuração:** `pyproject.toml` define `testpaths = ["tests"]` e `--import-mode=importlib`; não há `__init__.py` nos testes.
- **`tests/unit/scripts/`** (18/11/2026): testes do validador `scripts/okf_lint.py`. Um deles (`test_real_docs_bundle_is_valid`) valida o `docs/` real, então **uma documentação quebrada (link, índice ou frontmatter) faz a suíte falhar**.
- **Regra:** nunca carregar o MIRAGE em testes automatizados. Um teste real futuro deverá ser pulado quando não estiver configurado, como o do ONNX.

## Resultados verificados (18/11/2026)

| Execução | Resultado |
|---|---|
| `uv run python -m pytest -q experiments/mirage/tests` (fora da suíte principal) | **81 passed** (34 do `run_poc` + 47 do avaliador; Python 3.12.14). Eram 69 antes da validação do nome do checkpoint (E3) |
| `uv run --no-project --python 3.10 --with pytest --with "pydantic>=2,<3" python -m pytest experiments/mirage/tests` | **81 passed** (Python 3.10 + Pydantic 2, ambiente temporário do `uv`) |
| `uv run python -m pytest -q experiments/mirage/tests experiments/e2e/tests experiments/florence2/tests` (fora da suíte principal) | **188 passed, 1 skipped** (18/11/2026, noite: 84 + 85 + 19; o skip é o teste do YOLO real, que exige `E2E_ALLOW_REAL_MODELS=1`). Antes, só `experiments/e2e`: **35 passed, 1 skipped** (o skip é o teste com o ONNX real). Uma execução com o ONNX configurado deu 36 passed, mas rodou o YOLO numa etapa em que os modelos não deviam ser executados (registrado no log) |
| `uv run python -m pytest -q -rs` (sem ONNX) | **286 passed, 1 skipped** (18/11/2026, noite). Antes: 277 + 1 skipped. Motivo do skip: `Detection model and image paths are not configured.` |
| Com `DETECTION_MODEL_PATH` e `DETECTION_IMAGE_PATH` | 253 passed antes do artefato de relatório; **não executado** depois, porque esta etapa não autorizou executar modelos |
| `uv run python scripts/okf_lint.py` | `OK: no problems found.` |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 134 files already formatted (inclui `experiments/`, `scripts/` e os blocos Python dos `.md`) |

A contagem por arquivo está em [status](status.md#resultados-de-testes-por-arquivo-17112026-validador-acrescentado-em-18112026).

## Evolução da contagem

| Data | Total | Mudança |
|---|---:|---|
| 16/11/2026 (relato) | 92 | Suíte com texto, visualizador e integração com `FakeDetector` |
| 17/11/2026 | 92 | Refatoração do visualizador: 6 testes adaptados ao novo contrato, sem testes novos |
| 17/11/2026 | 102 | +10 do VQA (1 da interface, 8 do componente, 1 de integração) |
| 17/11/2026 | 171 | +69 do parser de texto: 55 do parser, 7 do componente, 2 de integração, +4 de `Detection` e +1 do visualizador |
| 17/11/2026 | 218 | +47 de regressão P1–P3: +44 do parser e +3 do componente |
| 18/11/2026 | 250 | +32 do validador da documentação (`tests/unit/scripts/test_okf_lint.py`), incluindo um teste que valida o `docs/` real |
| 18/11/2026 (tarde) | 253 | Validador com links relativos (ADR 008): 3 testes trocados e 3 novos, 35 no total |
| 18/11/2026 (tarde) | 278 | +25 do artefato de relatório (`tests/unit/artifacts/report/`). Fora da suíte: +12 do `run_poc` (81) e +36 de `experiments/e2e/` |
| 18/11/2026 (noite) | 287 | +9 do artefato de relatório (34 no total). Fora da suíte: `run_poc` 37, `experiments/e2e` 86, `experiments/florence2` 19 |
| 18/11/2026 (noite, Qwen3-VL) | 287 | Suíte principal inalterada. Fora da suíte: +26 de `experiments/qwen3vl` |
| 18/11/2026 (Fase 1 BCCD) | 292 | +5 do relatório (Qwen, avaliação). Fora da suíte: `experiments/mirage` 168 (+84, pareamento ótimo), `experiments/e2e` 105 (+19), `experiments/qwen3vl` 39 |
| 18/11/2026 (piloto BCCD) | 293 | +1 do relatório (`completed_inferences`). Fora da suíte: `experiments/e2e` 107 (+1 `draw_ground_truth`, +1 `completed_inferences`) |

## Casos cobertos nos componentes recentes

- **Visualizador:**
  - `prepare()` retorna `ImageContent` e `DetectionContent`;
  - desenho e pixel verde;
  - imagem original preservada;
  - zero detecções;
  - `prepare()` e `execute()` rejeitam entradas inválidas (incluindo dados crus no lugar de conteúdos).
- **VQA:**
  - interface abstrata;
  - `prepare()` retorna conteúdos e rejeita entradas inválidas;
  - pixels e pergunta são repassados;
  - resposta UTF-8 salva;
  - imagem protegida contra um answerer que a altera;
  - prompt vazio, resposta que não é texto e falha de inferência não geram saída;
  - integração com arquivos reais.

## Comandos

```bash
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest -q -rs
DETECTION_MODEL_PATH="/caminho/best.onnx" \
DETECTION_IMAGE_PATH="/caminho/exemplo.jpg" \
uv run python -m pytest -q -rs
```

- **Parser de texto e componente:** só JSON; `[]` versus resposta malformada; três convenções de coordenadas; números não finitos; ordem e limites; rejeição total; `conf=None`; nenhum arquivo parcial. Detalhes em [interpretação](component-text-detection-parsing.md#testes-verificados-em-17112026).
- **Integração completa simulada:** `FakeAnswerer` → VQA → parser → visualizador (`tests/integration/components/text_detection_parsing/`).
