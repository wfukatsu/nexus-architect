# 更新履歴

## 2026-08-19

- OKF v0.2 バンドルを新規作成。
- `aidd-infrastructure` の commit `ed2689dc47ade5b5ae5c0529ad39eaba403de279` を調査。
- `aidd-ci-templates` の commit `44139cad79c8d8255ef81b0109e5b10f119b1612` を調査。
- Terraform、Kubernetes、Helm、Kustomize、Argo CD、GitLab CI/CD、Docker、Cosign、Vault、External Secrets Operator、Prometheus/Grafana、Kyverno の公式資料を整理。


## 2026-09-28（自動）

- 出典ページのリダイレクトに合わせて `resource` を移転先 URL に更新（本文・出典 ID は変更なし）。
  - `delivery/argocd.md`: https://argo-cd.readthedocs.io/ → https://argo-cd.readthedocs.io/en/stable/
  - `foundation/kubernetes.md`: https://kubernetes.io/docs/ → https://kubernetes.io/docs/home/
  - `security/kyverno.md`: https://kyverno.io/docs/ → https://kyverno.io/docs/introduction/

## 2026-09-28

公開 upstream との照合（`/architect:revise-knowledge`）。対象実装の記述は変更していない。

- `security/kyverno.md`: 従来型 policy の非推奨スケジュールを公式の最新に更新（v1.19 = 2026年8月に正式 deprecated、v1.20 = 2026年11月見込みで removal。対象に Policy、CleanupPolicy、従来の PolicyException を追加）。v1.19 の admission warning、`kyverno_deprecated_api_requests_total`、CLI `--warnings-as-errors` を追記。確認事項を新設。`stale_after` は removal 前の再確認のため 2026-11-01。
- `foundation/kubernetes.md`: 出典 `k8s-security` の Cloud native security overview ページが削除され section index へリダイレクトされていたため、後継の Cloud Native Security and Kubernetes に差し替え、security の考え方を 4C の層から lifecycle phase（Develop / Distribute / Deploy / Runtime）に改訂。1.35 系と最新 1.37.1 の差、EOL 2027-02-28 を確認事項に追加。
- `delivery/docker-cosign.md`: Docker 27 の EOL と Cosign v3（新 bundle 形式・`--trusted-root`・`--use-signing-config` の既定化、v4 での旧機能削除予定）を確認事項に追加し、出典 `cosign-v3`（Sigstore Blog）を追加。改善候補の `docker:27` 固定をサポート中の系統への更新に改訂。
- `foundation/terraform.md`: 1.14.8 と最新 1.16.4 の差を確認事項に追加（設計指針は変更なし）。
- `architecture/technology-stack.md`: 固定 version と 2026-09-28 時点の最新 stable の差を確認事項の表として追加（固定値そのものは調査スナップショットの事実として維持）。`verified.by` は公開 release との照合を表す `process:official-document-cross-check` に変更。スナップショットの確認日は表のとおり 2026-08-19 のまま。

## 2026-10-09

公開 upstream との照合（`/architect:revise-knowledge`）。対象実装の記述は変更していない。

- `delivery/gitlab-cicd.md`: 出典 `gitlab-oidc`（ID token authentication）の更新に合わせ、認証の設計指針に 2 点を追記。(1) trust policy は path 系の claim だけに依存せず、対応していれば `project_id`・`namespace_id` を併用する（rename の影響を受けないため）。(2) merge request pipeline では `project_id`・`project_path`・`ref` が source project 側の値になり、job を実行する project は `job_project_id`・`job_project_path`（GitLab 18.4 以降）で識別する。出典 `gitlab-yaml`（CI/CD YAML syntax）の更新は、本書の設計指針（`rules`、`allow_failure`、`include`、resource group 等）に影響なし。
- `foundation/helm.md`: 変更なし（再確認のみ）。出典 `helm-use`（Using Helm、Helm 4.3.0 版）の更新後も、`helm get values`・`helm history`・`helm rollback` と revision の記述は本書の内容を支持する。

## 2026-11-01

公開 upstream との照合（`/architect:revise-knowledge`）。対象実装の記述は変更していない。

