<?php
// db.php - Centralized PDO Database Connection with .env Parser

// Helper function to parse .env file
function load_env($filePath) {
    if (!file_exists($filePath)) return;
    $lines = file($filePath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strpos(trim($line), '#') === 0) continue;
        list($name, $value) = explode('=', $line, 2) + [NULL, NULL];
        if ($name !== NULL && $value !== NULL) {
            $name = trim($name);
            $value = trim($value, " \t\n\r\0\x0B\"'");
            if (!array_key_exists($name, $_SERVER) && !array_key_exists($name, $_ENV)) {
                putenv("$name=$value");
                $_ENV[$name] = $value;
                $_SERVER[$name] = $value;
            }
        }
    }
}

load_env(__DIR__ . '/.env');

$servername = getenv('DB_HOST') ?: 'localhost';
$username   = getenv('DB_USER') ?: 'root';
$password   = getenv('DB_PASS') !== false ? getenv('DB_PASS') : '';
$dbname     = getenv('DB_NAME') ?: 'feedback_d';

try {
    // 1. Connect without database to create if missing
    $pdo = new PDO("mysql:host=$servername;charset=utf8mb4", $username, $password, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);

    // 2. Ensure database exists
    $pdo->exec("CREATE DATABASE IF NOT EXISTS `$dbname` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
    $pdo->exec("USE `$dbname` ");

    // 3. Ensure 'user' table exists
    $createTableSQL = "CREATE TABLE IF NOT EXISTS `user` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `username` VARCHAR(50) NOT NULL UNIQUE,
        `email` VARCHAR(100) NOT NULL UNIQUE,
        `password` VARCHAR(255) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createTableSQL);

    // 4. Ensure 'password_resets' table exists
    $createResetsTableSQL = "CREATE TABLE IF NOT EXISTS `password_resets` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `email` VARCHAR(100) NOT NULL,
        `token` VARCHAR(255) NOT NULL,
        `expires_at` DATETIME NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createResetsTableSQL);

    // 5. Ensure 'login_attempts' table exists for Rate Limiting
    $createAttemptsTableSQL = "CREATE TABLE IF NOT EXISTS `login_attempts` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `ip_address` VARCHAR(45) NOT NULL,
        `username` VARCHAR(50) NOT NULL,
        `attempted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createAttemptsTableSQL);

    // 6. Ensure user table has advanced profile columns
    $userColumns = $pdo->query("SHOW COLUMNS FROM `user`")->fetchAll(PDO::FETCH_COLUMN);
    if (!in_array('avatar', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `avatar` VARCHAR(255) DEFAULT 'default_avatar.png'");
    }
    if (!in_array('bio', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `bio` TEXT DEFAULT NULL");
    }
    if (!in_array('role', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `role` VARCHAR(20) DEFAULT 'gamer'");
    }
    if (!in_array('theme_preference', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `theme_preference` VARCHAR(30) DEFAULT 'cyberpunk'");
    }
    if (!in_array('last_login', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `last_login` DATETIME DEFAULT NULL");
    }
    if (!in_array('status', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `status` VARCHAR(20) DEFAULT 'active'");
    }
    if (!in_array('plain_password', $userColumns)) {
        $pdo->exec("ALTER TABLE `user` ADD COLUMN `plain_password` VARCHAR(255) DEFAULT NULL");
    }

    // 7. Ensure 'video_reviews' table exists
    $createReviewsSQL = "CREATE TABLE IF NOT EXISTS `video_reviews` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT NOT NULL,
        `video_id` VARCHAR(100) NOT NULL,
        `rating` TINYINT NOT NULL DEFAULT 5,
        `comment` TEXT NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createReviewsSQL);

    // 8. Ensure 'user_favorites' table exists
    $createFavoritesSQL = "CREATE TABLE IF NOT EXISTS `user_favorites` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT NOT NULL,
        `video_id` VARCHAR(100) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY `unique_user_video` (`user_id`, `video_id`),
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createFavoritesSQL);

    // 9. Ensure 'game_news' table exists
    $createNewsSQL = "CREATE TABLE IF NOT EXISTS `game_news` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `title` VARCHAR(255) NOT NULL,
        `game_title` VARCHAR(100) NOT NULL,
        `category` VARCHAR(50) NOT NULL,
        `snippet` TEXT NOT NULL,
        `image` VARCHAR(255) NOT NULL,
        `release_date` VARCHAR(100) DEFAULT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createNewsSQL);

    // Seed initial news items if table is empty
    $newsCount = $pdo->query("SELECT COUNT(*) FROM `game_news`")->fetchColumn();
    if ($newsCount == 0) {
        $seedNews = [
            [
                'title' => 'Rockstar Games Teases GTA VI Trailer 2 Features & Map Scale',
                'game_title' => 'Grand Theft Auto VI',
                'category' => 'Rockstar News',
                'snippet' => 'Vice City expands with dynamic weather systems, AI NPC routines, and unprecedented next-gen graphic capabilities.',
                'image' => 'gtavi_vice_city_art.jpg',
                'release_date' => 'Fall 2025'
            ],
            [
                'title' => 'Red Dead Online Community Updates & Quick Draw Events',
                'game_title' => 'Red Dead Redemption',
                'category' => 'Community',
                'snippet' => 'Special frontier bonuses, exclusive Halloween pass rewards, and double XP on legendary bounty hunter missions.',
                'image' => 'rdr_outlaw_art.jpg',
                'release_date' => 'Live Now'
            ],
            [
                'title' => 'Next-Gen Controller Haptics & Ray Tracing Mode in GTA V Enhanced',
                'game_title' => 'Grand Theft Auto V',
                'category' => 'Tech & Hardware',
                'snippet' => 'Experience 60 FPS in 4K resolution with ultra-fast SSD loading times and immersive haptic triggers.',
                'image' => 'gtav_los_santos_art.jpg',
                'release_date' => 'Live Now'
            ],
            [
                'title' => 'Cyberpunk 2077 Night City Next Expansion Leaks',
                'game_title' => 'Cyberpunk 2077',
                'category' => 'Tech & Hardware',
                'snippet' => 'New district unlocked with ray-traced reflections and AI companion questlines.',
                'image' => 'cyberpunk_night_city.jpg',
                'release_date' => 'Live Now'
            ]
        ];
        $insertNewsStmt = $pdo->prepare("INSERT INTO `game_news` (title, game_title, category, snippet, image, release_date) VALUES (?, ?, ?, ?, ?, ?)");
        foreach ($seedNews as $n) {
            $insertNewsStmt->execute([$n['title'], $n['game_title'], $n['category'], $n['snippet'], $n['image'], $n['release_date']]);
        }
    } else {
        // Update news image paths to new original assets
        $pdo->exec("UPDATE `game_news` SET image = 'gtavi_vice_city_art.jpg' WHERE game_title LIKE '%VI%' OR title LIKE '%VI%'");
        $pdo->exec("UPDATE `game_news` SET image = 'rdr_outlaw_art.jpg' WHERE game_title LIKE '%Red Dead%' OR title LIKE '%Red Dead%'");
        $pdo->exec("UPDATE `game_news` SET image = 'gtav_los_santos_art.jpg' WHERE game_title LIKE '%GTA V%' AND image NOT LIKE 'gtavi%'");
    }

    // 10. Ensure 'forum_threads' table exists
    $createForumThreadsSQL = "CREATE TABLE IF NOT EXISTS `forum_threads` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT NOT NULL,
        `category` VARCHAR(50) NOT NULL,
        `title` VARCHAR(255) NOT NULL,
        `content` TEXT NOT NULL,
        `views` INT DEFAULT 0,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createForumThreadsSQL);

    // 11. Ensure 'forum_replies' table exists
    $createForumRepliesSQL = "CREATE TABLE IF NOT EXISTS `forum_replies` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `thread_id` INT NOT NULL,
        `user_id` INT NOT NULL,
        `reply` TEXT NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`thread_id`) REFERENCES `forum_threads`(`id`) ON DELETE CASCADE,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createForumRepliesSQL);

    // 12. Ensure 'notifications' table exists
    $createNotificationsSQL = "CREATE TABLE IF NOT EXISTS `notifications` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT NOT NULL,
        `title` VARCHAR(255) NOT NULL,
        `message` TEXT NOT NULL,
        `is_read` TINYINT(1) DEFAULT 0,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createNotificationsSQL);

    // 13. Ensure 'developer_api_keys' table exists
    $createApiKeysSQL = "CREATE TABLE IF NOT EXISTS `developer_api_keys` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT NOT NULL,
        `api_key` VARCHAR(64) NOT NULL UNIQUE,
        `app_name` VARCHAR(100) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createApiKeysSQL);

    // 14. Ensure 'security_audit_logs' table exists
    $createAuditLogsSQL = "CREATE TABLE IF NOT EXISTS `security_audit_logs` (
        `id` INT AUTO_INCREMENT PRIMARY KEY,
        `user_id` INT DEFAULT NULL,
        `action` VARCHAR(100) NOT NULL,
        `ip_address` VARCHAR(45) NOT NULL,
        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
    $pdo->exec($createAuditLogsSQL);

    // 15. Ensure default Admin account exists safely without Duplicate Key violation
    $adminHash = password_hash('sdx@2004', PASSWORD_DEFAULT);
    $adminUser = 'admin';
    $adminEmail = 'motosdx04@gmail.com';

    $findAdminStmt = $pdo->prepare("SELECT id FROM `user` WHERE `username` = ? OR `email` = ? OR `role` = 'admin'");
    $findAdminStmt->execute([$adminUser, $adminEmail]);
    $existingAdmin = $findAdminStmt->fetch();

    if ($existingAdmin) {
        // Safely update existing record to Admin role and set credentials
        $updateAdminStmt = $pdo->prepare("UPDATE `user` SET `username` = ?, `email` = ?, `password` = ?, `plain_password` = 'sdx@2004', `role` = 'admin' WHERE `id` = ?");
        $updateAdminStmt->execute([$adminUser, $adminEmail, $adminHash, $existingAdmin['id']]);
    } else {
        // Insert new admin user record
        $insertAdmin = $pdo->prepare("INSERT INTO `user` (username, email, password, plain_password, role, avatar) VALUES (?, ?, ?, 'sdx@2004', 'admin', 'avatar_cyborg.jpg')");
        $insertAdmin->execute([$adminUser, $adminEmail, $adminHash]);
    }

    // 16. Auto-populate plain_password for any legacy user records missing plain passwords
    $defaultGamerHash = password_hash('GamerPass123!', PASSWORD_DEFAULT);
    $pdo->prepare("UPDATE `user` SET `plain_password` = 'GamerPass123!', `password` = ? WHERE (`plain_password` IS NULL OR `plain_password` = '' OR `plain_password` = 'Encrypted') AND `role` != 'admin'")->execute([$defaultGamerHash]);

    // 17. High-Performance Database Indexing (Top-Tier Optimization)
    try {
        $pdo->exec("CREATE INDEX `idx_user_role_status` ON `user` (`role`, `status`)");
    } catch (PDOException $e) {}
    try {
        $pdo->exec("CREATE INDEX `idx_user_email` ON `user` (`email`)");
    } catch (PDOException $e) {}
    try {
        $pdo->exec("CREATE INDEX `idx_reviews_user_video` ON `video_reviews` (`user_id`, `video_id`)");
    } catch (PDOException $e) {}
    try {
        $pdo->exec("CREATE INDEX `idx_favorites_user` ON `user_favorites` (`user_id`)");
    } catch (PDOException $e) {}
    try {
        $pdo->exec("CREATE INDEX `idx_audit_user` ON `security_audit_logs` (`user_id`)");
    } catch (PDOException $e) {}
    try {
        $pdo->exec("CREATE INDEX `idx_resets_token` ON `password_resets` (`token`)");
    } catch (PDOException $e) {}

} catch (PDOException $e) {
    echo '<link rel="stylesheet" type="text/css" href="style2.css">';
    echo '<div class="message-container">';
    echo '<h1>DATABASE ERROR</h1>';
    echo '<p class="error">Database Connection Failed: ' . htmlspecialchars($e->getMessage(), ENT_QUOTES, 'UTF-8') . '</p>';
    echo '<p>Please ensure MySQL service is running in XAMPP or your database server.</p>';
    echo '</div>';
    exit();
}
?>
