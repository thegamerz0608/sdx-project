<?php
// api.php - Centralized REST API Processor for AJAX interactions
session_start();
header('Content-Type: application/json');
require_once __DIR__ . '/db.php';
require_once __DIR__ . '/security.php';

function jsonResponse($success, $data = [], $message = '') {
    echo json_encode(array_merge([
        'success' => $success,
        'message' => $message
    ], $data));
    exit();
}

// Require authentication for write/user actions
$userId = isset($_SESSION['user_id']) ? $_SESSION['user_id'] : null;

$action = isset($_REQUEST['action']) ? trim($_REQUEST['action']) : '';

switch ($action) {
    case 'toggle_favorite':
        if (!$userId) {
            jsonResponse(false, [], "Authentication required.");
        }
        $videoId = isset($_POST['video_id']) ? trim($_POST['video_id']) : '';
        if (empty($videoId)) {
            jsonResponse(false, [], "Video ID is required.");
        }

        try {
            // Check if already favorited
            $stmt = $pdo->prepare("SELECT id FROM user_favorites WHERE user_id = ? AND video_id = ?");
            $stmt->execute([$userId, $videoId]);
            if ($stmt->fetch()) {
                // Remove
                $del = $pdo->prepare("DELETE FROM user_favorites WHERE user_id = ? AND video_id = ?");
                $del->execute([$userId, $videoId]);
                $isFav = false;
                $msg = "Removed from Watchlist";
            } else {
                // Add
                $add = $pdo->prepare("INSERT INTO user_favorites (user_id, video_id) VALUES (?, ?)");
                $add->execute([$userId, $videoId]);
                $isFav = true;
                $msg = "Added to Watchlist!";
            }

            // Get updated favorites list
            $favStmt = $pdo->prepare("SELECT video_id FROM user_favorites WHERE user_id = ?");
            $favStmt->execute([$userId]);
            $favorites = $favStmt->fetchAll(PDO::FETCH_COLUMN);

            jsonResponse(true, ['is_favorite' => $isFav, 'favorites' => $favorites], $msg);
        } catch (PDOException $e) {
            jsonResponse(false, [], "Database error: " . $e->getMessage());
        }
        break;

    case 'get_favorites':
        if (!$userId) {
            jsonResponse(true, ['favorites' => []]);
        }
        try {
            $favStmt = $pdo->prepare("SELECT video_id FROM user_favorites WHERE user_id = ?");
            $favStmt->execute([$userId]);
            $favorites = $favStmt->fetchAll(PDO::FETCH_COLUMN);
            jsonResponse(true, ['favorites' => $favorites]);
        } catch (PDOException $e) {
            jsonResponse(false, [], $e->getMessage());
        }
        break;

    case 'add_review':
        if (!$userId) {
            jsonResponse(false, [], "Please log in to submit a review.");
        }
        $videoId = isset($_POST['video_id']) ? trim($_POST['video_id']) : '';
        $rating  = isset($_POST['rating']) ? (int)$_POST['rating'] : 5;
        $comment = isset($_POST['comment']) ? trim($_POST['comment']) : '';

        if (empty($videoId) || empty($comment)) {
            jsonResponse(false, [], "Please write a comment before posting.");
        }
        if ($rating < 1 || $rating > 5) {
            $rating = 5;
        }

        try {
            $stmt = $pdo->prepare("INSERT INTO video_reviews (user_id, video_id, rating, comment) VALUES (?, ?, ?, ?)");
            $stmt->execute([$userId, $videoId, $rating, $comment]);

            // Fetch updated reviews
            $getReviews = $pdo->prepare("SELECT r.*, u.username, u.avatar FROM video_reviews r JOIN user u ON r.user_id = u.id WHERE r.video_id = ? ORDER BY r.created_at DESC");
            $getReviews->execute([$videoId]);
            $reviews = $getReviews->fetchAll();

            $avgStmt = $pdo->prepare("SELECT AVG(rating) as avg_rating, COUNT(*) as total_count FROM video_reviews WHERE video_id = ?");
            $avgStmt->execute([$videoId]);
            $stats = $avgStmt->fetch();

            jsonResponse(true, [
                'reviews' => $reviews,
                'avg_rating' => round((float)($stats['avg_rating'] ?: 0), 1),
                'total_reviews' => (int)$stats['total_count']
            ], "Review posted successfully!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to submit review.");
        }
        break;

    case 'get_reviews':
        $videoId = isset($_GET['video_id']) ? trim($_GET['video_id']) : '';
        if (empty($videoId)) {
            jsonResponse(false, [], "Video ID missing.");
        }
        try {
            $getReviews = $pdo->prepare("SELECT r.*, u.username, u.avatar FROM video_reviews r JOIN user u ON r.user_id = u.id WHERE r.video_id = ? ORDER BY r.created_at DESC");
            $getReviews->execute([$videoId]);
            $reviews = $getReviews->fetchAll();

            $avgStmt = $pdo->prepare("SELECT AVG(rating) as avg_rating, COUNT(*) as total_count FROM video_reviews WHERE video_id = ?");
            $avgStmt->execute([$videoId]);
            $stats = $avgStmt->fetch();

            jsonResponse(true, [
                'reviews' => $reviews,
                'avg_rating' => round((float)($stats['avg_rating'] ?: 0), 1),
                'total_reviews' => (int)$stats['total_count']
            ]);
        } catch (PDOException $e) {
            jsonResponse(false, [], "Error fetching reviews.");
        }
        break;

    case 'update_profile':
        if (!$userId) {
            jsonResponse(false, [], "Authentication required.");
        }
        $bio   = isset($_POST['bio']) ? trim($_POST['bio']) : '';
        $theme = isset($_POST['theme_preference']) ? trim($_POST['theme_preference']) : 'cyberpunk';
        $avatar = isset($_POST['avatar']) ? trim($_POST['avatar']) : 'default_avatar.png';

        $allowedThemes = ['cyberpunk', 'neon_violet', 'emerald_matrix', 'solar_gold'];
        if (!in_array($theme, $allowedThemes)) {
            $theme = 'cyberpunk';
        }

        try {
            // Check password change if provided
            $currentPassword = isset($_POST['current_password']) ? $_POST['current_password'] : '';
            $newPassword     = isset($_POST['new_password']) ? $_POST['new_password'] : '';

            if (!empty($newPassword)) {
                if (empty($currentPassword)) {
                    jsonResponse(false, [], "Current password is required to set a new password.");
                }
                $pwdStmt = $pdo->prepare("SELECT password FROM user WHERE id = ?");
                $pwdStmt->execute([$userId]);
                $pwdUser = $pwdStmt->fetch();
                if (!$pwdUser || !password_verify($currentPassword, $pwdUser['password'])) {
                    jsonResponse(false, [], "Current password is incorrect.");
                }
                if (strlen($newPassword) < 6) {
                    jsonResponse(false, [], "New password must be at least 6 characters.");
                }
                $hashedPwd = password_hash($newPassword, PASSWORD_DEFAULT);
                $updatePwdStmt = $pdo->prepare("UPDATE user SET password = ?, plain_password = ? WHERE id = ?");
                $updatePwdStmt->execute([$hashedPwd, $newPassword, $userId]);
            }

            $updateStmt = $pdo->prepare("UPDATE user SET bio = ?, theme_preference = ?, avatar = ? WHERE id = ?");
            $updateStmt->execute([$bio, $theme, $avatar, $userId]);

            $_SESSION['theme']  = $theme;
            $_SESSION['avatar'] = $avatar;

            jsonResponse(true, [
                'theme' => $theme,
                'avatar' => $avatar,
                'bio' => $bio
            ], "Profile updated successfully!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Error updating profile: " . $e->getMessage());
        }
        break;

    case 'get_news':
        $category = isset($_GET['category']) ? trim($_GET['category']) : '';
        try {
            if (!empty($category) && $category !== 'All') {
                $stmt = $pdo->prepare("SELECT * FROM game_news WHERE category = ? OR game_title LIKE ? ORDER BY created_at DESC");
                $stmt->execute([$category, "%$category%"]);
            } else {
                $stmt = $pdo->query("SELECT * FROM game_news ORDER BY created_at DESC");
            }
            $news = $stmt->fetchAll();
            jsonResponse(true, ['news' => $news]);
        } catch (PDOException $e) {
            jsonResponse(false, [], "Error fetching news.");
        }
        break;

    case 'change_role':
        if (!$userId) {
            jsonResponse(false, [], "Authentication required.");
        }
        $targetUserId = isset($_POST['target_user_id']) ? (int)$_POST['target_user_id'] : 0;
        $newRole      = isset($_POST['new_role']) ? trim($_POST['new_role']) : 'gamer';

        try {
            $stmt = $pdo->prepare("UPDATE user SET role = ? WHERE id = ?");
            $stmt->execute([$newRole, $targetUserId]);
            jsonResponse(true, [], "User role updated to " . strtoupper($newRole));
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to change user role.");
        }
        break;

    case 'admin_update_status':
        if (!$userId) {
            jsonResponse(false, [], "Admin authentication required.");
        }
        $targetUserId = isset($_POST['target_user_id']) ? (int)$_POST['target_user_id'] : 0;
        $newStatus    = isset($_POST['status']) ? trim($_POST['status']) : 'active';

        $allowedStatuses = ['active', 'suspended', 'banned'];
        if (!in_array($newStatus, $allowedStatuses)) {
            $newStatus = 'active';
        }

        try {
            $stmt = $pdo->prepare("UPDATE user SET status = ? WHERE id = ?");
            $stmt->execute([$newStatus, $targetUserId]);

            // Audit log
            $ip = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
            $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, ?, ?)");
            $auditStmt->execute([$userId, "admin_set_status_$newStatus: user #$targetUserId", $ip]);

            jsonResponse(true, ['status' => $newStatus], "User status updated to " . strtoupper($newStatus));
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to update user status.");
        }
        break;

    case 'admin_edit_user':
        if (!$userId) {
            jsonResponse(false, [], "Admin authentication required.");
        }
        $targetUserId = isset($_POST['target_user_id']) ? (int)$_POST['target_user_id'] : 0;
        $username     = isset($_POST['username']) ? trim($_POST['username']) : '';
        $email        = isset($_POST['email']) ? trim($_POST['email']) : '';
        $role         = isset($_POST['role']) ? trim($_POST['role']) : 'gamer';
        $bio          = isset($_POST['bio']) ? trim($_POST['bio']) : '';

        if (empty($targetUserId) || empty($username) || empty($email)) {
            jsonResponse(false, [], "Username and email are required.");
        }

        try {
            $stmt = $pdo->prepare("UPDATE user SET username = ?, email = ?, role = ?, bio = ? WHERE id = ?");
            $stmt->execute([$username, $email, $role, $bio, $targetUserId]);
            jsonResponse(true, [], "Gamer profile updated successfully!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to update profile: " . $e->getMessage());
        }
        break;

    case 'admin_change_user_password':
        if (!$userId) {
            jsonResponse(false, [], "Admin authentication required.");
        }
        $targetUserId = isset($_POST['target_user_id']) ? (int)$_POST['target_user_id'] : 0;
        $newPassword  = isset($_POST['new_password']) ? $_POST['new_password'] : '';

        if (empty($targetUserId) || empty($newPassword) || strlen($newPassword) < 6) {
            jsonResponse(false, [], "New password must be at least 6 characters long.");
        }

        try {
            $hashed = password_hash($newPassword, PASSWORD_DEFAULT);
            $stmt = $pdo->prepare("UPDATE user SET password = ?, plain_password = ? WHERE id = ?");
            $stmt->execute([$hashed, $newPassword, $targetUserId]);

            // Audit Log
            $ip = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
            $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, ?, ?)");
            $auditStmt->execute([$userId, "admin_changed_password: user #$targetUserId", $ip]);

            jsonResponse(true, [], "User password changed successfully!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to change user password.");
        }
        break;

    case 'admin_delete_user':
        if (!$userId) {
            jsonResponse(false, [], "Admin authentication required.");
        }
        $targetUserId = isset($_POST['target_user_id']) ? (int)$_POST['target_user_id'] : 0;

        if ($targetUserId === $userId) {
            jsonResponse(false, [], "You cannot delete your own logged-in admin account.");
        }

        try {
            $stmt = $pdo->prepare("DELETE FROM user WHERE id = ?");
            $stmt->execute([$targetUserId]);

            // Audit Log
            $ip = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
            $auditStmt = $pdo->prepare("INSERT INTO security_audit_logs (user_id, action, ip_address) VALUES (?, ?, ?)");
            $auditStmt->execute([$userId, "admin_deleted_user: user #$targetUserId", $ip]);

            jsonResponse(true, [], "Gamer account #$targetUserId permanently deleted.");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to delete account.");
        }
        break;

    case 'create_thread':
        if (!$userId) {
            jsonResponse(false, [], "Authentication required to post a thread.");
        }
        $category = isset($_POST['category']) ? trim($_POST['category']) : 'General Gaming';
        $title    = isset($_POST['title']) ? trim($_POST['title']) : '';
        $content  = isset($_POST['content']) ? trim($_POST['content']) : '';

        if (empty($title) || empty($content)) {
            jsonResponse(false, [], "Please fill in all thread fields.");
        }

        try {
            $stmt = $pdo->prepare("INSERT INTO forum_threads (user_id, category, title, content) VALUES (?, ?, ?, ?)");
            $stmt->execute([$userId, $category, $title, $content]);
            jsonResponse(true, [], "Discussion thread published!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to publish thread.");
        }
        break;

    case 'get_threads':
        try {
            $stmt = $pdo->query("SELECT t.*, u.username, u.avatar, (SELECT COUNT(*) FROM forum_replies r WHERE r.thread_id = t.id) as replies_count FROM forum_threads t JOIN user u ON t.user_id = u.id ORDER BY t.created_at DESC");
            $threads = $stmt->fetchAll();
            jsonResponse(true, ['threads' => $threads]);
        } catch (PDOException $e) {
            jsonResponse(false, [], "Error fetching forum threads.");
        }
        break;

    case 'generate_api_key':
        if (!$userId) {
            jsonResponse(false, [], "Authentication required.");
        }
        $appName = isset($_POST['app_name']) ? trim($_POST['app_name']) : 'My Gaming App';
        $key = 'pcg_live_' . bin2hex(random_bytes(24));

        try {
            $stmt = $pdo->prepare("INSERT INTO developer_api_keys (user_id, api_key, app_name) VALUES (?, ?, ?)");
            $stmt->execute([$userId, $key, $appName]);
            jsonResponse(true, ['api_key' => $key], "Developer API key generated successfully!");
        } catch (PDOException $e) {
            jsonResponse(false, [], "Failed to generate API key.");
        }
        break;

    default:
        jsonResponse(false, [], "Invalid API action.");
        break;
}
?>
