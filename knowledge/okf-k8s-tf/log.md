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