- `delivery/gitlab-cicd.md`: 出典 `gitlab-oidc`（ID token authentication）の更新に合わせ、merge request pipeline の認証指針に 1 点を追記。source code を持つ project を明示的に絞る claim として `source_project_id`・`source_project_path`（GitLab 19.5 以降）を挙げた。既存の `project_id`・`namespace_id` の併用と `job_project_id`・`job_project_path`（GitLab 18.4 以降）の記述は引き続き支持される。出典 `gitlab-components`（CI/CD components）と `gitlab-yaml`（CI/CD YAML syntax）の更新は、本書の設計指針（job 名衝突、version 固定、`allow_failure`、`include`、resource group 等）に影響なし。
- `delivery/docker-cosign.md`: 変更なし（再確認のみ）。出典 `docker-build`（Building best practices）の更新後も、multi-stage build、`.dockerignore`、信頼できる最小の base image、digest 固定と更新手段（Dependabot・Docker Scout）、同一 `RUN` での cleanup、non-root `USER` の記述は本書の設計指針を支持する。確認事項の最新 version を Docker Engine 29.9.2・Cosign 3.1.4（いずれも 2026-10-20 リリース）に更新。
- `architecture/design-build-checklist.md`: 変更なし（再確認のみ）。出典 `gitlab-components` の更新後も、他プロジェクトの component は `~latest` や Git 参照ではなく catalog の release か commit SHA に固定し、定期的に新しい release へ更新するという推奨は変わらず、CI template の固定と定期更新の項目を支持する。`verified` を追加し、`stale_after` を 2027-02-01 へ更新。
- `foundation/helm.md`: 変更なし（再確認のみ）。出典 5 ページ（Helm 4.3.1 版、2026-10-26 更新）を確認し、chart/release と values による環境差（`helm-intro`）、hook の失敗・削除 policy・TTL と release 非管理（`helm-hooks`）、`helm get values`・`helm history`・`helm rollback` と revision（`helm-use`）の記述はいずれも本書の内容を支持する。`helm history --show-rollback-revision` の追加は既存の指針と矛盾しない。
- `secrets/vault.md`: 変更なし（再確認のみ）。出典 `vault-policies`（Policies）の更新後も、path ベースで既定は拒否、root token は初期設定後に revoke、発行済み token の policy は変更できず revoke が必要、という記述は本書の内容を支持する（追加された list 値の照合方法（Vault 1.21.0 以降）、`deny_slash_in_templated_paths`、UI policy の事前設定は本書の指針と矛盾しない）。`vault-ha`・`vault-hardening`・`vault-k8s` の各指針も維持。
- `foundation/helm.md`（同日追記）: 確認事項を新設。Helm 4 の `helm upgrade` に `--atomic` が無く `--rollback-on-failure`・`--force-replace`・`--wait` strategy に置き換わっている点（Helm 4.3.1 版 CLI reference）と、対象実装の Terraform helm provider 2.17.0 の `atomic`・`force_update`・`wait` 属性が provider 3.x でどう対応するかを確認事項とした。出典 `helm-upgrade`（Helm Upgrade）を追加。設計指針の本文は変更なし。
- `secrets/vault.md`（同日追記）: 出典 `vault-audit`（Audit logging）を追加し、Production hardening の audit device の項に公式の根拠（2 つ以上の device を推奨、全 device に書き込めない要求は拒否される）を付けた。確認事項を新設し、対象実装の audit device の数と種類、blocked 時の運用、sensitive 値の HMAC 化の扱いを確認事項とした。
- `security/kyverno.md`（同日、`stale_after` 到来による再確認）: 設計指針は変更なし。出典 `kyverno-overview` の非推奨スケジュール（v1.19 = 正式 deprecated、v1.20 = 2026年11月見込みで removal）は変わらず、2026-11-01 時点の最新 stable は 1.19.2（2026-10-20）で v1.20 は未リリース。確認事項の version を更新し、v1.20 の release 後に再確認するため `stale_after` を 2026-12-01 とした。出典 `kyverno-reports` に追加された `openreports.io/v1alpha1`（alpha、将来 `wgpolicyk8s` を置き換える第一歩）を確認事項に追加。出典 `kyverno-validate` の Audit / Enforce の記述は本書を支持する。

## 2026-11-09（自動）

- 出典ページのリダイレクトに合わせて `resource` を移転先 URL に更新（本文・出典 ID は変更なし）。
  - `security/kyverno.md`: https://kyverno.io/docs/policy-types/cluster-policy/validate/ → https://release-1-18-0.kyverno.io/docs/policy-types/cluster-policy/validate/

## 2026-11-12

