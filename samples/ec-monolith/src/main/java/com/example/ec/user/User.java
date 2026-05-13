package com.example.ec.user;

import jakarta.persistence.*;
import java.time.LocalDateTime;

// [DEBT] 貧血ドメインモデル — ビジネスロジックが一切なく、ゲッター/セッターのみ (R11)
// [DEBT] パスワードが JSON レスポンスに含まれる可能性がある (@JsonIgnore 未使用) (R8)
@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String email;

    // [SECURITY] パスワードハッシュが外部に漏れるリスク — @JsonIgnore を付けていない
    @Column(nullable = false)
    private String passwordHash;

    @Column(nullable = false)
    private String name;

    @Enumerated(EnumType.STRING)
    private Role role;

    private LocalDateTime createdAt;

    public enum Role { CUSTOMER, ADMIN }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public Role getRole() { return role; }
    public void setRole(Role role) { this.role = role; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
