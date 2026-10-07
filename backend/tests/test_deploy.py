"""One-link deployment: the API and the built frontend share a single origin."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import mount_frontend
from backend.app.quality import QualityModel


def built_frontend(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>LineLens</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('linelens')", encoding="utf-8")
    return dist


def test_frontend_is_served_after_api_routes_with_spa_fallback(tmp_path):
    application = FastAPI()

    @application.get("/api/ping")
    def ping() -> dict:
        return {"ok": True}

    assert mount_frontend(application, built_frontend(tmp_path)) is True
    client = TestClient(application)
    assert client.get("/api/ping").json() == {"ok": True}
    assert "LineLens" in client.get("/").text
    assert client.get("/assets/app.js").text == "console.log('linelens')"
    # Client-side routes fall back to the app shell...
    assert "LineLens" in client.get("/incidents/INC-0001").text
    # ...but unknown API paths stay honest 404s.
    missing = client.get("/api/does-not-exist")
    assert missing.status_code == 404
    assert "LineLens" not in missing.text


def test_frontend_mount_is_skipped_without_a_build(tmp_path):
    application = FastAPI()
    assert mount_frontend(application, tmp_path / "missing") is False


def test_quality_model_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    for path in (QualityModel.MODEL_PATH, QualityModel.SCALER_PATH, QualityModel.ARTIFACT_PATH):
        assert path.is_absolute()
    monkeypatch.chdir(tmp_path)
    model = QualityModel()
    assert model.is_fallback() is False
    assert model.source == "versioned-synthetic-artifact"
