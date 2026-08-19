---
type: Technology Guide
title: Kustomize の設計・構築・運用
description: base と overlay で Kubernetes マニフェストの環境差を管理する知識。
resource: "https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/"
tags: [kustomize, kubernetes, manifests, overlays]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: kustomize-docs, resource: "https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/", title: Declarative Management Using Kustomize, author: "team:kubernetes" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

- staging の Argo CD app-of-apps entry point に `kustomization.yaml` を使う。
- ScalarDB の共通 base に DB 種別と scale overlay を組み合わせる。
- CI の promote job が image tag を更新し、Argo CD が同期する。

# Base と Overlay

base は再利用可能な resource 集合、overlay は base を参照し環境固有の customization を追加する。base は overlay を知らず、複数 overlay から再利用できる。[kustomize-docs]

- base に共通 identity、selector、port、probe 等を置く。
- overlay には replica、resource、hostname、storage、環境 label 等の差分だけを置く。
- base を環境条件で分岐させず、overlay の組合せで表現する。
- patch は target を一意にし、上流変更で暗黙に別 resource へ当たらないようにする。

# Image 更新

- `images` transformer で name/newName/newTag/digest を変更し、Deployment YAML の文字列置換を避ける。
- promotion の commit は source image digest、build pipeline、署名を追跡できるようにする。
- moving tag を使う場合も、実際にデプロイされた digest を記録・検証する。

# Generator と Secret

- ConfigMapGenerator の hash suffix は設定変更時の rollout に有効だが、参照側と prune を確認する。
- SecretGenerator に平文機密値を commit しない。ExternalSecret 等の resource 宣言だけを Git 管理する。

# 検証

```text
kubectl kustomize <overlay>
kubectl apply --server-side --dry-run=server -k <overlay>
```

- render 後の resource 名、namespace、selector、image、RBAC、cluster-scoped resource を CI で検査する。
- Argo CD が使う Kustomize version と開発/CI の version を揃える。
- remote base は可変 branch でなく immutable commit/tag に固定する。
