---
type: ADR
title: "ADR 009 — Relatório de execução como artefato tipado"
description: O relatório dos pipelines de ponta a ponta é um artefato ExecutionReportReference/ExecutionReportContent que exige a identidade de modelos reais e separa falha de infraestrutura, resposta inválida e detecções produzidas.
tags:
- adr
- artifacts
- report
- e2e
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T13:51:08-03:00"
evidence_basis: [approved, verified]
---

# ADR 009 — Relatório de execução como artefato tipado

- **Status:** Aceito (decisão E6 do usuário em 18/11/2026); implementado e testado com dados sintéticos.
- **Plano:** [pipelines com modelos reais](../plans/2026-11-18-plan-real-models-e2e.md)

## Contexto

- Os dois pipelines de ponta a ponta (YOLO real e MIRAGE real) precisam de um relatório persistido, com resultados **exclusivamente de modelos reais**, entradas, saídas, métricas, erros, tempos e evidências.
- O usuário pediu que o relatório siga `ArtifactReference`/`ArtifactContent` e que possa ser persistido e recuperado.
- Também pediu para separar **falha de infraestrutura**, **resposta inválida** e **detecções incorretas**.

## Decisão

1. Novo tipo de artefato em `mlops_workflows/artifacts/report/`:
   - `ExecutionReport` (Pydantic, `strict`, `extra="forbid"`): `run_id`, `created_at` (com fuso), `environment`, `models`, `pipelines`, `evaluations`, `deviations`;
   - `ExecutionReportContent.dematerialize(reference)`: grava JSON UTF-8;
   - `ExecutionReportReference.materialize()`: lê e **revalida** o JSON.
2. **Identidade de modelo obrigatória** (`ModelIdentity`): `kind` só admite modelos reais (`onnx_object_detector`, `mirage_official`), e `source` e `revision` não podem ser vazios. Pelo menos um modelo; chaves únicas; cada pipeline só usa um modelo do seu tipo (`yolo` → ONNX, `mirage` → MIRAGE oficial). Um simulador não tem como ser registrado.
3. **Status por execução** (`PipelineRun.status`):
   - `infrastructure_failure`: o modelo não rodou ou a saída não pôde ser lida (processo com erro, sem `stdout.txt`, sem marcador `Text Output:`, falha do ONNX);
   - `invalid_response`: o modelo respondeu, mas a resposta não é uma lista de detecções válida para o parser;
   - `succeeded`: detecções produzidas. **Se estão corretas** é medido na avaliação (TP/FP/FN), não no status.

   Uma execução bem-sucedida exige contagem de detecções e nenhum erro; uma falha exige mensagem de erro e nenhuma contagem.
4. Imagens e detecções **não** são embutidas: o relatório guarda `{kind, name, location}` e cada arquivo é recuperado pela sua própria referência (`ImageReference`, `DetectionReference`, `TextReference`).

## Por quê

- **Tipagem:** um JSON solto (alternativa B) ou um `TextContent` com JSON (alternativa C) não validariam nada. O esquema impede, já na gravação e na leitura, um relatório sem modelo real, um status incoerente ou um campo inesperado.
- **YAGNI:** só os campos pedidos; métricas copiadas do avaliador existente (`summary`, `per_class`), sem recalcular.

## Atualização de 18/11/2026 (decisão Q2 do usuário)

Extensão mínima, sem duplicar a implementação:
- `ModelIdentity.kind` ganha `llamacpp_gguf`; `pipeline` ganha `qwen3vl`, que só aceita modelos `llamacpp_gguf`.
- `Evaluation` ganha `class_aware` (padrão `True`), `subset` (`all_images` ou `valid_responses`; padrão `all_images`) e `confusion` (padrão vazio).
- Os padrões mantêm válidos os relatórios do YOLO e do MIRAGE.
- As verificações de inferência real continuam obrigatórias para qualquer resposta de modelo. A identidade não as substitui.
- +5 testes, 39 no total.
- **Piloto (18/11/2026):** `subset` ganhou `completed_inferences` (exclui só as falhas de infraestrutura; saídas inválidas continuam como falha do modelo). +1 teste, 40 no total.

## Consequências

- `mlops_workflows/artifacts/report/` (3 módulos) e `tests/unit/artifacts/report/test_execution_report.py` (25 testes).
- Os drivers em `experiments/e2e/pipelines.py` devolvem `PipelineRun`. A montagem do relatório completo (CLI) ainda não existe; veja o [plano](../plans/2026-11-18-plan-real-models-e2e.md).
- Documentação: [artefato de relatório](../references/artifact-execution-report.md).
