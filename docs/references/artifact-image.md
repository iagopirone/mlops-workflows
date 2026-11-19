---
type: Reference
title: Artefatos de imagem
description: Persistência de pixels BGR com validação e OpenCV.
tags:
- image
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

> **Conferido no código em 18/11/2026** (`artifacts/image/image_reference.py`, `image_content.py`, e a cópia do array em `detection_visualization_component.py`). A página nasceu do snapshot de 09/11/2026.

**`ImageReference`** (`artifacts/image/image_reference.py`): recebe `name` e `location`; `materialize()` verifica caminho, executa `cv2.imread()` e retorna `ImageContent`.

**`ImageContent`** (`artifacts/image/image_content.py`): contém `data: np.ndarray`; rejeita array vazio; `dematerialize(reference)` cria diretório de destino quando preciso e salva via `cv2.imwrite()`.

## Contrato e convenções

- A imagem carregada por `cv2.imread` usa ordem de canais **BGR** (não RGB).
- A classe de conteúdo habilita tipos arbitrários do Pydantic para `np.ndarray`.
- É lançada exceção caso o arquivo não exista, não possa ser lido, o array esteja vazio ou OpenCV não consiga gravar o arquivo.
- O componente de visualização copia o array para não modificar o original.

## Exemplo de uso

```python
ref = ImageReference(name="original", location="/path/to/image.jpg")
image_content = ref.materialize()
assert image_content.data.ndim == 3
```

Não pressupor que uma validação de `ImageContent` sozinha certifique todos os requisitos de um modelo (dtype, canais, dimensões); verificações adicionais ficam com detectores/componentes.
