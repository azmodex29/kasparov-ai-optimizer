from typing import Optional

_store: dict = {}


def save_result(run_id: str, result: dict) -> None:
    _store[run_id] = result


def get_result(run_id: str) -> Optional[dict]:
    return _store.get(run_id)


def list_results() -> list:
    return list(_store.keys())