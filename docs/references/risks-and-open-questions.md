---
type: Reference
title: Riscos e decisões em aberto
description: Riscos técnicos da integração e perguntas pendentes.
tags:
- risks
- decisions
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:28:27-03:00"
evidence_basis: [verified, approved, hypothesis]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado e testado em 17/11/2026
  title: Código, testes e execuções locais
- id: conversation
  resource: Relatos de desenvolvimento e decisões do usuário, 10–17/11/2026
  title: Evidências da conversa de desenvolvimento
---

# Riscos e mitigação

| Risco | Consequência | Ação |
|---|---|---|
| O MIRAGE não localiza objetos com precisão (não há capacidade documentada) | JSON de detecções enganoso | Prova de conceito com IoU contra anotações verdadeiras; marcar como experimental; `conf: null` |
| O MIRAGE ignora o pedido de JSON e responde no formato de colchetes do treino ou com texto em volta | O parser rejeita tudo (só JSON puro, por decisão) | Registrar respostas reais; só depois decidir se aceita outros formatos |
| Coordenadas relativas ao quadrado com padding, não à imagem | Caixas deslocadas | Formato de coordenadas declarado na configuração; conversão testada; confirmar na prova de conceito |
| Dependências do MIRAGE (Python ≤ 3.11, `pydantic<2`, `torch 2.1.2`) | Quebra do ambiente `uv` principal | Ambiente isolado; adaptador fora do processo |
| Sem GPU NVIDIA local | Não dá para rodar o MIRAGE | Desenvolvimento com simuladores; execução real em outro ambiente |
| ~~`run_poc.py` incompatível com Python 3.10~~ | — | Corrigido e validado no 3.10.21 (17/11/2026) |
| Imagem JPEG com rotação EXIF | Coordenadas do MIRAGE (PIL, sem rotação) e do projeto (OpenCV, com rotação) em grades diferentes | O `run_poc.py` recusa a imagem; salvar sem rotação |
| ~~Saída ambígua aceita pelo parser (chaves duplicadas, `cls` com espaços)~~ | — | P1–P2 corrigidos (17/11/2026) |
| Métricas infladas por respostas inválidas excluídas | Precisão espacial do MIRAGE superestimada | O avaliador mantém respostas inválidas e ausentes como FN (testado) |
| Associação errada entre resposta e imagem | IoU calculado contra a imagem errada | `image_id` explícito + `run.json` com uma imagem + checagem de dimensões; abortar em caso de divergência |
| Branch empilhada sobre o PR #3 aberto | Um PR para `rc` incluiria os commits do #3 | Esperar o #3 ser mesclado, ou abrir um PR com base em `feature/implementar-componentes` |
| Pesos com cerca de 18,4 GB / arquivos grandes no Git | Repositório inchado | Nunca versionar pesos, modelos ou imagens locais |
| Modelo ONNX com formato diferente | Pós-processamento YOLO errado | Validar as dimensões de entrada e saída (já implementado) |
| Código novo que formate `Detection.conf` sem checar `None` | `TypeError` | Visualizador já ajustado e testado; `examples/demo_detection.py` só recebe saídas do YOLO (sempre numéricas) |
| Escolher a convenção de coordenadas errada no parser | Caixas deslocadas, mas estruturalmente válidas | Convenção explícita no construtor; confirmar com inferência real |
| Refatorar o `prepare()` do `ObjectDetectionComponent` | Quebra testes e demo que usam `np.ndarray` | Só com aprovação; ajustar testes e demo junto |
| Contexto da conversa perdido | Retrabalho e decisões esquecidas | `handoff.md`, `log.md`, `status.md` e `CLAUDE.md` atualizados a cada etapa |
| Diagramas do ADR desatualizados | Divergência entre o desenho e o código | Atualizar ao estabilizar a integração |

## Decisões tomadas

- `Component` mantém `object` nas anotações, com validação em tempo de execução; não foi criado um `TypeVar`.
- `prepare()` devolve conteúdos: aplicado no visualizador e no VQA. Nos outros componentes, só com aprovação.
- `Detection` continua em `detection.py`, por enquanto.
- O VQA é experimental, e a resposta textual é salva como `TextReference`.
- Nada de inventar coordenadas, classes ou confiança.
- `Detection.conf: float | None`, obrigatório (aprovado e aplicado em 17/11/2026).
- Validação estrita: um item inválido rejeita a resposta inteira (aprovado e aplicado).
- O parser aceita só JSON puro (aprovado e aplicado).

## Perguntas pendentes

- Mecanismo do `MirageAnswerer`: subprocesso ou HTTP? Depende do ambiente da GPU.
- Multi-imagem (ponto forte do MIRAGE): é necessário para o caso de uso?
- Onde conseguir anotações verdadeiras para medir a localização?
