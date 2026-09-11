package com.example.shop.model;

import java.io.Serializable;

public class CartLine implements Serializable {

    private static final long serialVersionUID = 1L;

    private final Product product;
    private int quantity;

    public CartLine(Product product, int quantity) {
        this.product = product;
        this.quantity = quantity;
    }

    public Product getProduct() {
        return product;
    }

    public int getQuantity() {
        return quantity;
    }

    public void addQuantity(int more) {
        this.quantity += more;
    }

    public int getLineTotal() {
        return product.getPrice() * quantity;
    }
}
