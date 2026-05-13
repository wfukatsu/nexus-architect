package com.example.ec.order;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

// [DEBT] DTO 未使用 — Order エンティティをそのまま返している (R8)
@RestController
@RequestMapping("/api/orders")
@Tag(name = "Order", description = "注文 API")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    @Operation(summary = "注文確定")
    public ResponseEntity<Order> placeOrder(
        @RequestBody Map<String, Object> body,
        Authentication authentication
    ) {
        Long userId = Long.valueOf(body.get("userId").toString());
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cartItems = (List<Map<String, Object>>) body.get("items");
        String cardNumber = (String) body.get("cardNumber");

        Order order = orderService.placeOrder(userId, cartItems, cardNumber);
        return ResponseEntity.ok(order);
    }

    // [SECURITY] A01:2021 — IDOR 脆弱性 (R13)
    // ログイン中ユーザーが他ユーザーの注文 ID を指定してアクセスできる
    @GetMapping("/{id}")
    @Operation(summary = "注文詳細取得（IDOR 脆弱性あり）")
    public ResponseEntity<Order> getOrder(@PathVariable Long id, Authentication authentication) {
        // [BUG] authentication から userId を取り出して所有者チェックを行っていない
        return ResponseEntity.ok(orderService.getOrderById(id));
    }

    // [DEBT] N+1 クエリ問題: orders の各 items にアクセスするため N+1 発生 (R7)
    @GetMapping
    @Operation(summary = "自分の注文履歴一覧（N+1 クエリ問題あり）")
    public ResponseEntity<List<Order>> myOrders(@RequestParam Long userId) {
        // [DEBT] authentication から取得せず、リクエストパラメータから userId を受け取る（認可不備）
        return ResponseEntity.ok(orderService.getOrdersByUser(userId));
    }
}
