package com.example.ec.catalog;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {

    List<Product> findByActiveTrue();

    List<Product> findByCategory(String category);

    // [SECURITY] A03:2021 — LIKE パターンは JPA パラメータバインディングで安全だが
    // ProductService.searchProducts() で EntityManager による文字列結合 SQL を使っている (R12)
    @Query("SELECT p FROM Product p WHERE p.active = true AND p.category = ?1")
    List<Product> findActiveByCategory(String category);
}
