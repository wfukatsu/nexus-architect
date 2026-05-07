---
title: Claude Code / Codex 動作差異 ギャップ分析
schema_version: 1
skill: repo-research-analyst
generated_at: 2026-05-07
---

# Claude Code / Codex 動作差異 ギャップ分析

Claude Code と Codex の両方で利用できるようにするために、動作が異なる箇所を洗い出したドキュメントです。

## 凡例

- ✅ 対応済み（`AGENTS.md` / docs で吸収済み）
- ⚠️ 部分対応（マッピングはあるが実装側に残課題あり）
- ❌ 未対応（ギャップが残っている）

---

## 1. Plugin 登録・コマンド起動

| 項目 | Claude Code の動作 | Codex の動作 | 状態 |
|---|---|---|---|
| `.claude-plugin/marketplace.json` | 51 skills を `/architect:*` / `/scalardb:*` として自動登録 | 自動登録されない | ✅ `AGENTS.md` で `skills/<name>/SKILL.md` にマッピング |
| `claude plugin marketplace add` / `install` | 有効 | 無効 | ✅ `README.md` に Codex 向け代替手順を記載 |
| `disable-model-invocation: true`（pipeline） | Claude Code plugin system 側で解釈される frontmatter | Codex ではこのフラグ自体は解釈されない | ⚠️ pipeline を依存グラフに従うオーケストレーターとして扱う旨を `AGENTS.md` に明記すると安全 |

---

## 2. Tool 名のマッピング

| Claude Code ツール | Codex での代替 | 状態 |
|---|---|---|
| `Read` | `cat`, `sed`, `rg` | ✅ `AGENTS.md` に記載 |
| `Write` / `Edit` / `MultiEdit` | `apply_patch` | ✅ `AGENTS.md` に記載 |
| `Bash` | shell command | ✅ `AGENTS.md` に記載 |
| `Grep` / `Glob` / `LS` | `rg`, `find`, `ls` | ✅ `AGENTS.md` に記載 |
| `WebFetch` / `WebSearch` | Codex web access / Context7 / `curl` | ✅ `AGENTS.md` に記載（ただし `/scalardb:docs` の具体的な URL fetch は要確認） |
| `AskUserQuestion` | 番号付き選択肢をチャットで提示 | ✅ `AGENTS.md` に記載（7 skills に残存） |
| `Task` / Subagent | メインスレッドで順次実行 | ⚠️ 並列ステップが sequential になる点は許容ずみだが、下記の PLUGIN_ROOT パス問題を含む |
| `Skill` | 対象 SKILL.md を開いて従う | ✅ `AGENTS.md` に記載 |
| `ExitPlanMode` | 無視 | ✅ `AGENTS.md` に記載 |
| `TodoWrite` / `TodoRead` | ローカル todo ファイル（必要な場合のみ） | ✅ `AGENTS.md` に記載 |

---

## 3. PLUGIN_ROOT と subagent テンプレートのパス

**最も具体的なギャップ。**

Migration 系 skill (`migrate-mysql`, `migrate-oracle`, `migrate-postgresql`) は以下の形でテンプレートを参照します：

```
${CLAUDE_PLUGIN_ROOT}/subagents/mysql/0-test-connection.md
```

- `AGENTS.md` は「Codex では repo root を `CLAUDE_PLUGIN_ROOT` として扱う」と説明していますが、
- skill 本文ではその値を `PLUGIN_ROOT` というローカル変数に保存して使います
- 実際のファイルは `skills/common/subagents/mysql/0-test-connection.md` にあります
- repo root = `PLUGIN_ROOT` とすると `<repo-root>/subagents/mysql/` になるが、そのディレクトリは**存在しない**

また `migrate-mysql` の Step 0 フォールバック：

```bash
find ~/.claude/plugins -name "plugin.json" -path "*/scalardb-migration/*"
```

は plugin 名を `scalardb-migration` で検索しているが、実際の plugin 名は `architect` なので**Claude Code でも失敗する**。

| 問題 | 状態 |
|---|---|
| Codex での `PLUGIN_ROOT` = repo root では subagent テンプレートが見つからない | ❌ `AGENTS.md` の subagent パスマッピングが未記載 |
| `scalardb-migration` フォールバックは plugin 名が誤り | ❌ Claude Code でも機能しない（skill 本文のバグ） |

**修正案**: `AGENTS.md` の Runtime Paths セクションに以下を追加する。

```
When a skill references `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/`, use `skills/common/subagents/<db>/` instead.
```

---

## 4. `.claude/` 参照パス

| スキル内の参照パス | 実体の場所 | 状態 |
|---|---|---|
| `.claude/docs/api-reference.md` | `skills/common/references/api-reference.md` | ✅ `AGENTS.md` に fallback マッピング |
| `.claude/docs/exception-hierarchy.md` | `skills/common/references/exception-hierarchy.md` | ✅ |
| `.claude/docs/schema-format.md` | `skills/common/references/schema-format.md` | ✅ |
| `.claude/docs/interface-matrix.md` | `skills/common/references/interface-matrix.md` | ✅ |
| `.claude/docs/sql-reference.md` | `skills/common/references/sql-reference.md` | ✅ |
| `.claude/docs/code-patterns/*` | `skills/common/references/code-patterns/*` | ✅ |
| `.claude/rules/*` | `rules/*` | ✅ |
| `.claude/configuration/databases.env` | 互換パスとして `.claude/configuration/databases.env` を維持 | ✅ |
| `.claude/output/` | 互換パスとして `.claude/output/` を維持 | ✅ |

---

## 5. Hooks の自動実行

