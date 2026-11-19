---
type: Reference
title: Artefatos de texto
description: Representação de prompts e respostas textuais como artefatos UTF-8.
tags:
- text
- utf8
- prompt
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

# `TextContent` (`artifacts/text/text_content.py`, não commitado)

`data: str`. O `dematerialize(reference)` cria os diretórios, grava com `Path.write_text(..., encoding="utf-8")` e retorna a localização. Aceita texto vazio.

# `TextReference` (`artifacts/text/text_reference.py`, não commitado)

`materialize()` exige que o caminho seja um arquivo (senão gera `FileNotFoundError`) e lê como UTF-8. Bytes inválidos geram `UnicodeDecodeError`. Retorna `TextContent`.

## Uso atual

- **Prompt** de entrada do `VisualQuestionAnsweringComponent`.
- **Resposta textual** de saída do mesmo componente.
- Os prompts circulam como artefatos, não como strings soltas entre componentes.

## Testes (verificados em 17/11/2026)

`tests/unit/artifacts/text/test_text_content.py` e `test_text_reference.py` (separados em 19/11/2026), 7 passed:
- round-trip com Unicode;
- texto vazio;
- diretório pai;
- arquivo ausente;
- diretório no lugar do arquivo;
- tipo inválido;
- UTF-8 inválido.
