from inspect4all.enrichment.cache import (
    append_cache,
    content_hash,
    load_cache,
)


def test_content_hash_is_stable_and_sensitive():
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_load_missing_file_returns_empty(tmp_path):
    assert load_cache(tmp_path / "nope.jsonl") == {}


def test_append_then_load_roundtrip(tmp_path):
    p = tmp_path / "enrichment_cache.jsonl"
    append_cache(p, "f.py::foo", content_hash("body"), "ok")
    append_cache(p, "f.py::bar", content_hash("x"), "failed")
    assert load_cache(p) == {"f.py::foo": "ok", "f.py::bar": "failed"}


def test_later_status_wins(tmp_path):
    p = tmp_path / "enrichment_cache.jsonl"
    append_cache(p, "f.py::foo", "h", "failed")
    append_cache(p, "f.py::foo", "h", "ok")
    assert load_cache(p)["f.py::foo"] == "ok"
