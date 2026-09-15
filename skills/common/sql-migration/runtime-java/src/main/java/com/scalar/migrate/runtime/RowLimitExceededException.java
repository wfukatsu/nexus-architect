package com.scalar.migrate.runtime;

public class RowLimitExceededException extends RuntimeException {
  public RowLimitExceededException(String table, int limit) {
    super("fetch of " + table + " exceeded the row limit " + limit + "; narrow the pushdown predicate or paginate");
  }
}
