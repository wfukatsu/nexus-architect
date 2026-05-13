package com.example.ec.config;

import com.example.ec.catalog.Product;
import com.example.ec.catalog.ProductRepository;
import com.example.ec.inventory.Inventory;
import com.example.ec.inventory.InventoryRepository;
import com.example.ec.user.User;
import com.example.ec.user.UserRepository;
import com.example.ec.user.UserService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class DataLoader implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DataLoader.class);

    private final UserService userService;
    private final UserRepository userRepository;
    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository;

    public DataLoader(
        UserService userService,
        UserRepository userRepository,
        ProductRepository productRepository,
        InventoryRepository inventoryRepository
    ) {
        this.userService = userService;
        this.userRepository = userRepository;
        this.productRepository = productRepository;
        this.inventoryRepository = inventoryRepository;
    }

    @Override
    public void run(ApplicationArguments args) {
        log.info("Loading sample data...");

        // ユーザー登録（admin + customers）
        User admin = userService.register("admin@example-ec.com", AppConstants.ADMIN_DEFAULT_PASSWORD, "管理者");
        admin.setRole(User.Role.ADMIN);
        userRepository.save(admin);

        userService.register("alice@example.com", "pass1234", "Alice Tanaka");
        userService.register("bob@example.com", "pass5678", "Bob Yamamoto");
        userService.register("carol@example.com", "pass9012", "Carol Sato");

        // 商品登録（10件）
        String[][] products = {
            {"スマートフォン Pro", "最新フラッグシップモデル", "89800", "Electronics"},
            {"ワイヤレスイヤホン", "ノイズキャンセリング対応", "24800", "Electronics"},
            {"ラップトップ 14inch", "軽量ビジネス向けノートPC", "128000", "Electronics"},
            {"メカニカルキーボード", "青軸 フルサイズ", "12800", "Peripherals"},
            {"4Kモニター 27inch", "HDR対応ゲーミングモニター", "45000", "Peripherals"},
            {"ゲーミングマウス", "高DPI光学センサー", "8980", "Peripherals"},
            {"USBハブ 7ポート", "USB-C対応", "3980", "Accessories"},
            {"モバイルバッテリー", "20000mAh PD対応", "7800", "Accessories"},
            {"スマートウォッチ", "健康モニタリング機能付き", "34800", "Wearables"},
            {"ワイヤレス充電器", "15W急速充電", "4980", "Accessories"},
        };

        for (String[] p : products) {
            Product product = new Product();
            product.setName(p[0]);
            product.setDescription(p[1]);
            product.setPrice(new BigDecimal(p[2]));
            product.setCategory(p[3]);
            product = productRepository.save(product);

            Inventory inventory = new Inventory();
            inventory.setProductId(product.getId());
            inventory.setQuantity(50);
            inventory.setReserved(0);
            inventoryRepository.save(inventory);
        }

        log.info("Sample data loaded: 4 users, {} products", products.length);
    }
}
