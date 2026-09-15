package com.scalar.migrate.appside.golden;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.migrate.appside.AppSideQuery;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GoldenCheckTest {
  static Path fixture() throws Exception {
    return Path.of(GoldenCheckTest.class.getResource("/golden/tiny/golden.json").toURI());
  }

  /** SELECT id, name, amount, created FROM t ORDER BY id — returning Java-native types on purpose. */
  public static class TinyQuery implements AppSideQuery {
    @Override
    public List<Map<String, Object>> run(Map<String, List<Map<String, Object>>> tables) {
      List<Map<String, Object>> out = new ArrayList<>();
      for (Map<String, Object> r : tables.get("t")) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", ((BigDecimal) r.get("id")).longValue()); // Long vs Oracle's NUMBER
        m.put("name", r.get("name"));
        m.put("amount", r.get("amount"));
        m.put("created", r.get("created")); // LocalDate for id 2 vs Oracle DATE 2026-01-02 00:00:00
        out.add(m);
      }
      out.sort(Comparator.comparing(m -> (Long) m.get("id")));
      return out;
    }
  }

  static Map<String, Object> row(String[] cols, Object... values) {
    Map<String, Object> m = new LinkedHashMap<>();
    for (int i = 0; i < cols.length; i++) m.put(cols[i], values[i]);
    return m;
  }

  @Test
  void loadDecodesTypedValues() throws Exception {
    GoldenCheck.Golden g = GoldenCheck.load(fixture());
    assertTrue(g.ordered());
    assertEquals(List.of("id", "name", "amount", "created"), g.columns());
    Map<String, Object> first = g.tables().get("t").get(0);
    assertEquals(new BigDecimal("2"), first.get("id"));
    assertNull(first.get("amount"));
    assertEquals(LocalDate.parse("2026-01-02"), first.get("created"));
    Map<String, Object> second = g.tables().get("t").get(1);
    assertEquals(new BigDecimal("1.50"), second.get("amount"));
    assertEquals(LocalDateTime.parse("2026-01-01T10:30:00"), second.get("created"));
    assertInstanceOf(BigDecimal.class, g.tables().get("t").get(2).get("id")); // plain JSON number
    assertEquals(3, g.rows().size());
  }

  @Test
  void checkPassesWithMixedJavaTypes() throws Exception {
    assertEquals(List.of(), GoldenCheck.check(fixture(), new TinyQuery()));
    assertEquals(0, GoldenCheck.run(new String[] {fixture().toString(), TinyQuery.class.getName()}));
  }

  @Test
  void checkFailsForWrongImplementation() throws Exception {
    AppSideQuery reversed = tables -> {
      List<Map<String, Object>> rows = new TinyQuery().run(tables);
      java.util.Collections.reverse(rows);
      return rows;
    };
    List<String> diffs = GoldenCheck.check(fixture(), reversed);
    assertEquals(2, diffs.size(), diffs.toString()); // rows 0 and 2 swapped, row 1 in place
    assertTrue(diffs.get(0).startsWith("row 0 "), diffs.get(0));
  }

  @Test
  void numbersCompareByValue() {
    assertEquals(GoldenCheck.key(new BigDecimal("1.50")), GoldenCheck.key(1.5d));
    assertEquals(GoldenCheck.key(new BigDecimal("0.000")), GoldenCheck.key(0));
    assertEquals(GoldenCheck.key(new BigDecimal("100")), GoldenCheck.key(100L));
    assertTrue(!GoldenCheck.key("1").equals(GoldenCheck.key(1)));
    assertTrue(!GoldenCheck.key(null).equals(GoldenCheck.key("")));
    assertTrue(!GoldenCheck.key(LocalDateTime.parse("2026-01-01T00:00:01")).equals(GoldenCheck.key(LocalDate.parse("2026-01-01"))));
  }

  @Test
  void orderedComparisonReportsColumnDiffsAndCount() {
    String[] cols = {"k", "v"};
    List<List<Object>> expected = List.of(List.of("a", new BigDecimal("1")), Arrays.asList("b", null));
    List<String> diffs = GoldenCheck.compare(List.of(cols), expected,
        List.of(row(cols, "a", 2), row(cols, "b", null), row(cols, "c", 3)), true);
    assertEquals(3, diffs.size(), diffs.toString());
    assertTrue(diffs.stream().anyMatch(d -> d.contains("v: oracle=1 java=2")), diffs.toString());
    assertTrue(diffs.stream().anyMatch(d -> d.contains("row count: oracle=2, java=3")), diffs.toString());
  }

  @Test
  void unorderedComparisonIsMultiset() {
    String[] cols = {"k"};
    List<List<Object>> expected = List.of(List.of("x"), List.of("x"), List.of("y"));
    assertEquals(List.of(), GoldenCheck.compare(List.of(cols), expected,
        List.of(row(cols, "y"), row(cols, "x"), row(cols, "x")), false));
    List<String> diffs = GoldenCheck.compare(List.of(cols), expected,
        List.of(row(cols, "y"), row(cols, "x"), row(cols, "z")), false);
    assertEquals(List.of("missing (in oracle only): ['x']", "unexpected (in java only): ['z']"), diffs);
  }

  @Test
  void missingColumnIsReported() {
    List<String> diffs = GoldenCheck.compare(List.of("k"), List.of(Arrays.asList((Object) null)),
        List.of(new LinkedHashMap<>()), true);
    assertEquals(1, diffs.size(), diffs.toString());
    assertTrue(diffs.get(0).contains("column k missing"));
  }
}
