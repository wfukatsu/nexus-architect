package com.scalar.migrate.runtime;

import java.util.List;
import java.util.Map;

/** Execution plan produced by scalardb_migrate (references/architecture.md, Execution plans). */
public class Plan {
  public String pattern;
  public String source_dialect;
  public String source_sql;
  public List<Fetch> fetch;
  public Map<String, Residual> residual;
  public Map<String, Object> guardrails;
  public List<String> unresolved;
  public Map<String, Object> transaction;        // {"read_only": true}
  public Map<String, Object> recommended_config; // ScalarDB settings the fetches benefit from

  public static class Fetch {
    public String table;
    public String namespace;
    public String alias;
    public List<String> columns;
    public Map<String, String> column_types; // ScalarDB types
    public List<Object> predicates;          // Predicate or List<Predicate> (OR group) as parsed JSON
    public String scalardb_sql;
    public String access_path;
    public int max_rows;
    public List<List<String>> index_columns;  // indexes Residual builds on the fetched table before the query
  }

  public static class Residual {
    public String engine;
    public String mode;
    public String sql;
    public boolean build_indexes;  // build the fetches' index_columns in H2 before the query (off by default)
  }

  public static class Predicate {
    public String column;
    public String op;
    public Object value;
  }
}
