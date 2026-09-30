"""Connection discovery must honor the same frozen store as connected resources."""
import pytest
import yaml

from helpers.data.connection_manager import ConnectionManager
from helpers.data import data_helpers as dh
from helpers.knowledge.context_sync import ContextSyncError


@pytest.fixture
def external(tmp_path, monkeypatch):
    project = tmp_path / "project"
    knowledge = project / ".knowledge"
    knowledge.mkdir(parents=True)
    monkeypatch.chdir(project)
    monkeypatch.setattr(dh, "_KNOWLEDGE_DIR", knowledge)
    monkeypatch.setattr(dh, "_ACTIVE_YAML", knowledge / "active.yaml")
    monkeypatch.setattr(dh, "_load_env", lambda: None)
    monkeypatch.setenv("AAP_USE_REMOTE", "1")
    store = tmp_path / "context"
    for dataset in ("one", "two"):
        folder = store / "datasets" / dataset
        folder.mkdir(parents=True)
        (folder / "manifest.yaml").write_text(yaml.safe_dump(dict(dataset_id=dataset, connection=dict(type="snowflake", database=dataset.upper(), schema="PUBLIC"))))
    (knowledge / "active.yaml").write_text("active_dataset: one\n")
    (knowledge / "context-source.yaml").write_text("source: path\npath: ../context\n")
    return project, store


def test_external_connection_manifest_and_explicit_dataset(external):
    assert ConnectionManager(dataset_id="two")._config["connection"]["database"] == "TWO"
    assert ConnectionManager()._config["connection"]["database"] == "ONE"
    assert ConnectionManager(dataset_id="two").connection_type == "snowflake"


def test_installed_snapshot_connection_matches_store(external, tmp_path, monkeypatch):
    from helpers.knowledge.context_snapshot import snapshot_visible_context, install_snapshot
    project, store = external
    snapshot = tmp_path / "frozen"
    snapshot_visible_context(project, snapshot, source_override=store)
    worker = tmp_path / "worker"
    install_snapshot(snapshot, worker)
    monkeypatch.chdir(worker)
    monkeypatch.setattr(dh, "_KNOWLEDGE_DIR", worker / ".knowledge")
    assert ConnectionManager(dataset_id="two")._config["connection"]["database"] == "TWO"


@pytest.mark.parametrize("config", [
    "source: path\npath: ../missing\n", "source: path\n", "source: wrong\n",
    "source: path\npath: ../context\ndataset_path: ../escape\n", "[invalid]\n",
])
def test_bad_context_does_not_fallback_to_local(external, config):
    project, _ = external
    local = project / ".knowledge/datasets/one"
    local.mkdir(parents=True)
    (local / "manifest.yaml").write_text("connection: {type: snowflake, database: WRONG, schema: PUBLIC}\n")
    (project / ".knowledge/context-source.yaml").write_text(config)
    with pytest.raises(ContextSyncError):
        ConnectionManager(dataset_id="one")


def test_custom_path_cannot_silently_select_another_dataset(external):
    project, _ = external
    (project / ".knowledge/context-source.yaml").write_text("source: path\npath: ../context\ndataset_path: datasets/one\n")
    with pytest.raises(ContextSyncError, match="different dataset"):
        ConnectionManager(dataset_id="two")


def test_custom_path_needs_manifest_identity(external):
    project, store = external
    (project / ".knowledge/context-source.yaml").write_text("source: path\npath: ../context\ndataset_path: datasets/one\n")
    (store / "datasets/one/manifest.yaml").write_text("connection: {type: snowflake, database: ONE, schema: PUBLIC}\n")
    with pytest.raises(ContextSyncError, match="requires explicit dataset_id"):
        ConnectionManager(dataset_id="two")


def test_cached_git_read_does_not_fetch(external, monkeypatch):
    project, store = external
    (project / ".knowledge/context-source.yaml").write_text(yaml.safe_dump(dict(source="git", cache=str(store))))
    monkeypatch.setattr("helpers.knowledge.context_sync._git", lambda *args: pytest.fail("connection discovery must not fetch"))
    assert ConnectionManager(dataset_id="two")._config["connection"]["database"] == "TWO"


@pytest.mark.parametrize("content", ["- a\n- b\n", "bad: [\n"])
def test_invalid_manifest_is_an_error(external, content):
    _, store = external
    (store / "datasets/one/manifest.yaml").write_text(content)
    with pytest.raises(ContextSyncError, match="manifest|Manifest"):
        ConnectionManager(dataset_id="one")
