# Problem Loop Harness v0.3.1

この会話で得た問題解決の方法を、文章だけでなく再開可能な実行アセットにしました。
Python 3 標準ライブラリのみ。インストール不要。プロジェクトや認証を変更しません。

## Codex skillとして使う

このリポジトリ自体が `SKILL.md` を持つ自己完結したskillです。既存のPython runnerを重複実装せず、Codexが適用場面・反復・停止・復元方法を読み込む入口を追加しています。

レビュー済みcommitを取得し、checksumとテストを確認してから、書込みを許可されたskillディレクトリへ配置します。標準のユーザー領域へ導入する場合の例:

```sh
sha256sum -c SHA256SUMS
python3 -m unittest -v
python3 install_skill.py "${CODEX_HOME:-$HOME/.codex}/skills/problem-loop-harness"
```

インストーラーは明示した新規ディレクトリにmanifest掲載ファイルだけをコピーし、既存先は上書きしません。ネットワーク通信・設定変更・planの実行はしません。別環境でも同じ検証済みcommitから同じコマンドで再配置できます。権限外の書込みは事前に環境の承認手続きを守ってください。

導入後はCodexの新しいセッションでskill一覧に `problem-loop-harness` が認識されることを確認し、`$problem-loop-harness` で明示呼出できます。自動選択を無効にはしていませんが、実際の認識は導入先環境で別途確認します。この公開物の検証では一時ディレクトリへの導入のみ行い、利用者のグローバルskill設定は変更していません。

skillは常駐プロセスでもschedulerでもありません。案件state・証拠・外部wakeを別途保全し、実案件をskillディレクトリに置かないでください。

## 1コマンドで知識を復元

```sh
sh restore.sh
```

作業状態・証拠・障害・次の行動を含めて復元:

```sh
sh restore.sh /path/to/state.json
```

## 実行して試す

```sh
python3 -m unittest -v
# 本体と案件データを分離する。既存ファイルを上書きしない新規ディレクトリを使用。
HARNESS="$(pwd -P)"
CASE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/problem-loop-demo.XXXXXX")"
cp "$HARNESS/example.json" "$CASE_DIR/plan.json"
python3 "$HARNESS/loop.py" init "$CASE_DIR/state.json" --plan "$CASE_DIR/plan.json"
python3 "$HARNESS/loop.py" run "$CASE_DIR/state.json"
sh "$HARNESS/restore.sh" "$CASE_DIR/state.json"
```

`run` は依存関係の解決した工程を選び、実行結果を保存し、検証成功したときだけ次工程に進みます。既定20工程でcheckpoint停止。`--steps 1` なら1工程ずつ。同じコマンドでpending工程から再開します。行動失敗は副作用不明のunknownとなり再送しません。副作用がない/安全に再試行可能と確認した工程のみ `safe_retry: true` を明示するとstalledになります。独立工程は続行します。

計画には目的、完了条件、工程ごとのowner・next_action・depends・command・verify・timeout・authorizedを記述します。command/verifyはshell文字列ではなくargv配列です。検証は対象成果に固有の条件を確認してください。常に成功する検証では意味がありません。

### 分析から計画を変える

失敗ログを読み、仮説と代替行動を新planに記載して:

```sh
python3 loop.py revise demo-state.json --task prepare --plan revised.json --note '観測した原因と、変更で確かめる仮説'
python3 loop.py run demo-state.json
python3 loop.py learn demo-state.json --note '次回にも適用できる知見と適用条件'
```

`revise` は対象1工程のみを更新します。同一計画の盲目的な再試行は拒否します。完了した依存先のある工程を改変する場合は新しいrunを作成してください。新しい権限は付与しません。

### 異常終了

状態を原子的に保存し、行動開始を実行前に記録します。異常終了後はrunningをunknownに変え、行動を再送しません。

```sh
python3 loop.py unlock demo-state.json
python3 loop.py run demo-state.json
python3 loop.py reconcile demo-state.json --task prepare --note '副作用の照合後、検証だけ再実行'
```

unlockは記録されたPIDが存在しない場合のみ可能。別マシンへの移送時にはロックと実プロセスを別途確認してください。reconcileは検証コマンドだけを実行します。verifyは読み取り専用か冪等に設計してください。

## 保存と引き継ぎ

公開する本体（コード・一般化した手順・架空テスト）と、非公開の案件（plan・state・入力・成果物・ログ・request/response）を別ディレクトリで管理します。**実案件は原則として公開checkoutの外へ置いてください。** `loop.py init` の作業rootはplanのあるディレクトリなので、stateだけを外へ置かず、planとstateを同じ案件ディレクトリへ置きます。

`.gitignore` は秘密情報検出やアクセス制御ではありません。任意名の `plan.json`、入力ファイル、メモなどを漏れなく判定できず、既に追跡済みのファイルや `git add -f` も防げません。公開checkout内を使う必要がある場合に限り、全内容を無視する専用 `.private-work/` 配下へ案件一式を置きます。このディレクトリ名は補助策であり、暗号化や非公開ストレージを意味しません。

