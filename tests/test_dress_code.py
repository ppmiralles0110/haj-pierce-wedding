# =============================================================================
# tests/test_dress_code.py — Dress code reference photo tests
# =============================================================================
"""Tests for the four-slot dress code photo configuration."""

from app.models.wedding_config import (
    CONFIG_IMAGE_KEYS,
    DRESS_CODE_PHOTO_KEYS,
    DRESS_CODE_PHOTO_SLOTS,
    dress_code_photo_keys,
)


def test_four_slots_per_group():
    """Each dress-code group exposes exactly four photo slots."""
    assert DRESS_CODE_PHOTO_SLOTS == 4
    assert len(DRESS_CODE_PHOTO_KEYS["men"]) == 4
    assert len(DRESS_CODE_PHOTO_KEYS["women"]) == 4
    assert DRESS_CODE_PHOTO_KEYS["men"][0] == "dress_code_men_photo_1"
    assert DRESS_CODE_PHOTO_KEYS["women"][3] == "dress_code_women_photo_4"


def test_all_slots_are_servable():
    """Every slot key is allowed through the image-serving endpoint."""
    for keys in DRESS_CODE_PHOTO_KEYS.values():
        for key in keys:
            assert key in CONFIG_IMAGE_KEYS
    assert "hero_image_url" in CONFIG_IMAGE_KEYS
    assert "wedding_date" not in CONFIG_IMAGE_KEYS


def test_only_filled_slots_are_returned():
    """Empty slots are skipped and order is preserved."""
    config = {
        "dress_code_men_photo_1": "/static/uploads/a.jpg",
        "dress_code_men_photo_2": "",
        "dress_code_men_photo_3": "/static/uploads/c.jpg",
    }
    assert dress_code_photo_keys(config, "men") == [
        "dress_code_men_photo_1",
        "dress_code_men_photo_3",
    ]


def test_legacy_key_fills_slot_one():
    """A pre-existing single photo still renders in slot 1."""
    config = {"dress_code_women_photo": "/static/uploads/legacy.jpg"}
    assert dress_code_photo_keys(config, "women") == ["dress_code_women_photo"]


def test_slot_one_wins_over_legacy_key():
    """Once slot 1 is set, the legacy key is ignored (no duplicate photo)."""
    config = {
        "dress_code_men_photo": "/static/uploads/legacy.jpg",
        "dress_code_men_photo_1": "/static/uploads/new.jpg",
    }
    assert dress_code_photo_keys(config, "men") == ["dress_code_men_photo_1"]


def test_empty_config_returns_nothing():
    """No configured photos means the template falls back to placeholders."""
    assert dress_code_photo_keys({}, "men") == []
    assert dress_code_photo_keys({}, "women") == []


def test_details_page_renders_four_placeholders(auth_client):
    """With nothing configured, four placeholders render per group."""
    resp = auth_client.get("/details")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "For Him" in body and "For Her" in body
    for i in range(1, 5):
        assert f"seed/menattire{i}/" in body
        assert f"seed/womenattire{i}/" in body


def test_config_page_has_eight_upload_slots(admin_client):
    """The admin config form offers four upload inputs per group."""
    resp = admin_client.get("/admin/config")
    body = resp.data.decode()
    for group in ("men", "women"):
        for i in range(1, 5):
            assert f'name="dress_code_{group}_photo_{i}_file"' in body


def test_config_image_endpoint_rejects_unknown_key(auth_client):
    """Arbitrary config keys cannot be streamed as images."""
    assert auth_client.get("/photo/config/wedding_date").status_code == 404
