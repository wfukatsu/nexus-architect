---
description: |
  Comprehensive investigation of the target system covering technology stack, codebase structure, technical debt, and DDD readiness.
  /architect:investigate [target_path] to invoke.
  Used as the first step in legacy system analysis.
model: sonnet
user_invocable: true
---

# System Investigation

## Outcome

Gain a comprehensive understanding of the target system and generate the following four investigation reports:
1. **Technology Stack Analysis** — Languages, frameworks, libraries, external services
2. **Codebase Structure** — Directory layout, module structure, entry points
3. **Issues and Technical Debt** — Problem identification and severity classification (CRITICAL/High/Medium/Low)
4. **DDD Readiness** — Assessment of readiness for migration to domain-driven design

## Judgment Criteria

- Prioritize deep-diving into areas where technical debt is most concentrated
- Especially flag coupling issues that hinder domain decomposition
- Evaluate DDD readiness based on evidence (not speculation); use the scoring formula from @rules/evaluation-frameworks.md — do not estimate the final score independently
- Record any security concerns found

## Prerequisites

| File | Required/Recommended | Description |
|------|---------------------|-------------|
| target_path (argument) | Required | Path to the codebase under investigation |

## Available Resources

- **Serena MCP** — AST analysis via `get_symbols_overview`, `find_symbol` (preferred)
- **Glob/Grep** — File pattern search, keyword search within code
- **Read** — Reading configuration files and dependency definition files
- **Task(Explore)** — Parallel investigation of large codebases

## Execution

### issues-and-debt.md — 集計手順

1. 本文にすべての個別問題（`SEC-xx`、`DEBT-xx`）を書き出す
2. 書き出した項目を実際に数えて深刻度別に集計する
3. その集計結果をサマリーテーブルに記入する

**NG パターン**: サマリーテーブルを先に書いてから本文を埋める。本文と集計値が一致しなくなる。

### ddd-readiness.md — スコア計算手順

1. 12 基準すべてに個別スコア（1〜5）を採点する
2. 採点後、@rules/evaluation-frameworks.md の式で合計スコアを計算する:
   ```
   DDD Score = (0.30 × Strategic_Avg + 0.45 × Tactical_Avg + 0.25 × Architecture_Avg) / 5 × 100
   ```
3. 計算した値を Weighted Score テーブルの合計列に記入する
4. その値を Executive Summary のスコアとして使う

**NG パターン**: Executive Summary に先にスコアを書き、後から個別採点する。合計が一致しなくなる。

## Output

Write output files immediately upon completing each section:

| File | Content |
|------|---------|
| `reports/before/{project}/technology-stack.md` | Technology stack inventory and assessment |
| `reports/before/{project}/codebase-structure.md` | Directory and module structure |
| `reports/before/{project}/issues-and-debt.md` | Technical debt and issues list |
| `reports/before/{project}/ddd-readiness.md` | DDD readiness assessment |

All output files must include YAML frontmatter (title, schema_version: 1, phase, skill, generated_at).

Write all reports in the language configured in `work/pipeline-progress.json` (`options.output_language`).

## Completion

1. All four output files have been written
2. Verify numerical consistency:
   - `ddd-readiness.md`: Executive Summary のスコア = Weighted Score 列の合計（独立推定値ではない）
   - `issues-and-debt.md`: サマリーテーブルの各深刻度カウント = 本文の SEC-xx / DEBT-xx の実件数
3. Update investigate in pipeline-progress.json to "completed"
4. Report a summary of findings and any unresolved concerns

## Related Skills

| Skill | Relationship |
|-------|-------------|
| /architect:analyze | Downstream (uses these investigation results as input) |
| /architect:investigate-security | Related (detailed security investigation) |
