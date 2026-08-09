package com.example.orders;

/** Thrown when the order is not in a state this operation allows. */
public class IllegalOrderStateException extends RuntimeException {
    public IllegalOrderStateException(String message) {
        super(message);
    }
}
