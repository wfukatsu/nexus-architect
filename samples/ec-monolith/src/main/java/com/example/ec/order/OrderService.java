package com.example.ec.order;

import com.example.ec.catalog.Product;
import com.example.ec.catalog.ProductRepository;
import com.example.ec.config.AppConstants;
import com.example.ec.inventory.Inventory;
import com.example.ec.inventory.InventoryRepository;
import com.example.ec.inventory.InventoryService;
import com.example.ec.payment.Payment;
import com.example.ec.payment.PaymentGateway;
import com.example.ec.payment.PaymentRepository;
import com.example.ec.user.User;
import com.example.ec.user.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

// [DEBT] God Service — 注文・在庫・決済・ポイント・メール通知・ログを単一クラスで処理 (R6)
// [DEBT] 他ドメイン（inventory, catalog, payment, user）への直接依存 (R9)
// [DEBT] 500行超のメソッドチェーン
@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    // [DEBT] 5つのリポジトリを直接注入 — Service 間の協調が OrderService に集中している
    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository; // [DEBT] inventory パッケージへの直接依存 (R9)
    private final InventoryService inventoryService;
    private final PaymentRepository paymentRepository;    // [DEBT] payment パッケージへの直接依存 (R9)
    private final PaymentGateway paymentGateway;

    public OrderService(
        OrderRepository orderRepository,
        UserRepository userRepository,
        ProductRepository productRepository,
        InventoryRepository inventoryRepository,
        InventoryService inventoryService,
        PaymentRepository paymentRepository,
        PaymentGateway paymentGateway
    ) {
        this.orderRepository = orderRepository;
        this.userRepository = userRepository;
        this.productRepository = productRepository;
        this.inventoryRepository = inventoryRepository;
        this.inventoryService = inventoryService;
        this.paymentRepository = paymentRepository;
        this.paymentGateway = paymentGateway;
    }

    // [DEBT] God Method — 在庫確認・在庫引き当て・注文作成・決済・ポイント付与・メール送信を
    //        単一メソッドで実施。責務の分離が全くされていない (R6)
    @Transactional
    public Order placeOrder(Long userId, List<Map<String, Object>> cartItems, String cardNumber) {

        log.info("=== placeOrder started: userId={} ===", userId);

        // Step 1: ユーザー取得
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new RuntimeException("User not found: " + userId));
        log.debug("User found: {}", user.getEmail());

        // Step 2: カート内商品の検証と金額計算
        List<OrderItem> orderItems = new ArrayList<>();
        BigDecimal totalAmount = BigDecimal.ZERO;

        for (Map<String, Object> cartItem : cartItems) {
            Long productId = Long.valueOf(cartItem.get("productId").toString());
            int quantity = Integer.parseInt(cartItem.get("quantity").toString());

            // [DEBT] InventoryRepository を OrderService から直接呼び出している (R9)
            Inventory inventory = inventoryRepository.findByProductId(productId)
                .orElseThrow(() -> new RuntimeException("Inventory not found: " + productId));

            if (inventory.getAvailable() < quantity) {
                log.warn("Insufficient stock: productId={}, available={}, requested={}",
                    productId, inventory.getAvailable(), quantity);
                throw new RuntimeException("Insufficient stock for product: " + productId);
            }

            Product product = productRepository.findById(productId)
                .orElseThrow(() -> new RuntimeException("Product not found: " + productId));

            OrderItem item = new OrderItem();
            item.setProductId(productId);
            item.setProductName(product.getName());
            item.setQuantity(quantity);
            item.setUnitPrice(product.getPrice());
            orderItems.add(item);

            totalAmount = totalAmount.add(product.getPrice().multiply(BigDecimal.valueOf(quantity)));
        }

        // Step 3: 在庫引き当て（InventoryService 経由）
        for (Map<String, Object> cartItem : cartItems) {
            Long productId = Long.valueOf(cartItem.get("productId").toString());
            int quantity = Integer.parseInt(cartItem.get("quantity").toString());
            inventoryService.reserve(productId, quantity);
            log.debug("Reserved {} units of product {}", quantity, productId);
        }

        // Step 4: 注文レコード作成
        Order order = new Order();
        order.setUser(user);
        order.setStatus(Order.OrderStatus.PENDING);
        order.setTotalAmount(totalAmount);
        order.setCreatedAt(LocalDateTime.now());
        order.setUpdatedAt(LocalDateTime.now());
        order = orderRepository.save(order);

        for (OrderItem item : orderItems) {
            item.setOrder(order);
        }
        order.setItems(orderItems);
        order = orderRepository.save(order);

        log.info("Order created: orderId={}, totalAmount={}", order.getId(), totalAmount);

        // Step 5: 決済処理
        // [SECURITY] A09:2021 — カード番号末尾とユーザーIDと金額をログに出力 (R15)
        String cardLast4 = cardNumber != null && cardNumber.length() >= 4
            ? cardNumber.substring(cardNumber.length() - 4) : "****";
        log.info("Processing payment: userId={}, orderId={}, amount={}, cardLast4={}",
            userId, order.getId(), totalAmount, cardLast4);

        boolean paymentSuccess = paymentGateway.charge(
            cardNumber,
            totalAmount,
            AppConstants.PAYMENT_API_KEY  // [DEBT] ハードコードされた API キー使用 (R10)
        );

        if (!paymentSuccess) {
            // [DEBT] 決済失敗時の在庫ロールバックが不完全 — release() を呼ばずに例外だけスロー
            log.error("Payment failed for orderId={}", order.getId());
            order.setStatus(Order.OrderStatus.CANCELLED);
            orderRepository.save(order);
            throw new RuntimeException("Payment failed for order: " + order.getId());
        }

        // Step 6: Payment レコード保存
        Payment payment = new Payment();
        payment.setOrderId(order.getId());
        payment.setAmount(totalAmount);
        payment.setStatus(Payment.PaymentStatus.SUCCESS);
        payment.setCardLastFour(cardLast4);
        payment.setCreatedAt(LocalDateTime.now());
        paymentRepository.save(payment);

        // Step 7: 注文確定・在庫確定
        order.setStatus(Order.OrderStatus.CONFIRMED);
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);

        for (Map<String, Object> cartItem : cartItems) {
            Long productId = Long.valueOf(cartItem.get("productId").toString());
            int quantity = Integer.parseInt(cartItem.get("quantity").toString());
            inventoryService.confirm(productId, quantity);
        }

        // Step 8: ポイント付与（[DEBT] OrderService の責務ではない）
        int pointsEarned = totalAmount.intValue() / 100;
        log.info("Points earned for userId={}: {} points (orderId={})", userId, pointsEarned, order.getId());
        // TODO: ポイントサービスがないため直接 DB 更新はせず、ログのみ

        // Step 9: メール通知（[DEBT] OrderService が直接メール送信ロジックを持つ）
        sendOrderConfirmationEmail(user, order);

        // Step 10: 管理者への通知
        notifyAdmin(order, user);

        log.info("=== placeOrder completed: orderId={} ===", order.getId());
        return order;
    }

    // [DEBT] N+1 クエリ問題 — findByUserId は Order を取得するが、
    //        各 Order の items にアクセスすると追加クエリが発生する (R7)
    public List<Order> getOrdersByUser(Long userId) {
        List<Order> orders = orderRepository.findByUserId(userId);
        // items を参照することで N+1 が発生
        orders.forEach(o -> log.debug("Order {} has {} items", o.getId(), o.getItems().size()));
        return orders;
    }

    public Order getOrderById(Long id) {
        return orderRepository.findById(id)
            .orElseThrow(() -> new RuntimeException("Order not found: " + id));
    }

    // [DEBT] メール送信ロジックが OrderService に埋め込まれている（責務違反）
    private void sendOrderConfirmationEmail(User user, Order order) {
        // 実際のSMTP送信はせずログのみ（AppConstants のハードコード認証情報を参照）
        log.info("Sending order confirmation email to {} via {}:{} (auth: {})",
            user.getEmail(),
            AppConstants.SMTP_HOST,
            AppConstants.SMTP_PORT,
            AppConstants.SMTP_USER);
        log.debug("Email sent for orderId={}, userId={}", order.getId(), user.getId());
    }

    // [DEBT] 管理者通知ロジックも OrderService に埋め込まれている
    private void notifyAdmin(Order order, User user) {
        log.info("Admin notification: new order {} from {} (amount: {})",
            order.getId(), user.getEmail(), order.getTotalAmount());
        // 実際には AppConstants.ADMIN_EMAIL に通知すべき
    }
}
