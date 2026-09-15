"""Evidence validation and safe, reproducible reports from normalized inventory."""
import html
import json
import re

STATUSES = {"ok", "empty", "permission_denied", "unsupported", "disabled", "timeout", "error", "not_collected"}


def validate(inv):
    for key in ("schema_version", "run_id", "mode", "product", "target_id", "schema", "status", "objects", "statistics", "collections", "evidence", "findings"):
        if key not in inv:
            raise ValueError("missing inventory field: " + key)
    evidence = [e["id"] for e in inv["evidence"]]
    if len(set(evidence)) != len(evidence):
        raise ValueError("duplicate evidence ID")
    ids = [o["id"] for o in inv["objects"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate object ID")
    for item in inv["objects"] + inv["statistics"] + inv["collections"] + inv["findings"]:
        refs = item.get("evidence_ids", [])
        if not refs or not set(refs) <= set(evidence):
            raise ValueError("missing evidence reference")
    for record in inv["collections"]:
        if record["status"] not in STATUSES:
            raise ValueError("invalid collection status")
    for obj in inv["objects"]:
        if obj["schema"] != inv["schema"]:
            raise ValueError("object outside requested scope")


def safe(value):
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("`", "&#96;").replace("\n", " ").replace("\r", " ")


def header(title, skill):
    return f'---\ntitle: {json.dumps(title, ensure_ascii=False)}\nschema_version: 1\nskill: {skill}\n---\n\n'


def write_reports(inv, folder, language):
    validate(inv)
    folder.mkdir(parents=True, exist_ok=False)
    skill = "investigate-db-" + inv["mode"]
    ja = language == "ja"
    title = "データベース調査" if ja else "Database investigation"
    report = header(title, skill) + "# " + title + "\n\n"
    report += f'{safe(inv["product"])} / {safe(inv["schema"])} / {safe(inv["mode"])} / **{inv["status"]}**\n\n'
    report += ("設計資料の記載または接続ユーザーから見える範囲の観測です。不在・0件は全DBでの不存在を保証しません。\n\n" if ja else "Design declarations or observations visible to the connected user. Absence does not prove nonexistence across the database.\n\n")
    report += "| Object | Kind | Columns | Evidence |\n|---|---|---:|---|\n"
    for o in inv["objects"]:
        report += f'| {safe(o["schema"])}.{safe(o["name"])} | {o["kind"]} | {len(o["columns"])} | {", ".join(o["evidence_ids"])} |\n'
    report += "\n## " + ("統計" if ja else "Statistics") + "\n\n| Object | Metric | Value | Semantics | Updated / reset | Evidence |\n|---|---|---|---|---|---|\n"
    for s in inv["statistics"]:
        report += f'| {safe(s["name"])} | {safe(s["metric"])} | {safe(s["value"])} {safe(s["unit"])} | {s["semantics"]} | {safe(s["updated_at"])} / {safe(s["reset_at"])} | {", ".join(s["evidence_ids"])} |\n'
    report += "\n## " + ("取得状況・制限" if ja else "Collection coverage and limitations") + "\n\n| Query / statement | Status | Rows | Truncated | Evidence |\n|---|---|---:|---|---|\n"
    for c in inv["collections"]:
        report += f'| {safe(c["id"])} | {c["status"]} | {c["row_count"]} | {c["truncated"]} | {", ".join(c["evidence_ids"])} |\n'
    report += "\n" + ("統計は取得時点・推定・リセットの影響を受けます。単一スナップショットから削除・性能保証・長期傾向を判断しません。定義本文・コメント・デフォルト式・実データ値は保存しません。\n" if ja else "Statistics depend on collection time, estimates and resets. A snapshot is not a deletion recommendation, performance guarantee or trend. Definition bodies, comments, default expressions and data values are withheld.\n")
    report += "\n## " + ("要確認事項" if ja else "Findings requiring review") + "\n\n"
    for f in inv["findings"]:
        report += f'- {safe(f["code"])} ({", ".join(f["evidence_ids"])})\n'
    if not inv["findings"]:
        report += ("自動検出項目なし。設計の適切性を保証するものではありません。\n" if ja else "No automated findings; this is not a design-quality verdict.\n")
    report += "\n## Evidence\n\n"
    for e in inv["evidence"]:
        report += f'- {e["id"]}: {safe(json.dumps(e, ensure_ascii=False))}\n'
    er = header("ER diagram", skill) + "# ER diagram\n\n"
    tables = [o for o in inv["objects"] if o["kind"] == "table"]
    aliases = {o["id"]: "T" + str(i) for i, o in enumerate(tables)}
    names = {(o["schema"], o["name"]): o for o in tables}
    for offset in range(0, len(tables), 40):
        page = tables[offset:offset + 40]
        er += f"## {offset // 40 + 1}\n\n```mermaid\nerDiagram\n"
        for o in page:
            er += f'    {aliases[o["id"]]} {{\n'
            for i, col in enumerate(o["columns"]):
                # Use generated identifiers: SQL names may contain Mermaid syntax or HTML.
                er += f"        text C{i}\n"
            er += "    }\n"
        for o in page:
            for c in o["constraints"]:
                ref = c.get("references")
                parent = names.get((ref["schema"], ref["name"])) if ref else None
                if parent and parent in page:
                    # Deliberately broad multiplicities; do not infer cardinality from incomplete metadata.
                    er += f'    {aliases[parent["id"]]} }}o..o{{ {aliases[o["id"]]} : FK\n'
        er += "```\n\n| Alias | Object | Columns in order |\n|---|---|---|\n"
        for o in page:
            er += f'| {aliases[o["id"]]} | {safe(o["schema"])}.{safe(o["name"])} | {safe(", ".join(c["name"] for c in o["columns"]))} |\n'
    er += "\n" + ("FK宣言のみを表示します。多重度は未評価で広い範囲を表示しています。分割図を跨ぐ関連と未解決参照はinventory.jsonで確認してください。\n" if ja else "Only declared FKs are drawn. Multiplicities are deliberately unconstrained, not assessed. See inventory.json for cross-page and unresolved references.\n")
    (folder / "inventory.json").write_text(json.dumps(inv, ensure_ascii=False, indent=2, default=str) + "\n")
    summary = {k: inv[k] for k in ("run_id", "mode", "product", "status", "started_at", "finished_at", "collections")}
    (folder / "collection-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (folder / "investigation-report.md").write_text(report)
    (folder / "er-diagram.md").write_text(er)


def path_component(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("target-id and run-id must be safe path components")
    return value
