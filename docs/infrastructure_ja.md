# マルチクラウド インフラガイド

`/infra:*` プラグインは、アプリケーションが動く基盤を **3クラウド（AWS / Azure / GCP）** ×
**4環境（local / test / staging / production）** にわたって設計・実装・レビューします。
すべての主張はモデルの記憶ではなく、同梱の OKF `okf-k8s-tf` ナレッジバンドルに根拠を置きます。

architect パイプラインのフェーズではなく独立したプラグインです。自動では実行されません。

| コマンド | モデル | 役割 |
|---------|-------|------|
| `/infra:start` | sonnet | トリアージ：バンドル解決、鮮度チェック、対象環境とクラウドの確定、モードへの委譲 |
| `/infra:design` | opus | 構成を決定し、設計書・環境マトリクス・ADR を出力する |
| `/infra:implement` | sonnet | Terraform / マニフェスト / Helm values / Kustomize overlay / CI を実在のリポジトリへ書く |
| `/infra:review` | opus | 既存コードまたは設計書を評価し、重大度付きの指摘を出す |

## セットアップ

バンドルはリポジトリに同梱されているため、取得作業はありません。解決先を確認します。

```bash
tools/update-okf-bundle.sh status --bundle=k8s-tf
```

```
bundle:        k8s-tf (vendored — no remote)
resolved:      .../knowledge/okf-k8s-tf
okf_version:   0.2
documents:     23
stale_after:   earliest 2026-10-19 (a document past its date is re-verified, not quoted as current)
sections:
  architecture  delivery  foundation  operations  secrets  security
```

**リモートはありません。** 取得元リポジトリが削除されたため submodule ではなく実体を同梱して
います。`--latest` は取得を試みず、その事実を報告します。詳細は
[`knowledge/OKF-K8S-TF-PROVENANCE.md`](../knowledge/OKF-K8S-TF-PROVENANCE.md)。

別のコピーを参照させたい場合は、そのルートを `NEXUS_OKF_K8S_TF` に設定してください。

## 4つの前提

これらは助言ではなくスキルが強制する規約です。出力の形のほとんどはここから決まります。

### 1. マルチクラウドが既定

単一クラウド前提の答えは出しません。設計上の論点は **移植性境界** をどこに引くかです。

| 層 | 方針 |
|---|---|
| L1 クラウド固有（VPC/VNet、IAM、EKS/AKS/GKE、KMS） | 共通化しない。`modules/{aws,azure,gcp}` に閉じ込め、**output 名だけ揃える** |
| L2 Kubernetes（Deployment、Service、NetworkPolicy、RBAC） | 完全共通。クラウド分岐をこの層に持ち込まない |
| L3 プラットフォーム（Argo CD、Vault、ESO、Kyverno、kube-prometheus-stack） | chart と values を共通化し、クラウド差は最小の値差分に閉じる |
| L4 アプリケーション | 完全共通。接続先だけを注入する |

境界を上げすぎるとマニフェストがクラウド数だけ分岐し、下げすぎると Terraform module が
最小公倍数の巨大な条件分岐になります。共通で表せない差分が3件以上出たら、抽象化ではなく
**分離**を選びます。詳細は [`rules/infra/multi-cloud.md`](../rules/infra/multi-cloud.md)。

### 2. 4環境、ただし根拠の厚みは同じではない

| 環境 | バンドルの被覆 | 出力での書き方 |
|---|---|---|
| `local` | **記載なし** | 「OKF 範囲外」と明示し、公式ドキュメントかスキル自身の規約を根拠にする |
| `test` | 対象実装あり（直接適用） | 事実として引用できる |
| `staging` | 対象実装あり（Argo CD GitOps） | 事実として引用できる |
| `production` | **実装事実なし。設計指針のみ** | 「調査対象リポジトリに本番の実装事実はない」と明示し、staging に承認・保護・sync window を加算した形で提示して ADR に残す |

この被覆の偏りこそが、このプラグインの持つ最も有用な情報です。4環境を同じ確信度で語る
ツールは、根拠のない2つを創作していることになります。詳細は
[`rules/infra/environments.md`](../rules/infra/environments.md)。

環境間では **base・chart・image digest を同一に保ち**、差分は overlay か values の値差分に
閉じます。`if env == "production"` を base に書くことはありません。

### 3. 1リソース1オーナー

Terraform / Argo CD / CI / 手動 のうち2者以上が1つのリソースを管理している状態は、
レビューにおける最優先の指摘です。`/infra:design` は責任分界表を作った直後に自己検証し、
`/infra:review` は他の何よりも先に所有権マップを作ります。これがないと他の指摘に
優先順位を付けられないためです。

