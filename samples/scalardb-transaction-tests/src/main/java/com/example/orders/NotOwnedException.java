package com.example.orders;

/** Thrown when the order exists but belongs to someone else; rendered identically to not-found. */
public class NotOwnedException extends RuntimeException {
    public NotOwnedException(String message) {
        super(message);
    }
}
