---
type: Reference
title: Artefatos de vídeo
description: Carregamento e salvamento de frames de vídeo sem trilha de áudio.
tags:
- video
- opencv
- artifact
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), conferido em 18/11/2026
  title: Código local
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Classes

> **Conferido no código em 18/11/2026** (`artifacts/video/video_reference.py`, `video_content.py`). A página nasceu do snapshot de 09/11/2026.

- `VideoReference.materialize()` usa `cv2.VideoCapture`, lê frames em BGR, obtém FPS e retorna `VideoContent`.
- `VideoContent` contém `data: list[np.ndarray]` (ao menos um frame) e `fps: float` positivo e finito; `validate_frames()` exige frames BGR uint8 não vazios e dimensões uniformes.
- `VideoContent.dematerialize()` grava `.avi` com codec `MJPG` ou `.mp4` com codec `mp4v` via OpenCV, fechando o `VideoWriter` no bloco `finally`.

## Limites

- **Áudio não é preservado** na implementação inspecionada.
- Disponibilidade real de codecs depende da instalação de OpenCV e do sistema operacional.
- `YoloDetector` recebe uma única imagem (`np.ndarray` BGR uint8 de 3 canais); não há componente de detecção em vídeo (conferido em 18/11/2026).

Vídeo é um tipo de artefato genérico no projeto, não evidência de pipeline de detecção em vídeo já implementado.
