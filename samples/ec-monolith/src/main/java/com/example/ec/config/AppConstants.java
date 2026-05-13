package com.example.ec.config;

// [DEBT] ハードコードされた設定値 — 環境変数や設定ファイルに外出しすべき (R10)
public class AppConstants {

    // DB backup credentials (hardcoded)
    public static final String BACKUP_DB_URL = "jdbc:mysql://backup-db.internal:3306/ecdb";
    public static final String BACKUP_DB_USER = "backup_user";
    public static final String BACKUP_DB_PASSWORD = "B@ckup#2024!";

    // Admin account
    public static final String ADMIN_DEFAULT_PASSWORD = "admin1234";
    public static final String ADMIN_EMAIL = "admin@example-ec.com";

    // SMTP credentials
    public static final String SMTP_HOST = "smtp.gmail.com";
    public static final String SMTP_PORT = "587";
    public static final String SMTP_USER = "noreply@example-ec.com";
    public static final String SMTP_PASSWORD = "Smtp#Pass2024";

    // Payment gateway
    public static final String PAYMENT_API_KEY = "pk_live_51abc123xyz";
    public static final String PAYMENT_SECRET = "sk_live_secret_key_hardcoded";
}
