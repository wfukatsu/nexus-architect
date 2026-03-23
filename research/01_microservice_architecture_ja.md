# マイクロサービスアーキテクチャ調査

## 1. 各マイクロサービスが満たすべき要件

### 基本原則

| 原則 | 説明 |
|------|------|
| **単一責任** | 各サービスはビジネスドメインにおける一つの明確な責務のみを担う |
| **自律性** | 独立してデプロイ可能、他サービスの稼働状況に依存しない |
| **疎結合** | 明確に定義されたAPIを通じてのみ通信、内部実装の変更が他サービスに影響しない |
| **高凝集** | 関連する機能は同一サービス内に集約、データとロジックは同じサービス内に配置 |
| **独立デプロイ** | 他サービスを再デプロイせずに単独でリリース可能 |
| **技術的多様性** | サービスごとに最適な技術スタックを選択可能 |
| **障害分離** | 一つのサービスの障害がシステム全体に波及しない |
| **観測可能性** | サービスの内部状態を外部から把握できる |
| **セキュリティ** | ゼロトラスト原則に基づくサービス間認証・認可 |

### サービス境界の設計原則

- **DDD（Domain-Driven Design）**: 境界づけられたコンテキスト（Bounded Context）がサービス境界設計の最重要指針
- **ビジネスケイパビリティによる分割**: 技術的なレイヤーではなくビジネス機能単位で分割
- **コンテキストマッピング**: 境界間の関係性（Upstream/Downstream, Customer/Supplier, Anti-Corruption Layer等）を明確定義
- **イベントストーミング**: ドメインイベント中心のワークショップでサービス境界を発見

#### ScalarDB 2PC使用時のコンテキストマッピング

- **Coordinatorサービス** = Upstream（トランザクションのライフサイクルを管理）
- **Participantサービス** = Downstream（Coordinatorの指示に従う）
- **Anti-Corruption Layer**: Participantサービスは2PC参加のためのACLを設け、Coordinator固有のプロトコルがドメインロジックに浸透しないようにする
- **データオーナーシップ**: 各データエンティティには単一のオーナーサービスが存在（Database per Service パターン）

## 2. 開発における機能・非機能要件

### CI/CD パイプライン

各サービスが独立したパイプラインを持つことが原則。

```mermaid
flowchart LR
    A["コミット"] --> B["ビルド"] --> C["単体テスト"] --> D["静的解析"] --> E["コンテナビルド"]
    E --> F["統合テスト"] --> G["セキュリティスキャン"] --> H["ステージングデプロイ"]
    H --> I["E2Eテスト"] --> J["承認ゲート"] --> K["本番デプロイ"]
```

**リポジトリ戦略**:
- モノレポ（Bazel, Nx, Turborepo）: 依存関係管理が容易、原子的変更が可能
- ポリレポ: サービスごとの完全な独立性

**ツール例**: GitHub Actions, GitLab CI/CD, Jenkins, Argo Workflows, Tekton

### テスト戦略

| テスト種別 | 目的 | ツール例 | 実行頻度 |
|-----------|------|---------|---------|
| **単体テスト** | 個別クラス/関数の動作検証 | JUnit, pytest, Jest | コミットごと |
| **統合テスト** | DB、MQ等との連携検証 | Testcontainers, Spring Boot Test | コミットごと |
| **契約テスト** | サービス間API互換性検証 | Pact, Spring Cloud Contract | コミットごと |
| **E2Eテスト** | ユーザーシナリオ全体の検証 | Selenium, Cypress, Playwright | デプロイ前 |
| **カオステスト** | 障害時の回復性検証 | Chaos Monkey, Litmus | 定期的 |

**契約テスト**はマイクロサービスにおいて最重要テストの一つ。Consumer-Driven Contract Testing により、消費者側がプロバイダーに期待する契約を定義・検証する。

### バージョニング

