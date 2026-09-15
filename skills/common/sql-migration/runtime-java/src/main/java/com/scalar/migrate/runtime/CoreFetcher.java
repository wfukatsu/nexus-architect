package com.scalar.migrate.runtime;

import com.scalar.db.api.ConditionBuilder;
import com.scalar.db.api.ConditionSetBuilder;
import com.scalar.db.api.ConditionalExpression;
import com.scalar.db.api.ConditionalExpression.Operator;
import com.scalar.db.api.DistributedTransaction;
import com.scalar.db.api.DistributedTransactionAdmin;
import com.scalar.db.api.DistributedTransactionManager;
import com.scalar.db.api.Result;
import com.scalar.db.api.Scan;
import com.scalar.db.api.ScanBuilder;
import com.scalar.db.api.TableMetadata;
import com.scalar.db.io.Column;
import com.scalar.db.io.DataType;
import com.scalar.db.io.Key;
import com.scalar.db.service.TransactionFactory;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.List;
import java.util.Map;

/**
 * Fetch through the ScalarDB Core transactional API (Apache 2, no license). Only the pushdown predicates that the
 * Core API can express (partition key equality, AND of simple conditions) are used; the residual engine re-applies
 * the full predicate anyway, so the fetch only has to be a superset.
 */
public class CoreFetcher implements Fetcher {
  private final DistributedTransactionManager manager;
  private final DistributedTransactionAdmin admin;
  private DistributedTransaction tx;

  public CoreFetcher(String propertiesPath) throws Exception {
    TransactionFactory factory = TransactionFactory.create(propertiesPath);
    manager = factory.getTransactionManager();
    admin = factory.getTransactionAdmin();
  }

  @Override
  public void begin() throws Exception {
    // plans only read: a read-only transaction skips the Coordinator write at commit (ScalarDB 3.16+)
    tx = manager.startReadOnly();
  }

  @Override
  public Rows fetch(Plan.Fetch spec, Map<String, Object> params) throws Exception {
    String ns = spec.namespace;
    TableMetadata md = admin.getTableMetadata(ns, spec.table);
    if (md == null) throw new IllegalStateException("table not found in ScalarDB: " + ns + "." + spec.table);

    Map<String, Object> eq = new LinkedHashMap<>();
    List<Plan.Predicate> ands = new ArrayList<>();
    for (Object p : spec.predicates == null ? List.of() : spec.predicates) {
      if (p instanceof Map) { // simple predicate (Gson parses unknown Object as Map / List)
        Plan.Predicate pr = Runner.GSON.fromJson(Runner.GSON.toJson(p), Plan.Predicate.class);
        Object v = resolve(pr.value, params);
        if ("=".equals(pr.op)) eq.put(pr.column, v);
        ands.add(pr);
      } // OR groups are left to the residual engine
    }
    boolean partitionCovered = md.getPartitionKeyNames().stream().allMatch(eq::containsKey);

    Scan scan;
    if (partitionCovered) {
      Key.Builder kb = Key.newBuilder();
      for (String c : md.getPartitionKeyNames()) kb.add(Values.column(c, md.getColumnDataType(c), eq.get(c)));
      scan = Scan.newBuilder().namespace(ns).table(spec.table).partitionKey(kb.build()).limit(spec.max_rows + 1).build();
    } else {
      ScanBuilder.BuildableScanAll all = Scan.newBuilder().namespace(ns).table(spec.table).all();
      Set<ConditionalExpression> conds = new LinkedHashSet<>();
      for (Plan.Predicate pr : ands) {
        ConditionalExpression cond = condition(pr, md, params);
        if (cond != null) conds.add(cond);
      }
      scan = conds.isEmpty()
          ? all.limit(spec.max_rows + 1).build()
          : all.where(ConditionSetBuilder.andConditionSet(conds).build()).limit(spec.max_rows + 1).build();
    }

    List<String> cols = spec.columns == null || spec.columns.isEmpty() ? new ArrayList<>(md.getColumnNames()) : spec.columns;
    Rows out = new Rows();
    for (String c : cols) {
      out.columns.add(c);
      out.types.put(c, md.getColumnDataType(c).name());
    }
    List<Result> results = tx.scan(scan);
    if (results.size() > spec.max_rows) throw new RowLimitExceededException(spec.table, spec.max_rows);
    for (Result r : results) {
      Object[] row = new Object[cols.size()];
      for (int i = 0; i < cols.size(); i++) row[i] = Values.read(r, cols.get(i), md.getColumnDataType(cols.get(i)));
      out.rows.add(row);
    }
    return out;
  }

