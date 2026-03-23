# Mermaid Best Practices

## Valid Diagram Types

graph, flowchart, sequenceDiagram, classDiagram, stateDiagram, erDiagram,
journey, gantt, pie, mindmap, timeline, C4Context

## Non-ASCII Text

Nodes containing non-ASCII text (e.g., Japanese) must be wrapped in quotes:

```mermaid
graph TD
    A["Order Service"] --> B["Inventory Service"]
    A --> C["Payment Service"]
```

Japanese example:

```mermaid
graph TD
    A["注文サービス"] --> B["在庫サービス"]
    A --> C["決済サービス"]
```

## Node ID Naming

- Use short English identifiers: `OrderSvc`, `InventoryDB`
- Use the configured language for labels, never for IDs
- IDs must be unique and descriptive

## Common Syntax Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Mismatched brackets | Unbalanced `[` and `]` | Verify opening and closing brackets |
| Arrow syntax | Using `->` instead of `-->` | Use the correct arrow syntax |
| Special characters | `(`, `)` inside labels | Wrap in quotes |
| Empty block | `\`\`\`mermaid` immediately followed by `\`\`\`` | Add content |

## Complexity Guidelines

- Maximum of 20 nodes per diagram
- Split complex diagrams and show cross-references
- Use subgraphs for logical grouping
