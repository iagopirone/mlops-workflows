# Qwen3-VL-2B-Instruct (GGUF Q4_K_M) — prova de conceito local em CPU com llama.cpp

Experimento isolado, separado do Florence-2. **Nenhum componente de produção foi alterado.** Resultados e análise: `docs/reports/2026-11-18-qwen3vl-cpu-poc.md`. Referência: `docs/references/qwen3vl.md`.

## Ambiente isolado (nada é instalado no sistema nem no `.venv`)

- **llama.cpp:** binário oficial pré-compilado só para CPU, release `b12119` (04/11/2026), commit `6f1e6543704bc5b080c7a98e7b6f707b31f6ed51`, asset `llama-b12119-bin-ubuntu-x64.tar.gz` (SHA-256 `b766529b…`, conferido). Fica em `bin/`.
- **Pesos:** só os 2 arquivos necessários do repositório oficial `Qwen/Qwen3-VL-2B-Instruct-GGUF`, revisão `52d6c8ffea26cc873ac5ad116f8631268d7eb503`, em `models/`:
  - `Qwen3VL-2B-Instruct-Q4_K_M.gguf`: 1 107 409 952 bytes, SHA-256 `089d75c5…`;
  - `mmproj-Qwen3VL-2B-Instruct-F16.gguf`: 819 394 848 bytes, SHA-256 `c3d5afbe…`.

  O `run_qwen.py` recusa rodar se os hashes mudarem.
- **Executor:** `run_qwen.py`, só com a biblioteca padrão, rodado pelo `/usr/bin/python3`.
- `bin/`, `models/` e `outputs/` estão no `.gitignore` desta pasta.

```bash
mkdir -p experiments/qwen3vl/bin experiments/qwen3vl/models
curl -L -o experiments/qwen3vl/bin/llama-b12119-bin-ubuntu-x64.tar.gz \
  https://github.com/ggml-org/llama.cpp/releases/download/b12119/llama-b12119-bin-ubuntu-x64.tar.gz
tar -xzf experiments/qwen3vl/bin/llama-b12119-bin-ubuntu-x64.tar.gz -C experiments/qwen3vl/bin
REV=52d6c8ffea26cc873ac5ad116f8631268d7eb503
for f in Qwen3VL-2B-Instruct-Q4_K_M.gguf mmproj-Qwen3VL-2B-Instruct-F16.gguf; do
  curl -L -o experiments/qwen3vl/models/$f \
    https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF/resolve/$REV/$f
done
```

## Executar (da raiz do repositório)

```bash
# 1. Inferência real, com teto de memória (só o processo é encerrado se passar) e sem swap:
systemd-run --user --scope -p MemoryMax=3584M -p MemorySwapMax=0 -- \
  /usr/bin/python3 experiments/qwen3vl/run_qwen.py \
  --image /home/visioer/Downloads/BloodImage_00236.jpg \
  --output-dir experiments/qwen3vl/outputs/<run-id>
# 2. Conversão e visualização, no ambiente do projeto (componentes existentes):
uv run python -m experiments.qwen3vl.render \
  --run-dir experiments/qwen3vl/outputs/<run-id> --convention relative_1000
# Testes (sem carregar o modelo):
uv run python -m pytest -q experiments/qwen3vl/tests
```

**Parâmetros:**
- `-c 4096` é obrigatório: o padrão (`-c 0`) usaria o contexto de 256K tokens do modelo;
- `--temp 0 --seed 42` (greedy, para reprodutibilidade);
- `-n 1024`;
- `-t 10`.

Os prompts de localização seguem o cookbook oficial `2d_grounding`.

## Saídas (`outputs/<run-id>/`)

- `run.json`: execução, revisões, hashes, comando exato, memória e tempos por prompt.
- `<prompt>.stdout.txt` (resposta original, intacta) e `<prompt>.stderr.txt` (log do llama.cpp).
- `summary.json`, `<prompt>-detections.json` e `<prompt>-annotated.png`: gerados pelo `render.py`.
- `SHA256SUMS`: hashes de tudo.
