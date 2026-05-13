package com.example.ec.catalog;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.util.List;

@Service
public class ProductService {

    private final ProductRepository productRepository;

    @PersistenceContext
    private EntityManager entityManager;

    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<Product> getAllProducts() {
        return productRepository.findByActiveTrue();
    }

    public Product getProduct(Long id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Product not found: " + id));
    }

    // [SECURITY] A03:2021 — SQL インジェクション脆弱性 (R12)
    // keyword パラメータをそのまま SQL 文字列に結合している
    // 例: keyword = "' OR '1'='1" → 全件返却
    @SuppressWarnings("unchecked")
    public List<Product> searchProducts(String keyword) {
        String sql = "SELECT * FROM products WHERE active = 1 AND (" +
                     "name LIKE '%" + keyword + "%' OR " +
                     "description LIKE '%" + keyword + "%' OR " +
                     "category LIKE '%" + keyword + "%')";
        return entityManager.createNativeQuery(sql, Product.class).getResultList();
    }

    public Product createProduct(String name, String description, BigDecimal price, String category) {
        Product p = new Product();
        p.setName(name);
        p.setDescription(description);
        p.setPrice(price);
        p.setCategory(category);
        return productRepository.save(p);
    }

    public List<Product> getByCategory(String category) {
        return productRepository.findByCategory(category);
    }
}
