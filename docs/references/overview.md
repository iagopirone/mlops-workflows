---
type: Reference
title: Visão geral do mlops-workflows
description: Propósito, objetivos, escopo e casos de uso do repositório.
tags:
- project
- overview
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: repo-snapshot
  resource: https://github.com/iagopirone/mlops-workflows/tree/666fbb5a210a3cc4143e745bce888eebfe8dc2b2
  title: Snapshot da branch feature/implementar-componentes em 09/11/2026 (commit
    666fbb5)
- id: conversation
  resource: Relatos de desenvolvimento e saídas de terminal fornecidos pelo usuário
    nesta conversa, 10–16/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Visão geral

`mlops-workflows` é um projeto Python para organizar processamento e inferência de ML em componentes intercambiáveis, conectados por **referências e conteúdos de artefatos**. A finalidade é permitir pipelines reproduzíveis e extensíveis sem acoplar o orquestrador a um modelo específico.

- Repositório: https://github.com/iagopirone/mlops-workflows
- Linguagem: Python; gerenciador de ambiente/dependências: `uv`.
- Bibliotecas principais (conferidas no `pyproject.toml` em 18/11/2026): `pydantic`, `numpy`, `opencv-python-headless`, `onnxruntime`.
- Ferramentas de qualidade: `pytest`, `ruff`, `pre-commit`.
- Casos exercitados: detecção de células sanguíneas com YOLO ONNX; persistência JSON; geração de imagens anotadas.

## Objetivos arquiteturais

1. Separar **referência ao dado** de **dado materializado**.
2. Definir um contrato comum para componentes (`prepare`, `execute`).
3. Isolar a implementação de detectores por trás de abstração (`ObjectDetector`).
4. Reutilizar componentes, incluindo visualização de detecções de diferentes algoritmos.
5. Testar módulos isoladamente e combinados, com simuladores e com um modelo real.
6. Documentar continuamente o que foi implementado, decidido e descoberto (veja `CLAUDE.md` e [handoff](../handoff.md)).

## Estado observado (17/11/2026)

- A documentação foi sincronizada com o checkout local, que é a fonte de verdade.
- O estado detalhado está em [estado do projeto](status.md) e o contexto de continuidade em [handoff](../handoff.md).
- **Desafio atual:** integrar o MIRAGE. O objetivo final é imagem + prompt → MIRAGE → resposta textual → JSON de detecções → imagem com bounding boxes.
- **Já existe:** um componente VQA experimental, testado com simulador.
- **Ainda não aconteceu:** o MIRAGE real **nunca foi executado**, e a geração de caixas confiáveis é **hipótese**.

Consulte também a [arquitetura](contracts.md) e a [proveniência](provenance.md).
