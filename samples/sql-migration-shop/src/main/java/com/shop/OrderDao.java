package com.shop;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

/** Plain JDBC access the SQL migration inventory reads: a constant, a concatenation, and SQL from configuration. */
public class OrderDao {
  private static final String CUSTOMER_ORDERS =
      "SELECT order_no, status, COALESCE(total, 0) AS total FROM orders " +
      "WHERE customer_id = ? ORDER BY order_no";

  private final String reportQuery;  // loaded from application.properties at startup

  public OrderDao(String reportQuery) {
    this.reportQuery = reportQuery;
  }

  public List<OrderRow> customerOrders(Connection conn, long customerId) throws SQLException {
    try (PreparedStatement ps = conn.prepareStatement(CUSTOMER_ORDERS)) {
      ps.setLong(1, customerId);
      return OrderRow.map(ps.executeQuery());
    }
  }

  public List<Long> sortedOrderNumbers(Connection conn, String column) throws SQLException {
    try (ResultSet rs = conn.createStatement().executeQuery("SELECT order_no FROM orders ORDER BY " + column)) {
      return OrderRow.keys(rs);
    }
  }

  public ResultSet configuredReport(Connection conn) throws SQLException {
    return conn.prepareStatement(reportQuery).executeQuery();
  }
}
