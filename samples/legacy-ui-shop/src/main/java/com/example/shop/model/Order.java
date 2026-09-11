package com.example.shop.model;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

public class Order implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String orderNo;
    private final String userId;
    private final List<CartLine> lines;
    private final OrderForm form;
    private final int subtotal;
    private final int discount;
    private final int tax;
    private final int total;
    private final LocalDateTime orderedAt;

    public Order(String orderNo, String userId, List<CartLine> lines, OrderForm form,
                 int subtotal, int discount, int tax, int total, LocalDateTime orderedAt) {
        this.orderNo = orderNo;
        this.userId = userId;
        this.lines = new ArrayList<>(lines);
        this.form = form;
        this.subtotal = subtotal;
        this.discount = discount;
        this.tax = tax;
        this.total = total;
        this.orderedAt = orderedAt;
    }

    public String getOrderNo() {
        return orderNo;
    }

    public String getUserId() {
        return userId;
    }

    public List<CartLine> getLines() {
        return lines;
    }

    public OrderForm getForm() {
        return form;
    }

    public int getSubtotal() {
        return subtotal;
    }

    public int getDiscount() {
        return discount;
    }

    public int getTax() {
        return tax;
    }

    public int getTotal() {
        return total;
    }

    public LocalDateTime getOrderedAt() {
        return orderedAt;
    }
}
