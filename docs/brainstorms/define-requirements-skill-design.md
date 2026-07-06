# 設計案: `/architect:define-requirements` スキル

- **ステータス**: Draft（レビュー待ち）
- **作成日**: 2026-06-11
- **対象バージョン**: architect plugin 0.6.2 → 0.7.0

## 1. 目的と位置づけ

要件定義を行う新スキル `define-requirements` を architect プラグインに追加する。

- **Greenfield パスの起点**: 現在 `/architect:start` の greenfield パスには要件を成果物として固定するステップがなく、`workflow/greenfield/01_requirements_analysis.md` の手順書が存在するのみ。本スキルはこれをスキル化し、greenfield の Phase 0 とする
- **Legacy パスでも利用可能**: 独立スキルとして、`investigate` 完了後に As-Is/To-Be 要件を整理する用途でも起動できる（依存は持たない）
- **追加情報のインプット対応**: 与えられた情報（引数・既存成果物）に加えて、`--input` による資料投入と対話ヒアリングの両方で追加情報を取り込める

### 設計方針

1. **既存資産の参照、複製はしない** — FR/NFR 分類テーブル、ScalarDB 適用判定ツリー、XA 比較表は `workflow/greenfield/01_requirements_analysis.md` に既にあるため、スキルからテンプレートとして参照する
2. **`create-domain-story` の対話パターンを踏襲** — 「対話モード（デフォルト）+ `--auto` モード」「段階的ファシリテーション」の構成を再利用する
3. **ギャップ駆動ヒアリング** — 投入された資料を先に読み、埋まらなかった項目だけを質問する。資料が十分なら質問は最小限になる

## 2. 起動インターフェース

```
/architect:define-requirements [target_path] [--input=<file|dir>]... [--auto] [--no-scalardb]
```

| 引数/フラグ | 必須 | 説明 |
|------------|------|------|
| `target_path` | 任意 | 参照する既存コードベース（brownfield 的な要件定義の場合） |
| `--input=<file\|dir>` | 任意・複数可 | 追加インプット資料: RFP、議事録、既存設計書、業務フロー図など。Markdown/テキストを Read で取り込む |
| `--auto` | 任意 | ヒアリングを省略し、投入資料と既存成果物のみから生成。不明項目は `TBD` + Open Questions に記録 |
| `--no-scalardb` | 任意 | ScalarDB 適用判定（Step 4）をスキップ |

## 3. SKILL.md 設計

### 3.1 フロントマター

```yaml
---
description: |
  Define system requirements through document intake and interactive elicitation.
  Classifies functional/non-functional requirements, analyzes data and transaction
  requirements, and assesses ScalarDB applicability.
  /architect:define-requirements [target_path] [--input=<file|dir>] [--auto] [--no-scalardb] to invoke.
  Entry point for the greenfield design path. Can also run standalone or after
  /architect:investigate on the legacy path. Accepts additional input documents
  (RFP, meeting notes, existing design docs) via --input.
model: opus
user_invocable: true
---
```

- **model: opus** — 要件の引き出し・分類・適用判定は推論負荷が高い。`analyze` / `redesign` と同格の opus とする

### 3.2 本文構成（既存スキルのセクション規約に準拠）

| セクション | 内容 |
|-----------|------|
| Outcome | 4成果物（§4）の生成。FR/NFR が ID 付きで分類され、整合性要求レベルとトレース可能であること |
| Judgment Criteria | 推測で要件を捏造しない（資料・回答に根拠を持つ）。数値目標（レイテンシ/スループット/RPO/RTO）は必ず確認し、得られなければ TBD として Open Questions に残す。整合性要求は業務プロセス単位で判定する |
| Prerequisites | 下表（§3.3）|
| Available Resources | Read（資料取込）、Glob/Grep（target_path 調査）、AskUserQuestion（ヒアリング）、`workflow/greenfield/01_requirements_analysis.md`（テンプレート・判定ツリー）、`research/02_scalardb_usecases_{en,ja}.md`・`research/15_xa_heterogeneous_investigation_{en,ja}.md`（適用判定根拠） |
| Execution | 5ステップ（§3.4）+ 実行モード（§3.5）|
| Output | 4ファイル（§4）+ フロントマター規約 |
| Completion | 完了条件チェックリスト + `work/pipeline-progress.json` 更新 |
| Related Skills | start / investigate / analyze / select-scalardb-edition との関係 |

### 3.3 Prerequisites（入力テーブル）

