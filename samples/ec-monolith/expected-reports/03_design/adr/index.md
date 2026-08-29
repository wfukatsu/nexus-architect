---
title: "Architecture Decision Records — index"
schema_version: 1
phase: "Phase 3: Design"
skill: redesign
generated_at: "2026-08-29T02:30:00Z"
input_files:
  - reports/03_design/adr/
---

## 決定記録一覧

`adr-NNN-*.md` のフロントマターから再生成されるビュー。手で編集しない（@rules/architecture-decision-records.md §3）。

| ID | Title | Status | Skill | Decided | Upstream |
|----|-------|--------|-------|---------|----------|
| ADR-001 | 在庫（Inventory）を Ordering から独立した境界づけられたコンテキストにする | accepted | redesign | 2026-08-29 | CTX-002, CTX-003, NFR-002 |
| ADR-002 | 引当（Reservation）を StockItem とは別集約にし、同一トランザクションで書く | accepted | redesign | 2026-08-29 | ADR-001, AGG-002, AGG-003, NFR-002 |
| ADR-003 | 注文確定は分散トランザクションではなく Saga（イベント駆動の補償）で実現する | accepted | design-microservices | 2026-08-29 | ADR-001, STM-001, NFR-001, NFR-003 |
| ADR-004 | 通知（Notification）と ポイント（Identity）は Ordering のイベントに Conformist で追従する | accepted | design-microservices | 2026-08-29 | ADR-003, CTX-001, CTX-005 |
