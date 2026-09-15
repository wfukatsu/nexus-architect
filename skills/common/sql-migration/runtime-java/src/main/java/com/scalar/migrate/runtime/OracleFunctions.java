package com.scalar.migrate.runtime;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.Statement;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.time.temporal.TemporalAdjusters;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Oracle functions that H2's Oracle compatibility mode lacks, implemented as H2 Java user-defined functions
 * (the function compatibility gaps in references/architecture.md). Semantics follow the Oracle SQL
 * Language Reference; each function is registered with CREATE ALIAS on every residual session.
 */
public final class OracleFunctions {
  private OracleFunctions() {}

  private static final String[][] ALIASES = {
      {"INITCAP", "initcap"}, {"TO_NUMBER", "toNumber"}, {"MONTHS_BETWEEN", "monthsBetween"},
      {"NEXT_DAY", "nextDay"}, {"REGEXP_COUNT", "regexpCount"}, {"DAYS_BETWEEN", "daysBetween"},
  };

  static void register(Connection h2) throws Exception {
    try (Statement s = h2.createStatement()) {
      for (String[] a : ALIASES) {
        s.execute("CREATE ALIAS IF NOT EXISTS " + a[0] + " FOR \"" + OracleFunctions.class.getName() + "." + a[1] + "\"");
      }
    }
  }

  /** INITCAP: first letter of each word upper-case, the rest lower-case; words are delimited by non-alphanumerics. */
  public static String initcap(String s) {
    if (s == null) return null;
    StringBuilder sb = new StringBuilder(s.length());
    boolean start = true;
    for (char ch : s.toCharArray()) {
      if (Character.isLetterOrDigit(ch)) {
        sb.append(start ? Character.toUpperCase(ch) : Character.toLowerCase(ch));
        start = false;
      } else {
        sb.append(ch);
        start = true;
      }
    }
    return sb.toString();
  }

  /** TO_NUMBER(text): decimal conversion (format models are not supported). */
  public static BigDecimal toNumber(String s) {
    return s == null || s.isEmpty() ? null : new BigDecimal(s.trim());
  }

  /**
   * MONTHS_BETWEEN(d1, d2): whole months when both are the same day of month or both are month ends, otherwise a
   * fractional month based on a 31-day month (Oracle rule).
   */
  public static BigDecimal monthsBetween(LocalDateTime d1, LocalDateTime d2) {
    if (d1 == null || d2 == null) return null;
    LocalDate a = d1.toLocalDate(), b = d2.toLocalDate();
    long months = (a.getYear() - b.getYear()) * 12L + (a.getMonthValue() - b.getMonthValue());
    boolean aLast = a.equals(a.with(TemporalAdjusters.lastDayOfMonth()));
    boolean bLast = b.equals(b.with(TemporalAdjusters.lastDayOfMonth()));
    if (a.getDayOfMonth() == b.getDayOfMonth() || (aLast && bLast)) return BigDecimal.valueOf(months);
    double dayFraction = (a.getDayOfMonth() - b.getDayOfMonth()
        + (d1.toLocalTime().toSecondOfDay() - d2.toLocalTime().toSecondOfDay()) / 86400.0) / 31.0;
    return BigDecimal.valueOf(months + dayFraction);
  }

  /** NEXT_DAY(d, 'MONDAY'): the first named weekday strictly after d (time of day preserved). */
  public static LocalDateTime nextDay(LocalDateTime d, String weekday) {
    if (d == null || weekday == null) return null;
    String w = weekday.trim().toUpperCase(Locale.ROOT);
    DayOfWeek target = null;
    for (DayOfWeek dow : DayOfWeek.values()) {
      String name = dow.name();
      if (name.equals(w) || name.substring(0, 3).equals(w)) target = dow;
    }
    if (target == null) throw new IllegalArgumentException("NEXT_DAY: not a valid day of the week: " + weekday);
    return d.with(TemporalAdjusters.next(target));
  }

  /** REGEXP_COUNT(text, pattern): number of non-overlapping matches. */
  public static Integer regexpCount(String s, String pattern) {
    if (s == null || pattern == null) return null;
    Matcher m = Pattern.compile(pattern).matcher(s);
    int n = 0;
    while (m.find()) n++;
    return n;
  }

  /** Helper used by DATEDIFF rewrites of Oracle "date - date" (fractional days). */
  public static BigDecimal daysBetween(LocalDateTime a, LocalDateTime b) {
    if (a == null || b == null) return null;
    return BigDecimal.valueOf(ChronoUnit.SECONDS.between(b, a) / 86400.0);
  }
}
