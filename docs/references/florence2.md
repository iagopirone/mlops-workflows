---
type: Reference
title: Florence-2-base-ft — experimento local
description: Como o Florence-2-base-ft roda isolado em CPU, o formato das suas saídas, o adaptador para DetectionContent, os ajustes de compatibilidade e os limites observados.
tags:
- florence2
- experiment
- detection
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T14:55:00-03:00"
evidence_basis: [verified, hypothesis]
---

# Situação

**Experimental, em `experiments/florence2/`. Nenhum componente de produção foi alterado.** Primeira execução real em 18/11/2026: [relatório](../reports/2026-11-18-florence2-cpu-poc.md).

## Isolamento

- `venv` próprio (`experiments/florence2/.venv`), `torch` só para CPU, versões em `requirements.txt` e `requirements.lock.txt`. O `.venv` principal não é tocado.
- Modelo **local**, revisão fixada, só a lista explícita de arquivos e **sem** o `pytorch_model.bin`:

  ```bash
  experiments/florence2/.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('microsoft/Florence-2-base-ft', revision='f6c1a25888ffc1d945ee8a1a77ac833c7303d46e', local_dir='experiments/florence2/models/Florence-2-base-ft', allow_patterns=['config.json','configuration_florence2.py','modeling_florence2.py','processing_florence2.py','preprocessor_config.json','tokenizer.json','tokenizer_config.json','vocab.json','model.safetensors','LICENSE','README.md'])"
  ```

- A inferência roda com `HF_HUB_OFFLINE=1` e `HF_MODULES_CACHE` dentro do experimento. Os hashes do código remoto revisado e dos pesos são conferidos antes do carregamento.
- Na primeira tentativa, antes de existir o `HF_MODULES_CACHE`, o `transformers` copiou o código remoto para `~/.cache/huggingface/modules/transformers_modules/Florence-2-base-ft/`. É a mesma cópia revisada, fora do repositório.

## Tarefas e formato das saídas

- **Prompts oficiais:**
  - `<OD>`;
  - `<CAPTION_TO_PHRASE_GROUNDING>` + frase (por exemplo, `<CAPTION_TO_PHRASE_GROUNDING>white blood cells`).
- **Saída bruta:** texto com tokens `<loc_N>`, `N` de 0 a 999 (1000 *bins* por eixo).
- **`processor.post_process_generation`:** devolve `{task: {"bboxes": [[x1, y1, x2, y2], ...], "labels": [...]}}` em **pixels da imagem original**, com cada *bin* convertido para o centro: `(N + 0.5) · tamanho / 1000`.
- **Sem confiança.**

## Adaptador (`experiments/florence2/florence_detections.py`)

- **Valida e copia, sem alterar:**
  - estrutura exata;
  - mesma quantidade de caixas e rótulos;
  - 4 números finitos (não booleanos);
  - x1 < x2 e y1 < y2;
  - caixa dentro da imagem;
  - rótulo de texto não vazio.
- **Rejeita a resposta inteira** se algum item for inválido.
- **Não mapeia** rótulos para RBC, WBC ou Platelets.
- `conf=None` sempre.
- **Origem da classe** (`class_source`):
  - `<OD>` → `model`;
  - grounding → `prompt`. No grounding, um rótulo vazio recebe a frase do prompt.
- **Não usa** o `TextDetectionParser` do MIRAGE, que não muda.

## `render.py` (ambiente do projeto)

1. Lê o `run.json` e confere o SHA-256 e o tamanho da imagem.
2. Para cada tarefa, converte com o adaptador, grava um `DetectionReference` e desenha com o `DetectionVisualizationComponent` existente.
3. Grava o `summary.json`, com status `error`, `invalid_output`, `no_detections` ou `detections`, a fração de área de cada caixa (diagnóstico de caixa da imagem inteira) e os hashes.

## Compatibilidade (verificada com `transformers` 4.55.4)

| Problema | Contorno usado |
|---|---|
| `AttributeError: '_supports_sdpa'` ao carregar | `attn_implementation="eager"` |
| `KeyError: 'Cache only has 0 layers'` no `generate` | `use_cache=False` (mais lento) |

**Hipótese:** um `transformers` mais antigo dispensaria os dois contornos. Não testado.

## Testes

`experiments/florence2/tests/test_florence_detections.py`: 19 testes. Cobrem o adaptador e o `render` com execução sintética e não carregam o modelo.

```bash
uv run python -m pytest -q experiments/florence2/tests
```

## Limites observados (uma imagem; veja o relatório)

- O `<OD>` usa vocabulário genérico: rotulou a imagem inteira como "jellyfish".
- O grounding localizou bem o glóbulo branco, mas devolveu a **mesma** caixa para "red blood cells" e "white blood cells".
- Em todas as tarefas apareceu uma caixa da imagem inteira; plaquetas não foram localizadas.
