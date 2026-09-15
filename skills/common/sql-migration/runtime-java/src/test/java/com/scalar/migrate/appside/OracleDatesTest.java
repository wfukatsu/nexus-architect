package com.scalar.migrate.appside;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.time.LocalDate;
import java.time.LocalDateTime;
import org.junit.jupiter.api.Test;

class OracleDatesTest {
  static LocalDate d(String s) {
    return LocalDate.parse(s);
  }

  @Test
  void addMonthsMonthEndRule() {
    assertEquals(d("2024-02-29"), OracleDates.addMonths(d("2025-02-28"), -12)); // month end -> month end
    assertEquals(d("2025-02-28"), OracleDates.addMonths(d("2024-02-29"), 12));
    assertEquals(d("2026-03-31"), OracleDates.addMonths(d("2026-02-28"), 1));
    assertEquals(d("2026-04-30"), OracleDates.addMonths(d("2026-03-31"), 1));
    assertEquals(d("2026-02-28"), OracleDates.addMonths(d("2026-01-31"), 1));
    assertEquals(d("2026-02-28"), OracleDates.addMonths(d("2026-01-30"), 1)); // shorter target month clamps
    assertEquals(d("2026-03-30"), OracleDates.addMonths(d("2026-01-30"), 2));
    assertEquals(d("2025-12-15"), OracleDates.addMonths(d("2026-01-15"), -1));
    assertNull(OracleDates.addMonths((LocalDate) null, 1));
  }

  @Test
  void addMonthsKeepsTime() {
    assertEquals(LocalDateTime.parse("2024-02-29T23:59:59"),
        OracleDates.addMonths(LocalDateTime.parse("2025-02-28T23:59:59"), -12));
    assertNull(OracleDates.addMonths((LocalDateTime) null, 1));
  }

  @Test
  void yearMonth() {
    assertEquals("2026-12", OracleDates.yearMonth(LocalDateTime.parse("2026-12-31T23:59:59")));
    assertEquals("0099-01", OracleDates.yearMonth(d("0099-01-01")));
    assertNull(OracleDates.yearMonth((LocalDateTime) null));
  }
}
