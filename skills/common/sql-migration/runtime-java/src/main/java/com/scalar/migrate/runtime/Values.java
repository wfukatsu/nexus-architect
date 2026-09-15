package com.scalar.migrate.runtime;

import com.scalar.db.api.Result;
import com.scalar.db.io.BigIntColumn;
import com.scalar.db.io.BlobColumn;
import com.scalar.db.io.BooleanColumn;
import com.scalar.db.io.Column;
import com.scalar.db.io.DataType;
import com.scalar.db.io.DateColumn;
import com.scalar.db.io.DoubleColumn;
import com.scalar.db.io.FloatColumn;
import com.scalar.db.io.IntColumn;
import com.scalar.db.io.TextColumn;
import com.scalar.db.io.TimeColumn;
import com.scalar.db.io.TimestampColumn;
import com.scalar.db.io.TimestampTZColumn;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;

/** Conversions between JSON-ish Java objects, ScalarDB columns and H2 values. */
final class Values {
  private Values() {}

  static String h2Type(String scalardbType) {
    switch (scalardbType) {
      case "BOOLEAN": return "BOOLEAN";
      case "INT": return "INT";
      case "BIGINT": return "BIGINT";
      case "FLOAT": return "REAL";
      case "DOUBLE": return "DOUBLE PRECISION";
      case "TEXT": return "VARCHAR";
      case "BLOB": return "BINARY VARYING";
      case "DATE": return "DATE";
      case "TIME": return "TIME";
      case "TIMESTAMP": return "TIMESTAMP";
      case "TIMESTAMPTZ": return "TIMESTAMP WITH TIME ZONE";
      default: throw new IllegalArgumentException("unknown ScalarDB type " + scalardbType);
    }
  }

  static String h2TypeOf(Object v) {
    if (v == null) return "VARCHAR";
    if (v instanceof Boolean) return "BOOLEAN";
    if (v instanceof Integer) return "INT";
    if (v instanceof Long) return "BIGINT";
    if (v instanceof Float) return "REAL";
    if (v instanceof Double) return "DOUBLE PRECISION";
    if (v instanceof byte[]) return "BINARY VARYING";
    if (v instanceof LocalDate) return "DATE";
    if (v instanceof LocalTime) return "TIME";
    if (v instanceof LocalDateTime) return "TIMESTAMP";
    if (v instanceof Instant || v instanceof OffsetDateTime) return "TIMESTAMP WITH TIME ZONE";
    return "VARCHAR";
  }

  /** Build a typed ScalarDB column from a plan/JSON value (numbers arrive as Double from Gson, dates as ISO strings). */
  static Column<?> column(String name, DataType type, Object v) {
    if (v == null) {
      switch (type) {
        case BOOLEAN: return BooleanColumn.ofNull(name);
        case INT: return IntColumn.ofNull(name);
        case BIGINT: return BigIntColumn.ofNull(name);
        case FLOAT: return FloatColumn.ofNull(name);
        case DOUBLE: return DoubleColumn.ofNull(name);
        case TEXT: return TextColumn.ofNull(name);
        case BLOB: return BlobColumn.ofNull(name);
        case DATE: return DateColumn.ofNull(name);
        case TIME: return TimeColumn.ofNull(name);
        case TIMESTAMP: return TimestampColumn.ofNull(name);
        case TIMESTAMPTZ: return TimestampTZColumn.ofNull(name);
        default: throw new IllegalArgumentException("unsupported type " + type);
      }
    }
    switch (type) {
      case BOOLEAN: return BooleanColumn.of(name, v instanceof Boolean ? (Boolean) v : Boolean.parseBoolean(v.toString()));
      case INT: return IntColumn.of(name, ((Number) v).intValue());
      case BIGINT: return BigIntColumn.of(name, ((Number) v).longValue());
      case FLOAT: return FloatColumn.of(name, ((Number) v).floatValue());
      case DOUBLE: return DoubleColumn.of(name, ((Number) v).doubleValue());
      case TEXT: return TextColumn.of(name, v.toString());
      case BLOB: return BlobColumn.of(name, v instanceof byte[] ? (byte[]) v : Base64.getDecoder().decode(v.toString()));
      case DATE: return DateColumn.of(name, LocalDate.parse(v.toString()));
      case TIME: return TimeColumn.of(name, LocalTime.parse(v.toString()));
      case TIMESTAMP: return TimestampColumn.of(name, LocalDateTime.parse(v.toString().replace(' ', 'T')));
      case TIMESTAMPTZ: return TimestampTZColumn.of(name, Instant.parse(v.toString()));
      default: throw new IllegalArgumentException("unsupported type " + type);
    }
  }

  /** Read a column of a ScalarDB result as a plain Java object (null-safe). */
  static Object read(Result r, String name, DataType type) {
    if (r.isNull(name)) return null;
    switch (type) {
      case BOOLEAN: return r.getBoolean(name);
      case INT: return r.getInt(name);
      case BIGINT: return r.getBigInt(name);
      case FLOAT: return r.getFloat(name);
      case DOUBLE: return r.getDouble(name);
      case TEXT: return r.getText(name);
      case BLOB: return r.getBlobAsBytes(name);
      case DATE: return r.getDate(name);
      case TIME: return r.getTime(name);
      case TIMESTAMP: return r.getTimestamp(name);
      case TIMESTAMPTZ: return r.getTimestampTZ(name);
      default: throw new IllegalArgumentException("unsupported type " + type);
    }
  }

  /** Value as accepted by H2's setObject. */
  static Object toH2(Object v) {
    if (v instanceof Instant) return OffsetDateTime.ofInstant((Instant) v, ZoneOffset.UTC);
    return v;
  }

  /** Value for JSON output. */
  static Object toJson(Object v) {
    if (v == null) return null;
    if (v instanceof Number || v instanceof Boolean || v instanceof String) return v;
    if (v instanceof byte[]) return Base64.getEncoder().encodeToString((byte[]) v);
    if (v instanceof java.sql.Timestamp) return ((java.sql.Timestamp) v).toLocalDateTime().toString();
    if (v instanceof java.sql.Date) return ((java.sql.Date) v).toLocalDate().toString();
    if (v instanceof java.sql.Time) return ((java.sql.Time) v).toLocalTime().toString();
    return v.toString();
  }
}
