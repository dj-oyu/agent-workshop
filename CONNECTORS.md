# 正式な推論・wake接続

## 今回の環境で確認したこと

- `codex exec` は存在しますが、標準設定による ephemeral / read-only の呼出は app-server 初期化で `Read-only file system` となりました。認証や設定を変更して回避していません。
- 対話側には既存の内部担当への指示と結果取得、および durable task の作成・継続・読取りを行う正式ツールがあります。
- このPythonプロセス内には上記ツール用の認証済みSDKはありません。架空のHTTPエンドポイントやAPIキーを使いません。

## Outbox / Inboxの実接続

Pythonと推論担当の橋渡しを、正式ツールを持つ親担当が行います。

1. `python3 bridge.py request state.json request.json`
2. 親担当がrequestの内容を既存の内部推論担当へ渡す。渡す範囲は許可済みデータのみ。
3. 推論担当が `{"request_id":"...", "decision":{...}}` をresponse.jsonに保存。
4. 親担当が元要求との照合・操作の許可範囲を確認。
5. `python3 bridge.py accept state.json request.json response.json`
6. decisionがcontinue/reviseなら `python3 loop.py run state.json --steps 1` を実行し、次のrequestを作る。stopなら再実行しない。

応答の二重適用、別要求ID、古い状態に対する判断を拒否します。command変更の意味的な権限検査は親担当が担います。authorizedフラグだけで安全を保証しません。

## 永続wakeの運用契約

schedulerが利用できる親担当が、次の内容を保存し、その戻り値のIDを実際に取得して初めてwake設定済みとします。

- 成果の目的と終了条件
- state/request/evidenceの保存物と正規の取得方法
- 待っている具体的なtask turn/jobと現在状態
- 次回はまず実状態を読むこと。成功なら次工程へ、失敗なら仮説・代替を更新
- unknownは副作用照合が先。権限拒否を別経路から再送しない
- 進展なしの同一観測を繰り返さない。期限超過時は具体的な障害を報告
- 通知先と重要成果/判断が必要なときだけ送る条件
- 完了または取消時に終了

スクリプトだけではOS終了後のwakeは保証できません。環境外へ保存していないstateも永続化済みとは扱いません。Library等への保存と取得確認、実際のscheduler登録は別工程です。
