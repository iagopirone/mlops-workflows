# Referências — como o projeto é hoje

Documentos vivos: contratos, componentes, artefatos, estado e regras. O código é a fonte de verdade.

* [Artefato de contagem de classes](artifact-class-count.md) - ClassCount, ClassCountContent e ClassCountReference — esquema, validações de consistência e persistência em JSON da saída do ClassCountingComponent.
* [Artefatos de detecção](artifact-detection.md) - Esquema de detecções, validação, persistência e contratos de coordenadas.
* [Relatório de execução e drivers de ponta a ponta](artifact-execution-report.md) - ExecutionReport (artefato tipado), drivers dos pipelines YOLO e MIRAGE, conversor de anotações BCCD e reúso do avaliador para o YOLO.
* [Florence-2-base-ft — experimento local](florence2.md) - Execução isolada em CPU, formato das saídas, adaptador para DetectionContent, ajustes de compatibilidade e limites observados.
* [Qwen3-VL-2B (GGUF) com llama.cpp — experimento local](qwen3vl.md) - Execução isolada em CPU com teto de memória, convenção de coordenadas 0–1000 verificada, adaptador para DetectionContent e limites observados.
* [Artefatos de imagem](artifact-image.md) - Persistência de pixels BGR com validação e OpenCV.
* [Ciclo de vida dos artefatos e componentes](artifact-lifecycle.md) - Materialização, preparação, execução e persistência das saídas.
* [Modelo de artefatos](artifacts.md) - Abstrações, formatos e matriz de tipos de artefato.
* [Artefatos de texto](artifact-text.md) - Representação de prompts e respostas textuais como artefatos UTF-8.
* [Artefatos de vídeo](artifact-video.md) - Carregamento e salvamento de frames de vídeo sem trilha de áudio.
* [ClassCountingComponent](component-class-counting.md) - Contagem de detecções por classe, independente do detector, nos modos genérico (todas as classes) e restrito a um domínio configurado.
* [DetectionVisualizationComponent](component-detection-visualization.md) - Anotação independente do detector a partir de imagem e detecções.
* [ObjectDetectionComponent](component-object-detection.md) - Adaptação entre artefato de imagem, algoritmo de inferência e artefato JSON.
* [Padrão de componentes](components.md) - Contratos, fronteiras de responsabilidade e componentes atuais.
* [Interpretação de respostas textuais em detecções](component-text-detection-parsing.md) - TextDetectionParser e TextDetectionParsingComponent — formato aceito, convenções de coordenadas, confiança ausente, validação estrita e testes.
* [VisualQuestionAnsweringComponent (experimental)](component-visual-question-answering.md) - Componente genérico imagem + prompt → resposta textual, com modelo injetado por VisualQuestionAnswerer.
* [YoloDetector ONNX](component-yolo-detector.md) - Inferência e pós-processamento genérico de modelos YOLO em imagem.
* [Contratos centrais](contracts.md) - Interfaces ArtifactReference, ArtifactContent, Component e as interfaces de modelo injetadas.
* [SOLID e injeção de dependências](dependency-injection.md) - Como os componentes ficam desacoplados das implementações de modelos.
* [Invariantes do projeto](invariants.md) - Regras rígidas que nenhuma mudança pode violar sem uma decisão nova registrada em ADR.
* [Avaliador offline de detecções do MIRAGE](mirage-evaluation.md) - Como o evaluate_detections.py compara detecções extraídas de respostas textuais com anotações humanas; métricas, formatos, políticas e limitações.
* [MIRAGE — capacidades verificadas e viabilidade](mirage.md) - O que as fontes oficiais confirmam sobre o MIRAGE, requisitos, limites e prova de conceito planejada.
* [Diretrizes de documentação OKF](okf-guidelines.md) - Estrutura, frontmatter, nomes, links, índices, log e validação do bundle docs/, adaptados do new-visio-research-models.
* [Pipeline e etapas](pipeline.md) - Step e Pipeline em mlops_workflows/pipeline/ — campos, imutabilidade, finalização, regras de validação da estrutura, pipeline de exemplo e testes.
* [Visão geral do mlops-workflows](overview.md) - Propósito, objetivos, escopo e casos de uso do repositório.
* [Fontes, limites e confiança desta documentação](provenance.md) - Identificação das evidências, lacunas de acesso e estado de revisão humana.
* [Estrutura do repositório](repository-structure.md) - Mapa real dos diretórios e módulos no checkout local.
* [Referências de código e documentação](resources.md) - Relação de fontes úteis para manutenção dos conceitos e guias.
* [Riscos e decisões em aberto](risks-and-open-questions.md) - Riscos técnicos da integração e perguntas pendentes.
* [Inventário de implementação e pendências](status.md) - Distingue o que foi verificado no código, o que foi aprovado, o que é hipótese e o que está planejado.
* [Testes automatizados](test-suite.md) - Suítes, organização, comandos e resultados reais.
* [Ferramentas de desenvolvimento](tooling.md) - Python, uv, Ruff, pytest, pre-commit e práticas de versionamento.
* [Mecanismos transitórios](transitional-mechanisms.md) - Registro do que é provisório no código ou na documentação, com o critério para remover ou consolidar cada item.
