package com.example.ec.user;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

// [DEBT] DTO を使わず User エンティティをそのまま返している (R8)
@RestController
@RequestMapping("/api")
@Tag(name = "User", description = "ユーザー管理 API")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/auth/register")
    @Operation(summary = "ユーザー登録")
    public ResponseEntity<User> register(@RequestBody Map<String, String> body) {
        User user = userService.register(
            body.get("email"),
            body.get("password"),
            body.get("name")
        );
        // [DEBT] passwordHash を含む User エンティティをそのまま返している
        return ResponseEntity.ok(user);
    }

    @GetMapping("/users/{id}")
    @Operation(summary = "ユーザー取得")
    public ResponseEntity<User> getUser(@PathVariable Long id) {
        // [DEBT] 認可チェックなし — 他ユーザーの情報も取得できる
        return ResponseEntity.ok(userService.findById(id));
    }

    // [SECURITY] 管理者エンドポイント — SecurityConfig のバグで未認証アクセス可 (R16)
    @GetMapping("/admin/users")
    @Operation(summary = "全ユーザー一覧（管理者用）")
    public ResponseEntity<String> adminListUsers() {
        return ResponseEntity.ok("Admin endpoint — should require ROLE_ADMIN but is publicly accessible");
    }
}
