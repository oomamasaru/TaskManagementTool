# TaskManagementTool

PyQt6 で実装したローカル完結型のタスク管理ツールです。  
`task_management_requirements.md` の要件に沿って、カテゴリ列ベースのメイン画面、検索/フィルタ、完了済みタスク管理、JSON 自動保存、Undo/Redo を実装しています。

## 動作環境

- Python 3.12
- PyQt6

## 起動方法

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## 主な機能

- カテゴリ別タスク一覧（列表示）
- タスクの追加・編集・削除・複製
- タスクカードのドラッグ&ドロップ並び替え
- ステータス管理（固定 + カスタム）
- 完了済みタスクの別ダイアログ表示と復活
- ラベル管理
- テキスト検索 + ラベルボタンフィルタ
- 操作ごとの JSON 自動保存 + `.bak` バックアップ
- コマンド方式 Undo / Redo（Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z）

## 保存ファイル

- `task_board.json`
- `task_board.json.bak`
