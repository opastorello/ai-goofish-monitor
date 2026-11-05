import asyncio
import sqlite3

import pytest
from pydantic import ValidationError

from src.domain.models.task import Task, TaskCreate, TaskUpdate
from src.infrastructure.persistence.sqlite_connection import init_schema
from src.infrastructure.persistence.sqlite_task_repository import SqliteTaskRepository


def test_max_items_per_run_is_optional_and_positive():
    assert TaskCreate(task_name="a", keyword="b", description="c").max_items_per_run is None
    assert TaskCreate(task_name="a", keyword="b", description="c", max_items_per_run=4).max_items_per_run == 4
    assert TaskUpdate(max_items_per_run=3).max_items_per_run == 3


@pytest.mark.parametrize("value", [0, -1])
def test_max_items_per_run_rejects_non_positive_values(value):
    with pytest.raises(ValidationError):
        TaskUpdate(max_items_per_run=value)
    with pytest.raises(ValidationError):
        TaskCreate(task_name="a", keyword="b", description="c", max_items_per_run=value)


def test_max_items_per_run_survives_repository_roundtrip(tmp_path):
    repo = SqliteTaskRepository(str(tmp_path / "app.sqlite3"), legacy_config_file=None)
    task = Task(
        task_name="t",
        enabled=True,
        keyword="k",
        max_pages=1,
        personal_only=False,
        ai_prompt_base_file="prompts/base_prompt.txt",
        ai_prompt_criteria_file="prompts/x.txt",
        max_items_per_run=4,
    )
    saved = asyncio.run(repo.save(task))
    assert asyncio.run(repo.find_by_id(saved.id)).max_items_per_run == 4


def test_schema_migration_adds_max_items_per_run():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, task_name TEXT NOT NULL)")
    init_schema(conn)
    assert "max_items_per_run" in [row[1] for row in conn.execute("PRAGMA table_info(tasks)")]
    init_schema(conn)  # idempotent


def test_title_triage_defaults_off_and_survives_the_repository(tmp_path):
    assert TaskCreate(task_name="a", keyword="b", description="c").title_triage is False
    assert TaskUpdate(title_triage=True).title_triage is True
    repo = SqliteTaskRepository(str(tmp_path / "app.sqlite3"), legacy_config_file=None)
    task = Task(
        task_name="t",
        enabled=True,
        keyword="k",
        max_pages=1,
        personal_only=False,
        ai_prompt_base_file="prompts/base_prompt.txt",
        ai_prompt_criteria_file="prompts/x.txt",
        title_triage=True,
    )
    saved = asyncio.run(repo.save(task))
    assert asyncio.run(repo.find_by_id(saved.id)).title_triage is True


def test_schema_migration_adds_title_triage():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, task_name TEXT NOT NULL)")
    init_schema(conn)
    assert "title_triage" in [row[1] for row in conn.execute("PRAGMA table_info(tasks)")]
