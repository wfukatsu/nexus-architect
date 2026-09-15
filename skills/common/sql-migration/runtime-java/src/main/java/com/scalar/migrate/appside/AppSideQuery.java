package com.scalar.migrate.appside;

import java.util.List;
import java.util.Map;

/**
 * A query implemented in Java because it runs neither on ScalarDB SQL nor in the H2 residual engine.
 * Tables are keyed by lower-case table name, rows by lower-case column name. Numbers should be accepted as any
 * {@link Number} (golden data decodes NUMBER as BigDecimal); DATE arrives as LocalDateTime.
 * The golden check (golden.GoldenCheck) runs an implementation against rows captured from Oracle.
 */
public interface AppSideQuery {
  List<Map<String, Object>> run(Map<String, List<Map<String, Object>>> tables);
}
