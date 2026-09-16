from pathlib import Path

from protean_workspace.services.context import ContextRepository


CONTEXT_DIR = Path(__file__).resolve().parents[1] / "src" / "protean_workspace" / "data" / "context"


def test_unrelated_query_does_not_inject_character_personality() -> None:
    repository = ContextRepository(CONTEXT_DIR)
    context = repository.build_context("hello there")
    assert "Tom Riddle" not in context
    assert "refined and intelligent" not in context


def test_build_context_retrieves_networking_material() -> None:
    repository = ContextRepository(CONTEXT_DIR)
    context = repository.build_context("What is ARP used for?")
    assert "ARP" in context
    assert "Address Resolution Protocol" in context
