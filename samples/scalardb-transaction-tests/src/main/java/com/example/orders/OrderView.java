package com.example.orders;

import java.util.List;

/** Domain read model. customerEmail is Confidential and never reaches the API layer. */
public record OrderView(String orderId, String status, int totalAmount,
                        List<Line> items, String customerEmail) {
    public record Line(String productId, int quantity) {}
}
