---
type: Technology Guide
title: Prometheus と Grafana スタックの可観測性設計
description: metrics、alerts、dashboards、logs、traces、SLO を一貫して設計・運用する知識。
tags: [prometheus, grafana, alertmanager, loki, tempo, observability, slo]
generated: { by: codex/gpt-5, at: "2026-08-19T00:00:00+09:00" }
verified: { by: "process:official-document-cross-check", at: "2026-08-19T00:00:00+09:00" }
status: stable
stale_after: 2026-11-19
sources:
  - { id: prometheus-alerting, resource: "https://prometheus.io/docs/practices/alerting/", title: Alerting practices, author: "team:prometheus" }
  - { id: prometheus-rules, resource: "https://prometheus.io/docs/practices/rules/", title: Recording rules, author: "team:prometheus" }
  - { id: prometheus-naming, resource: "https://prometheus.io/docs/practices/naming/", title: Metric and label naming, author: "team:prometheus" }
  - { id: grafana-provisioning, resource: "https://grafana.com/docs/grafana/latest/administration/provisioning/", title: Grafana provisioning, author: "team:grafana" }
  - { id: loki-labels, resource: "https://grafana.com/docs/loki/latest/get-started/labels/bp-labels/", title: Loki label best practices, author: "team:grafana" }
  - { id: infrastructure-repo, resource: "https://gitlab.com/scalar-labs/ai-driven-devops/ai-devops-project-template/aidd-infrastructure", title: aidd-infrastructure }
---

# 対象実装

- kube-prometheus-stack、Prometheus node-exporter、kube-state-metrics、Alertmanager、Grafana。
- Grafana Alloy で telemetry を収集し、Loki に logs、Tempo に traces を保存する。
- Beyla で eBPF/OTel signal、Pyrra で SLO、OpenCost で Kubernetes cost を扱う。
- staging の自作 chart で PrometheusRule、AlertmanagerConfig、Pyrra SLO を GitOps 管理する。

# Signal の責任

| Signal | 主な用途 | 注意点 |
|---|---|---|
| Metrics | 数値傾向、SLI、alert | cardinality、retention、rule evaluation |
| Logs | event detail、audit、原因分析 | PII/secret、volume、label cardinality |
| Traces | 分散 request path、latency breakdown | sampling、service naming、context propagation |
| Profiles/eBPF | code/network の深掘り | overhead、kernel compatibility、権限 |

# Metrics と Label

- metric/label 名、unit、counter suffix を一貫させる。[prometheus-naming]
- label に user ID、request ID、URL 全文等の unbounded value を入れない。
- cluster、namespace、service、environment 等の共通 resource attribute を signal 間で揃える。
- scrape target、sample ingestion、WAL/storage、rule evaluation、remote write 自体を監視する。

# Recording rule と SLO

- 高頻度・高コスト query と SLI を recording rule にし、dashboard と alert が同じ定義を使う。
- recording rule は `level:metric:operations` の命名を基本にする。[prometheus-rules]
- availability/latency の good/total event、window、objective、error budget を service owner と合意する。
- Pyrra で生成された rule/alert と手書き rule の重複を避ける。

# Alert

Prometheus は「原因のすべて」ではなく、利用者に影響する symptom を中心に少数の actionable alert を推奨する。[prometheus-alerting]

- page は即時対応可能なもの、ticket は期限内対応、info は dashboard/log と分ける。
- `for` で一時的 blip を吸収し、severity、owner、runbook URL、dashboard URL を annotation/label に含める。
- service alert に加え、Prometheus/Alertmanager/collector 自身の停止を検知する。
- inhibit/group/routing と notification failure をテストする。

# Grafana as Code

Grafana は datasource と dashboard を file provisioning でき、GitOps と相性がよい。[grafana-provisioning]

- dashboard UID と datasource UID を安定化し、手動 UI 編集との所有関係を決める。
- dashboard は service overview → SLI → resource → dependency の drill-down を可能にする。
- anonymous access を避け、OIDC/RBAC、folder permission、secret datasource credential を管理する。
- dashboard JSON と alert/rule を code review し、環境 URL だけを差分化する。

# Loki

Loki は log content 全文でなく stream label を index する。label は region、cluster、namespace、application 等の bounded/static value にし、trace ID/order ID 等を label にしない。[loki-labels]

- high-cardinality data は structured metadata/log body に置く。
- tenant、retention、ingestion limit、object storage lifecycle を設計する。
- log に token、password、PII を出さず、収集段階でも redaction を検討する。

# Tempo と相関

- W3C Trace Context 等を入口から dependency まで伝播する。
- metrics exemplar、log の trace ID、Grafana datasource linkage で signal 間を移動できるようにする。
- sampling は error/slow trace を残しつつ、通常 traffic の cost を制御する。
- OTel service name、namespace、environment を一貫させる。

# Capacity と復旧

- daily samples/log bytes/spans、retention、replication、object storage request を見積もる。
- telemetry outage が application outage を引き起こさないよう、collector の backpressure と buffer を設計する。
- rule、dashboard、datasource config は Git から復旧できるようにし、object storage と Grafana DB の backup 対象を明確にする。
