# 変更履歴

Nexus Architect の主な変更点を記録します。

書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づき、
バージョニングは [セマンティック バージョニング](https://semver.org/lang/ja/) に従います。
バージョン番号は `.claude-plugin/marketplace.json` のプラグインごとのバージョンを指し、
3 つのプラグイン（`product`・`architect`・`scalardb`）は同一の番号で一括リリースされます。

## [Unreleased]

## [0.13.0] - 2026-07-07

### 追加
- **`product` プラグイン: `/product:name-product` スキル** — プロダクトを**アルファベット・アクロニム**として
  命名する：各文字が英単語の頭文字になる短く発音可能なラテン文字名で、名前自体が価値フレーズに展開される。
  ビジョン/ポジショニングに根ざして候補を絞り込み、1 案を推奨する。任意実行（`full` プロファイルに含む）。
  新ルール `rules/product/naming-frameworks.md` を追加。**product プラグインは 26 スキルに。**
- **Omnigent 互換レイヤー** — `OMNIGENT.md` とローダー（`tools/omnigent/load-skill.sh`）により、
  汎用マルチエージェント・オーケストレーターが約 90 個の `SKILL.md` を無改変で実行できる。ローダーは
  `plugin:skill` 名をファイルパスに解決し、翻訳プリアンブルを出力し、`${CLAUDE_PLUGIN_ROOT}` を展開する。
  非侵襲（スキルファイルの変更なし）でテスト付き。

### 変更
- **`AGENTS.md` のモデル階層推奨を現行の product 26 スキルに同期**（16 opus / 10 sonnet）。各スキルの
  `model:` frontmatter と両依存マニフェストに一致。

### 修正
- **入れ子 migrate サブスキルの陳腐化フラットパス（12 ファイル 30 箇所）** — 実行可能な `cd` ブロック、
  Related Skills、出力ツリー、抽出スクリプトのコメントが入れ子化前のパス
  （例: `skills/analyze-mysql-schema/...`。正しくは `skills/migrate-mysql/analyze-mysql-schema/...`）を
  参照していた。
- **ドキュメントのドリフト**: README のスキル数を修正（77 → 80）。CLAUDE.md のモデル階層表を修正
  （`analyze` = opus、`report` = haiku）し、product の階層リストを全 26 スキルに補完。CLAUDE.md に
  `/product:design-architecture` を追加。スキルリファレンス（EN/JA）に `/product:create-domain-story` と
  `/product:design-system` を追加。`generate-ui-mock` の説明を実際の駆動源（ドメインストーリー +
  デザインシステム）に更新。
- **パイプラインの範囲を明確化**: `skill-dependencies.yaml` 外の architect 12 スキル（インフラ、
  セキュリティ、オブザーバビリティ、DR、実装、コード生成、コスト見積、セキュリティ調査）を
  `/architect:pipeline` が実行しない**手動拡張ティア**として明記し、pipeline スキルの「全スキル」の
  記述を実態に合わせて修正。
- **product→architect ブリッジ成果物を受け手側で宣言**: `design-microservices` が `architecture.md` /
  `tech-stack-fitness.md` を、`design-api` が `api-design.md` を任意入力として明記（再導出でなく
  リファインするセマンティクス）。
- レビューフェーズの `parallel_with` 宣言を対称化。見出しを `Desired Outcome` / `Decision Criteria` に
  正規化（5 スキル）。scalardb ユーティリティ 5 スキルの説明に「Use when」トリガーを追加。`workflow/` と
  `research/` に位置づけ README を追加。README にドキュメント言語ポリシーを追加。Codex 監査ドキュメントに
  時点スナップショット注記を追加。getting-started（EN/JA）に `samples/ec-monolith` の導線を追加。
  define-requirements の brainstorm ドキュメントの陳腐化した `research/` ファイル名を修正。

### ドキュメント
- getting-started ガイド（EN/JA）に `/product:generate-frontend` を掲載。

## [0.12.0] - 2026-06-29

### 追加
- **`product` プラグイン: `/product:generate-frontend` スキル** — ナビゲート可能な UI モックとアクティブな
  デザインシステムから、**実行可能な React + TypeScript フロントエンド**を `generated/frontend/` に生成する。
  画面を **Atomic Design** で分解し（デザイントークン → atoms → molecules → organisms → templates → pages）、
  デザインシステムの各 `CMP-` を対応する原子レベルのコンポーネントに、各 UI モック画面をページにする。
  コンポーネントは **CSS Modules + CSS 変数**でスタイリングし、デザイントークンのみを参照する（生値は使わない）。
  ストーリーフロー（`next`/`prev`）は **react-router** で配線し、各コンポーネントを **Storybook** に variant/state
  ごとの story として登録する。自己完結でインストール可能な scaffold（React 18 + Vite + Storybook 8 + TS）を出力する。
  新ルール `rules/product/atomic-react-storybook.md` を追加。トレーサビリティに `COMP-`/`PAGE-` ノードを
  `CMP-`/`TOK-`/`STORY-` への Upstream 参照付きで記録する。spec フェーズの `generate-ui-mock` の後に実行する。
  **product プラグインは 25 スキルに。**

### 変更
- **`product` プラグイン: `/product:start` が `generate-frontend` を選択式ステップとして提示**するようになりました。
  UI モックの後に、実行可能な React + Storybook フロントエンドを生成するか対話的に尋ね（インタラクティブ）、
  `--auto` ではプロファイルに従う（`ux-to-spec` / `full` に含まれる）。新フラグ `--frontend` / `--no-frontend` で
  選択を強制でき、決定は `work/pipeline-progress.json` → `options.frontend` に記録する。このステップは非ブロッキングで、
  後続フェーズは生成コードではなくモックを参照する。

## [0.11.0] - 2026-06-26

### 変更
- **`product` プラグイン: `/product:generate-ui-mock` がクリックで遷移できるナビゲート可能なプロトタイプを生成**
  するようになりました。これまでの画面が独立した単一 HTML ファイル群だった状態から、ドメインストーリーの
  番号付きアクティビティ順に画面を並べ、各画面の「フローを前進させるアクション」を次のアクティビティの画面への
  実際の `<a href>` リンクにします。これにより、ストーリー全体をクリックで端から端まで辿れます。各画面には
  戻る/次へのナビゲーションと `step N of M` 表示、分岐は対象画面へのリンク、ストーリーごとのフローインデックス
  （`{STORY}-index.html`）を入口として追加します。ファイル名は決定論的（`{STORY}-NN-{slug}.html`）で、ソースに
  欠けているステップは無効化した `TBD` リンクとして表示します（デッドエンドは作りません）。トレーサビリティに
  画面間の `next`/`prev` エッジを記録します。

## [0.10.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:create-domain-story` スキル** — ペルソナ起点のドメインストーリーテリング。
  アクターはペルソナ（`PER-`）、アクティビティはジョブストーリー（`JOB-`）をジャーニー（`JNY-`）順に並べたもの、
  ワークアイテムは扱う対象から導出する。各ストーリーは「あるペルソナが主要ジョブを遂行する」ハッピーパスの
  シナリオで、ペルソナ×ジョブ単位でスコープする（境界づけられたコンテキストは `--domain` による任意の拡張）。
  UX フェーズの、ジャーニー／ポジショニングの後・UI モックの**前**に実行し、`reports/01_ux/domain-stories/` を
  `STORY-` トレーサビリティ付きで出力する。`/architect:create-domain-story` の product パイプライン版。
- **`product` プラグイン: `/product:design-system` スキル** — **分離管理**のデザインシステムを構築または
  `--import` で取り込む。構築はポジショニング／ペルソナ／ビジョンから **W3C DTCG** トークン
  （color/type/spacing/radius/elevation/motion）を WCAG コントラストゲート付きで導出。`--import` は既存システム
  （Tailwind config / DTCG JSON / Figma Tokens / CSS テーマ）を同一スキーマへ正規化する。出力は `reports/` 配下では
  なく専用の `design-system/<name>/` ツリーに置き、semver の `manifest.json` を持ち、複数の名前付きシステムを
  併存でき、**standalone**（いつでも単独実行可能）。アクティブなシステムは
  `work/pipeline-progress.json` → `options.design_system` に記録する。新ルール
  `rules/product/design-system.md` を追加。**product プラグインは 24 スキルに。**

### 変更
- **`/product:generate-ui-mock` がストーリー駆動＋デザインシステム適用に** — 画面は各ペルソナ×ジョブの
  ドメインストーリーから導出し（1 アクティビティ ≒ 1 画面操作）、アクティブなデザインシステムでスタイリングする。
  各 self-contained 画面に `tokens.css` をインライン注入し、`--fidelity=lo`（トークンのみ）または
  `mid`（トークン＋`CMP-` コンポーネントスタイル）で描画する。システム未設定時はアドホックな lo-fi へフォールバック。
  画面は `STORY-`/`CMP-` もトレースする。
- **UX フェーズの順序** — `full` プロファイルで `create-domain-story` と `design-system` をポジショニングの後・
  `generate-ui-mock` の前に実行し、モックが「選択された流れ」を「共有の視覚言語」で描けるようにした。

## [0.9.0] - 2026-06-24

### 追加
- **`product` プラグイン: `/product:design-architecture` スキル** — 境界づけられたコンテキスト・
  API レイヤー・データモデル・非機能要件を統合してランタイムの全体アーキテクチャを生成し（Mermaid の
  構成図 / クリティカルパス / デプロイ・スケーリングの 3 ビュー）、定型チェックリスト
  **Kong（API Gateway）・ScalarDB・ScalarDB Analytics・ScalarDL** に対する**技術適合度評価**を
  成果物の根拠に基づいて実施。各技術に **採用 / 条件付き採用 / 不採用** の判定と採用理由・配置を出力する。
  ScalarDB / ScalarDL の「採用」は architect プラグインの ScalarDB パイプラインへの橋渡しとなる。
  出力は `reports/03_domain/architecture.md` と `reports/03_domain/tech-stack-fitness.md`。
  `full` プロファイル（`define-nfr` の後の総合ステップ）と依存グラフに追加。新ルール
  `rules/product/architecture-and-tech-fitness.md` を追加。product プラグインは 22 スキルに。
- **product → architect ハンドオフ契約（`docs/design.md`）** — `product` の成果物が `architect`
  プラグインのインプットとしてどう橋渡しされるかの単一の真実。4 つの SKILL/ルールファイルで宙吊りに
  なっていた `design.md` 参照を解消。成果物マッピング（成果物ごとの ID 接頭辞 → `define-requirements`
  の成果物、§1.3）、`product` が供給しない設計上のギャップ（§1.4）、クロスプラグインの
  **トレーサビリティ書き戻し**契約（`FEAT-→FR-` リンク、`NFR-` の verbatim 再利用、§1.5）、
  正典の**適応エンジン**仕様（§7）を定義。

### 変更
- **`/architect:define-requirements` が product 成果物を取り込む** — `reports/0*_*/` の product
  レポートを自動検出し、product の ID を引き継ぎ、`tech-stack-fitness.md` を ScalarDB 適用判定の
  prior として利用し、`FR-`/`NFR-` ノードを `work/traceability.json` へ書き戻す。
- **`/architect:start`・`/architect:pipeline` の product 認識** — 前段でハンドオフ検出を行い、
  product レポートを渡してグリーンフィールドパスへ誘導する。
- **`/product:map-domains`** が `CTX-` ごとに粗い整合性ヒント（`Strong`/`Eventual`/`TBD`）を出力し、
  architect のトランザクション整合性分類の起点とする。
- **`/architect:review-consistency`** がクロスプラグインのトレーサビリティ継続性を検査する。

## [0.8.2] - 2026-06-20

### 変更
- 3 プラグインのバージョンを 0.8.2 に更新。

### ドキュメント
- これまで architect の 43 スキルのうち 41 件しか記載していなかった
  `create-domain-story`（設計）と `review-report`（レポート）を `README.md` および
  スキルリファレンス（en/ja）に追加。
- `/architect:pipeline` のフラグ記載を実態に合わせて修正
  （`--resume-from`・`--rerun-from`・`--skip-{phase}`・`--no-scalardb`・`--lang`）。
- Getting Started / Codex 利用ガイド（en/ja）に `product` プラグインの導線を追加：
  「プロダクトの方向性（グリーンフィールド）」の起点、`/product:*` のスキルマッピング
  （`skills/product/<name>/SKILL.md`）、product のインストールコマンドを追記。

## [0.8.1] - 2026-06-20

### 修正
- `product:` / `scalardb:` 名前空間のスキルが読み込まれないプラグイン名前空間の衝突を修正。
  マーケットプレイス マニフェストで各プラグインに明示的な `skills[]` 配列を持たせ、
  各プラグインが自身のコマンドのみを登録するようにした。

## [0.8.0] - 2026-06-20

### 追加
- **`product` プラグイン**（21 スキル、14 ルール）— プロダクトビジョンから SLA/NFR までを
  対話的・検証駆動で進めるプロダクト方向性パイプライン。深い設計の前に最もリスクの高い前提を
  抽出・検証し、トレーサビリティグラフで変更を再伝播し、システム実装設計のために
  `/architect:define-requirements` へ引き継ぐ。

これにより Nexus Architect は 3 プラグイン構成（`product`・`architect`・`scalardb`）、
合計 75 スキルのツールキットになりました。

## [0.7.0] - 2026-06-11

### 追加
- グリーンフィールドの起点となる `/architect:define-requirements` スキル：機能/非機能要件の
  分類、データ・トランザクション要件分析、ScalarDB 適用判断。`--input`・`--auto`・
  `--no-scalardb` をサポート。

## [0.6.2] - 2026-06-11

### 追加
- ドメインストーリーテリング用の `/architect:create-domain-story` スキル
  （ドメインごとの業務プロセスを可視化）。
- 生成された HTML レポートの品質をレビューする `/architect:review-report` スキル。
- ツールキット検証用の `ec-monolith` サンプルプロジェクト。

### 修正
- フック・スキル・マニフェスト全体のエージェント構成監査の指摘を解消。
- Mermaid バリデータのブロック解析を修復し、ユビキタス言語の用語整合ルールを追加。
- `investigate` スキルに計算手順と自己検証を追加。

## [0.6.1] - 2026-05-12

### 追加
- レビュー・評価スキルでの並列サブエージェント実行。
- スキーマレポート後の `migrate-oracle` SA3/SA4/SA5 ステージの並列化。

### 修正
- 28 ファイルにわたる多視点レビューの修正。
- 移行パイプライン全体のスキル呼び出しとネストされたサブスキルパスを修正。

## [0.6.0] - 2026-05-07

### 追加
- Codex 互換レイヤー（`AGENTS.md`）：Claude Code プラグインをインストールせずに
  同じスキルファイルを Codex から利用可能に。

### 修正
- `/architect:` プレフィックス登録を有効にするため、全 SKILL.md から `name` フィールドを削除。
- スキル監査の指摘（マニフェスト命名、フロントマター、JDBC パターン）を解消。

## [0.5.0] - 2026-03-24

### 変更
- ScalarDB 開発スキルを独立した `scalardb` プラグインに分離。

## [0.4.0] - 2026-03-23

### 追加
- データベース移行（Oracle / MySQL / PostgreSQL → ScalarDB）：スキーマ抽出、移行分析、
  ストアドプロシージャ/トリガーの Java 変換。

## [0.3.0] - 2026-03-23

### 追加
- ScalarDB アプリケーション開発スキル（スキーマモデリング、設定、CRUD/JDBC パターン、
  スキャフォールド、コードレビュー、移行アドバイザリ）。

## [0.2.0]

### 変更
- リポジトリを Claude Code プラグイン互換の構成に再編。