| 入力 | 必須/推奨 | 取得元 |
|------|----------|--------|
| `--input` 資料（RFP、議事録、設計書等） | 推奨 | ユーザー指定 |
| `target_path`（既存コードベース） | 任意 | ユーザー指定 |
| `reports/before/{project}/*.md` | 任意 | /architect:investigate（legacy パスで実行済みの場合、自動検出して入力に加える） |
| `work/pipeline-progress.json` | 推奨 | /architect:init-output（無ければ単独実行とみなし `output_language` をユーザーに確認） |

いずれも無い場合は対話ヒアリングのみで進行する（`--auto` との併用時はエラー）。

### 3.4 実行ステップ

```
Step 1: Intake（資料取込とギャップ分析）
  - --input 資料、target_path、既存 investigate 成果物を読み込む
  - 要件テンプレートの各項目（FR/NFR/データ/整合性/制約）に対し
    「資料から判明 / 未判明」をマッピングし、ギャップリストを作る

Step 2: Elicitation（ギャップ駆動ヒアリング）※ --auto 時はスキップ
  - ギャップリストの項目のみ AskUserQuestion で質問（§3.5 の5ステージ）
  - 回答ごとにギャップリストを更新し、全項目が判明または TBD 確定で終了

Step 3: Classification（要件分類・整理）
  - FR-xxx / NFR-xxx の ID 付与、優先度（High/Mid/Low）、関連サービス、
    データ整合性要求を分類テーブルに整理
  - データ要件: 現行/想定 DB 棚卸し、トランザクション要求マトリクス
    （Strong Consistency / Eventual Consistency / Local Tx の3レベル判定）

Step 4: ScalarDB Applicability（適用判定）※ --no-scalardb 時はスキップ
  - workflow/greenfield/01 の判定ツリーに従い評価
  - XA vs ScalarDB 比較表を記入し、判定結果と根拠を記録
  - 結果は推奨であり最終決定は select-scalardb-edition / start に委ねる

Step 5: Review & Output（確認と出力）
  - ドラフトを提示しユーザー確認（--auto 時は省略）
  - 4成果物を書き出し、pipeline-progress.json の phase を completed に更新
```

### 3.5 ヒアリング設計（対話モード・5ステージ）

`create-domain-story` の7ステージ・ファシリテーションに倣い、各ステージは「資料から判明済みの内容を提示 → 確認・補完を求める」形式とする。

| ステージ | 確認内容 |
|---------|---------|
| 1. Business Context | 事業目的、対象業務、ステークホルダー、スコープ（in/out） |
| 2. Functional Requirements | 主要業務プロセス、ユースケース、アクター |
| 3. Non-Functional Requirements | 性能（レイテンシ/スループットの数値目標）、可用性、RPO/RTO、セキュリティ/コンプライアンス |
| 4. Data & Integration | データ種別と量、既存/想定 DB、外部連携、業務プロセスごとの整合性要求 |
| 5. Constraints | 技術制約（言語/クラウド/既存資産）、体制、予算、スケジュール |

質問は1ステージあたり最大3問を目安にし、判明済み項目は質問しない（ギャップ駆動）。

## 4. 出力設計

出力先は **`reports/00_requirements/`** を新設する。`01_analysis` より前段の成果物であることを番号で表現する（`00_summary` と番号が重なるが、summary は最終レポートの集約先であり工程順を示すものではないため許容する）。

| ファイル | 内容 | 条件 |
|---------|------|------|
| `reports/00_requirements/requirements-definition.md` | ビジネスコンテキスト、スコープ、FR/NFR 分類テーブル、優先度、アクター一覧 | 常時 |
| `reports/00_requirements/data-transaction-requirements.md` | DB 棚卸し、トランザクション要求マトリクス、整合性レベル判定 | 常時 |
| `reports/00_requirements/scalardb-applicability.md` | 適用判定ツリー結果（Mermaid）、XA 比較表、判定根拠 | `--no-scalardb` 以外 |
| `reports/00_requirements/open-questions.md` | 未確定事項（TBD）、確認先、後続フェーズへの影響 | 常時 |

### 出力フロントマター（バリデーションフック準拠）

```yaml
---
title: "Requirements Definition: {project}"
schema_version: 1
phase: "Phase 0: Requirements"
skill: define-requirements
generated_at: "ISO8601"
mode: "interactive|auto"
input_files:
  - <取り込んだ --input 資料のパス>
---
```

本文は `work/pipeline-progress.json` の `options.output_language` に従う（既存規約どおり）。Mermaid 図（適用判定ツリー、コンテキスト図）は `@rules/mermaid-best-practices.md` に準拠。

## 5. パイプライン統合

### 5.1 `skills/common/skill-dependencies.yaml`

greenfield 用フェーズとして追加（既存 yaml は legacy のみのため、初の greenfield エントリとなる）:

