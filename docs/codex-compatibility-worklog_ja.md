---
title: Codex 互換対応 作業履歴
schema_version: 1
skill: repo-research-analyst
generated_at: 2026-05-07
---

# Codex 互換対応 作業履歴

このドキュメントは、`nexus-architect` を Claude Code からも Codex からも利用できるようにするために実施した作業の履歴です。

## 目的

Claude Code plugin としての既存利用方法を維持したまま、Codex でも同じ skill 群を利用できるようにする。

主な方針:

- `.claude-plugin/` と `CLAUDE.md` は残し、Claude Code の導入・slash command は壊さない
- Codex では `AGENTS.md` を互換レイヤーとして使う
- `skills/*/SKILL.md` は Claude Code / Codex の双方から参照できる形を維持する
- Claude Code hook は従来通り自動実行でき、Codex では手動実行できるようにする

## 1. 初期調査

リポジトリ全体を調査し、Claude Code と Codex で動作が異なる箇所を洗い出した。

確認した主な領域:

- `README.md`
- `CLAUDE.md`
- `.claude-plugin/marketplace.json`
- `.claude-plugin/plugin.json`
- `.claude/settings.local.json`
- `skills/*/SKILL.md`
- `skills/common/subagents/*`
- `rules/*`
- `hooks/validate-frontmatter.sh`
- `hooks/validate-mermaid.sh`

主な発見:

- Codex は `.claude-plugin/` を plugin として自動登録しない
- `/architect:*` と `/scalardb:*` は Codex ではそのまま slash command として登録されない
- 多くの skill が Claude Code tool 名である `Read`, `Write`, `Edit`, `Bash`, `Task`, `AskUserQuestion`, `WebFetch` を前提にしている
- migration 系 skill は `CLAUDE_PLUGIN_ROOT`, `.claude/configuration/databases.env`, `.claude/output/`, `Task` subagent に強く依存している
- hooks は Claude Code の `PostToolUse` JSON 入力を前提にしており、Codex からは自動実行されない

調査結果は以下に保存した。

- `docs/codex-compatibility-audit_ja.md`

## 2. Codex 互換レイヤーの追加

Codex がリポジトリ root で読むための `AGENTS.md` を追加した。

追加ファイル:

- `AGENTS.md`

記載した内容:

