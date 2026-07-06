---
title: Codex 互換性調査
schema_version: 1
skill: repo-research-analyst
generated_at: 2026-05-07
---

# Codex 互換性調査

このドキュメントは、`nexus-architect` リポジトリに含まれる Claude Code 用のエージェント、スキル、ルール、フックを Codex で使う場合に動作が異なる箇所を洗い出したものです。

> **注記（時点情報）**: 本ドキュメントは 2026-05-07 時点のスナップショットです。本文中の「51 skills / 2 plugins」や行番号の引用は当時の構成であり、現在は **3 plugins（product / architect / scalardb）/ 80 skills**（`/product:*` を含む）です。最新の構成は `README.md` と `.claude-plugin/marketplace.json` を参照してください。

## 概要

このリポジトリは Claude Code plugin としては整理されていますが、Codex では `.claude-plugin/marketplace.json` や `.claude-plugin/plugin.json` を plugin として自動登録しません。そのため、`/architect:*` や `/scalardb:*` の slash command は Codex ではそのまま実行できません。

Codex で利用するには、Claude Code 固有の plugin 配布、tool 名、Task サブエージェント、`.claude/` 配下の設定パス、PostToolUse hook を Codex の実行モデルに合わせて移植する必要があります。

## 差分一覧

| 区分 | Codex での影響 | 主な該当箇所 |
|---|---|---|
| Claude plugin 前提 | Codex は `.claude-plugin/marketplace.json` / `plugin.json` を plugin として読まないため、51 skills が `/architect:*` / `/scalardb:*` として登録されない | `README.md:3`, `.claude-plugin/marketplace.json:11` |
| Claude CLI 前提 | `claude plugin marketplace add/install/update` は Codex では使えない | `README.md:10`, `README.md:244` |
| slash command 前提 | `/architect:start`, `/scalardb:model` などは Codex では単なるテキスト。Codex skill として使うには `~/.codex/skills` へ移植するか、対象 `SKILL.md` を明示的に読む必要がある | `CLAUDE.md:16`, `CLAUDE.md:29` |
| Claude tool 名 | `Read`, `Write`, `Edit`, `Bash`, `Glob/Grep`, `WebFetch`, `Task`, `AskUserQuestion`, `Skill` などの指示が多数ある。Codex では AGENTS.md のマッピングに従って置換が必要 | `CLAUDE.md:130`, `skills/investigate/SKILL.md:35` |
| Task / Subagent 設計 | DB migration 系は Claude の `Task` サブエージェントを強く前提にしている。Codex では順次メインスレッドで実行するか、Codex 側の明示的な sub-agent 許可が必要 | `skills/migrate-mysql/SKILL.md:304`, `skills/migrate-mysql/SKILL.md:358`, `skills/migrate-database/SKILL.md:68` |
| AskUserQuestion | Claude の質問ツール前提。Codex では番号付き選択肢をチャットで提示して、ユーザーの回答を待つ必要がある | `skills/migrate-database/SKILL.md:25`, `skills/start/SKILL.md:46` |
| `.claude/` パス前提 | DB 設定、出力、参照 docs が `.claude/...` に固定されている箇所が多い。Codex で使うなら `.codex/` に寄せるか、互換ディレクトリとして `.claude/` を残す判断が必要 | `skills/migrate-mysql/SKILL.md:43`, `skills/review-code/SKILL.md:127`, `skills/docs/SKILL.md:28` |
| `CLAUDE_PLUGIN_ROOT` 前提 | migration 系は `CLAUDE_PLUGIN_ROOT` と `~/.claude/plugins` 探索に依存する。Codex では通常この環境変数はない | `skills/migrate-mysql/SKILL.md:19`, `skills/migrate-mysql/SKILL.md:31` |
| Hooks | `PostToolUse` hook が Claude の `Write/Edit/MultiEdit` tool payload を前提にしているため、Codex の編集では自動発火しない | `hooks/validate-frontmatter.sh:2`, `hooks/validate-mermaid.sh:2` |
| 権限設定 | `.claude/settings.local.json` の `Bash(...)`, `Read(...)` 許可ルールは Codex の sandbox/approval には反映されない | `.claude/settings.local.json:2` |
| WebFetch | `WebFetch` 指示は Codex では web/curl/Context7 相当へ置換が必要。ネットワーク制限下では承認が必要になる場合がある | `skills/docs/SKILL.md:13` |
| model 指定 | `model: sonnet` などの frontmatter は Claude plugin 側の指定で、Codex ではそのまま効かない | `skills/migrate-mysql/SKILL.md:5`, `skills/start/SKILL.md:5` |

## 影響が大きい領域

