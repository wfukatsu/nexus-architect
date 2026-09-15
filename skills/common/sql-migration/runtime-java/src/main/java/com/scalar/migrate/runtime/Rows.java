package com.scalar.migrate.runtime;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** A fetched relation: ordered column names, ScalarDB types (may be empty when unknown) and rows. */
public class Rows {
  public final List<String> columns = new ArrayList<>();
  public final Map<String, String> types = new LinkedHashMap<>();
  public final List<Object[]> rows = new ArrayList<>();
}
