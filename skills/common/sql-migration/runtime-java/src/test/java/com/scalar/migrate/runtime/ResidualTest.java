package com.scalar.migrate.runtime;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ResidualTest {

  private static Plan.Fetch fetch(String table, List<List<String>> indexes) {
    Plan.Fetch f = new Plan.Fetch();
    f.table = table;
    f.column_types = Map.of();
    f.index_columns = indexes;
    return f;
  }

  private static Rows rows(List<String> columns, Map<String, String> types, Object[]... data) {
    Rows r = new Rows();
    r.columns.addAll(columns);
    r.types.putAll(types);
    for (Object[] row : data) r.rows.add(row);
    return r;
  }

  private static void load(Residual residual) throws Exception {
    residual.load(fetch("orders", List.of(List.of("order_id"), List.of("customer_id"), List.of("no_such_column"))),
        rows(List.of("order_id", "customer_id"), Map.of("order_id", "INT", "customer_id", "INT"),
            new Object[] {1, 10}, new Object[] {2, 20}, new Object[] {3, 10}));
    residual.load(fetch("customers", List.of(List.of("customer_id"))),
        rows(List.of("customer_id", "name"), Map.of("customer_id", "INT", "name", "TEXT"),
            new Object[] {10, "a"}, new Object[] {20, "b"}));
  }

  private static long planIndexes(Residual residual) throws Exception {
    Map<String, Object> built = residual.query(
        "SELECT COUNT(DISTINCT INDEX_NAME) FROM INFORMATION_SCHEMA.INDEXES WHERE INDEX_NAME LIKE '%_ix%'", Map.of());
    return ((Number) ((List<?>) ((List<?>) built.get("rows")).get(0)).get(0)).longValue();
  }

  private static final String JOIN =
      "SELECT c.name FROM orders o JOIN customers c ON c.customer_id = o.customer_id ORDER BY o.order_id";

  @Test
  void buildsNoIndexesByDefault() throws Exception {
    try (Residual residual = new Residual("PostgreSQL")) {
      load(residual);
      assertEquals(List.of(List.of("a"), List.of("b"), List.of("a")), residual.query(JOIN, Map.of()).get("rows"));
      assertEquals(0L, planIndexes(residual));
    }
  }

  @Test
  void buildsThePlanIndexesWhenAskedAndSkipsOnesThatCannotBeBuilt() throws Exception {
    try (Residual residual = new Residual("PostgreSQL", true)) {
      load(residual);
      assertEquals(List.of(List.of("a"), List.of("b"), List.of("a")), residual.query(JOIN, Map.of()).get("rows"));
      // orders_ix0, orders_ix1, customers_ix3; the index on no_such_column (orders_ix2) was skipped
      assertEquals(3L, planIndexes(residual));
    }
  }
}
