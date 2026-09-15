package com.scalar.migrate.runtime;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Fetch through ScalarDB SQL (JDBC driver -> ScalarDB Cluster). This is the production path: the plan's
 * scalardb_sql is executed verbatim inside one JDBC transaction. Requires a licensed ScalarDB Cluster.
 */
public class JdbcFetcher implements Fetcher {
  private final Connection conn;

  public JdbcFetcher(String propertiesPath) throws Exception {
    conn = DriverManager.getConnection("jdbc:scalardb:" + propertiesPath);
    conn.setAutoCommit(false);
  }

  @Override
  public void begin() {
    // a JDBC transaction starts implicitly with the first statement
  }

  @Override
  public Rows fetch(Plan.Fetch spec, Map<String, Object> params) throws Exception {
    List<Object> binds = new ArrayList<>();
    String sql = Residual.bindNamed(spec.scalardb_sql, params, binds);
    try (PreparedStatement ps = conn.prepareStatement(sql)) {
      for (int i = 0; i < binds.size(); i++) ps.setObject(i + 1, binds.get(i));
      try (ResultSet rs = ps.executeQuery()) {
        ResultSetMetaData m = rs.getMetaData();
        Rows out = new Rows();
        for (int i = 1; i <= m.getColumnCount(); i++) {
          out.columns.add(m.getColumnLabel(i));
          if (spec.column_types != null && spec.column_types.containsKey(m.getColumnLabel(i)))
            out.types.put(m.getColumnLabel(i), spec.column_types.get(m.getColumnLabel(i)));
        }
        while (rs.next()) {
          if (out.rows.size() >= spec.max_rows) throw new RowLimitExceededException(spec.table, spec.max_rows);
          Object[] row = new Object[out.columns.size()];
          for (int i = 0; i < row.length; i++) row[i] = rs.getObject(i + 1);
          out.rows.add(row);
        }
        return out;
      }
    }
  }

  @Override
  public void commit() throws Exception {
    conn.commit();
  }

  @Override
  public void rollback() {
    try { conn.rollback(); } catch (Exception ignored) { }
  }

  @Override
  public void close() throws Exception {
    conn.close();
  }
}
