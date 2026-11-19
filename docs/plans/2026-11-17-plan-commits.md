---
type: Plan
title: Plano de commits da integração MIRAGE
description: Ordem dos commits que versionaram o trabalho da branch feature/integracao-mirage. Proposto em 17/11/2026 com 8 commits; executado em 19/11/2026 com 12, por autorização do usuário.
tags:
- git
- commits
- plan
status: draft
generated:
  by: human:iago.pirone
  at: "2026-11-18T08:29:15-03:00"
evidence_basis: [proposal, approved, verified]
sources:
- id: local-checkout
  resource: Checkout local em feature/integracao-mirage (HEAD d0fb7f2 + alterações não commitadas), inspecionado em 17/11/2026
  title: Estado do Git verificado
---

# Plano de commits

> **Origem:** seção "Plano de commits proposto (17/11/2026, não executado)" de `quality/tooling.md` no bundle antigo, movida em 18/11/2026 para cá. O texto original segue abaixo; o único ajuste está marcado como **Atualização de 18/11/2026**.
>
> **Estado:** proposta. **Commits não autorizados** pelo usuário.


**Contexto:**
- Branch `feature/integracao-mirage`, sobre `d0fb7f2`, que é o mesmo commit da head do PR #3.
- O PR #3 está **aberto** e ainda não entrou na `rc`.

**Ordem proposta.** Cada commit deixa a suíte passando, porque as dependências vêm antes. Seguindo o padrão do histórico (`tipo(escopo): descrição` em português):

1. `test(artifacts): organiza testes de imagem e vídeo em subpastas`
   - remove `tests/unit/artifacts/test_{image,video}.py`;
   - adiciona `tests/unit/artifacts/{image,video}/`;
   - o conteúdo é idêntico, só mudou de pasta.
2. `feat(artifacts): adiciona artefatos de texto`
   - `mlops_workflows/artifacts/text/` + `tests/unit/artifacts/text/`.
3. `feat(artifacts): permite detecções sem confiança`
   - `artifacts/detection/detection.py` + `tests/unit/artifacts/detection/test_detection_artifacts.py`.
4. `feat(components): adiciona visualização de detecções`
   - `components/detection_visualization/` + testes unitários e de integração;
   - já na versão com `ImageContent`/`DetectionContent` e rótulo sem confiança;
   - depende do commit 3.
5. `feat(components): adiciona componente experimental de VQA`
   - `components/visual_question_answering/` + testes.
6. `feat(components): interpreta detecções em respostas textuais`
   - `components/text_detection_parsing/` + testes;
   - a integração usa os commits 4 e 5.
7. `chore(experiments): adiciona prova de conceito isolada do MIRAGE`
   - `experiments/mirage/`, incluindo `ruff.toml` (alvo Python 3.10 e `src` na raiz, só nessa pasta) e o avaliador `evaluate_detections.py`. Sem `__pycache__`, que é ignorado.
   - Depende do commit 6, porque o avaliador importa o `TextDetectionParser`.
8. `docs: adiciona base OKF 0.2, handoff e CLAUDE.md`
   - `docs/mlops-workflows-okf-0.2/` + `CLAUDE.md`.

**Antes de commitar:**
- `git add` por caminho, nunca `git add .`;
- conferir `git status` depois de cada commit;
- opcionalmente, rodar a suíte a cada commit.
- **Os hooks do pre-commit também rodam.**

**Para o PR:**
- esperar o #3 ser mesclado na `rc`;
- ou abrir um PR empilhado com base em `feature/implementar-componentes`.
- Um PR direto para `rc` agora incluiria os commits do #3.

## Atualização de 18/11/2026 (reorganização da documentação)

O commit 8 passa a abranger os caminhos da nova estrutura:

- `docs/` inteiro: `index.md`, `log.md`, `handoff.md`, `CLAUDE.md` e as pastas `adr/`, `diagrams/`, `playbooks/`, `plans/`, `references/`, `reports/`;
- a remoção de `docs/ADR-001-workflow-architecture.md` e de `docs/diagrams/*.mmd`, já versionados, que foram movidos para `docs/adr/001-workflow-architecture.md` e `docs/diagrams/*.md`;
- `scripts/okf_lint.py` e `tests/unit/scripts/test_okf_lint.py`;
- `CLAUDE.md` da raiz.

Mensagem sugerida: `docs: reorganiza a documentação no padrão OKF e adiciona validador`.

## Atualização de 19/11/2026: execução autorizada

O usuário autorizou os commits, o push, o PR e o comentário no Jira. Os experimentos criados depois de 17/11 (Florence-2, Qwen3-VL, pipelines de ponta a ponta e o `ExecutionReport`) ganharam commits próprios. A ordem executada foi:

1. `feat(artifacts): permite detecções sem confiança`
2. `docs: reorganiza a documentação no padrão OKF e adiciona validador` (inclui `CLAUDE.md`, `scripts/okf_lint.py` e os testes dele)
3. `test(artifacts): organiza testes de imagem e vídeo em subpastas`
4. `feat(artifacts): adiciona artefatos de texto`
5. `feat(components): adiciona visualização de detecções`
6. `feat(components): adiciona componente experimental de VQA`
7. `feat(components): interpreta detecções em respostas textuais`
8. `feat(artifacts): adiciona relatório de execução`
9. `chore(experiments): adiciona prova de conceito do MIRAGE e avaliador`
10. `chore(experiments): adiciona experimento do Florence-2 em CPU`
11. `chore(experiments): adiciona experimento do Qwen3-VL em CPU`
12. `chore(experiments): adiciona pipelines de ponta a ponta e avaliação no BCCD`

**Por que a documentação veio cedo:** o hook de pre-commit roda a suíte inteira, e o teste do validador confere o `docs/` real. Enquanto a remoção dos arquivos antigos de `docs/` não estivesse commitada, o hook os restaurava temporariamente e o teste falhava. Pelo mesmo motivo, a mudança de `Detection.conf` foi a primeira.

**Limitação:** o hook roda os testes com os arquivos ainda não commitados presentes na árvore. Por isso, ele não prova que cada commit, isolado, passa na suíte; prova que a árvore completa passa.

**PR:** empilhado, com base em `feature/implementar-componentes`, porque o PR #3 ainda não entrou na `rc`.
