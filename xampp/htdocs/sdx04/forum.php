<?php
// forum.php - Gamer Community Discussion Forum
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';

$userId = $_SESSION['user_id'];
$theme  = $_SESSION['theme'] ?? 'cyberpunk';
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gamer Discussion Forum - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .forum-container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }
        .forum-header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            flex-wrap: wrap;
            gap: 15px;
        }
        .btn-new-thread {
            background: linear-gradient(135deg, var(--accent-color), #0088cc);
            color: #000;
            font-family: 'Rajdhani', sans-serif;
            font-size: 16px;
            font-weight: 700;
            padding: 10px 24px;
            border-radius: 25px;
            border: none;
            cursor: pointer;
            box-shadow: 0 0 15px var(--accent-color);
            transition: all 0.3s ease;
        }
        .btn-new-thread:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 25px var(--accent-color);
        }
        .thread-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 20px;
            transition: all 0.3s ease;
        }
        .thread-card:hover {
            border-color: var(--accent-color);
            box-shadow: 0 0 20px var(--glow-color);
            transform: translateX(4px);
        }
        .thread-main {
            flex-grow: 1;
        }
        .thread-cat {
            font-size: 11px;
            font-weight: 700;
            color: var(--accent-color);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .thread-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: #fff;
            margin: 0 0 6px 0;
            cursor: pointer;
        }
        .thread-title:hover {
            color: var(--accent-color);
        }
        .thread-meta {
            font-size: 12px;
            color: var(--text-sub);
        }
        .thread-stats {
            text-align: center;
            min-width: 80px;
        }
        .thread-stat-val {
            font-family: 'Rajdhani', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: var(--accent-color);
        }
        .thread-stat-lbl {
            font-size: 11px;
            color: var(--text-sub);
            text-transform: uppercase;
        }
        /* Modal */
        .thread-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9);
            justify-content: center; align-items: center;
            padding: 20px;
        }
        .modal-card {
            background: #0f121d;
            border: 1px solid var(--border-glow);
            box-shadow: 0 0 35px var(--glow-color);
            border-radius: 16px;
            width: 100%; max-width: 650px;
            padding: 30px;
            position: relative;
        }
    </style>
</head>
<body>

    <div class="forum-container">
        <!-- Navigation Header -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link">📰 News</a>
                <a href="forum.php" class="nav-link active">💬 Forums</a>
                <a href="games.php" class="nav-link">💻 PC Specs</a>
                <a href="profile.php" class="nav-link">👤 Profile</a>
                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <div class="forum-header-bar">
            <div>
                <h1 style="font-family: 'Rajdhani', sans-serif; color: var(--accent-color); margin: 0; font-size: 32px;">💬 Gamer Community Forum</h1>
                <p style="color: var(--text-sub); margin: 4px 0 0 0;">Discuss GTA VI map theories, Red Dead clans, and hardware rigs.</p>
            </div>
            <button class="btn-new-thread" onclick="openNewThreadModal()">+ CREATE NEW THREAD</button>
        </div>

        <!-- Forum Threads Feed -->
        <div id="threadsList">
            <div style="text-align: center; color: #777; padding: 40px;">Loading forum discussions...</div>
        </div>
    </div>

    <!-- New Thread Modal -->
    <div id="newThreadModal" class="thread-modal">
        <div class="modal-card">
            <button class="close-modal-btn" onclick="closeThreadModal()">&times;</button>
            <h2 style="font-family: 'Rajdhani', sans-serif; color: var(--accent-color); margin-top: 0;">Post a New Discussion Thread</h2>
            <form id="newThreadForm">
                <input type="hidden" name="action" value="create_thread">
                <div style="margin-bottom: 15px;">
                    <label style="display:block; color:#ccc; margin-bottom: 5px; font-weight: 600;">Category</label>
                    <select name="category" class="comment-input-box" style="height: 42px;">
                        <option value="GTA VI Theories">🔥 GTA VI Speculations & Map</option>
                        <option value="Red Dead Frontier">🤠 Red Dead Online Clans</option>
                        <option value="Hardware & PC Rigs">💻 Hardware & PC Specs</option>
                        <option value="General Gaming">🎮 General Gaming Lounge</option>
                    </select>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="display:block; color:#ccc; margin-bottom: 5px; font-weight: 600;">Thread Title</label>
                    <input type="text" name="title" class="comment-input-box" placeholder="What's your thread about?" required>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display:block; color:#ccc; margin-bottom: 5px; font-weight: 600;">Discussion Content</label>
                    <textarea name="content" rows="4" class="comment-input-box" placeholder="Write your thoughts or questions..." required></textarea>
                </div>
                <button type="submit" class="btn-new-thread" style="width: 100%;">PUBLISH THREAD</button>
            </form>
        </div>
    </div>

    <script>
        function openNewThreadModal() {
            document.getElementById('newThreadModal').style.display = 'flex';
        }
        function closeThreadModal() {
            document.getElementById('newThreadModal').style.display = 'none';
        }

        function loadThreads() {
            fetch('api.php?action=get_threads')
                .then(res => res.json())
                .then(data => {
                    var list = document.getElementById('threadsList');
                    if (data.success && data.threads.length > 0) {
                        list.innerHTML = data.threads.map(t => `
                            <div class="thread-card">
                                <img src="${t.avatar || 'gamer.jpg'}" style="width: 50px; height: 50px; border-radius: 50%; border: 2px solid var(--accent-color); object-fit: cover;" onerror="this.src='gamer.jpg'">
                                <div class="thread-main">
                                    <div class="thread-cat">${t.category}</div>
                                    <h3 class="thread-title" onclick="alert('Viewing thread details: ${t.title}')">${t.title}</h3>
                                    <div class="thread-meta">Posted by <strong>${t.username}</strong> • ${new Date(t.created_at).toLocaleDateString()}</div>
                                </div>
                                <div class="thread-stats">
                                    <div class="thread-stat-val">${t.replies_count || 0}</div>
                                    <div class="thread-stat-lbl">Replies</div>
                                </div>
                            </div>
                        `).join('');
                    } else {
                        list.innerHTML = '<div style="text-align: center; color: #777; padding: 40px;">No forum threads posted yet. Be the first to start a conversation!</div>';
                    }
                });
        }

        document.getElementById('newThreadForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(this);
            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    closeThreadModal();
                    loadThreads();
                });
        });

        document.addEventListener('DOMContentLoaded', loadThreads);
    </script>
</body>
</html>
