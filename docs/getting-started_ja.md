# はじめに

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/wfukatsu/nexus-architect.git
cd nexus-architect

# Python依存パッケージ（任意）
pip install -r requirements.txt

# Mermaid CLI（任意、図のレンダリング用）
npm install -g @mermaid-js/mermaid-cli
```

## 基本的な使い方

### Claude Code と Codex

Claude Code では plugin をインストールし、slash command を直接使います。

Codex ではリポジトリ root でセッションを開き、同じコマンド文字列をチャットで依頼してください。`AGENTS.md` が `/product:<name>`、`/architect:<name>`、`/scalardb:<name>` を対応する `SKILL.md` にマッピングします（`/product:<name>` は `skills/product/<name>/SKILL.md` に解決されます）。詳細は [Codex で Nexus Architect を使う](codex-usage_ja.md) を参照してください。

### 1. プロダクトの方向性を決める（グリーンフィールド）

新規プロダクトはここから始めます。ビジョンから SLA/NFR までを検証駆動で進めるパイプラインで、最終的に `/architect:define-requirements` へ引き継ぎます。

```bash
# インタラクティブなパイプライン（深い設計の前に最もリスクの高い前提を検証）
/product:start

# プロファイルでスコープを絞る
/product:start --profile=mvp

# React + Storybook のフロントエンド生成ステップを含める（--no-frontend で除外）
/product:start --frontend

# その後、システム実装設計へ引き継ぐ
/architect:define-requirements
```

UI モックの後、`/product:start` は任意で `/product:generate-frontend` を実行し、モックとアクティブなデザインシステムから実行可能な React + Storybook の scaffold を `generated/frontend/` に生成できます（Atomic Design、トークンスタイリング）。選択式で、対話的に確認するか `--frontend` / `--no-frontend` で強制できます。

プロダクトの名前が必要なときは `/product:name-product` が **アクロニム名** を作ります。各文字が英単語の頭文字になる短く発音可能なアルファベット名で、名前自体がプロダクトの価値を表すフレーズに展開されます（例: `N`ext-generation `E`xtensible e`X`change `U`nified `S`ystem）。展開に使う単語は Vision とポジショニングから取り、候補を絞り込んで 1 案を推奨します。`full` プロファイルでは Vision の後に実行され、任意のタイミングで単体実行もできます。

```bash
/product:name-product                     # 現在の Vision/ポジショニングから生成
/product:name-product --seed=SCALAR       # ベース単語の各文字に対応する英単語を探す
/product:name-product --style=initialism  # 発音可能な単語ではなく文字読み（例: SDK）
```

product スキルの全カタログは [スキルリファレンス](skill-reference_ja.md) を、パイプライン実行前に用意すべきインプットは [product インプット要件ガイド](product-input-requirements_ja.md) を参照してください。

### 2. レガシーシステムの分析

```bash
# インタラクティブワークフロー（推奨）
/architect:start ./path/to/legacy-project

# または個別のスキルをステップごとに実行
/architect:investigate ./path/to/legacy-project
/architect:analyze ./path/to/legacy-project
/architect:evaluate-mmi ./path/to/legacy-project
/architect:evaluate-ddd ./path/to/legacy-project
/architect:integrate-evaluations
```

手元にレガシーシステムがない場合は、同梱のサンプルモノリス `samples/ec-monolith` を
ターゲットパスに指定すると、分析ワークフローを一通り試せます。

レガシー／グリーンフィールド（`/architect:define-requirements`）の各パスで用意すべきインプットは [architect インプット要件ガイド](architect-input-requirements_ja.md) を参照してください。

### 3. フルパイプライン実行

```bash
# 全フェーズを自動実行
/architect:pipeline ./path/to/project

# ScalarDBなしで実行
/architect:pipeline ./path/to/project --no-scalardb

# 分析のみ
/architect:pipeline ./path/to/project --analyze-only

# 特定のフェーズから再開
/architect:pipeline ./path/to/project --resume-from=design-microservices
```

### 4. レビューの実行

```bash
# 5視点並列レビュー（設計完了後）
# /architect:pipeline が自動的に実行しますが、個別に実行することも可能です
```

### 5. コードの生成

コード生成スキルは `/architect:pipeline` に**含まれていません** — パイプラインはレビューと
レポートで終わります。設計完了後に、次の順で自分で呼び出します:

```bash
# 1. 設計をコーディング可能な仕様へ            （要: reports/03_design/）
/architect:design-implementation

# 2. テスト仕様                                （要: reports/06_implementation/）
/architect:generate-test-specs

# 3. アプリケーションコード                    （要: reports/06_implementation/ + scalardb-schema.md）
/architect:generate-scalardb-code             # -> generated/{service}/

