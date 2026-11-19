---
type: ADR
title: "ADR 004 — MIRAGE fora do processo, em ambiente isolado"
description: O MIRAGE roda em ambiente próprio (Python 3.10, CUDA) fora do pacote; o projeto só consome suas respostas textuais.
tags:
- adr
- mirage
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:34:40-03:00"
evidence_basis: [approved, verified, hypothesis]
---

# ADR 004 — MIRAGE fora do processo, em ambiente isolado

- **Status:** Aceito (decisões do usuário em 17/11/2026; registrado em ADR em 18/11/2026)

## Contexto

Verificado nas fontes oficiais em 17/11/2026 ([MIRAGE](../references/mirage.md)): o MIRAGE exige CUDA, Python ≤ 3.11, `pydantic<2` e `torch 2.1.2`, e os pesos ocupam cerca de 18,4 GB. O projeto usa Python 3.12 e Pydantic 2. A máquina local não tem GPU NVIDIA.

## Decisão

- O MIRAGE roda **fora do processo** do projeto, num ambiente próprio (conda, Python 3.10), numa máquina com GPU.
- A prova de conceito fica em `experiments/mirage/`, isolada do pacote; o `run_poc.py` usa só a biblioteca padrão e é compatível com Python 3.10.
- O desenvolvimento no pacote usa simuladores (`FakeAnswerer`).
- A execução real, a instalação de dependências e o download de pesos exigem aprovação.

## Alternativas consideradas

- Instalar o MIRAGE no ambiente principal: impossível sem quebrar o projeto (`pydantic<2`, `torch 2.1.2`).
- Um detector guiado por texto (OWLv2, Grounding DINO) atrás do `ObjectDetector`: **pendente**, a avaliar se a hipótese do MIRAGE falhar.

## Consequências

- Um `MirageAnswerer` futuro terá de chamar um processo ou serviço externo; o mecanismo **não foi definido**.
- A hipótese de que o MIRAGE gera caixas confiáveis continua **não comprovada**.
- Documentos vivos: [MIRAGE](../references/mirage.md), [mecanismos transitórios](../references/transitional-mechanisms.md), invariantes I13–I14 em [invariantes](../references/invariants.md).
- Origem: [log](../log.md), 17/11/2026, "Decisões do usuário" e "Pesquisa do MIRAGE".
