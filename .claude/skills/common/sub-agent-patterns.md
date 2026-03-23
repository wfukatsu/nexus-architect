# サブエージェントパターン集

スキル実行中にTask toolで呼び出すサブエージェントの8つの再利用パターン。

## Pattern 1: コードベース探索

大規模コードベースの構造調査に使用。

```
Task(subagent_type="Explore",
  prompt="調査対象 {target_path} のパッケージ構造を探索し、
    主要モジュール一覧と依存関係をJSON形式でまとめてください。",
  description="コードベース構造調査")
```

## Pattern 2: 前フェーズ出力読み込み

コンテキストウィンドウ保護のため、前フェーズの出力をサブエージェントで要約。

```
Task(subagent_type="Explore",
  prompt="以下のファイルを読み込み、{current_skill}に必要な情報を抽出:
    必須: reports/02_evaluation/mmi-overview.md
    抽出項目: 1. モジュール別MMIスコア 2. BC候補 3. 主要改善点
    結果をMarkdown形式で返してください。",
  description="前フェーズ出力読み込み")
```

## Pattern 3: アーキテクチャ分析

マイクロサービスパターンの検出と評価。

```
Task(subagent_type="general-purpose",
  prompt="対象システムのアーキテクチャパターンを分析:
    - 通信パターン（同期/非同期）
    - データ所有パターン
    - 障害伝搬パス",
  description="アーキテクチャパターン分析")
```

## Pattern 4: コード生成

設計仕様からのコード合成。

```
Task(subagent_type="general-purpose",
  prompt="以下の設計仕様に基づきSpring Boot + ScalarDBコードを生成:
    - エンティティ: {entities}
    - リポジトリ: {repositories}
    @.claude/rules/scalardb-coding-patterns.md を参照",
  description="ScalarDBコード生成")
```

## Pattern 5: エンティティ抽出

ドメインモデルの自動識別。

```
Task(subagent_type="Explore",
  prompt="{target_path} からドメインエンティティを抽出:
    - クラス名、属性、関連
    - ビジネスルール（バリデーション）
    結果をテーブル形式で返してください。",
  description="エンティティ抽出")
```

## Pattern 6: 比較分析

複数ドキュメントの横断的比較。

```
Task(subagent_type="general-purpose",
  prompt="以下の2つの設計案を比較分析:
    - 案A: {file_a}
    - 案B: {file_b}
    比較軸: 性能、保守性、移行コスト、リスク",
  description="設計案比較")
```

## Pattern 7: マルチドキュメント統合

複数の分析結果を1つのレポートに統合。

```
Task(subagent_type="general-purpose",
  prompt="以下の分析結果を統合レポートにまとめてください:
    {file_list}
    重複を排除し、優先度順に整理してください。",
  description="分析結果統合")
```

## Pattern 8: 制約充足確認

設計の実現可能性検証。

```
Task(subagent_type="general-purpose",
  prompt="以下の設計が制約条件を満たすか検証:
    設計: {design_file}
    制約: 2PC最大3サービス、OCC競合率5%未満、レイテンシ100ms以下
    違反箇所と代替案を報告してください。",
  description="制約充足検証")
```
