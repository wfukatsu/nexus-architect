package com.scalar.migrate.appside;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Objects;
import org.junit.jupiter.api.Test;

class HierarchyTest {
  record Node(Integer id, Integer parent, String name) {}

  static List<Hierarchy.Entry<Node>> fromRoots(List<Node> rows) {
    return Hierarchy.connectBy(rows, Node::id, Node::parent, n -> n.parent() == null, Node::name, "/");
  }

  static String render(List<Hierarchy.Entry<Node>> entries) {
    StringBuilder sb = new StringBuilder();
    for (Hierarchy.Entry<Node> e : entries) {
      sb.append(e.row().id()).append(' ').append(e.level()).append(' ').append(e.path()).append(' ')
          .append(e.root().id()).append(' ').append(e.isLeaf() ? 1 : 0).append('\n');
    }
    return sb.toString();
  }

  @Test
  void preOrderLevelPathRootLeaf() {
    List<Node> rows = List.of(
        new Node(1, null, "A"), new Node(3, 1, "C"), new Node(2, 1, "B"), new Node(4, 3, "D"),
        new Node(10, null, "X"), new Node(11, 10, "Y"),
        new Node(99, 98, "orphan"));
    // depth-first pre-order; siblings (3, 2) keep input order; the orphan is unreachable
    assertEquals("""
        1 1 /A 1 0
        3 2 /A/C 1 0
        4 3 /A/C/D 1 1
        2 2 /A/B 1 1
        10 1 /X 10 0
        11 2 /X/Y 10 1
        """, render(fromRoots(rows)));
  }

  @Test
  void rowReachableFromTwoStartRowsAppearsTwice() {
    List<Node> rows = List.of(new Node(1, null, "A"), new Node(2, 1, "B"), new Node(3, 2, "C"));
    List<Hierarchy.Entry<Node>> out =
        Hierarchy.connectBy(rows, Node::id, Node::parent, n -> n.id() <= 2, Node::name, " > ");
    assertEquals("""
        1 1  > A 1 0
        2 2  > A > B 1 0
        3 3  > A > B > C 1 1
        2 1  > B 2 0
        3 2  > B > C 2 1
        """, render(out));
  }

  @Test
  void nullPathValueContributesEmptyString() {
    List<Node> rows = List.of(new Node(1, null, "A"), new Node(2, 1, null), new Node(3, 2, "C"));
    assertEquals(List.of("/A", "/A/", "/A//C"), fromRoots(rows).stream().map(Hierarchy.Entry::path).toList());
  }

  @Test
  void withoutPathFunctionPathIsNull() {
    List<Node> rows = List.of(new Node(1, null, "A/B"));
    Hierarchy.Entry<Node> e = Hierarchy.connectBy(rows, Node::id, Node::parent, n -> n.parent() == null).get(0);
    assertNull(e.path());
    assertTrue(e.isLeaf());
  }

  @Test
  void nullParentNeverMatchesNullId() {
    List<Node> rows = List.of(new Node(null, null, "root with null id"), new Node(2, null, "B"));
    assertTrue(fromRoots(rows).stream().allMatch(e -> e.level() == 1 && e.isLeaf()));
  }

  @Test
  void cycleReachedDuringTraversalIsOra01436() {
    // 1 -> 2 -> 3 -> 1
    List<Node> rows = List.of(new Node(1, 3, "A"), new Node(2, 1, "B"), new Node(3, 2, "C"));
    IllegalStateException e = assertThrows(IllegalStateException.class,
        () -> Hierarchy.connectBy(rows, Node::id, Node::parent, n -> n.id() == 1, Node::name, "/"));
    assertTrue(e.getMessage().contains("ORA-01436"), e.getMessage());
  }

  @Test
  void selfLoopIsOra01436() {
    List<Node> rows = List.of(new Node(5, 5, "self"));
    assertThrows(IllegalStateException.class,
        () -> Hierarchy.connectBy(rows, Node::id, Node::parent, n -> Objects.equals(n.id(), 5)));
  }

  @Test
  void unreachableCycleIsIgnored() {
    List<Node> rows = List.of(new Node(1, null, "A"), new Node(7, 8, "P"), new Node(8, 7, "Q"));
    assertEquals(1, fromRoots(rows).size());
  }

  @Test
  void separatorInsideValueIsOra30004() {
    List<Node> rows = List.of(new Node(1, null, "A"), new Node(2, 1, "B > C"));
    IllegalStateException e = assertThrows(IllegalStateException.class,
        () -> Hierarchy.connectBy(rows, Node::id, Node::parent, n -> n.parent() == null, Node::name, " > "));
    assertTrue(e.getMessage().contains("ORA-30004"), e.getMessage());
  }
}