公開 upstream との照合（`/architect:revise-knowledge`、PR #121 の週次 refresh を受けて）。対象実装の記述は変更していない。

- `security/kyverno.md`: kyverno.io の最新ドキュメントが再構成され、出典 `kyverno-overview`（Policy types overview）から「Deprecated API Versions」「Deprecation Schedule for Legacy Types」の節が消え、CEL ベースの 5 type と namespaced variant だけを掲げる構成になった（従来型の reference は version selector 経由）。非推奨スケジュール（v1.18 stable / v1.19 deprecated / v1.20 removal）の根拠として、同じ内容を保持する 1.19 版 docs を出典 `kyverno-overview-1-19`（https://release-1-19-0.kyverno.io/docs/policy-types/overview/）として追加し、該当箇所の引用を付け替えた。移行手順の根拠として出典 `kyverno-migration`（Migrating to CEL Policies）を追加し、`kyverno_legacy_policies_total` gauge と alert、`kyverno-pre` の `LegacyPolicyPresent` event、`kyverno migrate` が policy logic を変換しない点、CEL に直接の対応が無い rule（`podSecurity`・`allowExistingViolations`・`failureActionOverrides`・`patchStrategicMerge`・`manifests`）、Chainsaw test の書き換えを「重要な非推奨情報」と移行手順に追記。出典 `kyverno-reports`（Policy reports）は CEL 型前提に書き直されており、`validationActions`（`Audit` / `Deny` / `Warn`）の切替と、report の結果種別に `warn` が加わった点（`--allowedResults` 既定 5 種）を反映。2026-11-12 時点の release 状況（最新 stable 1.19.2、v1.20.0 は rc.5 = 2026-11-11 で GA 未）を確認事項に反映。出典 `kyverno-validate` は 2026-11-09 の自動 refresh で kyverno.io 自身の redirect 先（1.18 版 docs）に移っており、Audit / Enforce の記述は引き続き本書を支持するため据え置き。本書の `resource`（Introduction）の変更は誤字修正のみ。`stale_after` は v1.20 GA 待ちのため 2026-12-01 のまま。
- `delivery/argocd.md`: 出典 `argocd-sync-waves`（Sync Phases and Waves）に追加された hook の注意点を「Ordering と Health」に反映。PreSync hook は同じ Application の Secret 等より先に適用されるため credential を Application 外か低い wave の hook Secret に置く、hook は毎回の sync で実行される、hook Job には `ttlSecondsAfterFinished` でなく `hook-delete-policy` を使う、Job の exit 0 だけで phase が成功になる・長い migration は operation timeout にかかる、prune は wave の逆順で進み失敗で下位 wave が止まる。出典 `argocd-security`（Security）に追加された `/swagger-ui`（設計上未認証）と `server.disable.swagger.ui` を「セキュリティ」に追記。出典 `argocd-auto-sync`（Automated Sync Policy）から、automated sync 有効時は rollback できない点と `syncPolicy.retry` を「復旧」「自動同期」に反映（旧記述「一時 rollback 後に auto-sync が再適用する」を、無効化して rollback し再有効化で再適用、に正した）。出典 `argocd-declarative`（Declarative Setup）に追加された `resource.selectors` は本書の指針に影響なし。
- `foundation/helm.md`: 出典 `helm-use`（Using Helm、Helm 4.3.1 版）に追加された uninstall の記述を反映。`helm.sh/resource-policy: keep` による resource の残置と `--cascade orphan` の意味を「CRD」に、uninstall 後は release record も消えるため rollback できない（`--keep-history` を除く）点を「Upgrade と rollback」に追記。`helm get values`・`helm history`・`helm rollback` の記述は引き続き本書を支持する。
- `delivery/gitlab-cicd.md`: 変更なし（再確認のみ）。出典 `gitlab-oidc`（ID token authentication）の `job_project_*`（18.4）・`source_project_*`（19.5）の claim 定義は本書の記述どおり。出典 `gitlab-yaml`（CI/CD YAML syntax）に追加された job keyword `description`（GitLab 19.6）と、出典 `gitlab-components`（CI/CD components）の微修正は本書の設計指針に影響なし。
- `architecture/design-build-checklist.md`: 変更なし（再確認のみ）。出典 `gitlab-components` の「他プロジェクトの component は commit SHA（推奨）か catalog の release に固定し、`~latest` を避ける」という推奨は変わらず、CI template の固定の項目を支持する。
