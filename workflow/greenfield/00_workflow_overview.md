# ScalarDB × マイクロサービス 実装計画ワークフロー

## 概要

本ワークフローは、ScalarDB Clusterを活用したマイクロサービスアーキテクチャの実装計画を、段階的かつ体系的に策定するためのガイドである。調査フェーズ（`research/`ディレクトリ）の成果物を入力として、実装可能な計画を出力する。

## 全体フロー

```mermaid
flowchart TD
    subgraph Phase1["Phase 1: 要件・判断"]
        W01["01 要件分析・適用判断"]
        W02["02 ドメインモデリング"]
        W03["03 ScalarDB適用範囲決定"]
    end

    subgraph Phase2["Phase 2: 設計"]
        W04["04 データモデル設計"]
        W05["05 トランザクション設計"]
        W06["06 API・インターフェース設計"]
    end

    subgraph Phase3["Phase 3: 基盤"]
        W07["07 インフラストラクチャ設計"]
        W08["08 セキュリティ設計"]
        W09["09 オブザーバビリティ設計"]
        W10["10 障害復旧・DR設計"]
    end

    subgraph Phase4["Phase 4: 実行"]
        W11["11 実装ガイド"]
        W12["12 テスト戦略"]
        W13["13 デプロイ・ロールアウト"]
    end

    W01 --> W02 --> W03
    W03 --> W04 --> W05 --> W06
    W06 --> W07
    W07 --> W08
    W07 --> W09
    W07 --> W10
    W08 --> W11
    W09 --> W11
    W10 --> W11
    W11 --> W12 --> W13

    style Phase1 fill:#e8f5e9,stroke:#4caf50
    style Phase2 fill:#e3f2fd,stroke:#2196f3
    style Phase3 fill:#fff3e0,stroke:#ff9800
    style Phase4 fill:#fce4ec,stroke:#e91e63
```

## フェーズ一覧

| フェーズ | ステップ | ファイル | 入力（調査資料） | 成果物 |
|---------|---------|---------|----------------|--------|
| **Phase 1** | 01 要件分析・適用判断 | [01_requirements_analysis.md](./01_requirements_analysis.md) | `00_summary`, `02_usecases`, `15_xa` | 要件一覧、ScalarDB適用判定結果 |
| | 02 ドメインモデリング | [02_domain_modeling.md](./02_domain_modeling.md) | `01_microservice`, `03_logical_data_model` | 境界コンテキスト図、集約設計 |
| | 03 ScalarDB適用範囲決定 | [03_scalardb_scope_decision.md](./03_scalardb_scope_decision.md) | `02_usecases`, `07_transaction`, `15_xa` | ScalarDB管理対象テーブル一覧 |
| **Phase 2** | 04 データモデル設計 | [04_data_model_design.md](./04_data_model_design.md) | `03_logical_data_model`, `04_physical_data_model`, `05_db_investigation` | スキーマ定義、DB選定結果 |
| | 05 トランザクション設計 | [05_transaction_design.md](./05_transaction_design.md) | `07_transaction_model`, `09_batch`, `13_317_deep_dive` | トランザクション境界定義 |
| | 06 API・インターフェース設計 | [06_api_interface_design.md](./06_api_interface_design.md) | `08_transparent_data_access`, `01_microservice` | API仕様、サービス間通信設計 |
| **Phase 3** | 07 インフラ設計 | [07_infrastructure_design.md](./07_infrastructure_design.md) | `06_infrastructure`, `13_317_deep_dive` | K8sマニフェスト、Helm values |
| | 08 セキュリティ設計 | [08_security_design.md](./08_security_design.md) | `10_security` | セキュリティポリシー、RBAC設計 |
| | 09 オブザーバビリティ設計 | [09_observability_design.md](./09_observability_design.md) | `11_observability` | ダッシュボード定義、アラートルール |
| | 10 障害復旧設計 | [10_disaster_recovery_design.md](./10_disaster_recovery_design.md) | `12_disaster_recovery` | DR計画、バックアップ設計 |
| **Phase 4** | 11 実装ガイド | [11_implementation_guide.md](./11_implementation_guide.md) | 全設計成果物 | 実装タスク一覧、優先順位 |
| | 12 テスト戦略 | [12_testing_strategy.md](./12_testing_strategy.md) | 全設計成果物 | テスト計画、品質基準 |
| | 13 デプロイ・ロールアウト | [13_deployment_rollout.md](./13_deployment_rollout.md) | `06_infrastructure`, `12_disaster_recovery` | デプロイ手順、カナリア計画 |

## テンプレート

| テンプレート | ファイル | 用途 |
|------------|---------|------|
| サービス設計書 | [templates/service_design_template.md](./templates/service_design_template.md) | 各マイクロサービスの設計書テンプレート |
| データモデル定義書 | [templates/data_model_template.md](./templates/data_model_template.md) | テーブル設計・スキーマ定義テンプレート |
| レビューチェックリスト | [templates/review_checklist.md](./templates/review_checklist.md) | 各フェーズ完了時のレビュー項目 |

## 調査資料との対応関係

```mermaid
flowchart LR
    subgraph 調査資料["調査資料 (research/)"]
        D00["00 サマリーレポート"]
        D01["01 MSAアーキテクチャ"]
        D02["02 ユースケース"]
        D03["03 論理データモデル"]
        D04["04 物理データモデル"]
        D05["05 DB調査"]
        D06["06 インフラ前提条件"]
        D07["07 トランザクションモデル"]
        D08["08 透過的データアクセス"]
        D09["09 バッチ処理"]
        D10["10 セキュリティ"]
        D11["11 オブザーバビリティ"]
        D12["12 障害復旧"]
        D13["13 ScalarDB 3.17"]
        D15["15 XA調査"]
    end

    subgraph ワークフロー["ワークフロー (workflow/)"]
        W01["01 要件分析"]
        W02["02 ドメイン"]
        W03["03 適用範囲"]
        W04["04 データモデル"]
        W05["05 トランザクション"]
        W06["06 API設計"]
        W07["07 インフラ"]
        W08["08 セキュリティ"]
        W09["09 監視"]
        W10["10 DR"]
    end

    D00 --> W01
    D02 --> W01
    D15 --> W01
    D01 --> W02
    D03 --> W02
    D02 --> W03
    D07 --> W03
    D15 --> W03
    D03 --> W04
    D04 --> W04
    D05 --> W04
    D07 --> W05
    D09 --> W05
    D13 --> W05
    D08 --> W06
    D01 --> W06
    D06 --> W07
    D13 --> W07
    D10 --> W08
    D11 --> W09
    D12 --> W10
```

## 利用方法

1. **Phase 1から順に進める**: 各ステップのワークフローファイルを開き、記載された手順に従って作業を進める
2. **デシジョンポイントで判断**: 各ステップ内のデシジョンツリーやチェックリストで判断を行い、結果を記録する
3. **テンプレートを活用**: `templates/`内のテンプレートをコピーして、各サービス・各テーブルの設計書を作成する
4. **レビューチェックリスト**: 各フェーズ完了時にレビューチェックリストで品質を確認する
5. **参照先を確認**: 各ステップ内で参照される調査資料（`research/`ディレクトリ）の該当セクションを確認する
