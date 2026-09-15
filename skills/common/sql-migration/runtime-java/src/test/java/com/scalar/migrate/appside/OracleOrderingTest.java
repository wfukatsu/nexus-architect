package com.scalar.migrate.appside;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.Test;

class OracleOrderingTest {
  static final String KANJI = "𠮷"; // U+20BB7 (surrogate pair)
  static final String HALF_WIDTH_A = "ｱ"; // U+FF71

  @Test
  void binaryIsCodePointOrderNotUtf16Order() {
    // UTF-8 bytes: U+FF71 = EF BD B1 < U+20BB7 = F0 A0 AE B7
    assertTrue(OracleOrdering.BINARY.compare(HALF_WIDTH_A, KANJI) < 0);
    assertTrue(HALF_WIDTH_A.compareTo(KANJI) > 0); // String.compareTo disagrees
    assertTrue(OracleOrdering.BINARY.compare(" > " + KANJI + "店", " > " + HALF_WIDTH_A + "店") > 0);
  }

  @Test
  void binaryBasics() {
    assertTrue(OracleOrdering.BINARY.compare("ab", "abc") < 0);
    assertTrue(OracleOrdering.BINARY.compare("B", "a") < 0); // upper case before lower case
    assertEquals(0, OracleOrdering.BINARY.compare("", ""));
  }

  @Test
  void ascNullsLastDescNullsFirst() {
    List<String> v = new ArrayList<>(Arrays.asList("b", null, "a", "c"));
    v.sort(OracleOrdering.asc(OracleOrdering.BINARY));
    assertEquals(Arrays.asList("a", "b", "c", null), v);
    v.sort(OracleOrdering.desc(OracleOrdering.BINARY));
    assertEquals(Arrays.asList(null, "c", "b", "a"), v);
    List<Integer> n = new ArrayList<>(Arrays.asList(2, null, 10));
    n.sort(OracleOrdering.desc(Comparator.<Integer>naturalOrder()));
    assertEquals(Arrays.asList(null, 10, 2), n);
  }
}
