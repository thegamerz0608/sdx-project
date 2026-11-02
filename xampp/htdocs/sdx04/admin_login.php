<?php
// admin_login.php - Dedicated Administrator Security Portal
session_start();
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

$message = '';
$error = '';

// If already logged in as admin, redirect directly to admin.php
if (isset($_SESSION['is_admin']) && $_SESSION['is_admin'] === true) {
    header("Location: admin.php");
    exit();
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $csrfToken = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    if (!verify_csrf_token($csrfToken)) {
        $error = "Invalid security token (CSRF). Please refresh and try again.";
    } else {
        $username = isset($_POST["username"]) ? trim($_POST["username"]) : '';
        $password = isset($_POST["password"]) ? $_POST["password"] : '';
        $ipAddress = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1';

        if (is_ip_rate_limited($pdo, $ipAddress, 5, 15)) {
            $error = "SECURITY ALERT: Too many failed admin attempts. Please wait 15 minutes before trying again.";
        } elseif (empty($username) || empty($password)) {
            $error = "Please enter both admin username and password.";
        } else {
            try {
                // Fetch user record
                $stmt = $pdo->prepare("SELECT id, username, email, password, role FROM user WHERE username = ? OR email = ?");
                $stmt->execute([$username, $username]);
                $user = $stmt->fetch();

                if ($user && password_verify($password, $user['password'])) {
                    // Check if role is admin
                    if ($user['role'] === 'admin') {
                        clear_login_attempts($pdo, $ipAddress);
                        session_regenerate_id(true);

                        $_SESSION['admin_user_id']  = $user['id'];
                        $_SESSION['admin_username'] = $user['username'];
                        $_SESSION['is_admin']       = true;
                        $_SESSION['user_id']        = $user['id'];
                        $_SESSION['username']       = $user['username'];
                        $_SESSION['role']           = 'admin';

                        // Audit Log
                        $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, 'admin_login_success', ?)");
                        $auditStmt->execute([$user['id'], $ipAddress]);

                        header("Location: admin.php");
                        exit();
                    } else {
                        $error = "ACCESS DENIED: Account does not have Administrator privileges.";
                        
                        // Audit Log
                        $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, 'admin_access_denied_regular_user', ?)");
                        $auditStmt->execute([$user['id'], $ipAddress]);
                    }
                } else {
                    record_failed_attempt($pdo, $ipAddress, $username);
                    $error = "Invalid Administrator credentials.";
                    
                    // Audit Log
                    $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (NULL, 'admin_login_failed', ?)");
                    $auditStmt->execute([$ipAddress]);
                }
            } catch (PDOException $e) {
                $error = "System database error during authentication.";
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Administrator Security Portal - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        body {
            background-color: #050608;
            background-image: radial-gradient(circle at 50% 50%, rgba(255, 0, 128, 0.2) 0%, transparent 70%), url('cyberpunk_night_city.jpg');
            background-size: cover;
            background-position: center;
            font-family: 'Inter', sans-serif;
        }
        .form {
            border-color: rgba(255, 0, 128, 0.5);
            box-shadow: 0 0 35px rgba(255, 0, 128, 0.4);
        }
        .form h1 {
            color: #ff0080;
            text-shadow: 0 0 15px #ff0080;
            border-bottom-color: rgba(255, 0, 128, 0.4);
        }
        .box:focus {
            border-color: #ff0080;
            box-shadow: 0 0 12px rgba(255, 0, 128, 0.6);
        }
        #submit {
            background: linear-gradient(135deg, #ff0080, #7928ca);
            box-shadow: 0 4px 15px rgba(255, 0, 128, 0.4);
        }
        #submit:hover {
            background: linear-gradient(135deg, #ff0080, #ff4d4d);
            box-shadow: 0 0 25px rgba(255, 0, 128, 0.8);
        }
    </style>
</head>
<body>
    <form action="admin_login.php" method="post" class="form">
        <h1>🛡️ ADMIN PORTAL</h1>
        <?php echo csrf_input(); ?>

        <?php if (!empty($error)): ?>
            <div class="toast-notification error" style="display:block; margin-bottom:15px; background:rgba(255,0,128,0.2); border-color:#ff0080; color:#ff0080;">
                <p><?php echo htmlspecialchars($error); ?></p>
            </div>
        <?php endif; ?>

        <input type="text" name="username" class="box" placeholder="Admin Username or Email" autocomplete="username" required>
        
        <div class="password-wrapper">
            <input type="password" name="password" id="adminPassword" class="box" placeholder="Admin Password" autocomplete="current-password" required>
            <button type="button" class="toggle-password" style="color:#ff0080;" onclick="toggleVisibility('adminPassword', this)">👁️</button>
        </div>

        <input type="submit" value="AUTHENTICATE ADMIN" id="submit">

        <div style="margin-top: 20px; text-align: center; font-size: 0.85rem; color: #888;">
            <p><a href="index.php" style="color: #aaa; text-decoration: none;">← Go to Gamer User Login</a></p>
        </div>
    </form>

    <script>
        function toggleVisibility(inputId, btn) {
            var input = document.getElementById(inputId);
            if (input.type === "password") {
                input.type = "text";
                btn.textContent = "🙈";
            } else {
                input.type = "password";
                btn.textContent = "👁️";
            }
        }
    </script>
</body>
</html>