### 4. バンドルが一次情報

主張には出典（`[foundation/terraform.md]`）を付けます。バンドルに記載がないことは記憶で
埋めず、「記載がない」と明示します。バンドル自身が持つ3区分は出力にも保たれます。
**対象実装**は事実、**設計指針**は出典付きの推奨、**確認事項**は成果物末尾に未解決のまま残します。

対象実装の区分は特定2コミットのスナップショットです。実物のリポジトリが読める場合は、
実物が事実でバンドルは基準となり、その差分が報告されます。

## 実行の流れ

```bash
# 1. トリアージ — バンドル / 鮮度 / 環境 / クラウドを確定してモードへ委譲
/infra:start ./platform

# 既に確定しているならモードを直接呼んでもよい
/infra:design ./platform --env=staging --env=production --cloud=aws --cloud=azure
/infra:implement ./platform --env=staging --cloud=aws
/infra:review ./platform --env=production --cloud=aws
```

設計 → **ユーザー確認** → 実装 の順です。「設計して実装して」という複合依頼は意図的に
分割され、設計の合意なしに実装へ進みません。

成果物は `work/pipeline-progress.json` があれば `reports/08_infrastructure/` に、
なければ対象リポジトリの `docs/infra/` に保存されます。

```
reports/08_infrastructure/
├── infra-design-<システム名>.md      # /infra:design
├── env-matrix-<システム名>.md        # /infra:design
├── adr/adr-<連番>-<slug>.md          # /infra:design
└── reviews/review-<対象>-r<n>.md     # /infra:review — 2回目以降は前回指摘との照合から始まる
```

## architect パイプラインとの境界

| architect | infra | 境界 |
|---|---|---|
| `/architect:design-infrastructure` | `/infra:design` | 論理と具体。architect は設計パイプラインの1フェーズとしてインフラを決め、infra はそれをマルチクラウド × 4環境の具体構成にする |
| `/architect:generate-infra-code` → `generated/` | `/infra:implement` | 出力先。codegen は `generated/` に雛形と品質ゲート CI を出し、`/infra:implement` は実在のインフラリポジトリへマージ対象のコードを書く |
| `/architect:design-security`・`design-observability`・`design-disaster-recovery` | `/infra:design` の該当節 | 方針と手段。architect は認可モデル・SLI/SLO・RTO/RPO を決め、infra は Vault / ESO / Prometheus / Kyverno とその配置を決める |
| `/architect:review-operations` | `/infra:review` | 対象物。architect は設計書の運用準備状況を見て、infra は Terraform・マニフェスト・CI を見る。所有権の重複・digest の断絶・秘密情報の露出は architect 側にない観点 |

architect パイプラインを先に流す必要はありませんが、
`reports/03_design/target-architecture.md` と `reports/08_infrastructure/*.md` が
存在すれば入力として読まれます。

## 最初の実行前に知っておくとよいこと

- **Kyverno の `ClusterPolicy` には期限がある。** `kyverno.io/v1 ClusterPolicy` は deprecated で、
  v1.20（2026年10月予定）で削除されます。`security/kyverno.md` の `stale_after` が他より短いのも、
  レビューの既知課題の筆頭に挙がるのもこのためです。
- **test と staging の非対称は意図された設計。** test は直接適用、staging は GitOps という
  非対称は対象実装における設計判断であり、それ自体は指摘対象ではありません。指摘すべきは
  「非対称が意図的だと文書化されていないこと」と「test の drift 再作成手順の欠如」です。
- **昇格するのは digest** であってコードでも tag でもありません。各昇格 commit から
  source digest・build pipeline・署名を追跡できる必要があります。
- **バージョンは調べて書く。記憶で書かない** — リポジトリ全体と同じ規約です
  （[`rules/dependency-versions.md`](../rules/dependency-versions.md)）。
- **実装は sonnet で走る。** 複雑な移行、state surgery、CRD upgrade といった難所に当たった
  場合は、無理に進めずその旨を伝えて `/model opus` への切替を提案します。

## スキルが読むルール

| ルール | 内容 |
|---|---|
| [`rules/okf-k8s-tf-bundle.md`](../rules/okf-k8s-tf-bundle.md) | バンドルの解決、話題→文書の対応表、3区分、鮮度、引用記法、情報源の優先順位 |
| [`rules/infra/environments.md`](../rules/infra/environments.md) | 4環境の定義、被覆状況、環境パリティ、昇格経路、ローカルで緩めてよいこと、レビュー観点 |
| [`rules/infra/multi-cloud.md`](../rules/infra/multi-cloud.md) | 移植性境界、クラウド対応表、state 境界、デリバリーと可観測性、アンチパターン |
