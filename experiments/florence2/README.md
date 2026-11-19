# Florence-2-base-ft — prova de conceito local em CPU

Experimento isolado, **sem alterar componentes de produção**. Resultados e análise: `docs/reports/2026-11-18-florence2-cpu-poc.md`; referência: `docs/references/florence2.md`.

## Ambiente isolado

- `venv` próprio em `experiments/florence2/.venv` (Python 3.12), criado com o `uv`. O `.venv` principal não é tocado.
- Versões fixadas em `requirements.txt`; versões exatas instaladas em `requirements.lock.txt`. O `torch` é **só CPU**, do índice oficial do PyTorch.
- Modelo: `microsoft/Florence-2-base-ft`, revisão `f6c1a25888ffc1d945ee8a1a77ac833c7303d46e`.
  - Só a lista explícita de arquivos, em `models/Florence-2-base-ft/`.
  - O `pytorch_model.bin` (pickle) **não** é baixado; os pesos vêm do `model.safetensors`.
- O código remoto (`trust_remote_code=True`) foi revisado antes do uso. O `run_florence.py` **recusa** rodar se o SHA-256 do código ou dos pesos mudar.
- `.venv/`, `models/` e `outputs/` estão no `.gitignore` desta pasta.

```bash
uv venv experiments/florence2/.venv --python 3.12
uv pip install --python experiments/florence2/.venv/bin/python \
  -r experiments/florence2/requirements.txt \
  --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
  --index-strategy unsafe-best-match
# Download dos arquivos (revisão fixada, lista explícita): veja docs/references/florence2.md
```

## Executar (da raiz do repositório)

```bash
# 1. Inferência real, no venv isolado, sem rede:
HF_HUB_OFFLINE=1 experiments/florence2/.venv/bin/python experiments/florence2/run_florence.py \
  --image /home/visioer/Downloads/BloodImage_00236.jpg \
  --output-dir experiments/florence2/outputs/<run-id>
# 2. Conversão e visualização, no ambiente do projeto (componentes existentes):
uv run python -m experiments.florence2.render --run-dir experiments/florence2/outputs/<run-id>
# Testes (sem carregar o modelo):
uv run python -m pytest -q experiments/florence2/tests
```

## Ajustes de compatibilidade com o `transformers` 4.55.4

Os dois ajustes são registrados no `run.json`. Nenhum altera o código do modelo:

- **`attn_implementation="eager"`:** sem ele, o carregamento falha com `AttributeError: '_supports_sdpa'`.
- **`use_cache=False` no `generate`:** sem ele, a geração falha com `KeyError: 'Cache only has 0 layers'`. A primeira tentativa, que falhou assim, está preservada em `outputs/2026-11-18-attempt1-cache-error/`.

## Saídas (`outputs/<run-id>/`)

- `run.json`: modelo, revisão e hashes, imagem (dimensões, SHA-256, EXIF), parâmetros, versões, tempos, memória, e por tarefa o prompt, a saída bruta e a saída estruturada do processador.
- `task-N-raw.txt`: o texto bruto gerado.
- `summary.json`, `task-N-detections.json` e `task-N-annotated.png`: gerados pelo `render.py`.
- `SHA256SUMS`: hashes de tudo.
