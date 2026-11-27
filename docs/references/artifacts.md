---
type: Reference
title: Modelo de artefatos
description: Abstrações, formatos e matriz de tipos de artefato.
tags:
- artifacts
- pydantic
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

# Organização

O par `Reference` / `Content` encapsula localização, carregamento, representação e persistência.

| Formato | Reference | Content | Dados na memória | Saída |
|---|---|---|---|---|
| Imagem | `ImageReference` | `ImageContent` | `np.ndarray` BGR | Arquivo de imagem via OpenCV |
| Vídeo | `VideoReference` | `VideoContent` | `list[np.ndarray]` + `fps` | `.avi` / `.mp4` sem áudio |
| Detecções | `DetectionReference` | `DetectionContent` | `list[Detection]` | JSON |
| Texto | `TextReference` | `TextContent` | `str` | UTF-8 |
| Contagem de classes | `ClassCountReference` | `ClassCountContent` | `ClassCount` (Pydantic) | JSON UTF-8 ([detalhes](artifact-class-count.md), desde 23/11/2026) |
| Relatório de execução | `ExecutionReportReference` | `ExecutionReportContent` | `ExecutionReport` (Pydantic) | JSON UTF-8 ([detalhes](artifact-execution-report.md), desde 18/11/2026) |

## Responsabilidades

- `Reference`: identifica o artefato e implementa `materialize()`.
- `Content`: representa os dados e implementa `dematerialize(reference)`.
- A validação usa Pydantic e regras específicas do formato.

## Exemplo

```python
ref = TextReference(name="prompt", location="outputs/prompt.txt")
TextContent(data="Detect objects in this image").dematerialize(ref)
restored = ref.materialize()
assert restored.data == "Detect objects in this image"
```

Conferido no código local em 18/11/2026: imagem e vídeo (`artifacts/image/`, `artifacts/video/`); texto e detecção foram verificados no código e nos testes em 17/11/2026. A página nasceu do snapshot de 09/11/2026 e de relatos (valores antigos em [proveniência](provenance.md)).
