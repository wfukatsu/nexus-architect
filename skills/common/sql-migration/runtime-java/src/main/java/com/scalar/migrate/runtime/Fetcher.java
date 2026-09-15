package com.scalar.migrate.runtime;

import java.util.Map;

/** Executes the fetch part of a plan through ScalarDB. Both implementations go through ScalarDB only. */
public interface Fetcher extends AutoCloseable {
  /** Begin one ScalarDB transaction; every fetch of a plan runs inside it (consistent snapshot). */
  void begin() throws Exception;

  Rows fetch(Plan.Fetch spec, Map<String, Object> params) throws Exception;

  void commit() throws Exception;

  void rollback();
}
