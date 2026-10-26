from pathlib import Path
from tempfile import TemporaryDirectory

from mlops_workflows.artifacts.file import FileArtifact

# 1. Cria a referência para a imagem original.
entrada = FileArtifact(
    name="imagem_entrada",
    location="/home/visioer/Área de trabalho/image.png",
)

print("Conteúdo ainda não carregado:", entrada.data is None)

# 2. Carrega os bytes da imagem.
entrada.materialize()

print("Imagem carregada:", len(entrada.data), "bytes")

# A cópia será criada numa pasta temporária.
with TemporaryDirectory() as folder:
    # 3. Define onde salvar a cópia.
    saida = FileArtifact(
        name="imagem_copia",
        location=str(Path(folder) / "copia.png"),
    )

    # 4. Salva o conteúdo da entrada no destino.
    referencia = saida.dematerialize(entrada)

    print("Cópia salva em:", referencia)

    # 5. Converte apenas a referência para JSON.
    mensagem = saida.model_dump_json(include={"name", "location"})

    print("Referência em JSON:", mensagem)

    # 6. Cria outro objeto usando a referência.
    recuperado = FileArtifact.model_validate_json(mensagem)

    assert recuperado.data is None

    # 7. Carrega os bytes da cópia.
    recuperado.materialize()

    # 8. Confere se o conteúdo foi preservado.
    assert recuperado.data == entrada.data

    print("SUCESSO: a cópia tem os mesmos bytes da imagem original.")

print("A cópia temporária foi removida. A imagem original foi preservada.")