| 手法 | 例 | 長所 | 短所 |
|------|---|------|------|
| URLパス | `/api/v1/orders` | 直感的、キャッシュ容易 | URLが変わる |
| ヘッダー | `Accept: application/vnd.api.v2+json` | URL安定 | 可視性低い |
| クエリパラメータ | `/api/orders?version=2` | 実装簡単 | キャッシュ困難 |

- SemVer（MAJOR.MINOR.PATCH）を採用
- Tolerant Reader パターンで後方互換性を維持

## 3. デプロイにおける機能・非機能要件

### コンテナ化

- **Docker**: コンテナはパッケージングと配布の業界標準。マルチステージビルドでイメージ最小化、非rootユーザー実行、セキュリティスキャン必須
- **Kubernetes**: コンテナオーケストレーションのデファクトスタンダード。HPA/VPAによる自動スケーリング

**Kubernetesエコシステム**:

| コンポーネント | 役割 | 代表的ツール |
|--------------|------|------------|
| サービスメッシュ | サービス間通信管理 | Istio, Linkerd |
| Ingress | 外部トラフィック制御 | NGINX Ingress, Traefik, Envoy Gateway |
| シークレット管理 | 機密情報管理 | Vault, Sealed Secrets |
| パッケージ管理 | アプリケーションパッケージ化 | Helm |
| GitOps | 宣言的デプロイ | Argo CD, Flux |

### デプロイ戦略

| 戦略 | 説明 | 長所 | 短所 |
|------|------|------|------|
| **ブルーグリーン** | 2環境を切替 | ダウンタイムゼロ、即座のロールバック | 2環境分のリソース必要 |
| **カナリアリリース** | 段階的トラフィック移行（5%→100%） | リスク最小化 | 実装複雑 |
| **ローリングアップデート** | Podを段階的入替 | Kubernetesデフォルト | ロールバックが遅い |
| **A/Bテスト** | ユーザー属性ベース | 効果測定可能 | 設計複雑 |

### Infrastructure as Code

| ツール | 用途 | 特徴 |
|--------|------|------|
| **Terraform** | クラウドインフラ全般 | 宣言的、マルチクラウド対応 |
| **Pulumi** | クラウドインフラ | 汎用プログラミング言語で記述 |
| **Helm** | Kubernetesアプリケーション | テンプレートベース |
| **Kustomize** | K8sマニフェスト管理 | パッチベース |

## 4. 運用における機能・非機能要件

### ヘルスチェック（Kubernetes）

| 種類 | 目的 | 失敗時の動作 |
|------|------|------------|
| **Startup Probe** | 起動完了確認 | 他プローブを無効化 |
| **Liveness Probe** | プロセス生存確認 | コンテナ再起動 |
| **Readiness Probe** | リクエスト受付可否 | Serviceから除外 |

### サーキットブレーカー

状態遷移: CLOSED（正常）→ OPEN（遮断）→ HALF-OPEN（試行）→ CLOSED/OPEN

ツール例: Resilience4j

### スケーリング戦略

- **水平スケーリング**: Pod数増減（HPA）、ステートレスサービスに最適
- **垂直スケーリング**: リソース増減（VPA）、ステートフルサービスに適用
- **KEDA**: Kubernetes Event-Driven Autoscaling、イベント駆動スケーリング

基本的に水平スケーリングを優先し、サービスをステートレスに設計する。

### 障害復旧パターン

| パターン | 説明 |
|---------|------|
| リトライ | 指数バックオフで再試行 |
| タイムアウト | 応答最大時間を設定 |
| バルクヘッド | リソースプール分離 |
| フォールバック | 代替処理（キャッシュ、デフォルト値） |
| 冪等性 | 同じ操作を複数回実行しても結果同一 |

#### ScalarDB Cluster障害時の影響分析

