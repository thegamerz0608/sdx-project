<?php
// security.php - Enterprise Security, CSRF Protection & Rate Limiting Utility

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// 1. Set Enterprise Security Headers
header("X-Frame-Options: SAMEORIGIN");
header("X-Content-Type-Options: nosniff");
header("X-XSS-Protection: 1; mode=block");
header("Referrer-Policy: strict-origin-when-cross-origin");

// 2. CSRF Token Functions
function generate_csrf_token() {
    if (empty($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

function verify_csrf_token($token) {
    if (isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token)) {
        return true;
    }
    return false;
}

function csrf_input() {
    $token = generate_csrf_token();
    return '<input type="hidden" name="csrf_token" value="' . htmlspecialchars($token, ENT_QUOTES, 'UTF-8') . '">';
}

// 3. Brute Force Login Rate Limiting Functions
function is_ip_rate_limited($pdo, $ip_address, $max_attempts = 5, $lockout_minutes = 15) {
    try {
        $stmt = $pdo->prepare("SELECT COUNT(*) FROM login_attempts WHERE ip_address = ? AND attempted_at > NOW() - INTERVAL ? MINUTE");
        $stmt->execute([$ip_address, $lockout_minutes]);
        $attempts = $stmt->fetchColumn();
        return $attempts >= $max_attempts;
    } catch (PDOException $e) {
        return false;
    }
}

function record_login_attempt($pdo, $ip_address, $username = '') {
    try {
        $stmt = $pdo->prepare("INSERT INTO login_attempts (ip_address, username) VALUES (?, ?)");
        $stmt->execute([$ip_address, $username]);
    } catch (PDOException $e) {
        // Silently handle if table missing
    }
}

function record_failed_attempt($pdo, $ip_address, $username = '') {
    record_login_attempt($pdo, $ip_address, $username);
}

function clear_login_attempts($pdo, $ip_address) {
    try {
        $stmt = $pdo->prepare("DELETE FROM login_attempts WHERE ip_address = ?");
        $stmt->execute([$ip_address]);
    } catch (PDOException $e) {
        // Silently handle
    }
}
?>
