---
type: Reference
title: Qwen3-VL-2B-Instruct (GGUF) com llama.cpp — experimento local
description: Como o Qwen3-VL-2B Q4_K_M roda isolado em CPU com llama.cpp, o limite de memória, a convenção de coordenadas verificada, o adaptador para DetectionContent e os limites observados.
tags:
- qwen3-vl
- llama.cpp
- experiment
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T15:36:19-03:00"
evidence_basis: [verified, hypothesis]
---

# Situação

**Experimental, em `experiments/qwen3vl/`, separado do Florence-2. Nenhum componente de produção foi alterado.** Primeira execução real em 18/11/2026: [relatório](../reports/2026-11-18-qwen3vl-cpu-poc.md).

## Isolamento e procedência

- **Runtime:** binário oficial do llama.cpp `b12119` (só CPU, digest conferido), em `experiments/qwen3vl/bin/`. Não há Python de terceiros: o `run_qwen.py` usa só a biblioteca padrão.
- **Pesos:** só `Qwen3VL-2B-Instruct-Q4_K_M.gguf` e `mmproj-Qwen3VL-2B-Instruct-F16.gguf`, do repositório oficial `Qwen/Qwen3-VL-2B-Instruct-GGUF`, revisão `52d6c8ff…`. Os hashes são conferidos antes de cada execução.
- **Teto de memória obrigatório:** o `run_qwen.py` **recusa rodar** fora de um escopo com `MemoryMax` e `MemorySwapMax=0`. Comando: `systemd-run --user --scope -p MemoryMax=3584M -p MemorySwapMax=0 -- /usr/bin/python3 experiments/qwen3vl/run_qwen.py ...`.
- **`-c 4096` obrigatório:** com o padrão do llama.cpp, o cache KV seria dimensionado para 256K tokens.

Comandos completos no README do experimento (`experiments/qwen3vl/README.md`).

## Convenção de coordenadas

- **Documentada** (cookbook oficial `2d_grounding`): JSON `[{"bbox_2d": [x1, y1, x2, y2], "label": ...}]`, em **escala relativa de 0 a 1000 por eixo**: `x/1000·largura` e `y/1000·altura`.
- **Verificada em 18/11/2026:** valores até x = 980 e y = 999 numa imagem de 640 × 480 descartam pixels, e a caixa convertida envolve o glóbulo branco.
- O adaptador recebe a convenção **explicitamente**: `relative_1000` ou `pixel`.

## Adaptador (`experiments/qwen3vl/qwen_detections.py`)

- **Aceita** um único array JSON, como texto inteiro ou dentro de **um** bloco ```` ```json ````, com objetos de exatamente `bbox_2d` (4 números finitos) e `label` (texto não vazio).
- **Não troca** x1 e x2, **não corta** coordenadas, **não mapeia** rótulos e **não inventa** confiança (`conf=None`). O cookbook oficial troca coordenadas invertidas; aqui elas tornam a resposta inválida.
- **Rejeita a resposta inteira** se algum item for inválido; texto cortado ou malformado é `invalid_output`.
- **`coordinate_evidence`:** registra os máximos de x e y e se eles descartam pixels ou a escala de 0 a 1000. Também lê caixas bem formadas dentro de um JSON quebrado, só como evidência, sem virar detecção.
- O `TextDetectionParser` do MIRAGE **não** é usado nem alterado.

## `render.py` (ambiente do projeto)

1. Confere o SHA-256 da imagem.
2. Para os prompts `ground_*`, converte e desenha com o `DetectionVisualizationComponent` existente.
3. Grava o `summary.json` com os estados: `error`, `text_only` (prompt descritivo), `invalid_output`, `no_detections` ou `detections`.

## Testes

`experiments/qwen3vl/tests/test_qwen_detections.py`: 26 testes sintéticos (adaptador, evidência de coordenadas e `render`), sem carregar o modelo.

```bash
uv run python -m pytest -q experiments/qwen3vl/tests
```

## Limites observados (uma imagem; veja o relatório)

- Rótulos trocados: o glóbulo branco foi chamado de "red blood cell" e de "platelet".
- Repetição e JSON cortado nas respostas longas (greedy, `-n 1024`).
- Plaquetas não localizadas.
- **Aviso do llama.cpp:** o grounding do Qwen-VL precisaria de ≥ 1024 tokens de imagem (`--image-min-tokens 1024`), e a execução usou o padrão. Repetir com 1024 tokens está pendente de decisão, porque aumenta a memória.