- **Shared-Cluster障害**: 全サービスのトランザクション処理が停止。読み取り専用のフォールバックモードの設計を推奨
- **ネットワーク分断時**: ScalarDBのOCCはネットワーク分断時にトランザクションがabortされる。サービスは自身のローカルキャッシュからの読み取りを確保すべき
- **ScalarDB Clusterバージョンアップ時**: ローリングアップデート中もトランザクション処理は継続するが、新旧バージョン混在時の互換性を事前検証すること

**災害復旧戦略**:

| 戦略 | RTO | RPO | コスト |
|------|-----|-----|-------|
| バックアップ&リストア | 数時間 | 数時間 | 低 |
| パイロットライト | 数十分 | 数分 | 中 |
| ウォームスタンバイ | 数分 | 秒〜分 | 高 |
| マルチリージョンActive-Active | ほぼゼロ | ほぼゼロ | 非常に高 |

## 5. 監視における機能・非機能要件

### 可観測性の3本柱

1. **メトリクス**: 数値データ時系列（Prometheus + Grafana）
2. **ログ**: テキストイベント構造化・非構造化（ELK, Loki）
3. **トレース**: リクエストの流れの追跡（OpenTelemetry, Jaeger）

### メトリクス（RED/USEメソッド）

**REDメソッド（サービスレベル）**: Rate、Errors、Duration
**USEメソッド（リソースレベル）**: Utilization、Saturation、Errors

**SLI/SLO/SLA**:
- SLI: 測定指標（例: p99レイテンシ=200ms）
- SLO: 内部目標（例: p99<300ms を99.9%で維持）
- SLA: 顧客契約（例: 月間稼働率99.95%）

### 分散トレーシング

| ツール | 特徴 |
|--------|------|
| **OpenTelemetry** | ベンダー中立のテレメトリ標準（CNCF）、業界の収束点 |
| **Jaeger** | Uber発、CNCF卒業、分散トレーシング特化 |
| **Grafana Tempo** | Grafanaエコシステムとの統合 |

### ログ集約

- **ELKスタック**: Elasticsearch + Logstash + Kibana。全文検索に優れる
- **Grafana Loki**: Prometheusと同じラベルモデル、低ストレージコスト、Grafana統合

**ベストプラクティス**: JSON構造化ログ必須、トレースIDを含める、PIIを含めない

### アラート

| 重大度 | 通知先 | 例 |
|--------|--------|---|
| Critical | PagerDuty/Opsgenie | サービスダウン、データ損失 |
| Warning | Slack | レイテンシ上昇、ディスク残量 |
| Info | メール/ダッシュボード | デプロイ完了 |

## 6. APIの種類と特長

| API | 特長 | 適用場面 | 制約 |
|-----|------|---------|------|
| **REST** | HTTP標準、JSON、OpenAPI仕様、キャッシュ制御 | 外部公開API、CRUDサービス | オーバー/アンダーフェッチング |
| **gRPC** | protobufバイナリ、HTTP/2、双方向ストリーミング、型安全 | サービス間内部通信、低レイテンシ要求 | ブラウザ直接呼出困難 |
| **GraphQL** | クライアント指定データ形状、単一エンドポイント | BFF、モバイルアプリ | N+1問題、キャッシュ複雑 |
| **イベント駆動** | 非同期・疎結合、高拡張性、最終整合性 | 非同期連携、イベントソーシング | デバッグ困難、冪等性設計必要 |
| **WebSocket** | 全二重通信、持続接続、低レイテンシ | チャット、リアルタイム通知 | 水平スケーリング複雑 |

### イベント駆動ツール比較

| 特性 | Apache Kafka | RabbitMQ | Amazon SQS/SNS |
|------|-------------|----------|----------------|
| モデル | 分散ログ | メッセージブローカー | マネージドキュー |
| 順序保証 | パーティション内 | キュー内 | FIFOキュー |
| スループット | 非常に高い | 中〜高 | 高 |
| 永続化 | 長期保持可能 | 消費後削除 | 最大14日 |

