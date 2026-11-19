"""Test the runner configurations without running llama.cpp."""

from pathlib import Path

import pytest

from experiments.qwen3vl import run_qwen

ORIGINAL = ["--temp", "0", "--seed", "42", "-n", "1024", "-c", "4096", "-t", "10"]


def options(args: list[str]) -> dict[str, str]:
    return dict(zip(args[::2], args[1::2], strict=True))


def test_original_config_is_the_first_run():
    assert run_qwen.CONFIGS["original"] == ORIGINAL


def test_tokens1024_changes_only_the_image_tokens():
    changed = options(run_qwen.CONFIGS["tokens1024"])

    assert changed.pop("--image-min-tokens") == "1024"
    assert changed == options(ORIGINAL)


def test_official_sampling_changes_only_the_samplers():
    changed = options(run_qwen.CONFIGS["official_sampling"])
    samplers = {k: changed.pop(k) for k in list(changed) if k not in options(ORIGINAL)}

    assert samplers == {
        "--top-p": "0.8",
        "--top-k": "20",
        "--min-p": "0",
        "--repeat-penalty": "1.0",
        "--presence-penalty": "1.5",
    }
    assert changed.pop("--temp") == "0.7"
    assert changed == {k: v for k, v in options(ORIGINAL).items() if k != "--temp"}


def test_combined_is_official_sampling_plus_image_tokens():
    combined = options(run_qwen.CONFIGS["combined"])

    assert combined.pop("--image-min-tokens") == "1024"
    assert combined == options(run_qwen.CONFIGS["official_sampling"])


@pytest.mark.parametrize("config", sorted(run_qwen.CONFIGS))
def test_every_config_keeps_the_context_limit(config):
    assert options(run_qwen.CONFIGS[config])["-c"] == "4096"


def test_build_command():
    command = run_qwen.build_command("Describe.", Path("/img.jpg"), "tokens1024")

    assert command[0].endswith("llama-mtmd-cli")
    assert command[command.index("--image") + 1] == "/img.jpg"
    assert command[command.index("-p") + 1] == "Describe."
    assert (
        command[-len(run_qwen.CONFIGS["tokens1024"]) :]
        == run_qwen.CONFIGS["tokens1024"]
    )
