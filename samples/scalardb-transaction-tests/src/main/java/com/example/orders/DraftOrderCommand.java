package com.example.orders;

import java.util.List;

public record DraftOrderCommand(List<Line> items) {
    public record Line(String productId, int quantity) {}
}
