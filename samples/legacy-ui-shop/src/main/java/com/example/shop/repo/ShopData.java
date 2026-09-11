package com.example.shop.repo;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import com.example.shop.model.CartLine;
import com.example.shop.model.Order;
import com.example.shop.model.OrderForm;
import com.example.shop.model.Product;
import com.example.shop.model.User;

/**
 * In-memory store standing in for the database. Everything is lost on restart.
 */
public final class ShopData {

    private static final ShopData INSTANCE = new ShopData();

    private static final List<String> CATEGORIES = List.of("文房具", "事務用品", "オフィス家具");

    private final Map<String, Product> products = new LinkedHashMap<>();
    private final Map<String, User> users = new LinkedHashMap<>();
    private final List<Order> orders = new ArrayList<>();
    private int productSeq;
    private int orderSeq;

    private ShopData() {
        addProduct("P001", "ボールペン 黒 10本入", "文房具", 880, 120);
        addProduct("P002", "ノート A4 5冊パック", "文房具", 1100, 80);
        addProduct("P003", "蛍光マーカー 5色セット", "文房具", 650, 64);
        addProduct("P004", "クリアファイル A4 100枚", "事務用品", 2480, 40);
        addProduct("P005", "コピー用紙 A4 2500枚", "事務用品", 3980, 25);
        addProduct("P006", "ホッチキス 中型", "事務用品", 1320, 30);
        addProduct("P007", "シュレッダー 小型", "事務用品", 8800, 6);
        addProduct("P008", "オフィスチェア メッシュ", "オフィス家具", 19800, 8);
        addProduct("P009", "ワークデスク 幅120cm", "オフィス家具", 24800, 4);
        addProduct("P010", "書類キャビネット 3段", "オフィス家具", 15400, 5);
        addProduct("P011", "デスクライト LED", "オフィス家具", 4980, 12);
        addProduct("P012", "付箋 75mm角 20冊", "文房具", 1540, 0);
        productSeq = products.size();

        users.put("customer1", new User("customer1", "pass1", "山田 太郎",
                "taro.yamada@example.co.jp", "customer", true));
        users.put("admin1", new User("admin1", "pass1", "佐藤 花子",
                "hanako.sato@example.co.jp", "admin", false));
    }

    public static ShopData get() {
        return INSTANCE;
    }

    private void addProduct(String id, String name, String category, int price, int stock) {
        products.put(id, new Product(id, name, category, price, stock, imageFor(category)));
    }

    private static String imageFor(String category) {
        if ("文房具".equals(category)) {
            return "stationery.svg";
        }
        if ("事務用品".equals(category)) {
            return "office.svg";
        }
        return "furniture.svg";
    }

    public synchronized User authenticate(String userId, String password) {
        User user = users.get(userId);
        if (user == null || !user.passwordMatches(password)) {
            return null;
        }
        return user;
    }

    public List<String> categories() {
        return CATEGORIES;
    }

    public synchronized List<Product> searchProducts(String keyword, String category) {
        List<Product> result = new ArrayList<>();
        for (Product p : products.values()) {
            if (keyword != null && !keyword.isBlank() && !p.getName().contains(keyword.trim())) {
                continue;
            }
            if (category != null && !category.isBlank() && !category.equals(p.getCategory())) {
                continue;
            }
            result.add(p.copy());
        }
        return result;
    }

    public synchronized Product findProduct(String id) {
        Product p = products.get(id);
        return p == null ? null : p.copy();
    }

    public synchronized void saveProduct(Product product) {
        if (product.getId() == null || product.getId().isBlank()) {
            productSeq++;
            product.setId(String.format("P%03d", productSeq));
        }
        product.setImage(imageFor(product.getCategory()));
        products.put(product.getId(), product.copy());
    }

    public synchronized void deleteProduct(String id) {
        products.remove(id);
    }

    public synchronized Order placeOrder(String userId, List<CartLine> lines, OrderForm form,
                                         int subtotal, int discount, int tax, int total) {
        orderSeq++;
        LocalDateTime now = LocalDateTime.now();
        String orderNo = "ORD" + now.format(DateTimeFormatter.BASIC_ISO_DATE)
                + "-" + String.format("%04d", orderSeq);
        Order order = new Order(orderNo, userId, lines, form, subtotal, discount, tax, total, now);
        orders.add(order);
        return order;
    }
}
