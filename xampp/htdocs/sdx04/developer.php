<?php
// developer.php - Developer API Portal & Key Manager
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';
$userId = $_SESSION['user_id'];
$theme  = $_SESSION['theme'] ?? 'cyberpunk';

// Fetch existing API keys
$stmt = $pdo->prepare("SELECT * FROM developer_api_keys WHERE user_id = ? ORDER BY created_at DESC");
$stmt->execute([$userId]);
$userKeys = $stmt->fetchAll();
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer API Portal - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .dev-container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }
        .page-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 32px;
            color: var(--accent-color);
            margin: 0 0 10px 0;
            text-transform: uppercase;
        }
        .dev-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
        }
        .dev-card h2 {
            font-family: 'Rajdhani', sans-serif;
            color: var(--accent-color);
            margin-top: 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 10px;
        }
        code-block {
            display: block;
            background: #000;
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            padding: 15px;
            color: #00ff88;
            font-family: monospace;
            font-size: 13px;
            overflow-x: auto;
            margin: 10px 0;
        }
    </style>
</head>
<body>

    <div class="dev-container">
        <!-- Navigation Header -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link">📰 News</a>
                <a href="forum.php" class="nav-link">💬 Forums</a>
                <a href="games.php" class="nav-link">💻 PC Specs</a>
                <a href="developer.php" class="nav-link active">🔑 API Portal</a>
                <a href="profile.php" class="nav-link">👤 Profile</a>
                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <h1 class="page-title">🔑 Developer API Portal</h1>
        <p style="color: var(--text-sub); margin-top: 0; margin-bottom: 30px;">Build third-party gaming apps, bots, or widgets using our JSON REST API.</p>

        <!-- Generate API Key Form -->
        <div class="dev-card">
            <h2>Generate Developer API Access Token</h2>
            <form id="genKeyForm" style="display:flex; gap:15px; flex-wrap:wrap;">
                <input type="hidden" name="action" value="generate_api_key">
                <input type="text" name="app_name" class="comment-input-box" style="flex-grow:1; margin-bottom:0;" placeholder="Application / Bot Name (e.g. Discord GTA Bot)" required>
                <button type="submit" class="comment-post-btn" style="height:42px;">GENERATE TOKEN</button>
            </form>

            <h3 style="color:#fff; font-family:'Rajdhani', sans-serif; margin-top:25px;">Your Active API Keys:</h3>
            <?php if (count($userKeys) > 0): ?>
                <?php foreach ($userKeys as $k): ?>
                    <div style="background:rgba(0,0,0,0.5); border:1px solid var(--border-glow); padding:15px; border-radius:10px; margin-bottom:10px;">
                        <div style="color:var(--accent-color); font-weight:bold;"><?php echo htmlspecialchars($k['app_name']); ?></div>
                        <code style="color:#00ff88; font-size:14px;"><?php echo htmlspecialchars($k['api_key']); ?></code>
                        <div style="font-size:12px; color:#888; margin-top:4px;">Created: <?php echo date('M d, Y', strtotime($k['created_at'])); ?></div>
                    </div>
                <?php endforeach; ?>
            <?php else: ?>
                <p style="color:#777;">No API keys generated yet.</p>
            <?php endif; ?>
        </div>

        <!-- Documentation -->
        <div class="dev-card">
            <h2>📖 REST API Documentation</h2>

            <h3 style="color:#fff; font-family:'Rajdhani', sans-serif;">1. Fetch Latest News Feed</h3>
            <div class="code-block" style="background:#000; border:1px solid var(--border-glow); padding:15px; border-radius:8px; color:#00ff88; font-family:monospace;">
                GET http://localhost/sdx04/api.php?action=get_news&category=Rockstar+News
            </div>

            <h3 style="color:#fff; font-family:'Rajdhani', sans-serif; margin-top:20px;">2. Fetch Video Community Reviews</h3>
            <div class="code-block" style="background:#000; border:1px solid var(--border-glow); padding:15px; border-radius:8px; color:#00ff88; font-family:monospace;">
                GET http://localhost/sdx04/api.php?action=get_reviews&video_id=VQRLujxTm3c
            </div>

            <h3 style="color:#fff; font-family:'Rajdhani', sans-serif; margin-top:20px;">3. Toggle Favorites Watchlist</h3>
            <div class="code-block" style="background:#000; border:1px solid var(--border-glow); padding:15px; border-radius:8px; color:#00ff88; font-family:monospace;">
                POST http://localhost/sdx04/api.php<br>
                Payload: action=toggle_favorite&video_id=VQRLujxTm3c
            </div>
        </div>
    </div>

    <script>
        document.getElementById('genKeyForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(this);
            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                });
        });
    </script>
</body>
</html>
