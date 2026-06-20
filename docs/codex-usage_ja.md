# Codex で Nexus Architect を使う

Nexus Architect は引き続き Claude Code plugin として利用できます。同時に、リポジトリ直下の `AGENTS.md` により Codex からも利用できます。

## セットアップ

リポジトリをクローンし、必要に応じて依存パッケージを入れます。

```bash
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect
pip install -r requirements.txt
```

Mermaid のレンダリングが必要な場合は任意で入れます。

```bash
npm install -g @mermaid-js/mermaid-cli
```

## スキルの呼び出し方

Claude Code では `/product:start`、`/architect:start`、`/scalardb:model` のような slash command が使えます。

Codex では同じコマンド文字列をチャットで依頼してください。Codex は `AGENTS.md` のルールに従って対応する `SKILL.md` を読みます。

- `/product:start` -> `skills/product/start/SKILL.md`（product スキルは `skills/product/` 配下にネストされています）
- `/architect:start ./path/to/project` -> `skills/start/SKILL.md`
- `/architect:pipeline ./path/to/project` -> `skills/pipeline/SKILL.md`
- `/scalardb:model` -> `skills/model/SKILL.md`
- `/scalardb:review-code ./path/to/app` -> `skills/review-code/SKILL.md`

次のようにファイルを直接指定しても構いません。

```text
skills/design-microservices/SKILL.md を使って ./target-app の目標アーキテクチャを設計してください。
```

## 互換ルール

Codex では Claude Code の tool 参照を次のように読み替えます。

| Claude Code の参照 | Codex での動作 |
|---|---|
| `Read` | `sed`, `cat`, `rg` などでファイルを読む |
| `Write`, `Edit`, `MultiEdit` | `apply_patch` で編集する |
| `Bash` | shell command を実行する |
| `Glob`, `Grep`, `LS` | `rg --files`, `rg`, `find`, `ls` を使う |
| `WebFetch`, `WebSearch` | Codex の web access、Context7、または承認済み `curl` を使う |
| `AskUserQuestion` | 番号付き選択肢をチャットで提示し、回答を待つ |
| `Task`, `Subagent` | ユーザーが明示的に sub-agent 利用を依頼しない限り、Codex のメインスレッドで実行する |
| `Skill` | 参照された `SKILL.md` を開いて従う |

## 実行時パス

Codex ではリポジトリ root を `CLAUDE_PLUGIN_ROOT` とみなします。

通常の出力先は以下です。

```text
reports/      分析・設計ドキュメント
generated/    生成コード
work/         パイプライン状態と中間コンテキスト
```

一部の database migration スキルは `.claude/configuration/databases.env` と `.claude/output/` を使います。これは Claude Code との互換パスとして残し、Codex からも同じ設定を使えるようにします。

スキルが `.claude/docs/` や `.claude/rules/` の Claude インストール済み参照ファイルを指す場合、Codex ではリポジトリ内の `skills/common/references/` と `rules/` の実体を使います。

Migration スキルが `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/` または `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/<db>/` の subagent prompt template を指す場合、Codex では `skills/common/subagents/<db>/` を使います。

## 検証

Claude Code では hooks を `PostToolUse` hook として自動実行できます。Codex では必要に応じて手動実行してください。

```bash
hooks/validate-frontmatter.sh reports/before/example/technology-stack.md
hooks/validate-mermaid.sh reports/before/example/codebase-structure.md
```

どちらの hook も Claude Code の stdin JSON 形式を引き続き受け付けるため、Claude Code 互換性は維持されます。

## Claude Code 互換性

Claude Code での使い方はこれまで通りです。

```bash
claude plugin marketplace add wfukatsu/nexus-architect
claude plugin install product@nexus-architect --scope user
claude plugin install architect@nexus-architect --scope user
claude plugin install scalardb@nexus-architect --scope user
```

インストール後は、`README.md` に記載された `/product:*`、`/architect:*`、`/scalardb:*` のコマンドを利用できます。
