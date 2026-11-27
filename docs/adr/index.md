# Decisões de arquitetura (ADR)

Documentos temporais: uma decisão e o porquê. Não se reescreve um ADR aceito; uma mudança gera um ADR novo.

* [ADR 001 — Estrutura genérica para a inferência no ciclo de MLOps](001-workflow-architecture.md) - Decisão arquitetural original (proposta em 15/10/2026) do workflow genérico de inferência, com nota de divergência em relação ao código atual.
* [ADR 002 — prepare() devolve conteúdos de artefatos](002-prepare-returns-artifact-contents.md) - Component.prepare() retorna ImageContent, DetectionContent, TextContent etc., e não o .data cru.
* [ADR 003 — Detection.conf pode ser nulo](003-nullable-detection-confidence.md) - Detecções sem confiança calibrada usam conf null; nunca se inventa um valor.
* [ADR 004 — MIRAGE fora do processo, em ambiente isolado](004-mirage-out-of-process.md) - O MIRAGE roda em ambiente próprio (Python 3.10, CUDA) fora do pacote; o projeto só consome suas respostas textuais.
* [ADR 005 — Interpretação estrita de detecções em texto](005-strict-json-text-detection-parsing.md) - O TextDetectionParser aceita só JSON puro, com convenção de coordenadas explícita, e rejeita a resposta inteira se algum item for inválido.
* [ADR 006 — Avaliação offline de detecções](006-offline-detection-evaluation.md) - Respostas inválidas ou ausentes contam como falso negativo; métricas sem AP/mAP porque não há confiança.
* [ADR 007 — Documentação contínua no padrão OKF do new-visio-research-models](007-okf-documentation-structure.md) - A documentação faz parte de cada tarefa e fica em docs/, no padrão OKF do repositório de referência, com handoff na raiz.
* [ADR 008 — Links internos relativos](008-relative-internal-links.md) - Links entre documentos passam a ser relativos (válidos pela OKF 0.2) para funcionar no GitHub; adaptação em relação ao repositório de referência.
* [ADR 009 — Relatório de execução como artefato tipado](009-execution-report-artifact.md) - ExecutionReportReference/ExecutionReportContent com identidade de modelos reais obrigatória e status que separam falha de infraestrutura, resposta inválida e detecções produzidas.
* [ADR 010 — Correspondência bipartida ótima](010-optimal-bipartite-matching.md) - O avaliador troca o greedy pelo algoritmo húngaro (mais TP, depois maior soma de IoU) e ganha o modo independente de classe com matriz de confusão.