```yaml
  # Phase: Requirements (greenfield entry point; optional on legacy path)
  define-requirements:
    category: requirements
    depends_on: []
    optional: true          # legacy パイプラインの既存挙動に影響を与えない
    outputs:
      - reports/00_requirements/requirements-definition.md
      - reports/00_requirements/data-transaction-requirements.md
      - reports/00_requirements/scalardb-applicability.md
      - reports/00_requirements/open-questions.md
    model: opus
```

### 5.2 `skills/start/SKILL.md`

Greenfield パスの記述を更新:

- 「User describes requirements only -> Greenfield design path」の直後に、**最初に `/architect:define-requirements` を実行**するステップを追加
- ScalarDB Usage Decision は `scalardb-applicability.md` の判定結果を第一の根拠として参照するよう変更（現在はユーザー発言ベースのヒューリスティックのみ）

### 5.3 `templates/output-structure.md`

ディレクトリ構造図の先頭に `00_requirements/` セクションを追記し、後続スキルとの依存関係（`design-scalardb` / `design-data-layer` / `map-domains` が参照可能）を記載する。

## 6. 変更ファイル一覧（実装チェックリスト）

| # | ファイル | 変更 |
|---|---------|------|
| 1 | `skills/define-requirements/SKILL.md` | 新規作成（本設計 §3） |
| 2 | `.claude-plugin/marketplace.json` | architect の `skills` 配列に `./skills/define-requirements` を追加（`./skills/start` の直後、工程順を保つ）。version 0.7.0 |
| 3 | `.claude-plugin/plugin.json` | version 0.7.0 |
| 4 | `skills/common/skill-dependencies.yaml` | §5.1 のフェーズ追加 |
| 5 | `templates/output-structure.md` | `00_requirements/` 追記 |
| 6 | `skills/start/SKILL.md` | §5.2 のルーティング更新 |
| 7 | `docs/skill-reference.md` / `docs/skill-reference_ja.md` | Orchestration の次に「Requirements」セクションを新設しテーブル追加 |
| 8 | `CLAUDE.md` | Command Reference（Investigation & Analysis の前）に追加 |
| 9 | `README.md` | スキル数更新（architect 40→41、全体 51→52） |

`AGENTS.md` は汎用マッピングのため変更不要。SKILL.md 内で使用するツールは AGENTS.md のツール対応表に載っているもの（Read / Glob / Grep / AskUserQuestion / Write）に限定し、Codex 互換を維持する。

## 7. テスト計画

1. **入力資料あり（auto）**: `docs/brainstorms/sample-ec-monolith-requirements.md` を `--input` に渡し `--auto` で実行 → 4成果物が生成され、フロントマター/Mermaid バリデーションフックを通過すること
2. **対話モード**: 資料なしで起動し、5ステージのヒアリングが行われ、回答が FR/NFR テーブルに反映されること
3. **ギャップ駆動の確認**: 資料に NFR 数値が含まれる場合、ステージ3でその数値を再質問しないこと
4. **`--no-scalardb`**: `scalardb-applicability.md` が生成されず、他3ファイルは生成されること
5. **プラグイン認識**: ローカルマーケットプレイス再インストール後、`/architect:define-requirements` が認識されること
6. **legacy パス非干渉**: `/architect:pipeline` を既存プロジェクトで実行し、define-requirements が強制実行されないこと（optional）

## 8. 検討した代替案

| 論点 | 採用案 | 代替案と不採用理由 |
|------|--------|------------------|
| 出力先 | `reports/00_requirements/` 新設 | `reports/01_analysis/` 同居 → analyze の成果物契約を汚染する。`before/` → legacy の investigate 専用領域のため意味が混ざる |
| ScalarDB 判定の所在 | 本スキルに含める（`--no-scalardb` で省略可） | `select-scalardb-edition` に全委譲 → 同スキルはエディション選択が責務で、適用可否judgment は要件（整合性要求）と不可分なため本スキル側に置く |
| ヒアリング方式 | ギャップ駆動（資料を先に読み不足のみ質問） | 全項目質問 → 資料を渡したのに同じことを聞かれる体験が悪い |
| 依存グラフ | `optional: true` で追加 | greenfield 専用 yaml 分割 → オーケストレーター変更が大きくなるため将来課題とする |

## 9. 未決事項

- [ ] `start` の greenfield パスで define-requirements を必須とするか、推奨に留めるか（本案は推奨: 既に要件書があるユーザーは `--input` + `--auto` で形式変換的に通すこともできる）
- [ ] PDF/Word 形式の `--input` 対応（Read は PDF 可。docx は対象外のため初版はテキスト/Markdown/PDF までとする案）
- [ ] バージョンを 0.7.0（minor）とするか 0.6.3（patch)とするか — 新スキル追加のため minor を推奨
