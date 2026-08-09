package com.example.orders;

/** Thrown when the order does not exist, or is not the caller's — the two are indistinguishable by design (existence is confidential). */
public class OrderNotFoundException extends RuntimeException {
    public OrderNotFoundException(String message) {
        super(message);
    }
}
