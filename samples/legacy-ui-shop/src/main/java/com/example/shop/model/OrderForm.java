package com.example.shop.model;

import java.io.Serializable;

/** Shipping and payment details entered on the order entry screen. */
public class OrderForm implements Serializable {

    private static final long serialVersionUID = 1L;

    private String shippingName;
    private String postalCode;
    private String address;
    private String phone;
    private String email;
    /** CARD, BANK or COD. */
    private String paymentMethod;
    private String notes;

    public String getPaymentMethodLabel() {
        if ("CARD".equals(paymentMethod)) {
            return "クレジットカード";
        }
        if ("BANK".equals(paymentMethod)) {
            return "銀行振込";
        }
        if ("COD".equals(paymentMethod)) {
            return "代金引換";
        }
        return "";
    }

    public String getShippingName() {
        return shippingName;
    }

    public void setShippingName(String shippingName) {
        this.shippingName = shippingName;
    }

    public String getPostalCode() {
        return postalCode;
    }

    public void setPostalCode(String postalCode) {
        this.postalCode = postalCode;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getPaymentMethod() {
        return paymentMethod;
    }

    public void setPaymentMethod(String paymentMethod) {
        this.paymentMethod = paymentMethod;
    }

    public String getNotes() {
        return notes;
    }

    public void setNotes(String notes) {
        this.notes = notes;
    }
}