- `/architect:<name>` を `skills/<name>/SKILL.md` にマッピング
- `/scalardb:<name>` を `skills/<name>/SKILL.md` にマッピング
- `Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `WebFetch`, `AskUserQuestion`, `Task`, `Skill` などの Claude Code tool 参照を Codex の操作に読み替えるルール
- `CLAUDE_PLUGIN_ROOT` を Codex ではリポジトリ root とみなすルール
- `.claude/docs/*` を `skills/common/references/*` に読み替えるルール
- `.claude/rules/*` を `rules/*` に読み替えるルール
- `.claude/configuration/databases.env` と `.claude/output/` は Claude Code / Codex 共有用の互換パスとして残す方針

## 3. Codex 利用ガイドの追加

Codex 用の利用ガイドを英語・日本語で追加した。

追加ファイル:

- `docs/codex-usage.md`
- `docs/codex-usage_ja.md`

記載した内容:

- Codex でのセットアップ
- `/architect:*` と `/scalardb:*` の呼び出し方法
- Claude Code tool 参照の Codex での読み替え表
- 実行時パスの扱い
- `.claude/docs/` / `.claude/rules/` 参照の fallback
- hooks の手動検証方法
- Claude Code 互換性を維持する方針

## 4. README と Getting Started の更新

README に Codex の利用方法を直接反映した。

変更ファイル:

- `README.md`

主な変更:

- 冒頭を Claude Code と Codex の両対応として更新
- `Using with Codex` セクションを追加
- Codex での clone / optional dependency install 手順を追加
- `AGENTS.md` によるマッピングルールを記載
- `/architect:start`, `/architect:pipeline`, `/scalardb:model`, `/scalardb:review-code` の Codex 呼び出し例を追加
- Claude Code tool 参照の Codex 読み替え表を追加
- hooks の手動実行例を追加
- Requirements に Codex を追加
- Documentation に `docs/codex-usage.md` と `docs/codex-usage_ja.md` へのリンクを追加

Getting Started にも Codex への導線を追加した。

変更ファイル:

- `docs/getting-started.md`
- `docs/getting-started_ja.md`

## 5. Hooks の Codex 手動実行対応

Claude Code の `PostToolUse` hook としての互換性を維持したまま、Codex から手動実行できるようにした。

変更ファイル:

- `hooks/validate-frontmatter.sh`
- `hooks/validate-mermaid.sh`

変更内容:

- 検証ロジックを `validate_file` 関数に分離
- 引数に Markdown ファイルを渡した場合は手動検証として実行
- 引数がない場合は従来通り stdin の Claude Code hook JSON を読む
- `Write`, `Edit`, `MultiEdit` 以外の tool では従来通り何もしない

手動実行例:

```bash
hooks/validate-frontmatter.sh reports/before/example/technology-stack.md
hooks/validate-mermaid.sh reports/before/example/codebase-structure.md
```

## 6. レビューで見つかった問題と修正

全体レビューで、hook の Claude Code JSON 入力経由の失敗が正しく非ゼロ終了になっていない問題を発見した。

問題:

- `validate_file` が `return 1` しても、末尾で `exit 0` していた
- そのため、手動実行では失敗するが、Claude Code hook 経由では常に成功扱いになっていた
- Claude Code の自動ブロックが効かなくなるため、互換性上の重大な問題だった

修正:

- `hooks/validate-frontmatter.sh` の末尾を `exit $?` に変更
- `hooks/validate-mermaid.sh` の末尾を `exit $?` に変更

修正後、Claude Code hook JSON 経由でも検証失敗時に `status=1` になることを確認した。

## 7. 実施した検証

実行した検証:

```bash
bash -n hooks/validate-frontmatter.sh
bash -n hooks/validate-mermaid.sh
hooks/validate-mermaid.sh README.md AGENTS.md docs/codex-usage.md docs/codex-usage_ja.md docs/codex-compatibility-audit_ja.md
```

Claude Code hook JSON 入力の成功ケース:

```bash
printf '%s\n' '{"tool_name":"Write","tool_input":{"file_path":"README.md"}}' | hooks/validate-mermaid.sh
```

frontmatter 失敗ケース:

- 手動実行: `status=1`
- Claude hook JSON 経由: `status=1`

Mermaid 失敗ケース:

- 手動実行: `status=1`
- Claude hook JSON 経由: `status=1`

## 8. 変更ファイル一覧

追加:

- `AGENTS.md`
- `docs/codex-compatibility-audit_ja.md`
- `docs/codex-usage.md`
- `docs/codex-usage_ja.md`
- `docs/codex-compatibility-worklog_ja.md`

変更:

- `README.md`
- `docs/getting-started.md`
- `docs/getting-started_ja.md`
- `hooks/validate-frontmatter.sh`
- `hooks/validate-mermaid.sh`

## 9. 現在の状態

Claude Code:

- `.claude-plugin/` と `CLAUDE.md` は維持
- 既存の plugin install と slash command 利用経路は維持
- hooks は `PostToolUse` JSON 入力を引き続き受け付ける
- hook の失敗は非ゼロ終了として返る

Codex:

- `AGENTS.md` により `/architect:*` と `/scalardb:*` の呼び出しルールを提供
- Claude Code tool 参照の読み替えルールを提供
- `.claude/docs/` と `.claude/rules/` の fallback を提供
- hooks を手動実行できる

## 10. 残リスクと今後の候補

残リスク:

- migration 系 skill の本文はまだ Claude Code の `Task` subagent 記述を多く含む。Codex では `AGENTS.md` の読み替えに従って実行できるが、skill 本文自体は未移植
- `AskUserQuestion` の JSON 例は各 skill 内に残っている。Codex では番号付き選択肢に読み替える必要がある
- `.claude/configuration/databases.env` と `.claude/output/` は互換パスとして残しているため、将来 `.codex/` に統一したい場合は追加設計が必要

今後の候補:

- migration 系 skill を Codex / Claude Code 両対応の表現へ段階的に書き換える
- `rules/codex-compatibility.md` を追加し、skill 本文から参照できる共通ルールにする
- hooks の手動検証をまとめる `hooks/validate-all.sh` を追加する
- README の日本語版が必要であれば `README_ja.md` を追加する
