package com.example.ec.payment;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import java.math.BigDecimal;

// 外部決済ゲートウェイのモック実装
@Component
public class PaymentGateway {

    private static final Logger log = LoggerFactory.getLogger(PaymentGateway.class);

    // [SECURITY] A09:2021 — 決済情報をログに出力 (R15)
    // カード番号全体とAPIキーがデバッグログに含まれる
    public boolean charge(String cardNumber, BigDecimal amount, String apiKey) {
        log.debug("PaymentGateway.charge: card={}, amount={}, apiKey={}",
            cardNumber, amount, apiKey); // [SECURITY] カード番号とAPIキーをログ出力

        if (cardNumber == null || cardNumber.isBlank()) {
            log.warn("Payment declined: no card number provided");
            return false;
        }

        // モック: 4242始まりのカードは成功、それ以外は失敗
        boolean success = cardNumber.startsWith("4242");
        log.info("Payment result: success={}, card_last4={}, amount={}",
            success,
            cardNumber.length() >= 4 ? cardNumber.substring(cardNumber.length() - 4) : "****",
            amount);
        return success;
    }
}
