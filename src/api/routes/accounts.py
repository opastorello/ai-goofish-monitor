"""
闲鱼账号管理路由
"""
import json
import os
import re
import asyncio
import aiofiles
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.account_guard import AccountGuard
from src.failure_guard import FailureGuard
from src.infrastructure.config.env_manager import env_manager
from src.services.login_status_service import check_login_state


router = APIRouter(prefix="/api/accounts", tags=["accounts"])

ACCOUNT_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,50}$")


class AccountCreate(BaseModel):
    name: str
    content: str


class AccountUpdate(BaseModel):
    content: str


def _strip_quotes(value: str) -> str:
    if not value:
        return value
    if value.startswith(("\"", "'")) and value.endswith(("\"", "'")):
        return value[1:-1]
    return value


def _state_dir() -> str:
    raw = env_manager.get_value("ACCOUNT_STATE_DIR", "state") or "state"
    return _strip_quotes(raw.strip())


def _ensure_state_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _validate_name(name: str) -> str:
    trimmed = name.strip()
    if not trimmed or not ACCOUNT_NAME_RE.match(trimmed):
        raise HTTPException(status_code=400, detail="账号名称只能包含字母、数字、下划线或短横线。")
    return trimmed


def _account_path(name: str) -> str:
    filename = f"{name}.json"
    return os.path.join(_state_dir(), filename)


def _validate_json(content: str) -> None:
    try:
        json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="提供的内容不是有效的JSON格式。")


@router.get("", response_model=List[dict])
async def list_accounts():
    state_dir = _state_dir()
    if not os.path.isdir(state_dir):
        return []
    files = [f for f in os.listdir(state_dir) if f.endswith(".json")]
    accounts = []
    for filename in sorted(files):
        name = filename[:-5]
        accounts.append({
            "name": name,
            "path": os.path.join(state_dir, filename),
        })
    return accounts


class GuardResetRequest(BaseModel):
    task_name: Optional[str] = None
    account: Optional[str] = None


@router.get("/guard", response_model=dict)
async def get_guard_state():
    """风控保护（熔断）状态：各任务的连续失败数与暂停情况。"""
    guard = FailureGuard()
    account_guard = AccountGuard()
    return {
        "threshold": guard.threshold,
        "pause_seconds": guard.pause_seconds,
        "tasks": await asyncio.to_thread(guard.snapshot),
        "cooldown_seconds": int(account_guard.cooldown_seconds),
        "accounts": await asyncio.to_thread(account_guard.snapshot),
    }


@router.post("/guard/reset", response_model=dict)
async def reset_guard(body: Optional[GuardResetRequest] = None):
    """手动解除风控熔断；不传 task_name 时重置全部任务。"""
    task_name = body.task_name if body else None
    account = body.account if body else None
    count = 0
    if account is None:
        count += await asyncio.to_thread(FailureGuard().reset, task_name)
    if task_name is None:
        count += await asyncio.to_thread(AccountGuard().reset, account)
    return {"message": "风控保护已重置", "reset": count}


@router.get("/{name}/status", response_model=dict)
async def get_account_status(name: str):
    """检查账号登录态是否仍然有效（不启动浏览器，只发一次轻量请求）。"""
    path = _account_path(name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="账号不存在")
    result = await asyncio.to_thread(check_login_state, path)
    return {"name": name, **result}


@router.get("/{name}", response_model=dict)
async def get_account(name: str):
    account_name = _validate_name(name)
    path = _account_path(account_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="账号不存在")
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    return {"name": account_name, "path": path, "content": content}


@router.post("", response_model=dict)
async def create_account(data: AccountCreate):
    account_name = _validate_name(data.name)
    _validate_json(data.content)
    state_dir = _state_dir()
    _ensure_state_dir(state_dir)
    path = _account_path(account_name)
    if os.path.exists(path):
        raise HTTPException(status_code=409, detail="账号已存在")
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(data.content)
    return {"message": "账号已添加", "name": account_name, "path": path}


@router.put("/{name}", response_model=dict)
async def update_account(name: str, data: AccountUpdate):
    account_name = _validate_name(name)
    _validate_json(data.content)
    state_dir = _state_dir()
    _ensure_state_dir(state_dir)
    path = _account_path(account_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="账号不存在")
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(data.content)
    return {"message": "账号已更新", "name": account_name, "path": path}


@router.delete("/{name}", response_model=dict)
async def delete_account(name: str):
    account_name = _validate_name(name)
    path = _account_path(account_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="账号不存在")
    os.remove(path)
    return {"message": "账号已删除"}
