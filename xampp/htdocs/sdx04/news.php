<?php
// news.php - Interactive Gaming News & Trailer Releases Hub
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';

$username = isset($_SESSION['username']) ? $_SESSION['username'] : 'Gamer';
$theme    = isset($_SESSION['theme']) ? $_SESSION['theme'] : 'cyberpunk';
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gaming News & Releases - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .news-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .page-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 36px;
            color: var(--accent-color);
            margin: 0 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 15px var(--accent-color);
        }
        .news-filter-bar {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .news-filter-btn {
            background: rgba(20, 20, 30, 0.8);
            color: #ccc;
            border: 1px solid var(--border-glow);
            padding: 10px 22px;
            border-radius: 25px;
            font-family: 'Rajdhani', sans-serif;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .news-filter-btn:hover, .news-filter-btn.active {
            background: var(--accent-color);
            color: #000;
            box-shadow: 0 0 15px var(--accent-color);
            border-color: var(--accent-color);
        }
        .news-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        .news-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            overflow: hidden;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
        }
        .news-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 0 25px var(--glow-color);
            border-color: var(--accent-color);
        }
        .news-card-img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-bottom: 1px solid var(--border-glow);
        }
        .news-card-body {
            padding: 20px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }
        .news-category-tag {
            font-size: 12px;
            font-weight: 700;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .news-card-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: #fff;
            margin: 0 0 12px 0;
            line-height: 1.3;
        }
        .news-card-snippet {
            color: #aaa;
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 20px;
            flex-grow: 1;
        }
        .news-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 15px;
            color: #888;
            font-size: 13px;
        }
        .release-badge {
            background: rgba(0, 255, 255, 0.15);
            color: var(--accent-color);
            padding: 4px 10px;
            border-radius: 12px;
            border: 1px solid var(--accent-color);
            font-weight: 700;
        }
    </style>
</head>
<body>

    <div class="news-container">
        <!-- Navigation Header -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link active">📰 Gaming News</a>
                <a href="profile.php" class="nav-link">👤 My Profile</a>
                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <h1 class="page-title">📰 Latest Gaming News & Bulletins</h1>
        <p style="color: #aaa; margin-top: 0; margin-bottom: 30px;">Stay up-to-date with Rockstar Games, GTA VI leaks, patch notes, and hardware tech.</p>

        <!-- Filter Bar -->
        <div class="news-filter-bar">
            <button class="news-filter-btn active" onclick="loadNews('All', this)">All News</button>
            <button class="news-filter-btn" onclick="loadNews('Rockstar News', this)">Rockstar News</button>
            <button class="news-filter-btn" onclick="loadNews('GTA VI', this)">GTA VI</button>
            <button class="news-filter-btn" onclick="loadNews('Red Dead', this)">Red Dead Online</button>
            <button class="news-filter-btn" onclick="loadNews('Tech & Hardware', this)">Tech & Hardware</button>
        </div>

        <!-- News Grid -->
        <div class="news-grid" id="newsGrid">
            <div style="grid-column: 1 / -1; text-align: center; color: #aaa; padding: 40px;">Loading latest news...</div>
        </div>
    </div>

    <script>
        function loadNews(category, btnElement) {
            if (btnElement) {
                document.querySelectorAll('.news-filter-btn').forEach(b => b.classList.remove('active'));
                btnElement.classList.add('active');
            }

            var grid = document.getElementById('newsGrid');
            grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #aaa; padding: 40px;">Loading news...</div>';

            fetch('api.php?action=get_news&category=' + encodeURIComponent(category))
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.news.length > 0) {
                        grid.innerHTML = data.news.map(item => `
                            <div class="news-card">
                                <img src="${item.image}" class="news-card-img" alt="${item.title}" onerror="this.src='gta.png'">
                                <div class="news-card-body">
                                    <div class="news-category-tag">${item.category} • ${item.game_title}</div>
                                    <h3 class="news-card-title">${item.title}</h3>
                                    <p class="news-card-snippet">${item.snippet}</p>
                                    <div class="news-card-footer">
                                        <span>📅 ${new Date(item.created_at).toLocaleDateString()}</span>
                                        <span class="release-badge">${item.release_date || 'Live'}</span>
                                    </div>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #aaa; padding: 40px;">No news articles found in this category.</div>';
                    }
                })
                .catch(err => {
                    grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: #ff4d4d; padding: 40px;">Failed to load news articles.</div>';
                });
        }

        // Initial load
        document.addEventListener('DOMContentLoaded', function() {
            loadNews('All');
        });
    </script>
</body>
</html>
