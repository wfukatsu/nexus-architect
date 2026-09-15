package com.scalar.migrate.appside;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.MathContext;
import java.math.RoundingMode;

/** Oracle NUMBER arithmetic on BigDecimal. Every function propagates NULL (null in, null out). */
public final class OracleNumbers {
  private OracleNumbers() {}

  /** NUMBER precision: 38 significant digits. */
  public static final MathContext NUMBER = new MathContext(38, RoundingMode.HALF_UP);

  /** ROUND(n, scale): half away from zero (-2.5 -> -3). A negative scale rounds left of the decimal point. */
  public static BigDecimal round(BigDecimal n, int scale) {
    return n == null ? null : n.setScale(scale, RoundingMode.HALF_UP);
  }

  /** a / b with 38 significant digits. */
  public static BigDecimal divide(BigDecimal a, BigDecimal b) {
    if (a == null || b == null) return null;
    if (b.signum() == 0) throw new ArithmeticException("ORA-01476: divisor is equal to zero");
    return a.divide(b, NUMBER);
  }

  /** a * b (exact). */
  public static BigDecimal multiply(BigDecimal a, BigDecimal b) {
    return a == null || b == null ? null : a.multiply(b);
  }

  /** SUM: NULLs are ignored; all NULL (or no rows) gives NULL. */
  public static BigDecimal sum(Iterable<? extends BigDecimal> values) {
    BigDecimal s = null;
    for (BigDecimal v : values) {
      if (v != null) s = s == null ? v : s.add(v);
    }
    return s;
  }

  /** AVG: NULLs are ignored (neither summed nor counted); all NULL (or no rows) gives NULL. 38 significant digits. */
  public static BigDecimal avg(Iterable<? extends BigDecimal> values) {
    BigDecimal s = null;
    long n = 0;
    for (BigDecimal v : values) {
      if (v != null) {
        s = s == null ? v : s.add(v);
        n++;
      }
    }
    return n == 0 ? null : divide(s, BigDecimal.valueOf(n));
  }

  /** Any Number (or numeric string) as BigDecimal; Double/Float via their shortest decimal representation. */
  public static BigDecimal toBigDecimal(Object v) {
    if (v == null) return null;
    if (v instanceof BigDecimal) return (BigDecimal) v;
    if (v instanceof BigInteger) return new BigDecimal((BigInteger) v);
    if (v instanceof Long || v instanceof Integer || v instanceof Short || v instanceof Byte) {
      return BigDecimal.valueOf(((Number) v).longValue());
    }
    if (v instanceof Double || v instanceof Float) return new BigDecimal(v.toString());
    return new BigDecimal(v.toString().trim());
  }
}
