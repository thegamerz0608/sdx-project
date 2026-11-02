<?php
// forgot_password.php - Real Password Reset Link Request & Email Dispatcher
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

$message = '';
$error = '';
$resetUrl = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $csrfToken = isset($_POST['csrf_token']) ? $_POST['csrf_token'] : '';
    if (!verify_csrf_token($csrfToken)) {
        $error = "Invalid security token (CSRF). Please refresh and try again.";
    } else {
        $email = isset($_POST['email']) ? trim($_POST['email']) : '';
        if (empty($email) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $error = "Please enter a valid registered email address.";
        } else {
            try {
                $stmt = $pdo->prepare("SELECT id, email, username FROM user WHERE email = ?");
                $stmt->execute([$email]);
                $user = $stmt->fetch();

                if ($user) {
                    $token = bin2hex(random_bytes(32));
                    $expires_at = date('Y-m-d H:i:s', time() + 86400); // 24 hours valid

                    // Purge previous unused reset requests for this email
                    $delStmt = $pdo->prepare("DELETE FROM password_resets WHERE email = ?");
                    $delStmt->execute([$email]);

                    $tokenStmt = $pdo->prepare("INSERT INTO password_resets (email, token, expires_at) VALUES (?, ?, ?)");
                    $tokenStmt->execute([$email, $token, $expires_at]);

                    // Construct real absolute reset URL
                    $protocol = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? "https" : "http");
                    $domain = $_SERVER['HTTP_HOST'];
                    $scriptDir = rtrim(dirname($_SERVER['PHP_SELF']), '/\\');
                    $resetUrl = "$protocol://$domain$scriptDir/reset_password.php?token=" . $token;

                    // Send HTML Email via PHP mail()
                    $subject = "Pro Controller Gaming - Password Reset Request";
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
                        <div style='max-width: 600px; margin: 0 auto; background: #121622; border: 1px solid #00ffff; padding: 30px; border-radius: 16px; box-shadow: 0 0 25px rgba(0, 255, 255, 0.4);'>
                            <h2 style='color: #00ffff; margin-top: 0;'>PRO CONTROLLER GAMING</h2>
                            <p style='font-size: 16px;'>Hello <strong style='color: #00ffff;'>" . htmlspecialchars($user['username']) . "</strong>,</p>
                            <p>We received a request to reset your password for account <strong>" . htmlspecialchars($email) . "</strong>.</p>
                            <p style='margin: 25px 0;'>
                                <a href='" . $resetUrl . "' style='background: linear-gradient(135deg, #00ffff, #0088cc); color: #000000; padding: 14px 28px; font-weight: bold; border-radius: 25px; text-decoration: none; display: inline-block; box-shadow: 0 0 15px #00ffff;'>RESET MY PASSWORD NOW</a>
                            </p>
                            <p style='font-size: 13px; color: #aaaaaa;'>Or copy and paste this link into your browser:<br><a href='" . $resetUrl . "' style='color: #00ffff; word-break: break-all;'>" . $resetUrl . "</a></p>
                            <p style='font-size: 12px; color: #777777; margin-top: 20px; border-top: 1px solid #222; padding-top: 10px;'>This link is valid for 1 hour. If you did not request a password reset, please ignore this email.</p>
                        </div>
                    </body>
                    </html>";

                    $mailSent = @mail($email, $subject, $emailBody, $headers);

                    $message = 'A password recovery email has been sent to <strong style="color:#00ffff;">' . htmlspecialchars($email, ENT_QUOTES, 'UTF-8') . '</strong>.<br>Please check your mail inbox or spam folder to reset your password.';

                    // Audit Log
                    $ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '127.0.0.1';
                    $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, ?, ?)");
                    $auditStmt->execute([$user['id'], 'password_reset_requested: ' . $email, $ip]);

                } else {
                    $error = "No registered account found with email: " . htmlspecialchars($email);
                }
            } catch (PDOException $e) {
                $error = "Unable to process password reset request. Error: " . $e->getMessage();
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
    <title>Forgot Password - Pro Controller Gaming</title>
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
    <form action="forgot_password.php" method="post" class="form" aria-label="Forgot Password Form">
        <h1>FORGOT PASSWORD</h1>
        <?php echo csrf_input(); ?>

        <?php if (!empty($message)): ?>
            <div class="toast-notification success" style="display:block; margin-bottom:15px; background: rgba(0, 255, 255, 0.15); border-color: #00ffff;">
                <p style="color: #fff; line-height: 1.6;"><?php echo $message; ?></p>
            </div>
        <?php endif; ?>

        <?php if (!empty($error)): ?>
            <div class="toast-notification error" style="display:block; margin-bottom:15px;">
                <p><?php echo htmlspecialchars($error); ?></p>
            </div>
        <?php endif; ?>

        <?php if (empty($message)): ?>
            <input type="email" name="email" class="box" placeholder="Enter your registered email" autocomplete="email" required>
            <input type="submit" value="SEND PASSWORD RESET LINK" id="submit">
        <?php endif; ?>

        <div class="register-link" style="margin-top: 20px;">
            <p>Remember your password? <a href="index.php">Back to Login</a></p>
        </div>
    </form>
</body>
</html>