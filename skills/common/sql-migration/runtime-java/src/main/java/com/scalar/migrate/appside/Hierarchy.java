package com.scalar.migrate.appside;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;

/**
 * Oracle hierarchical query {@code START WITH <startWith> CONNECT BY PRIOR <id> = <parentId>} over in-memory rows.
 *
 * Entries come out in Oracle's depth-first pre-order. Oracle leaves sibling order unspecified (unless ORDER SIBLINGS BY);
 * here siblings keep input order. A row reachable from several roots appears once per root, as in Oracle. A NULL
 * parent id never matches (NULL = x is not true). Traversal is recursive: depth is bounded by the call stack.
 */
public final class Hierarchy {
  private Hierarchy() {}

  /**
   * One output row of the hierarchical query.
   *
   * @param row    the row
   * @param level  LEVEL (root = 1)
   * @param path   SYS_CONNECT_BY_PATH(pathValue, separator), or null when no path function was given
   * @param root   CONNECT_BY_ROOT row
   * @param isLeaf CONNECT_BY_ISLEAF = 1
   */
  public record Entry<T>(T row, int level, String path, T root, boolean isLeaf) {}

  /** START WITH / CONNECT BY without SYS_CONNECT_BY_PATH. */
  public static <T, K> List<Entry<T>> connectBy(List<T> rows, Function<? super T, K> id,
      Function<? super T, K> parentId, Predicate<? super T> startWith) {
    return connectBy(rows, id, parentId, startWith, null, null);
  }

  /**
   * START WITH / CONNECT BY with SYS_CONNECT_BY_PATH: the separator is prefixed before every value (also the root's)
   * and a NULL value contributes an empty string.
   *
   * @throws IllegalStateException ORA-01436 when a row is reached again below itself (cycle), ORA-30004 when a path
   *                               value contains the separator
   */
  public static <T, K> List<Entry<T>> connectBy(List<T> rows, Function<? super T, K> id,
      Function<? super T, K> parentId, Predicate<? super T> startWith,
      Function<? super T, String> pathValue, String separator) {
    Objects.requireNonNull(rows, "rows");
    if (pathValue != null && (separator == null || separator.isEmpty())) {
      throw new IllegalArgumentException("SYS_CONNECT_BY_PATH needs a non-empty separator");
    }
    Map<K, List<T>> children = new HashMap<>();
    for (T r : rows) {
      K p = parentId.apply(r);
      if (p != null) children.computeIfAbsent(p, k -> new ArrayList<>()).add(r);
    }
    Walker<T, K> w = new Walker<>(id, children, pathValue, separator);
    for (T r : rows) {
      if (startWith.test(r)) w.visit(r, r, 1, "");
    }
    return w.out;
  }

  private static final class Walker<T, K> {
    final Function<? super T, K> id;
    final Map<K, List<T>> children;
    final Function<? super T, String> pathValue;
    final String separator;
    final Set<T> ancestors = Collections.newSetFromMap(new IdentityHashMap<>());
    final List<Entry<T>> out = new ArrayList<>();

    Walker(Function<? super T, K> id, Map<K, List<T>> children, Function<? super T, String> pathValue, String separator) {
      this.id = id;
      this.children = children;
      this.pathValue = pathValue;
      this.separator = separator;
    }

    void visit(T row, T root, int level, String parentPath) {
      if (!ancestors.add(row)) {
        throw new IllegalStateException("ORA-01436: CONNECT BY loop in user data (row " + row + ")");
      }
      String path = null;
      if (pathValue != null) {
        String v = pathValue.apply(row);
        if (v != null && v.contains(separator)) {
          throw new IllegalStateException("ORA-30004: when using SYS_CONNECT_BY_PATH function, cannot have separator as"
              + " part of column value (value \"" + v + "\")");
        }
        path = parentPath + separator + (v == null ? "" : v);
      }
      K key = id.apply(row);
      List<T> kids = key == null ? List.of() : children.getOrDefault(key, List.of());
      out.add(new Entry<>(row, level, path, root, kids.isEmpty()));
      for (T child : kids) visit(child, root, level + 1, path);
      ancestors.remove(row);
    }
  }
}