### API選定ガイド

| 要件 | 推奨API | 理由 |
|------|---------|------|
| 外部公開API | REST | 広く理解、ツール豊富 |
| サービス間内部通信 | gRPC | 高性能、型安全 |
| モバイルBFF | GraphQL | 柔軟なデータ取得 |
| 非同期処理 | Kafka/RabbitMQ | 疎結合、高信頼性 |
| リアルタイム双方向 | WebSocket | 低レイテンシ |
| 複合パターン | REST+gRPC+Kafka | 用途に応じた使い分け |

---

## 7. ScalarDB Clusterがマイクロサービスアーキテクチャに与える影響

### アーキテクチャ設計への影響

ScalarDB Clusterを導入することで、マイクロサービスアーキテクチャの設計指針に以下の変化が生じる。

| 従来のアプローチ | ScalarDB導入後 |
|----------------|---------------|
| サービス間トランザクションはSagaパターンで結果整合性 | Two-Phase Commitインターフェースで強整合性を選択可能 |
| 各サービスのDB選択はトランザクション互換性に制約される | ポリグロットパーシステンスを制約なく採用可能 |
| DB移行はビッグバンまたは複雑な並行運用が必要 | Multi-Storage機能で段階的・無停止移行が可能 |
| クロスサービスの分析クエリにはETL/データウェアハウスが必要 | ScalarDB Analyticsで異種DB横断クエリを直接実行可能 |

### デプロイメントパターン

ScalarDB Clusterは2つのデプロイメントパターンを提供する（[公式ドキュメント](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/deployment-patterns-for-microservices/)参照）。

**Shared-Cluster パターン（推奨）:**
- 全マイクロサービスが1つのScalarDB Clusterを共有
- One-Phase Commitインターフェースで簡潔に実装
- リソース効率が高く運用管理が容易

#### Shared-Clusterパターンのリスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| **単一障害点化** | ScalarDB Cluster障害で全サービスのTx停止 | HA構成（最低3ノード）、Circuit Breakerによるグレースフルデグラデーション |
| **Noisy Neighbor** | 一部サービスのスパイクが他サービスに波及 | ResourceQuotaで十分なリソース確保、Group Commit有効化 |
| **デプロイ結合** | ScalarDB Clusterバージョンアップが全サービスに影響 | Blue-Greenデプロイ、カナリアリリース |
| **データ所有権の曖昧化** | 複数サービスのデータが同一基盤を共有 | Namespace単位のRBAC（3.17）で論理的に分離 |

> **設計原則**: Shared-Clusterは「データベースインフラの共有」であり「データの共有」ではない。各サービスは自身のNamespaceのデータのみにアクセスすべき。

**Separated-Cluster パターン:**
- マイクロサービスごとに専用のScalarDB Clusterを配置
- Two-Phase Commitインターフェースでサービス間トランザクションを実現
- チーム間の独立性を最大化する場合に有効

### サービスメッシュとの共存

ScalarDB Clusterはgroupメンバーシップとリクエストルーティング機能を内蔵しており、Istio/Linkerd等のサービスメッシュとは補完的に動作する。サービスメッシュはmTLS、トラフィック制御、可観測性を担当し、ScalarDB Clusterはトランザクション管理とデータルーティングを担当する。

---

## 参考文献

- [Sam Newman "Building Microservices" (O'Reilly)](https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/)
- [Martin Fowler - Microservices](https://martinfowler.com/articles/microservices.html)
- [Microservices.io - Patterns](https://microservices.io/patterns/index.html)
- [ScalarDB Cluster Deployment Patterns for Microservices](https://scalardb.scalar-labs.com/docs/latest/scalardb-cluster/deployment-patterns-for-microservices/)
- [The Twelve-Factor App](https://12factor.net/)
- [CNCF Cloud Native Landscape](https://landscape.cncf.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