# 4. インフラコード                            （要: reports/08_infrastructure/）
/architect:design-infrastructure              # インフラのレポートがまだ無ければ先にこれ
/architect:generate-infra-code                # -> generated/infrastructure/

# 5. 生成物のドキュメント
/architect:generate-docs
```

各ステップが必要とするのは直前のステップのレポートだけなので、それらが既にあれば途中から入れます。
ここでの出力はすべて `generated/` 配下（git-ignore）で、**再実行で上書き**されます — 手で編集して
育てるコードベースではなく、使い捨ての足場として扱ってください。

レポートツリーを一切使わない近道が2つあります: `/scalardb:build-app`（要件から動く ScalarDB
アプリまで）と `/product:generate-frontend`（UI モックから `generated/frontend/` の React +
Storybook スキャフォールドまで）。

### 6. バックログ経由でのコード配送

再生成する足場ではなく、**レビューしてマージするコード**を作る場合はこちらを使います。
プロジェクトの**実際のソースツリー**に書き込み、Issue ごとにマージ済み PR/MR まで進めます:

```bash
# レポート -> トラッカー上の Epic / Sub-Epic / Issue（作成前に必ず承認を求めます）
/architect:export-backlog --target=github --repo=<owner>/<name>
/architect:export-backlog --target=gitlab --project=<group>/<project>

# Epic 配下の全 Issue を実装 -> レビュー -> [あなたの承認] -> マージ
/architect:deliver-backlog --epic=E1

# 1ステップずつ実行する場合
/architect:implement-backlog I1.2.3     # 作業ブランチ上にコード + ドキュメント
/architect:review-issue I1.2.3          # Epic 全体整合レビュー、ブロッカー自動修正、PR/MR 作成
/architect:merge-issue I1.2.3           # プリフライト + 確認、マージ、ロールアップ
```

`deliver-backlog` は半自律です: 人間のゲート（PR/MR 承認、マージ実行、ブロッカーの判断）で必ず
停止し、`reports/backlog/backlog-manifest.json` から再開します。進捗はトラッカー上に
`status::*` ラベル・進捗コメント・チェックボックスとして現れます — 受入基準は実装・検証された
時点で、親のタスクリストのボックスは子が実際にマージされた時点でチェックされます。

前提: 対象プロジェクトに対して `gh` または `glab` が認証済みであること。

### 7. 依存バージョンの選択

生成物がバージョンを pin する場面では、生成時にレジストリから最新状況を調べ、安定版かつ EOL でなく
相互に互換なリリースを選びます。決定表は `work/version-decisions.json` に記録されます。
承認するかどうかは選べます:

```bash
/architect:generate-scalardb-code --confirm-versions      # 決定表を提示して確認する
/product:generate-frontend --no-confirm-versions          # 解決した安定版を確認なしで採用
/architect:implement-backlog I1.2.3 --refresh-versions    # キャッシュを使わず再解決
```

プロジェクト単位で一度だけ決めることもできます（`/architect:start` が出力言語と一緒に尋ねます）:

```json
{ "options": { "confirm_versions": true } }
```

未設定の場合、対話実行では確認し、`--auto` では確認せず採用します。

## 出力の確認

すべての出力は以下のディレクトリに生成されます：

```
reports/          # 分析・設計ドキュメント（Markdown）
generated/        # 生成コード（Java、K8sマニフェスト等）
work/             # パイプライン状態
```

統合HTMLレポート：
```bash
/architect:report
# -> reports/00_summary/full-report.html
```

## 8. ScalarDBアプリケーション開発

```bash
# スキーマをインタラクティブに設計
/scalardb:model

# 完全なスタータープロジェクトを生成
/scalardb:scaffold

# 要件からアプリケーション全体を構築
/scalardb:build-app

# ScalarDBの正確性についてコードレビュー
/scalardb:review-code
```

詳細は [ScalarDB開発ガイド](scalardb-development.md) を参照してください。

## 9. ScalarDBへのデータベース移行

```bash
# 統合エントリポイント（データベースを選択）
/architect:migrate-database

# または特定のデータベースに直接移行
/architect:migrate-oracle
/architect:migrate-mysql
/architect:migrate-postgresql
```

前提条件：Python 3.9以上、データベースクライアントツール、`pip install python-dotenv mysql-connector-python psycopg2-binary`

詳細は [データベース移行ガイド](database-migration.md) を参照してください。

## MCPサーバー（推奨）

- **Serena**：AST レベルのコード分析とシンボル検索に最適
- **Context7**：最新のScalarDBドキュメントの動的取得
