from __future__ import annotations

from pathlib import Path

from task_manager.controller import BoardController
from task_manager.main_window import run_app
from task_manager.storage import StorageManager


def main() -> int:
    """メイン処理

    Returns:
        int: 終了コード
    """
    # データファイルの準備
    data_file = Path.cwd() / "task_board.json"
    storage = StorageManager(data_file)
    controller = BoardController(storage)

    # メインウィンドウを表示
    run_app(controller)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