  private static ConditionalExpression condition(Plan.Predicate pr, TableMetadata md, Map<String, Object> params) {
    DataType type = md.getColumnDataType(pr.column);
    Object v = resolve(pr.value, params);
    switch (pr.op) {
      case "=": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.EQ);
      case "<>": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.NE);
      case ">": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.GT);
      case ">=": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.GTE);
      case "<": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.LT);
      case "<=": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, v), Operator.LTE);
      case "LIKE": return ConditionBuilder.column(pr.column).isLikeText(v.toString());
      case "NOT LIKE": return ConditionBuilder.column(pr.column).isNotLikeText(v.toString());
      case "IS NULL": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, null), Operator.IS_NULL);
      case "IS NOT NULL": return ConditionBuilder.buildConditionalExpression(Values.column(pr.column, type, null), Operator.IS_NOT_NULL);
      default: return null; // BETWEEN etc.: residual engine handles it
    }
  }

  @SuppressWarnings("unchecked")
  static Object resolve(Object value, Map<String, Object> params) {
    if (value instanceof Map && ((Map<String, Object>) value).containsKey("param")) {
      String name = ((Map<String, Object>) value).get("param").toString();
      if (!params.containsKey(name)) throw new IllegalArgumentException("missing bind parameter: " + name);
      return params.get(name);
    }
    return value;
  }

  @Override
  public void commit() throws Exception {
    tx.commit();
  }

  @Override
  public void rollback() {
    try { if (tx != null) tx.abort(); } catch (Exception ignored) { }
  }

  @Override
  public void close() {
    manager.close();
    admin.close();
  }

  /** Used by the loader: upsert JSON rows (transactional, through ScalarDB). */
  public int load(String ns, String table, List<Map<String, Object>> rows) throws Exception {
    TableMetadata md = admin.getTableMetadata(ns, table);
    if (md == null) throw new IllegalStateException("table not found in ScalarDB: " + ns + "." + table);
    DistributedTransaction t = manager.start();
    try {
      for (Map<String, Object> row : rows) {
        Key.Builder pk = Key.newBuilder();
        for (String c : md.getPartitionKeyNames()) pk.add(Values.column(c, md.getColumnDataType(c), row.get(c)));
        com.scalar.db.api.UpsertBuilder.Buildable b = com.scalar.db.api.Upsert.newBuilder().namespace(ns).table(table).partitionKey(pk.build());
        if (!md.getClusteringKeyNames().isEmpty()) {
          Key.Builder ck = Key.newBuilder();
          for (String c : md.getClusteringKeyNames()) ck.add(Values.column(c, md.getColumnDataType(c), row.get(c)));
          b = b.clusteringKey(ck.build());
        }
        for (String c : md.getColumnNames()) {
          if (md.getPartitionKeyNames().contains(c) || md.getClusteringKeyNames().contains(c)) continue;
          Column<?> col = Values.column(c, md.getColumnDataType(c), row.get(c));
          b = b.value(col);
        }
        t.upsert(b.build());
      }
      t.commit();
      return rows.size();
    } catch (Exception e) {
      try { t.abort(); } catch (Exception ignored) { }
      throw e;
    }
  }
}
