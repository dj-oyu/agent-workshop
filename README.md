# Codex skills

複数のCodex skillを名前別ディレクトリで管理するコレクションです。現在は課題発見・計画・実行・検証・再計画を反復する `problem-loop-harness` を収録します。リポジトリは配布・開発用であり、それ自体をskillフォルダとして扱いません。

```text
.agents/skills/problem-loop-harness/
  SKILL.md              # 発見・適用の入口
  loop.py               # 状態保存・実行・検証
  adaptive.py           # 推論アダプタとの反復
  bridge.py             # 外部jobとの接続
  checkpoint.py         # 非公開案件の保存・復元
  install_skill.py      # manifest検証付き再配置
  PLAYBOOK.md           # 問題解決手順
  README.md             # 実行方法
  SHA256SUMS            # skill内のファイル整合性
```

## 検証と再配置

```sh
cd .agents/skills/problem-loop-harness
sha256sum -c SHA256SUMS
python3 -m unittest -v
# 別の許可済みプロジェクトに、既存skillを上書きせず配置
python3 install_skill.py /path/to/project/.agents/skills/problem-loop-harness
```

repo内で利用するときは追加コピー不要です。Codexがこのrepo内を作業ディレクトリとして開いた状態でskill一覧を確認し、`$problem-loop-harness` で明示呼出してください。変更は自動検出されますが、見えない場合はCodexを再起動してください。

[公式の探索場所](https://learn.chatgpt.com/docs/build-skills): repoでは作業ディレクトリからrepo rootまでの `.agents/skills` が対象です。単なるrootのSKILL.mdや任意の `skills/` フォルダだけではrepo-local自動発見になりません。環境により管理済みskill配置は別に存在するため、グローバル領域を推測して変更しません。

[実行ガイド](.agents/skills/problem-loop-harness/README.md) / [設計手順](.agents/skills/problem-loop-harness/PLAYBOOK.md) / [停止契約](.agents/skills/problem-loop-harness/STOP_CONTRACT.md)

## 検証の範囲

Pythonのテスト・一時プロジェクトへの再配置・ハッシュ一致を検証します。実Codexセッションでの発見・暗黙選択は別工程であり、ファイル配置テストだけで成功とは主張しません。skillはschedulerやsandboxではありません。実案件を継続するには許可済み実行環境と永続wakeへの接続が必要です。private state・モデル・ログは公開repoの外に置いてください。
