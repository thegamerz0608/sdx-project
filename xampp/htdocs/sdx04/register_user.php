<?php
// register_user.php - Enterprise User Registration Processor
session_start();
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

// Detect if client requested JSON response (AJAX/Fetch)
$isJson = (!empty($_SERVER['HTTP_ACCEPT']) && strpos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false) ||
          (!empty($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest');

function respond_register($success, $message, $redirectUrl = null) {
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
        echo '<link rel="stylesheet" type="text/css" href="style3.css">';
        echo '<div class="message-container">';
        echo '<h1>' . ($success ? 'REGISTRATION SUCCESSFUL' : 'REGISTRATION ERROR') . '</h1>';
        echo '<p class="' . ($success ? 'success' : 'error') . '">' . htmlspecialchars($message, ENT_QUOTES, 'UTF-8') . '</p>';
        if ($redirectUrl) {
            echo '<p>Redirecting...</p>';
            echo '<p>If not redirected, <a href="' . $redirectUrl . '">click here</a>.</p>';
            echo '</div>';
            echo '<meta http-equiv="refresh" content="3; url=' . $redirectUrl . '">';
        } else {
            echo '<p><a href="signup.php">Try again</a></p>';
            echo '</div>';
        }
        exit();
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 1. Verify CSRF Token
    $csrfToken = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    if (!verify_csrf_token($csrfToken)) {
        respond_register(false, "Invalid security token (CSRF). Please refresh and try again.", "signup.php");
    }

    $username         = isset($_POST['username']) ? trim($_POST['username']) : '';
    $email            = isset($_POST['email']) ? trim($_POST['email']) : '';
    $password         = isset($_POST['password']) ? $_POST['password'] : '';
    $confirm_password = isset($_POST['confirm_password']) ? $_POST['confirm_password'] : '';

    if (empty($username) || empty($email) || empty($password) || empty($confirm_password)) {
        respond_register(false, "Please fill in all required fields.", "signup.php");
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        respond_register(false, "Please enter a valid email address.", "signup.php");
    }

    if ($password !== $confirm_password) {
        respond_register(false, "Passwords do not match.", "signup.php");
    }

    if (strlen($password) < 6) {
        respond_register(false, "Password must be at least 6 characters long.", "signup.php");
    }

    try {
        // Check if username or email exists
        $stmt = $pdo->prepare("SELECT id FROM user WHERE username = ? OR email = ?");
        $stmt->execute([$username, $email]);
        
        if ($stmt->rowCount() > 0) {
            respond_register(false, "The username or email is already registered.", "index.php");
        }

        $hashed_password = password_hash($password, PASSWORD_DEFAULT);

        $insertStmt = $pdo->prepare("INSERT INTO user (username, email, password, plain_password) VALUES (?, ?, ?, ?)");
        if ($insertStmt->execute([$username, $email, $hashed_password, $password])) {
            // Auto login user after registration
            $newUserId = $pdo->lastInsertId();
            $_SESSION['user_id']  = $newUserId;
            $_SESSION['username'] = $username;

            respond_register(true, "Registration successful! Welcome, " . $username . "!", "Practise.php");
        } else {
            respond_register(false, "Something went wrong during registration. Please try again.", "signup.php");
        }
    } catch (PDOException $e) {
        respond_register(false, "Registration failed due to a database error.", "signup.php");
    }
} else {
    header("Location: signup.php");
    exit();
}
?>

