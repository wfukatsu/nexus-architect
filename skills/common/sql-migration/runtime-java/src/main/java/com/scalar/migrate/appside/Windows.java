package com.scalar.migrate.appside;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

/**
 * Analytic (window) functions over in-memory partitions. Typical use: partitionBy, sort each partition with the
 * window's ORDER BY (OracleOrdering), then compute a per-row list aligned with the sorted partition.
 */
public final class Windows {
  private Windows() {}

  /** PARTITION BY key: groups in first-seen order, rows in input order. A null key is its own partition. */
  public static <T, K> Map<K, List<T>> partitionBy(Collection<T> rows, Function<? super T, ? extends K> key) {
    Map<K, List<T>> out = new LinkedHashMap<>();
    for (T r : rows) out.computeIfAbsent(key.apply(r), k -> new ArrayList<>()).add(r);
    return out;
  }

  /** LAG(value, offset, default) over a sorted partition; result i belongs to row i. */
  public static <T, V> List<V> lag(List<T> sorted, Function<? super T, ? extends V> value, int offset, V defaultValue) {
    return shift(sorted, value, -offset, defaultValue);
  }

  /** LEAD(value, offset, default) over a sorted partition; result i belongs to row i. */
  public static <T, V> List<V> lead(List<T> sorted, Function<? super T, ? extends V> value, int offset, V defaultValue) {
    return shift(sorted, value, offset, defaultValue);
  }

  private static <T, V> List<V> shift(List<T> sorted, Function<? super T, ? extends V> value, int by, V defaultValue) {
    List<V> out = new ArrayList<>(sorted.size());
    for (int i = 0; i < sorted.size(); i++) {
      int j = i + by;
      // Oracle: the default applies only when the offset row is outside the partition, not when its value is NULL
      out.add(j >= 0 && j < sorted.size() ? value.apply(sorted.get(j)) : defaultValue);
    }
    return out;
  }

  /**
   * AVG(v) OVER (... ROWS BETWEEN preceding PRECEDING AND CURRENT ROW): NULLs ignored, NULL if the frame has no
   * non-NULL value. Computed with 38 significant digits (OracleNumbers.avg); the caller applies ROUND.
   */
  public static List<BigDecimal> movingAverage(List<? extends BigDecimal> values, int preceding) {
    if (preceding < 0) throw new IllegalArgumentException("preceding must be >= 0");
    List<BigDecimal> out = new ArrayList<>(values.size());
    for (int i = 0; i < values.size(); i++) {
      out.add(OracleNumbers.avg(values.subList(Math.max(0, i - preceding), i + 1)));
    }
    return out;
  }

  /** ROW_NUMBER() over a sorted partition: 1..n. */
  public static List<Long> rowNumber(List<?> sorted) {
    List<Long> out = new ArrayList<>(sorted.size());
    for (int i = 0; i < sorted.size(); i++) out.add(i + 1L);
    return out;
  }

  /** RANK() over a partition sorted by cmp: ties (cmp == 0) share a rank and leave gaps (1, 1, 3). */
  public static <T> List<Long> rank(List<T> sorted, Comparator<? super T> cmp) {
    List<Long> out = new ArrayList<>(sorted.size());
    for (int i = 0; i < sorted.size(); i++) {
      out.add(i > 0 && cmp.compare(sorted.get(i - 1), sorted.get(i)) == 0 ? out.get(i - 1) : i + 1L);
    }
    return out;
  }

  /** DENSE_RANK() over a partition sorted by cmp: ties share a rank without gaps (1, 1, 2). */
  public static <T> List<Long> denseRank(List<T> sorted, Comparator<? super T> cmp) {
    List<Long> out = new ArrayList<>(sorted.size());
    for (int i = 0; i < sorted.size(); i++) {
      if (i == 0) out.add(1L);
      else out.add(out.get(i - 1) + (cmp.compare(sorted.get(i - 1), sorted.get(i)) == 0 ? 0 : 1));
    }
    return out;
  }
}
