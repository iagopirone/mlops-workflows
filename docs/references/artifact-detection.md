---
type: Reference
title: Artefatos de detecção
description: Esquema de detecções, validação, persistência e contratos de coordenadas.
tags:
- detection
- json
- pydantic
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Modelo de dados

Arquivos (commit `b1b3c4f`):
- `artifacts/detection/detection.py`: `Detection`;
- `detection_content.py`: `DetectionContent`;
- `detection_reference.py`: `DetectionReference`.

`Detection(BaseModel)` é **pública**:

| Campo | Tipo | Regra no código |
|---|---|---|
| `cls` | `str` | — |
| `conf` | `float \| None` | `Annotated[float, Field(ge=0.0, le=1.0)] \| None`; **obrigatório e sem padrão** (passar `None` explicitamente quando a fonte não tem confiança) |
| `box` | `list[float]` | `Field(min_length=4, max_length=4)`; convenção `[x1, y1, x2, y2]` em pixels da imagem original |

- `Detection` **não** usa `strict=True`, diferente dos artefatos.
- `DetectionContent.data: list[Detection]`; `dematerialize()` grava `json.dumps([d.model_dump() ...], indent=2)` em UTF-8 e cria os diretórios.
- `DetectionReference.materialize()`:
  - exige que o arquivo exista e que o JSON seja uma lista;
  - valida cada item com `Detection.model_validate`.

```json
[
  {"cls": "RBC", "conf": 0.94, "box": [10.0, 20.0, 65.0, 80.0]},
  {"cls": "WBC", "conf": 0.88, "box": [110.0, 22.0, 180.0, 105.0]}
]
```

## Invariantes semânticos

- O modelo **não** garante `x2 > x1`, `y2 > y1`, valores finitos nem caixas dentro da imagem.
- O `YoloDetector` garante essas condições na própria saída: recorta aos limites, descarta caixas sem área e valores não finitos.
- O `TextDetectionParser` também garante essas condições: rejeita valores não finitos e caixas fora de ordem ou fora dos limites.

## Organização dos arquivos

Foi discutido mover `Detection` para `detection_content.py`. A mudança **não foi aplicada**, e `Detection` continua em `detection.py`, importada por 6 módulos.

## Confiança ausente (aplicado em 17/11/2026)

- **O que mudou:** `conf` passou a aceitar `None`, gravado como `"conf": null` no JSON.
- **Por quê:** detecções vindas de texto, como as do MIRAGE, não têm uma confiança calibrada, e **inventar um valor é proibido**.
- **Compatibilidade:**
  - o YOLO sempre preenche `conf`;
  - os JSONs antigos continuam válidos;
  - o fluxo real foi revalidado (17 detecções idênticas).
- **Visualizador:** sem confiança, o rótulo mostra só `cls`.

Testes em `tests/unit/artifacts/detection/`: `test_detection.py` (3, modelo `Detection`), `test_detection_content.py` (17, validação de `data` e gravação do JSON, lido direto com `json`, sem `materialize()`) e `test_detection_reference.py` (7, leitura e ida e volta), separados em 19/11/2026. Veja [interpretação de texto](component-text-detection-parsing.md).
