package com.scalar.migrate.appside.golden;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.scalar.migrate.appside.AppSideQuery;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
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
import org.junit.jupiter.api.io.TempDir;

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

  /** SELECT id FROM t WHERE id >= :min — a query that needs its bind parameter. */
  public static class AtLeastQuery implements AppSideQuery {
    @Override
    public List<Map<String, Object>> run(Map<String, List<Map<String, Object>>> tables) {
      return run(tables, Map.of());
    }

    @Override
    public List<Map<String, Object>> run(Map<String, List<Map<String, Object>>> tables, Map<String, Object> params) {
      BigDecimal min = (BigDecimal) params.get("min");
      List<Map<String, Object>> out = new ArrayList<>();
      for (Map<String, Object> r : tables.get("t")) {
        if (((BigDecimal) r.get("id")).compareTo(min) >= 0) out.add(Map.of("id", r.get("id")));
      }
      return out;
    }
  }

  @Test
  void parametersReachTheImplementation(@TempDir Path dir) throws Exception {
    Path golden = dir.resolve("golden.json");
    Files.writeString(golden, "{\"query\": \"SELECT id FROM t WHERE id >= :min\", \"ordered\": false, \"params\": {\"min\": 2},"
        + " \"tables\": {\"t\": [{\"id\": 1}, {\"id\": 2}, {\"id\": 3}]}, \"expected\": {\"columns\": [\"id\"], \"rows\": [[2], [3]]}}");
    assertEquals(Map.of("min", new BigDecimal("2")), GoldenCheck.load(golden).params());
    assertEquals(List.of(), GoldenCheck.check(golden, new AtLeastQuery()));
    assertEquals(0, GoldenCheck.run(new String[] {golden.toString(), AtLeastQuery.class.getName()}));
  }

  @Test
  void aGoldenWithoutParametersGivesAnEmptyMap() throws Exception {
    assertEquals(Map.of(), GoldenCheck.load(fixture()).params());
    assertEquals(List.of(), GoldenCheck.check(fixture(), new TinyQuery())); // one-argument implementations still run
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
    assertTrue(diffs.stream().anyMatch(d -> d.contains("v: expected=1 actual=2")), diffs.toString());
    assertTrue(diffs.stream().anyMatch(d -> d.contains("row count: expected=2, actual=3")), diffs.toString());
    assertTrue(diffs.stream().noneMatch(d -> d.contains("oracle") || d.contains("java")), diffs.toString());
  }

  @Test
  void unorderedComparisonIsMultiset() {
    String[] cols = {"k"};
    List<List<Object>> expected = List.of(List.of("x"), List.of("x"), List.of("y"));
    assertEquals(List.of(), GoldenCheck.compare(List.of(cols), expected,
        List.of(row(cols, "y"), row(cols, "x"), row(cols, "x")), false));
    List<String> diffs = GoldenCheck.compare(List.of(cols), expected,
        List.of(row(cols, "y"), row(cols, "x"), row(cols, "z")), false);
    assertEquals(List.of("missing (expected only): ['x']", "unexpected (actual only): ['z']"), diffs);
  }

  @Test
  void sourceIsOptionalAndShownOnlyInTheSummary(@TempDir Path dir) throws Exception {
    assertNull(GoldenCheck.load(fixture()).source()); // older golden.json without "source"
    Path pg = dir.resolve("golden.json");
    Files.writeString(pg, Files.readString(fixture()).replaceFirst("\\{", "{\"source\": \"postgres\", "));
    assertEquals("postgres", GoldenCheck.load(pg).source());

    PrintStream stdout = System.out;
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    System.setOut(new PrintStream(out, true, StandardCharsets.UTF_8));
    try {
      AppSideQuery reversed = tables -> {
        List<Map<String, Object>> rows = new TinyQuery().run(tables);
        java.util.Collections.reverse(rows);
        return rows;
      };
      assertEquals(2, GoldenCheck.check(pg, reversed).size());
      assertEquals(0, GoldenCheck.run(new String[] {pg.toString(), TinyQuery.class.getName()}));
    } finally {
      System.setOut(stdout);
    }
    assertEquals("PASS 3 rows (expected from postgres)", out.toString(StandardCharsets.UTF_8).trim());
  }

  @Test
  void missingColumnIsReported() {
    List<String> diffs = GoldenCheck.compare(List.of("k"), List.of(Arrays.asList((Object) null)),
        List.of(new LinkedHashMap<>()), true);
    assertEquals(1, diffs.size(), diffs.toString());
    assertTrue(diffs.get(0).contains("column k missing"));
  }
}
