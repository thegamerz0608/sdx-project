<?php
// setup_db.php - Standalone Database Initializer
header('Content-Type: text/html; charset=utf-8');
echo '<!DOCTYPE html><html lang="en"><head><title>Database Setup</title>';
echo '<link rel="stylesheet" type="text/css" href="style2.css"></head><body>';
echo '<div class="message-container" style="width:550px;">';

$servername = "localhost";
$username   = "root";
$password   = "";
$dbname     = "feedback_d";

echo '<h1>DATABASE SETUP</h1>';

try {
    // Connect to MySQL server
    $pdo = new PDO("mysql:host=$servername;charset=utf8mb4", $username, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);

    // Create Database
    $pdo->exec("CREATE DATABASE IF NOT EXISTS `$dbname` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;");
    echo '<p class="success">✓ Database <strong>`' . $dbname . '`</strong> is ready.</p>';

    $pdo->exec("USE `$dbname`;");

    // Create Table
    $tableSql = "CREATE TABLE IF NOT EXISTS `user` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `username` VARCHAR(50) NOT NULL UNIQUE,
        `email` VARCHAR(100) NOT NULL UNIQUE,
        `password` VARCHAR(255) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    
    $pdo->exec($tableSql);
    echo '<p class="success">✓ Table <strong>`user`</strong> is ready.</p>';

    // Check if test user exists
    $stmt = $pdo->prepare("SELECT id FROM user WHERE username = ?");
    $stmt->execute(['admin']);
    if ($stmt->rowCount() == 0) {
        $testPassword = password_hash('admin123', PASSWORD_DEFAULT);
        $insertStmt = $pdo->prepare("INSERT INTO user (username, email, password) VALUES (?, ?, ?)");
        $insertStmt->execute(['admin', 'admin@example.com', $testPassword]);
        echo '<p class="success">✓ Default test account created:</p>';
        echo '<p><strong>Username:</strong> admin | <strong>Password:</strong> admin123</p>';
    } else {
        echo '<p class="success">✓ Test account `admin` already exists.</p>';
    }

    echo '<br><p><a href="index.html" style="color:#00ffff;">→ Go to Login Page</a></p>';

} catch (PDOException $e) {
    echo '<p class="error">❌ Setup Failed: ' . htmlspecialchars($e->getMessage(), ENT_QUOTES, 'UTF-8') . '</p>';
    echo '<p>Make sure MySQL is running in XAMPP or your database service.</p>';
}

echo '</div></body></html>';
?>
