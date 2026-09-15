package com.scalar.migrate.appside;

import java.util.Comparator;

/** Comparators with Oracle ORDER BY defaults. */
public final class OracleOrdering {
  private OracleOrdering() {}

  /**
   * NLS_SORT=BINARY string order on an AL32UTF8 database: UTF-8 byte order, which equals Unicode code point order.
   * String.compareTo compares UTF-16 units and puts supplementary characters (e.g. U+20BB7) before U+E000..U+FFFF
   * (e.g. half-width katakana), so it must not be used. Nulls are not handled; wrap with asc/desc.
   */
  public static final Comparator<String> BINARY = OracleOrdering::compareCodePoints;

  /** ORDER BY x ASC: NULLS LAST (Oracle default). */
  public static <T> Comparator<T> asc(Comparator<? super T> cmp) {
    return Comparator.nullsLast(cmp);
  }

  /** ORDER BY x DESC: reversed, NULLS FIRST (Oracle default). */
  public static <T> Comparator<T> desc(Comparator<? super T> cmp) {
    Comparator<T> c = (a, b) -> cmp.compare(b, a);
    return Comparator.nullsFirst(c);
  }

  static int compareCodePoints(String a, String b) {
    int i = 0;
    int j = 0;
    while (i < a.length() && j < b.length()) {
      int ca = a.codePointAt(i);
      int cb = b.codePointAt(j);
      if (ca != cb) return Integer.compare(ca, cb);
      i += Character.charCount(ca);
      j += Character.charCount(cb);
    }
    return Integer.compare(a.length() - i, b.length() - j);
  }
}
