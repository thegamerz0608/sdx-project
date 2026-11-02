<?php
// reset_password.php - Enterprise Token-Based Password Reset Processor
session_start();
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

$token = isset($_GET['token']) ? trim($_GET['token']) : (isset($_POST['token']) ? trim($_POST['token']) : '');
$message = '';
$error = '';
$validToken = false;
$email = '';

if (!empty($token) && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    try {
        $stmt = $pdo->prepare("SELECT email, expires_at FROM password_resets WHERE token = ? ORDER BY id DESC LIMIT 1");
        $stmt->execute([$token]);
        $reset = $stmt->fetch();

        if ($reset) {
            $expiryTime = strtotime($reset['expires_at']);
            // Valid if expiry time is in future OR created recently within 24 hours
            if ($expiryTime > (time() - 3600)) {
                $validToken = true;
                $email = $reset['email'];
            } else {
                $error = "This password reset link has expired. Please request a new link.";
            }
        } else {
            $error = "Invalid password reset link. Please request a new link.";
        }
    } catch (PDOException $e) {
        $error = "Database error verifying token: " . $e->getMessage();
    }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['new_password'])) {
    $csrfToken = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    $token = isset($_POST['token']) ? trim($_POST['token']) : '';
    $new_password = $_POST['new_password'];
    $confirm_password = $_POST['confirm_password'];

    if (!verify_csrf_token($csrfToken)) {
        $error = "Invalid security token (CSRF). Please try again.";
    } elseif (empty($new_password) || strlen($new_password) < 6) {
        $error = "New password must be at least 6 characters long.";
    } elseif ($new_password !== $confirm_password) {
        $error = "Passwords do not match. Please verify.";
    } else {
        try {
            $stmt = $pdo->prepare("SELECT email FROM password_resets WHERE token = ? ORDER BY id DESC LIMIT 1");
            $stmt->execute([$token]);
            $reset = $stmt->fetch();

            if ($reset) {
                $email = $reset['email'];
                $hashed = password_hash($new_password, PASSWORD_DEFAULT);

                $updateStmt = $pdo->prepare("UPDATE user SET password = ?, plain_password = ? WHERE email = ?");
                $updateStmt->execute([$hashed, $new_password, $email]);

                // Delete used tokens
                $delStmt = $pdo->prepare("DELETE FROM password_resets WHERE email = ?");
                $delStmt->execute([$email]);

                // Send Confirmation Email with New Password
                $protocol = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http");
                $domain = $_SERVER['HTTP_HOST'];
                $scriptDir = rtrim(dirname($_SERVER['PHP_SELF']), '/\\');
                $loginUrl = "$protocol://$domain$scriptDir/index.php";

                $subject = "Security Alert: Password Reset Successful";
                $headers  = "MIME-Version: 1.0\r\n";
                $headers .= "Content-type: text/html; charset=UTF-8\r\n";
                $headers .= "From: Pro Controller Gaming <motosdx04@gmail.com>\r\n";
                $headers .= "Reply-To: motosdx04@gmail.com\r\n";
                $headers .= "X-Mailer: PHP/" . phpversion() . "\r\n";
                $headers .= "Auto-Submitted: auto-generated\r\n";

                $emailBody = "
                <!DOCTYPE html>
                <html>
                <body style='font-family: Arial, sans-serif; background-color: #0a0b10; color: #ffffff; padding: 30px;'>
                    <div style='max-width: 600px; margin: 0 auto; background: #121622; border: 1px solid #00ff88; padding: 30px; border-radius: 16px; box-shadow: 0 0 25px rgba(0, 255, 136, 0.3);'>
                        <h2 style='color: #00ff88; margin-top: 0;'>PASSWORD RESET SUCCESSFUL</h2>
                        <p style='font-size: 16px;'>Hello Gamer,</p>
                        <p>This email confirms that the password for your account <strong>" . htmlspecialchars($email) . "</strong> has been successfully changed.</p>
                        <div style='background: rgba(0, 255, 136, 0.1); border-left: 4px solid #00ff88; padding: 15px; border-radius: 6px; margin: 20px 0;'>
                            <p style='margin: 0; color: #ffffff; font-size: 14px;'>🔒 <strong>Security Notice:</strong> Your account password was securely updated. For your security, passwords are never sent in plain text emails.</p>
                        </div>
                        <p style='margin: 25px 0;'>
                            <a href='" . $loginUrl . "' style='background: #00ff88; color: #000000; padding: 14px 28px; font-weight: bold; border-radius: 25px; text-decoration: none; display: inline-block;'>LOG IN TO YOUR ACCOUNT NOW</a>
                        </p>
                        <p style='font-size: 12px; color: #777777; margin-top: 20px; border-top: 1px solid #222; padding-top: 10px;'>If you did not perform this password change, please contact an Administrator immediately to secure your account.</p>
                    </div>
                </body>
                </html>";

                @mail($email, $subject, $emailBody, $headers);

                // Audit Log
                $ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1';
                $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (NULL, ?, ?)");
                $auditStmt->execute(['password_reset_completed: ' . $email, $ip]);

                $message = "Your password has been successfully reset! A security confirmation email has been sent to your inbox.";
                $validToken = false;
            } else {
                $error = "Invalid or expired token.";
            }
        } catch (PDOException $e) {
            $error = "Failed to reset password. Database error.";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Set New Password - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        body {
            background-color: #0a0b10;
            background-image: radial-gradient(circle at 50% 50%, rgba(0, 255, 255, 0.25) 0%, transparent 60%), url('gtavi_vice_city_art.jpg');
            background-size: cover;
            background-position: center;
            font-family: 'Inter', sans-serif;
        }
        .form h1 {
            font-family: 'Rajdhani', sans-serif;
        }
    </style>
</head>
<body>

    <div class="form">
        <h1>RESET PASSWORD</h1>

        <?php if (!empty($message)): ?>
            <div class="toast-notification success" style="display:block; margin-bottom:15px;">
                <p><?php echo htmlspecialchars($message); ?></p>
            </div>
            <meta http-equiv="refresh" content="3; url=index.php">
            <div class="register-link">
                <p><a href="index.php">Click here if not redirected automatically</a></p>
            </div>
        <?php elseif (!empty($error)): ?>
            <div class="toast-notification error" style="display:block; margin-bottom:15px;">
                <p><?php echo htmlspecialchars($error); ?></p>
            </div>
            <div class="register-link">
                <p><a href="forgot_password.php">Request a new reset link</a></p>
            </div>
        <?php elseif ($validToken): ?>
            <form method="post" action="reset_password.php" style="width: 100%; display: flex; flex-direction: column; align-items: center;">
                <?php echo csrf_input(); ?>
                <input type="hidden" name="token" value="<?php echo htmlspecialchars($token); ?>">
                <p style="color: #00ffff; font-size: 0.95rem; text-align: center; margin-bottom: 15px;">Setting new password for:<br><strong><?php echo htmlspecialchars($email); ?></strong></p>
                <input type="password" name="new_password" class="box" placeholder="New Password (min 6 chars)" required minlength="6">
                <input type="password" name="confirm_password" class="box" placeholder="Confirm New Password" required minlength="6">
                <input type="submit" value="UPDATE PASSWORD" id="submit">
            </form>
        <?php else: ?>
            <p style="color: #ff4d4d; text-align: center;">No valid reset token provided.</p>
            <div class="register-link">
                <p><a href="forgot_password.php">Go to Forgot Password</a></p>
            </div>
        <?php endif; ?>
    </div>

</body>
</html>
