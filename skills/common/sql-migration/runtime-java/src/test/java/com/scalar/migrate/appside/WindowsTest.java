package com.scalar.migrate.appside;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import org.junit.jupiter.api.Test;

class WindowsTest {
  static List<BigDecimal> decs(String... v) {
    return Arrays.stream(v).map(s -> s == null ? null : new BigDecimal(s)).toList();
  }

  static void assertDecs(List<BigDecimal> expected, List<BigDecimal> actual) {
    assertEquals(expected.size(), actual.size());
    for (int i = 0; i < expected.size(); i++) {
      if (expected.get(i) == null) assertNull(actual.get(i), "index " + i);
      else assertEquals(0, expected.get(i).compareTo(actual.get(i)), "index " + i + ": " + actual.get(i));
    }
  }

  @Test
  void partitionByKeepsFirstSeenOrder() {
    Map<String, List<String>> p = Windows.partitionBy(List.of("b1", "a1", "b2", "c1", "a2"), s -> s.substring(0, 1));
    assertEquals(List.of("b", "a", "c"), List.copyOf(p.keySet()));
    assertEquals(List.of("b1", "b2"), p.get("b"));
  }

  @Test
  void partitionByNullKey() {
    Map<String, List<String>> p = Windows.partitionBy(List.of("x", "", "y"), s -> s.isEmpty() ? null : "k");
    assertEquals(List.of(""), p.get(null));
  }

  @Test
  void lagAndLead() {
    List<Integer> rows = Arrays.asList(10, 20, null, 40);
    Function<Integer, Integer> id = x -> x;
    assertEquals(Arrays.asList(-1, 10, 20, null), Windows.lag(rows, id, 1, -1)); // NULL value is not replaced
    assertEquals(Arrays.asList(null, null, 10, 20), Windows.lag(rows, id, 2, null));
    assertEquals(Arrays.asList(20, null, 40, 0), Windows.lead(rows, id, 1, 0));
    assertEquals(rows, Windows.lag(rows, id, 0, -1));
  }

  @Test
  void movingAverageIgnoresNulls() {
    // frames (2 PRECEDING): [10] [10,-] [10,-,20] [-,20,-] [20,-,-] [-,-,-]
    assertDecs(decs("10", "10", "15", "20", "20", null),
        Windows.movingAverage(decs("10", null, "20", null, null, null), 2));
    assertDecs(decs(), Windows.movingAverage(decs(), 2));
  }

  @Test
  void movingAverageKeepsPrecisionForCallerRounding() {
    // (1 + 0 + 0) / 3 = 0.333... (38 digits) -> ROUND 0
    List<BigDecimal> avg = Windows.movingAverage(decs("1", "0", "0"), 2);
    assertEquals(new BigDecimal("0." + "3".repeat(38)), avg.get(2));
    // (5 + -10) / 2 = -2.5 exactly -> ROUND -3 (half away from zero)
    List<BigDecimal> neg = Windows.movingAverage(decs("5", "-10"), 1);
    assertEquals(0, new BigDecimal("-3").compareTo(OracleNumbers.round(neg.get(1), 0)));
  }

  @Test
  void ranks() {
    List<Integer> asc = List.of(10, 10, 20, 30, 30, 30, 40);
    Comparator<Integer> cmp = Comparator.naturalOrder();
    assertEquals(List.of(1L, 2L, 3L, 4L, 5L, 6L, 7L), Windows.rowNumber(asc));
    assertEquals(List.of(1L, 1L, 3L, 4L, 4L, 4L, 7L), Windows.rank(asc, cmp));
    assertEquals(List.of(1L, 1L, 2L, 3L, 3L, 3L, 4L), Windows.denseRank(asc, cmp));
  }

  @Test
  void ranksDescendingNullsFirst() {
    Comparator<BigDecimal> desc = OracleOrdering.desc(Comparator.<BigDecimal>naturalOrder());
    List<BigDecimal> sorted = new java.util.ArrayList<>(decs("5", null, "3", "5.0", null));
    sorted.sort(desc);
    assertDecs(decs(null, null, "5", "5.0", "3"), sorted);
    assertEquals(List.of(1L, 1L, 3L, 3L, 5L), Windows.rank(sorted, desc));
    assertEquals(List.of(1L, 1L, 2L, 2L, 3L), Windows.denseRank(sorted, desc)); // 5 and 5.0 tie (compareTo)
  }
}
