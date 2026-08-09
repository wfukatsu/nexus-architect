package com.example.orders;

/**
 * The authenticated caller. Both fields come from verified token claims only — never from a request
 * body, query parameter, or unverified header (rules/api-security-checks.md, tenant isolation).
 */
public record Caller(String subject, String tenantId) {
}
