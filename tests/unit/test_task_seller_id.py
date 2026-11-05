import asyncio
import sqlite3

import pytest
from pydantic import ValidationError

from src.domain.models.task import Task, TaskCreate, TaskGenerateRequest, TaskUpdate
from src.infrastructure.persistence.sqlite_connection import init_schema
from src.infrastructure.persistence.sqlite_task_repository import SqliteTaskRepository


def _create(**extra):
    return TaskCreate(task_name="Loja iPhone", keyword="苹果", description="iphone", **extra)


def test_seller_id_accepts_store_url_and_plain_id():
    url = "https://www.goofish.com/personal?userId=391299371"
    assert _create(seller_id=url).seller_id == "391299371"
    assert _create(seller_id="391299371").seller_id == "391299371"
    assert TaskUpdate(seller_id=url).seller_id == "391299371"
    request = TaskGenerateRequest(task_name="a", keyword="b", description="c", seller_id=url)
    assert request.seller_id == "391299371"


def test_seller_id_blank_means_search_task():
    assert _create().seller_id is None
    assert _create(seller_id="").seller_id is None
    assert _create(seller_id="   ").seller_id is None


@pytest.mark.parametrize("bad", ["abc", "https://example.com/personal?userId=391299371", "123"])
def test_seller_id_rejects_invalid_values(bad):
    with pytest.raises(ValidationError):
        _create(seller_id=bad)


@pytest.mark.parametrize("pages", [0, -7])
def test_max_pages_must_be_positive(pages):
    with pytest.raises(ValidationError):
        TaskUpdate(max_pages=pages)
    with pytest.raises(ValidationError):
        _create(max_pages=pages)


def test_seller_id_survives_repository_roundtrip(tmp_path):
    repo = SqliteTaskRepository(str(tmp_path / "app.sqlite3"), legacy_config_file=None)
    task = Task(
        task_name="Loja iPhone",
        enabled=True,
        keyword="苹果",
        max_pages=3,
        personal_only=False,
        ai_prompt_base_file="prompts/base_prompt.txt",
        ai_prompt_criteria_file="prompts/x.txt",
        seller_id="391299371",
    )
    saved = asyncio.run(repo.save(task))
    assert asyncio.run(repo.find_by_id(saved.id)).seller_id == "391299371"


def test_schema_migration_adds_seller_id_to_old_databases():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, task_name TEXT NOT NULL)")
    conn.execute("INSERT INTO tasks (id, task_name) VALUES (0, 'antiga')")
    init_schema(conn)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(tasks)")]
    assert "seller_id" in columns
    assert conn.execute("SELECT seller_id FROM tasks WHERE id = 0").fetchone()[0] is None
    init_schema(conn)  # idempotent
