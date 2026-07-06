---
title: Claude Code / Codex 動作差異 ギャップ分析
schema_version: 1
skill: repo-research-analyst
generated_at: 2026-05-15
---

# Claude Code / Codex 動作差異 ギャップ分析

Claude Code と Codex の両方で利用できるようにするために、動作が異なる箇所を洗い出したドキュメントです。

> **注記（時点情報）**: 本ドキュメントは 2026-05-15 時点のスナップショットです。本文中の「51 skills」は当時の構成であり、現在は **3 plugins（product / architect / scalardb）/ 80 skills**（`/product:*` を含む）です。最新の構成は `README.md` と `.claude-plugin/marketplace.json` を参照してください。

## 凡例

- ✅ 対応済み（`AGENTS.md` / docs で吸収済み）
- ⚠️ 部分対応（マッピングはあるが実装側に残課題あり）

---

## 1. Plugin 登録・コマンド起動

| 項目 | Claude Code の動作 | Codex の動作 | 状態 |
|---|---|---|---|
| `.claude-plugin/marketplace.json` | 51 skills を `/architect:*` / `/scalardb:*` として自動登録 | 自動登録されない | ✅ `AGENTS.md` で `skills/<name>/SKILL.md` にマッピング |
| `claude plugin marketplace add` / `install` | 有効 | 無効 | ✅ `README.md` に Codex 向け代替手順を記載 |
| `disable-model-invocation: true`（pipeline） | Claude Code plugin system 側で解釈される frontmatter | Codex ではこのフラグ自体は解釈されない | ✅ pipeline を依存グラフに従うオーケストレーターとして扱う旨を `AGENTS.md` に明記済み |

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
| `Task` / Subagent | メインスレッドで順次実行 | ✅ 並列ステップが sequential になる点は `AGENTS.md` で許容済み |
| `Skill` | 対象 SKILL.md を開いて従う | ✅ `AGENTS.md` に記載 |
| `ExitPlanMode` | 無視 | ✅ `AGENTS.md` に記載 |
| `TodoWrite` / `TodoRead` | ローカル todo ファイル（必要な場合のみ） | ✅ `AGENTS.md` に記載 |

---

## 3. PLUGIN_ROOT と subagent テンプレートのパス

Migration 系 skill (`migrate-mysql`, `migrate-oracle`, `migrate-postgresql`) は subagent prompt template を以下の形で参照します：

```
${PLUGIN_ROOT}/skills/common/subagents/mysql/0-test-connection.md
```

現在の対応状況:

- `AGENTS.md` は Codex では repo root を `CLAUDE_PLUGIN_ROOT` として扱うと説明している
- `AGENTS.md` は `${CLAUDE_PLUGIN_ROOT}/skills/common/subagents/<db>/` と legacy の `${CLAUDE_PLUGIN_ROOT}/subagents/<db>/` を `skills/common/subagents/<db>/` に読み替える
- migration 系 skill の Step 0 fallback は `*/architect/*` を検索する
- `migrate-mysql` / `migrate-postgresql` / `migrate-oracle` は Step 0 で求めた `PLUGIN_ROOT` を後続の template path に使う

| 問題 | 状態 |
|---|---|
| Codex での subagent template path | ✅ `AGENTS.md` に明記済み |
| Step 0 fallback の plugin 名 | ✅ `*/architect/*` に修正済み |
| `PLUGIN_ROOT` と `CLAUDE_PLUGIN_ROOT` の混在 | ✅ migration orchestrator 内の後続参照を `PLUGIN_ROOT` に統一済み |

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
| hook の終了コード | 失敗時 non-zero → Claude が自己修正 | 手動実行時 non-zero → Codex は気付くが自動発火はしない | ✅ `AGENTS.md` で対象ファイル編集後の手動実行を must として明記済み |
| `validate-frontmatter.sh` の stdin vs 引数 | stdin JSON で動作 | 引数指定で動作 | ✅ 両モード対応済み |
| `validate-mermaid.sh` の stdin vs 引数 | stdin JSON で動作 | 引数指定で動作 | ✅ 両モード対応済み |

---

## 6. Model 指定

| 項目 | Claude Code | Codex | 状態 |
|---|---|---|---|
| `model: opus` / `sonnet` / `haiku` (frontmatter) | Claude Code の plugin system がモデルを切り替える | このフラグは無視される | ✅ `AGENTS.md` に Codex 向け model recommendation として明記済み |
| `skill-dependencies.yaml` の `model:` フィールド | pipeline がモデルを参照してサブエージェントに指示 | pipeline では参照されない | ✅ Codex では `AGENTS.md` の推奨表を参考情報として使う |

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

## 残存ギャップ一覧

| # | 問題 | 影響 | 状態 |
|---|---|---|---|
| R1 | Codex では Claude Code の `Task` 自動並列実行と `<usage>` block 集計がそのまま再現されない | Migration / review 系の実行時間や metrics 表示が Claude Code と完全一致しない | 運用上の制約。`AGENTS.md` でメインスレッド順次実行に fallback する |
| R2 | Codex の sandbox / approval model は `.claude/settings.local.json` の allowlist を読まない | ネットワークアクセスや一部 shell command で承認が必要になる | 運用上の制約。Codex 側の承認フローに従う |
| R3 | `WebFetch` / `WebSearch` 相当は Codex のネットワーク設定に依存する | `/scalardb:docs` など外部 URL を使う skill が制限環境で止まる可能性がある | 運用上の制約。web access、Context7、または承認済み `curl` を使う |

### 優先度

**High**

- なし

**Medium**

- **R1**: Claude Code の subagent 並列実行と Codex の順次 fallback は実行時間と metrics の差として残る

**Low**

- **R2**: `.claude/settings.local.json` の allowlist は Codex には反映されない
- **R3**: 外部 URL アクセスは Codex の network approval に依存する
