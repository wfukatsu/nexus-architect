package com.example.ec.catalog;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

// [DEBT] DTO 未使用 — Product エンティティをそのまま返している (R8)
@RestController
@RequestMapping("/api/products")
@Tag(name = "Catalog", description = "商品カタログ API")
public class ProductController {

    private final ProductService productService;

    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    @Operation(summary = "商品一覧取得")
    public ResponseEntity<List<Product>> list() {
        return ResponseEntity.ok(productService.getAllProducts());
    }

    @GetMapping("/{id}")
    @Operation(summary = "商品詳細取得")
    public ResponseEntity<Product> get(@PathVariable Long id) {
        return ResponseEntity.ok(productService.getProduct(id));
    }

    // [SECURITY] keyword パラメータが SQL インジェクションに対して脆弱 (R12)
    @GetMapping("/search")
    @Operation(summary = "商品検索（キーワード）")
    public ResponseEntity<List<Product>> search(@RequestParam String keyword) {
        return ResponseEntity.ok(productService.searchProducts(keyword));
    }

    @PostMapping
    @Operation(summary = "商品登録（管理者用）")
    public ResponseEntity<Product> create(@RequestBody Map<String, Object> body) {
        Product p = productService.createProduct(
            (String) body.get("name"),
            (String) body.get("description"),
            new BigDecimal(body.get("price").toString()),
            (String) body.get("category")
        );
        return ResponseEntity.ok(p);
    }
}
