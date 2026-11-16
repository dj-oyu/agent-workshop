# Problem Loop Harness

複数工程の作業を、実行・検証・計画修正・再開のループとして管理する Python ツールです。工程の依存関係、実行結果、検証証拠を保存し、中断後も未完の作業から続けられます。Python 3 標準ライブラリのみで動作します。

## はじめる

Skill の導入は[リポジトリの README](../../../README.md)、エージェント向け手順は [SKILL.md](SKILL.md) を参照してください。以下はこのディレクトリで実行します（シェル例は POSIX 環境向け）。

```sh
HARNESS="$(pwd -P)"
CASE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/problem-loop-demo.XXXXXX")"
cp "$HARNESS/example.json" "$CASE_DIR/plan.json"
python3 "$HARNESS/loop.py" init "$CASE_DIR/state.json" --plan "$CASE_DIR/plan.json"
python3 "$HARNESS/loop.py" run "$CASE_DIR/state.json"
sh "$HARNESS/restore.sh" "$CASE_DIR/state.json"
```

このデモは一時ディレクトリ内に2つのファイルを作成し、内容を検証します。実案件では永続的な非公開ディレクトリに plan と state をまとめて置いてください。コマンドの作業ディレクトリは plan の親ディレクトリです。

計画の形式は [example.json](example.json) を参照してください。目的と完了条件に加え、各工程に担当、次の行動、依存関係、実行コマンド、検証コマンド、タイムアウト、許可の記録を指定します。コマンドは shell 文字列ではなく argv 配列です。

## 実行と再開

- `loop.py run STATE`：実行と検証。既定で最大20工程。`--steps 1` で1工程ずつ進めます。
- `restore.sh STATE`：状態・証拠・次の作業を表示します。実行や停止解除はしません。
- `loop.py revise STATE --task ID --plan PLAN --note NOTE`：原因と代替案に基づいて対象工程を改訂します。
- `loop.py reconcile STATE --task ID --note NOTE`：結果が不明な工程の検証だけを実行します。行動は再送しません。

実行失敗や異常終了による結果不明は `unknown` として扱います。安全に再試行できる工程だけに `safe_retry: true` を設定してください。同じ失敗を無条件に繰り返さず、証拠から計画を更新します。

## 保存と復元

```sh
python3 checkpoint.py export /path/to/case/state.json case.zip --include artifact.txt
python3 checkpoint.py restore case.zip new-case-directory
python3 loop.py reconcile new-case-directory/state.json --task TASK_ID --note '復元した成果を検証'
python3 loop.py run new-case-directory/state.json
```

必要な入力・成果物を `--include` で指定します。復元後、以前完了していた工程も検証が済むまで `unknown` になります。checkpoint とログは許可された非公開の保存先へ保全してください。ハッシュは破損検出用であり、内容の安全性を保証しません。

## 制約

- **信頼できる計画だけを実行してください。** sandbox ではなく、`authorized` は権限を付与しません。検証コマンドにも読み取り専用または冪等な操作を使います。
- 推論担当と永続スケジューラは別途接続が必要です。本体だけでは計画の自動生成やプロセス終了後の再開を保証しません。
- 停止状態は保存されますが、実行中のコマンドや外部ジョブをキャンセルしません。
- 実案件の入力・状態・ログは公開 checkout の外に置きます。`.gitignore` は機密情報の漏えいを防ぐ仕組みではありません。

## 詳細とテスト

- [PLAYBOOK.md](PLAYBOOK.md)：課題発見から検証・計画修正までの設計
- [CONNECTORS.md](CONNECTORS.md)：推論担当との連携、外部ジョブ待ちからの再開
- [STOP_CONTRACT.md](STOP_CONTRACT.md)：停止と明示的な再開

```sh
sha256sum -c SHA256SUMS
python3 -m unittest -v
```
