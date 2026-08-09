package com.example.orders;

/** Thrown when the original request for this Idempotency-Key is still running. */
public class IdempotencyKeyInFlightException extends RuntimeException {
    public IdempotencyKeyInFlightException(String message) {
        super(message);
    }
}
