"""Live collection through a bounded query port."""


def collect(adapter, port, schema, clock, limit=10000, budget=120):
    return {"objects": [], "statistics": [], "evidence": [], "collections": [], "findings": []}
