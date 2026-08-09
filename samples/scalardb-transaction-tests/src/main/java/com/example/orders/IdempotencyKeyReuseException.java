package com.example.orders;

/** Thrown when the same Idempotency-Key arrived with a different request body. */
public class IdempotencyKeyReuseException extends RuntimeException {
    public IdempotencyKeyReuseException(String message) {
        super(message);
    }
}
