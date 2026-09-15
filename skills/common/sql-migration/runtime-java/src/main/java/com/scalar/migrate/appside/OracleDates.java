package com.scalar.migrate.appside;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.TemporalAdjusters;

/** Oracle date functions. NULL in, NULL out. */
public final class OracleDates {
  private OracleDates() {}

  private static final DateTimeFormatter YYYY_MM = DateTimeFormatter.ofPattern("uuuu-MM");

  /**
   * ADD_MONTHS(d, n): if d is the last day of its month, or the target month is shorter than d's day, the result is
   * the last day of the target month (2025-02-28 -12 -> 2024-02-29; 2026-01-31 +1 -> 2026-02-28). Time is preserved.
   */
  public static LocalDate addMonths(LocalDate d, int n) {
    if (d == null) return null;
    LocalDate r = d.plusMonths(n); // plusMonths already clamps to the target month's end
    return d.getDayOfMonth() == d.lengthOfMonth() ? r.with(TemporalAdjusters.lastDayOfMonth()) : r;
  }

  public static LocalDateTime addMonths(LocalDateTime d, int n) {
    return d == null ? null : LocalDateTime.of(addMonths(d.toLocalDate(), n), d.toLocalTime());
  }

  /** TO_CHAR(d, 'YYYY-MM'). */
  public static String yearMonth(LocalDateTime d) {
    return d == null ? null : YYYY_MM.format(d);
  }

  public static String yearMonth(LocalDate d) {
    return d == null ? null : YYYY_MM.format(d);
  }
}
