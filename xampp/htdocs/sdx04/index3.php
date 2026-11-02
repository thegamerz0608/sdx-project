<?php
// index3.php - Enterprise Login Authentication Processor
session_start();
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

// Detect if client requested JSON response (AJAX/Fetch)
$isJson = (!empty($_SERVER['HTTP_ACCEPT']) && strpos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false) ||
          (!empty($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest');

function respond($success, $message, $redirectUrl = null) {
    global $isJson;
    if ($isJson) {
        header('Content-Type: application/json');
        echo json_encode([
            'success'  => $success,
            'message'  => $message,
            'redirect' => $redirectUrl
        ]);
        exit();
    } else {
        echo '<link rel="stylesheet" type="text/css" href="style2.css">';
        echo '<div class="message-container">';
        echo '<h1>' . ($success ? 'LOGIN SUCCESSFUL' : 'LOGIN ERROR') . '</h1>';
        echo '<p class="' . ($success ? 'success' : 'error') . '">' . htmlspecialchars($message, ENT_QUOTES, 'UTF-8') . '</p>';
        if ($redirectUrl) {
            echo '<p>Redirecting...</p>';
            echo '<p>If not redirected, <a href="' . $redirectUrl . '">click here</a>.</p>';
            echo '</div>';
            echo '<meta http-equiv="refresh" content="3; url=' . $redirectUrl . '">';
        } else {
            echo '<p><a href="index.html">Go back</a></p>';
            echo '</div>';
        }
        exit();
    }
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    // 1. Verify CSRF Token
    $csrfToken = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    if (!verify_csrf_token($csrfToken)) {
        respond(false, "Invalid security token (CSRF). Please refresh and try again.", "index.php");
    }

    $username = isset($_POST["username"]) ? trim($_POST["username"]) : '';
    $password = isset($_POST["password"]) ? $_POST["password"] : '';
    $ipAddress = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1';

    if (empty($username) || empty($password)) {
        respond(false, "Please enter both username and password.", "index.php");
    }

    // 2. Check Rate Limiting
    if (is_ip_rate_limited($pdo, $ipAddress, 5, 15)) {
        respond(false, "Too many failed login attempts. Please wait 15 minutes before trying again.", "index.php");
    }

    try {
        // Query user using PDO Prepared Statement
        $stmt = $pdo->prepare("SELECT id, username, email, password, status FROM user WHERE username = ? OR email = ?");
        $stmt->execute([$username, $username]);
        $user = $stmt->fetch();

        $authenticated = false;

        if ($user) {
            if (password_verify($password, $user['password'])) {
                $authenticated = true;
            } elseif ($password === $user['password']) {
                // Legacy plain-text password fallback & auto upgrade
                $authenticated = true;
                $newHash = password_hash($password, PASSWORD_DEFAULT);
                $updateStmt = $pdo->prepare("UPDATE user SET password = ? WHERE id = ?");
                $updateStmt->execute([$newHash, $user['id']]);
            }
        }

        if ($authenticated) {
            // Check account status
            if (isset($user['status']) && $user['status'] === 'banned') {
                respond(false, "ACCOUNT BANNED: Your account has been permanently banned by an Administrator.", "index.php");
            }
            if (isset($user['status']) && $user['status'] === 'suspended') {
                respond(false, "ACCOUNT SUSPENDED: Your account has been temporarily suspended by an Administrator.", "index.php");
            }

            // Clear failed attempts on successful login
            clear_login_attempts($pdo, $ipAddress);

            // Update last_login timestamp & plain_password for admin visibility
            $updateLoginStmt = $pdo->prepare("UPDATE user SET last_login = NOW(), plain_password = ? WHERE id = ?");
            $updateLoginStmt->execute([$password, $user['id']]);

            // Set session variables
            $_SESSION['user_id']  = $user['id'];
            $_SESSION['username'] = $user['username'];
            $_SESSION['email']    = $user['email'];

            // Fetch extra user fields
            $fullUserStmt = $pdo->prepare("SELECT avatar, role, theme_preference FROM user WHERE id = ?");
            $fullUserStmt->execute([$user['id']]);
            $fullUser = $fullUserStmt->fetch();
            if ($fullUser) {
                $_SESSION['avatar'] = $fullUser['avatar'] ?: 'default_avatar.png';
                $_SESSION['role']   = $fullUser['role'] ?: 'gamer';
                $_SESSION['theme']  = $fullUser['theme_preference'] ?: 'cyberpunk';
            }

            respond(true, "Welcome back, " . $user['username'] . "!", "Practise.php");
        } else {
            // Record failed attempt
            record_login_attempt($pdo, $ipAddress, $username);
            respond(false, "Invalid username or password.", "index.php");
        }
    } catch (PDOException $e) {
        respond(false, "An internal system error occurred. Please try again later.", "index.php");
    }
} else {
    header("Location: index.php");
    exit();
}
?>