### 1. Plugin 登録とコマンド起動

`README.md` と `CLAUDE.md` は、Claude Code plugin と slash command を前提にしています。

- `README.md:10` 以降は `claude plugin marketplace add` と `claude plugin install` による導入を説明している
- `CLAUDE.md:16` では `/architect:skill-name` と `/scalardb:skill-name` の利用を前提にしている
- `.claude-plugin/marketplace.json` は 2 plugins と 51 skills の登録情報を持つが、Codex はこの形式を自動解釈しない

Codex で同等に使うには、各 `skills/*/SKILL.md` を Codex skill 形式に移植するか、起動時に対象 skill を明示的に読む運用が必要です。

### 2. Database migration 系スキル

最も Claude Code 依存が強いのは以下の DB migration orchestrator です。

- `skills/migrate-oracle/SKILL.md`
- `skills/migrate-mysql/SKILL.md`
- `skills/migrate-postgresql/SKILL.md`
- `skills/migrate-database/SKILL.md`

これらは次の前提を持ちます。

- `AskUserQuestion` で DB 接続情報を収集する
- `.claude/configuration/databases.env` を読み書きする
- `CLAUDE_PLUGIN_ROOT` または `~/.claude/plugins` から plugin root を探す
- `Task` tool で Bash subagent と general-purpose subagent を起動する
- subagent の `<usage>` block から token 数を抽出する
- 一部フェーズを並列実行する

Codex では、質問は通常のチャット、ファイル操作は shell/apply_patch、subagent 処理は順次実行または明示的な Codex sub-agent 許可に置き換える必要があります。

### 3. 参照パスの不整合

ScalarDB 系 skill の多くは `.claude/docs/` や `.claude/rules/` を参照しますが、このリポジトリ上の実体は主に `skills/common/references/` と `rules/` にあります。

例:

- `skills/docs/SKILL.md:28` は `.claude/docs/` を参照
- `skills/review-code/SKILL.md:127` は `.claude/docs/*` と `.claude/rules/*` を参照
- DB migration 系は `.claude/configuration/databases.env` と `.claude/output/` を参照

Codex 対応では、参照パスをリポジトリ相対パスに統一するか、`.claude/` 互換ディレクトリを生成する必要があります。

### 4. Hooks と検証

`hooks/validate-frontmatter.sh` と `hooks/validate-mermaid.sh` は Claude Code の `PostToolUse` hook payload を標準入力から受け取り、`tool_name` が `Write`, `Edit`, `MultiEdit` の場合にだけ検証します。

Codex の `apply_patch` や shell 編集ではこの hook は自動実行されません。そのため、Codex 対応では以下のどちらかが必要です。

- hooks を手動実行できる検証スクリプトとして整備する
- Codex workflow 側で Markdown/frontmatter/Mermaid 検証コマンドを明示的に実行する

## Codex 対応の推奨方針

1. `AGENTS.md` にある Claude tool mapping を正式な Codex 互換ルールとしてドキュメント化する
2. `CLAUDE_PLUGIN_ROOT` 依存を repo root 検出に置き換える
3. `.claude/` 参照を、互換ディレクトリとして残すか、`work/` / `reports/` / `rules/` / `skills/common/references/` に統一する
4. migration orchestrator の `Task` 前提を、Codex で順次実行できる明示的な手順に書き換える
5. `AskUserQuestion` の JSON 指示を、番号付き選択肢でユーザー回答を待つ形式に書き換える
6. `WebFetch` 指示を、Codex の web/curl/Context7 利用に置き換える
7. hooks を Claude hook 依存から独立した検証コマンドとして実行できるようにする
8. README に Claude Code 向け導入手順とは別に Codex 向け利用手順を追加する

## 優先度

### High

- slash command / plugin 登録が Codex で効かない問題
- DB migration 系の `CLAUDE_PLUGIN_ROOT`, `.claude/configuration`, `Task`, `AskUserQuestion` 依存
- `.claude/docs` / `.claude/rules` 参照の実体不一致

### Medium

- hooks が Codex 編集で自動発火しない問題
- `WebFetch` の置換
- `model: sonnet` など Claude model 指定の無効化

### Low

- README の Claude CLI 専用説明
- `.claude/settings.local.json` の権限ルールが Codex に反映されない問題

## 次の作業候補

Codex 対応を進める場合は、まず `docs/codex-usage_ja.md` のような利用ガイドを追加し、次に migration 系の共通互換ルールを `rules/codex-compatibility.md` として切り出すのがよいです。その後、`migrate-oracle`, `migrate-mysql`, `migrate-postgresql` の 3 ファイルを同じ変換方針で修正できます。
