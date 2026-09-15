package com.scalar.migrate.appside;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;

class OracleNumbersTest {
  static BigDecimal d(String s) {
    return new BigDecimal(s);
  }

  static void same(String expected, BigDecimal actual) {
    assertEquals(0, d(expected).compareTo(actual), "expected " + expected + " but was " + actual);
  }

  @Test
  void roundHalfAwayFromZero() {
    same("3", OracleNumbers.round(d("2.5"), 0));
    same("-3", OracleNumbers.round(d("-2.5"), 0));
    same("-2", OracleNumbers.round(d("-2.4999"), 0));
    same("3.13", OracleNumbers.round(d("3.125"), 2));
    same("-3.13", OracleNumbers.round(d("-3.125"), 2));
    same("0", OracleNumbers.round(d("0.333"), 0));
    same("1300", OracleNumbers.round(d("1250.1"), -2));
    same("-1300", OracleNumbers.round(d("-1250"), -2));
    assertNull(OracleNumbers.round(null, 2));
  }

  @Test
  void divideWith38SignificantDigits() {
    BigDecimal third = OracleNumbers.divide(d("1"), d("3"));
    assertEquals(38, third.precision());
    assertEquals(d("0." + "3".repeat(38)), third);
    same("-2.5", OracleNumbers.divide(d("-5"), d("2")));
    assertEquals(d("0." + "6".repeat(37) + "7"), OracleNumbers.divide(d("2"), d("3")));
  }

  @Test
  void divideByZeroIsOra01476() {
    ArithmeticException e = assertThrows(ArithmeticException.class, () -> OracleNumbers.divide(d("1"), d("0.00")));
    assertTrue(e.getMessage().contains("ORA-01476"));
    assertNull(OracleNumbers.divide(null, d("0"))); // NULL / 0 is NULL in Oracle
    assertNull(OracleNumbers.divide(d("1"), null));
  }

  @Test
  void multiplyPropagatesNull() {
    same("312.5", OracleNumbers.multiply(d("3.125"), d("100")));
    assertNull(OracleNumbers.multiply(null, d("100")));
  }

  @Test
  void sumAndAvgIgnoreNulls() {
    List<BigDecimal> mixed = Arrays.asList(null, d("1"), d("2"), null);
    same("3", OracleNumbers.sum(mixed));
    same("1.5", OracleNumbers.avg(mixed));
    assertNull(OracleNumbers.sum(Arrays.asList(null, null)));
    assertNull(OracleNumbers.avg(Arrays.asList(null, null)));
    assertNull(OracleNumbers.sum(List.of()));
    assertNull(OracleNumbers.avg(List.of()));
    same("0", OracleNumbers.sum(List.of(d("10"), d("-10"))));
  }

  @Test
  void toBigDecimal() {
    assertEquals(d("0.1"), OracleNumbers.toBigDecimal(0.1d));
    same("42", OracleNumbers.toBigDecimal(42L));
    same("7", OracleNumbers.toBigDecimal(7));
    same("1.50", OracleNumbers.toBigDecimal(" 1.50"));
    assertNull(OracleNumbers.toBigDecimal(null));
  }
}
