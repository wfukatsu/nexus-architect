package com.example.shop.model;

import java.io.Serializable;

public class User implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String id;
    private final String password;
    private final String name;
    private final String email;
    /** "customer" or "admin". */
    private final String role;
    /** Premium member flag (members get the volume discount). */
    private final boolean member;

    public User(String id, String password, String name, String email, String role, boolean member) {
        this.id = id;
        this.password = password;
        this.name = name;
        this.email = email;
        this.role = role;
        this.member = member;
    }

    public String getId() {
        return id;
    }

    public boolean passwordMatches(String candidate) {
        return password.equals(candidate);
    }

    public String getName() {
        return name;
    }

    public String getEmail() {
        return email;
    }

    public String getRole() {
        return role;
    }

    public boolean isMember() {
        return member;
    }
}
