package com.example.shop.model;

import java.io.Serializable;

public class Product implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;
    private String name;
    private String category;
    private int price;
    private int stock;
    private String image;

    public Product() {
    }

    public Product(String id, String name, String category, int price, int stock, String image) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.price = price;
        this.stock = stock;
        this.image = image;
    }

    public Product copy() {
        return new Product(id, name, category, price, stock, image);
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public int getPrice() {
        return price;
    }

    public void setPrice(int price) {
        this.price = price;
    }

    public int getStock() {
        return stock;
    }

    public void setStock(int stock) {
        this.stock = stock;
    }

    public String getImage() {
        return image;
    }

    public void setImage(String image) {
        this.image = image;
    }
}
