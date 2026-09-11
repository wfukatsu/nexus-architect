package com.example.shop.model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Shopping cart held in the HTTP session under the key "cart". */
public class Cart implements Serializable {

    private static final long serialVersionUID = 1L;

    private final List<CartLine> lines = new ArrayList<>();

    public void add(Product product, int quantity) {
        for (CartLine line : lines) {
            if (line.getProduct().getId().equals(product.getId())) {
                line.addQuantity(quantity);
                return;
            }
        }
        lines.add(new CartLine(product, quantity));
    }

    public void remove(String productId) {
        lines.removeIf(line -> line.getProduct().getId().equals(productId));
    }

    public List<CartLine> getLines() {
        return Collections.unmodifiableList(lines);
    }

    public int getItemCount() {
        int count = 0;
        for (CartLine line : lines) {
            count += line.getQuantity();
        }
        return count;
    }

    public int getSubtotal() {
        int subtotal = 0;
        for (CartLine line : lines) {
            subtotal += line.getLineTotal();
        }
        return subtotal;
    }

    public boolean isEmpty() {
        return lines.isEmpty();
    }
}