```text
public/problem-loop-harness/  # 公開する本体のみ
private/case-name/            # 別の非公開作業場所: plan.json, state.json, 入力, 成果物, ログ
```

公開時は変更した本体ファイルを個別に指定し、`git diff --cached --name-only` と `git diff --cached` で対象と内容を確認します。案件ディレクトリを一括追加しないでください。checkpointも内容を点検し、許可された非公開の保存先へ保存・再取得確認します。上記デモの一時ディレクトリは永続保存先ではありません。プログラム本体はGitやLibraryに保存できる独立した資産です。zipとSHA256SUMSで受渡可能です。実行環境の消失に備え、ローカルに置いただけで永続保存済みとは扱わないでください。

## 境界

これは自動で問題を理解するLLMでも、永続schedulerでも、権限制御sandboxでもありません。人またはagentが計画を構築/改訂し、runnerが実行と証拠保存を担います。`authorized: true` は既存許可の記録であり、権限を新設しません。信頼できないplanは実行しないでください。

runnerは1プロセスで逐次実行します。複数担当は別stateに分け、同一成果の書込みを重複させないでください。全state更新コマンドは共通lockで排他します。state更新コマンドはrun停止後に使用します。子孫プロセスを起動するコマンドや外部ジョブには、別途cancel/reconcile/wakeアダプタが必要です。外部待ちの継続は実際の通知/スケジュールIDを得て初めて設定済みとします。このパッケージ単体は実機試験やpushを行いません。

## 推論担当と反復するアダプタ

`adaptive.py` は各実行後、証拠・新イベント・未完状態・自問リストをJSONで信頼済みのローカル推論アダプタのstdinに渡します。アダプタはJSONで `action: continue|revise|stop` と `diagnosis`（原因仮説）、`alternative`（代替案）、`expected_test`（次の検証）を返します。reviseにはtaskとreplacement（工程全体）が必要です。結果を保存し、次周で実行します。既定5周でcheckpoint停止します。

```sh
python3 adaptive.py state.json -- python3 trusted_planner_adapter.py
```

このadapter自体は同梱していません。利用環境の推論担当/APIへ接続する部分です。証拠には秘密が含まれ得るため、外部APIへの転送は許可済み範囲だけで実装してください。返されたコマンドの許可・安全性を審査する責任もtrusted adapterにあります。スクリプトはsandboxではありません。

自動修正できるのはsafe_retryを明示したstalled工程だけです。unknownの再送や許可フラグの拡張は拒否します。実テスト `test_adaptive.py` では「失敗→証拠を受ける推論スタブ→原因/代替/次検証を返す→計画修正→再実行→成果検証成功」の2周を通しています。これは接続プロトコルの試験であり、LLMの推論品質を証明する試験ではありません。

## 環境を失っても再配置する

本体ZIPと、案件ごとの非公開checkpointを分けて環境外に保存します。本体ZIPを新しい作業ディレクトリへ展開し、そのディレクトリで `sha256sum -c SHA256SUMS` と `python3 -m unittest -v` を実行してください。Python 3 標準ライブラリのみで動きます。

案件のstateは作業root直下に置き、必要な入力・成果物を明示して保存します。自動で全ファイルを収集しません。

```sh
python3 checkpoint.py export path/to/state.json case.zip --include artifact.txt
python3 checkpoint.py restore case.zip new-case-directory
python3 loop.py reconcile new-case-directory/state.json --task completed-task --note '復元成果物を信頼済みの読み取り専用検証で再確認'
python3 loop.py run new-case-directory/state.json
```

復元だけではコマンドを実行しません。以前doneだった工程もunknownに戻し、検証だけのreconcileを通すまで依存工程を進めません。行動の自動再送はしません。欠けた入力を復旧済みと扱わないためです。

コマンドに埋め込まれた旧root絶対パス、実行中状態、symlink、不正なZIPパスは拒否します。絶対パスを含む計画は、自動変換せず実行前に見直してください。checkpointのハッシュは破損検出であり、信頼性や実行権限を保証しません。

案件checkpoint・ログ・request/responseには機密が含まれ得ます。公開Gitへは本体・架空テスト・一般化した文書だけを保存し、実案件は非公開の保存先へ保全します。スケジューラと推論担当への接続は環境ごとの別工程です。本ZIP単独では長時間の自律稼働を保証しません。

## 停止状態の永続化

stop判定はstateに保存し、次のプロセス・checkpoint復元後も自動再開しません。`resume` は状況表示のみです。明示的な `unpause` で解除します。実行中コマンドや提出済み外部jobのキャンセル機構は未実装です。詳しくは STOP_CONTRACT.md を参照してください。
