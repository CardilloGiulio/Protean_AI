import json
from pathlib import Path

from protean_workspace.core.config import PACKAGE_DIR


MANIFEST_PATH = PACKAGE_DIR / "static" / "assets" / "immersion" / "manifest.json"


def _url_to_file(url: str) -> Path:
    prefix = "/static/"
    assert url.startswith(prefix)
    return PACKAGE_DIR / "static" / url.removeprefix(prefix)


def test_immersion_manifest_enables_partial_runtime() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema"] == "protean.immersion-assets/v1"
    assert manifest["immersion_mode_enabled"] is True
    assert manifest["sprite_mode_enabled"] is True
    assert "incoming" in manifest["feature_status"].lower()


def test_supplied_sprite_packs_are_ready_and_missing_packs_stay_open() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    packs = {pack["id"]: pack for pack in manifest["sprite_packs"]}

    assert len(packs) == 118
    assert {pack_id for pack_id, pack in packs.items() if pack["status"] == "ready"} == {
        "hermione-year1",
        "hermione-year5",
        "tom-student-16",
        "tom-student-17",
    }
    assert sum(pack["status"] == "incoming" for pack in packs.values()) == 114
    assert "sherlock-baker-street" not in packs
    assert "hermione-year2" in packs

    for pack in packs.values():
        assert set(pack["expressions"]) == {
            "neutral",
            "positive",
            "amused",
            "serious",
            "concerned",
            "surprised",
            "thinking",
        }
        for expression in pack["expressions"].values():
            if expression["status"] == "ready":
                assert _url_to_file(expression["path"]).is_file()
            else:
                assert expression["status"] == "incoming"
                assert expression["path"] is None
                assert expression["expected_filename"].endswith(".webp")


def test_supplied_backgrounds_are_ready_and_remaining_slots_stay_open() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    backgrounds = manifest["backgrounds"]

    assert len(backgrounds) == 80
    assert sum(item["status"] == "ready" for item in backgrounds) == 17
    assert sum(item["status"] == "incoming" for item in backgrounds) == 63
    assert not any(item["id"].startswith("bg-sh-") for item in backgrounds)

    for item in backgrounds:
        if item["status"] == "ready":
            assert _url_to_file(item["path"]).is_file()
        else:
            assert item["path"] is None
            assert item["expected_filename"].endswith(".webp")


def test_diary_tom_remains_diary_first_despite_sprite_availability() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pack = next(pack for pack in manifest["sprite_packs"] if pack["id"] == "tom-student-16")

    assert pack["status"] == "ready"
    assert "diary-imprint" in pack["phase_ids"]
    assert "diary object" in pack["usage_notes"]


def test_workspace_uses_dynamic_immersion_implementation_badge() -> None:
    static_dir = PACKAGE_DIR / "static"
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    js = (static_dir / "js" / "app.js").read_text(encoding="utf-8")
    assert "Partial library" not in html
    assert 'id="immersionStatusBadge"' in html
    assert 'implemented ? "Implemented" : "Not yet implemented"' in js
