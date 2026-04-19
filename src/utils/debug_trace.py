from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock

_TRACE_LOG_PATH = Path.cwd() / "debug_lifecycle.log"
_TRACE_LOCK = Lock()


def trace_debug(message: str) -> None:
    """一時デバッグログを追記する。

    Args:
        message (str): 出力するメッセージ
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    line = f"[{timestamp}] {message}\n"
    try:
        with _TRACE_LOCK, _TRACE_LOG_PATH.open("a", encoding="utf-8") as stream:
            stream.write(line)
    except Exception:
        # 一時ログ処理で本処理に影響を出さないため、例外は握りつぶす。
        return


def trace_log_path() -> Path:
    """デバッグログファイルのパスを返す。"""
    return _TRACE_LOG_PATH