| 項目 | Claude Code | Codex | 状態 |
|---|---|---|---|
| `PostToolUse` hook の自動発火 | Write/Edit 後に自動実行 | `apply_patch` では自動実行されない | ✅ 手動実行サポートを追加済み |
| hook の終了コード | 失敗時 non-zero → Claude が自己修正 | 手動実行時 non-zero → Codex は気付かない | ⚠️ Codex 側での hook 実行を促す記述は `AGENTS.md` にあるが、強制はできない |
| `validate-frontmatter.sh` の stdin vs 引数 | stdin JSON で動作 | 引数指定で動作 | ✅ 両モード対応済み |
| `validate-mermaid.sh` の stdin vs 引数 | stdin JSON で動作 | 引数指定で動作 | ✅ 両モード対応済み |

---

## 6. Model 指定

| 項目 | Claude Code | Codex | 状態 |
|---|---|---|---|
| `model: opus` / `sonnet` / `haiku` (frontmatter) | Claude Code の plugin system がモデルを切り替える | このフラグは無視される | ⚠️ `AGENTS.md` 未記載。Codex は現在のモデルで全 skill を実行する |
| `skill-dependencies.yaml` の `model:` フィールド | pipeline がモデルを参照してサブエージェントに指示 | pipeline では参照されない | ❌ Codex でパイプラインを実行する場合、モデル選択の根拠が失われる |

### 各 skill の model 指定一覧（Codex での参考情報）

| model | 該当 skill |
|---|---|
| opus | analyze, design-api, design-data-layer, design-implementation, design-infrastructure, design-microservices, design-scalardb, generate-scalardb-code, map-domains, redesign |
| sonnet | analyze-data-model, design-disaster-recovery, design-observability, design-scalardb-analytics, design-security, estimate-cost, evaluate-ddd, evaluate-mmi, generate-infra-code, generate-test-specs, integrate-evaluations, investigate, investigate-security, migrate-database, migrate-mysql, migrate-oracle, migrate-postgresql, pipeline, review-business, review-consistency, review-data-integrity, review-operations, review-risk, review-scalardb, review-synthesizer, select-scalardb-edition |
| haiku | init-output, render-mermaid |

---

## 7. 並列実行

| 項目 | Claude Code | Codex | 状態 |
|---|---|---|---|
| `parallel_with` フェーズ（pipeline） | Task tool で並列実行 | メインスレッドで順次実行 | ✅ `AGENTS.md` に許容として記載 |
| migrate-mysql Steps 10: 2 subagent 同時起動 | 1 メッセージで 2 つの Task を送信 | 順次実行に fallback | ✅ `AGENTS.md` で許容（ただし所要時間が増加） |
| review-consistency / review-operations などの並列レビュー | Task で同時起動 | 順次実行 | ✅ `AGENTS.md` で許容 |

---

## 8. WebFetch / 外部 URL アクセス

| スキル | アクセス先 | 状態 |
|---|---|---|
| `/scalardb:docs` | `https://scalardb.scalar-labs.com/llms-full.txt` | ⚠️ Codex の network access が有効であれば `curl` や Context7 で代替可能。ネットワーク制限環境では失敗する。`AGENTS.md` に記載あり |

---

## 9. `.claude/settings.local.json` の権限設定

| 項目 | Claude Code | Codex | 状態 |
|---|---|---|---|
| `Bash(...)` / `Read(...)` の allowlist | Claude Code の承認画面をバイパス | Codex の sandbox model には反映されない | ✅ 既知の差異（ドキュメント化済み） |

---

## 残存ギャップ一覧（要対応）

| # | 問題 | 影響 | 推奨対応 |
|---|---|---|---|
| G1 | `PLUGIN_ROOT/subagents/<db>/` → 実体は `skills/common/subagents/<db>/` だが AGENTS.md に明示なし | Migration 系で subagent テンプレートが見つからない | `AGENTS.md` の Runtime Paths に `${CLAUDE_PLUGIN_ROOT}/subagents/` → `skills/common/subagents/` のマッピングを追加 |
| G2 | migrate-mysql/oracle/postgresql Step 0 のフォールバックが `*/scalardb-migration/*` を検索する（plugin 名が誤り） | Claude Code でも Codex でも STEP 0 fallback が動作しない | skill 本文を修正：`find ~/.claude/plugins -name "plugin.json" -path "*/architect/*"` に変更するか、fallback ごと削除してリポジトリ相対パスに固定 |
| G3 | `disable-model-invocation: true`（pipeline skill）が Codex で解釈されない | Codex では frontmatter フラグによる特別扱いがないため、pipeline の実行規約が曖昧になる | `AGENTS.md` に「pipeline SKILL.md は `skill-dependencies.yaml` を読んで順次 SKILL.md を呼び出すオーケストレーターとして動作する」旨を記載 |
| G4 | `model: opus/sonnet/haiku` フラグが Codex で無視される | 重い分析（analyze, redesign 等）が軽量モデルで実行されるリスク | `AGENTS.md` に model 推奨表を追加（ユーザーへの参考情報として） |
| G5 | hooks の強制実行が Codex でできない | frontmatter / Mermaid の検証が保証されない | `AGENTS.md` の "After editing" セクションをより強い指示（should → must）に変更し、実行コマンド例を明示 |

### 優先度

**High（実害あり）**

- **G1**: Codex で Migration 系 skill を実行した場合、subagent テンプレートが見つからずフェーズが中断する
- **G2**: `scalardb-migration` フォールバックは Claude Code でも動作しない。plugin 名の誤りで両環境に影響

**Medium**

- **G3**: pipeline skill の `disable-model-invocation` フラグは Codex で解釈されないため、pipeline 実行規約を明文化した方がよい
- **G4**: model 指定が失われ、全 skill が同じモデルで動く

**Low**

- **G5**: hooks の手動実行の強制は AGENTS.md の文言調整のみで対応可能
