<?php
// profile.php - Modern Cyberpunk Gamer Profile & Settings Dashboard
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';

$userId = $_SESSION['user_id'];

// Fetch user profile from database
$stmt = $pdo->prepare("SELECT * FROM user WHERE id = ?");
$stmt->execute([$userId]);
$user = $stmt->fetch();

if (!$user) {
    header("Location: logout.php");
    exit();
}

// Fetch stats
$favCountStmt = $pdo->prepare("SELECT COUNT(*) FROM user_favorites WHERE user_id = ?");
$favCountStmt->execute([$userId]);
$favCount = $favCountStmt->fetchColumn();

$reviewCountStmt = $pdo->prepare("SELECT COUNT(*) FROM video_reviews WHERE user_id = ?");
$reviewCountStmt->execute([$userId]);
$reviewCount = $reviewCountStmt->fetchColumn();

$avatar = $user['avatar'] ?: 'default_avatar.png';
$theme  = $user['theme_preference'] ?: 'cyberpunk';
$bio    = $user['bio'] ?: '';
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gamer Profile & Settings - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .profile-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        .profile-header-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            box-shadow: 0 0 25px var(--glow-color);
            border-radius: 16px;
            padding: 30px;
            display: flex;
            align-items: center;
            gap: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        .avatar-large {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 3px solid var(--accent-color);
            box-shadow: 0 0 20px var(--accent-color);
            object-fit: cover;
            background: #1a1a2e;
        }
        .profile-info h1 {
            margin: 0 0 8px 0;
            color: var(--accent-color);
            font-family: 'Rajdhani', sans-serif;
            font-size: 32px;
            letter-spacing: 1px;
        }
        .badge {
            display: inline-block;
            background: var(--badge-bg, rgba(0, 255, 255, 0.2));
            color: var(--accent-color);
            border: 1px solid var(--accent-color);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 36px;
            font-weight: 700;
            color: var(--accent-color);
        }
        .stat-label {
            color: #aaa;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .settings-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
        }
        .settings-card h2 {
            font-family: 'Rajdhani', sans-serif;
            color: var(--accent-color);
            margin-top: 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #ddd;
        }
        .form-control {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            color: #fff;
            font-family: inherit;
            box-sizing: border-box;
        }
        .form-control:focus {
            outline: none;
            border-color: var(--accent-color);
            box-shadow: 0 0 10px var(--accent-color);
        }
        .avatar-presets {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .avatar-preset-img {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            border: 2px solid transparent;
            cursor: pointer;
            transition: all 0.3s ease;
            object-fit: cover;
            background: #222;
        }
        .avatar-preset-img:hover, .avatar-preset-img.active {
            border-color: var(--accent-color);
            box-shadow: 0 0 15px var(--accent-color);
            transform: scale(1.1);
        }
        .btn-save {
            background: linear-gradient(135deg, var(--accent-color), #0088cc);
            color: #000;
            font-weight: 700;
            font-family: 'Rajdhani', sans-serif;
            font-size: 18px;
            padding: 12px 30px;
            border: none;
            border-radius: 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px var(--accent-color);
        }
        .btn-save:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 25px var(--accent-color);
        }
        .toast-msg {
            padding: 12px 20px;
            border-radius: 8px;
            margin-top: 15px;
            display: none;
            font-weight: 600;
        }
        .toast-msg.success {
            background: rgba(0, 255, 128, 0.2);
            border: 1px solid #00ff80;
            color: #00ff80;
        }
        .toast-msg.error {
            background: rgba(255, 77, 77, 0.2);
            border: 1px solid #ff4d4d;
            color: #ff4d4d;
        }
    </style>
</head>
<body>

    <div class="profile-container">
        <!-- Navigation Header -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link">📰 Gaming News</a>
                <a href="profile.php" class="nav-link active">👤 My Profile</a>
                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <!-- Profile Header -->
        <div class="profile-header-card">
            <img src="<?php echo htmlspecialchars($avatar); ?>" alt="Gamer Avatar" id="headerAvatarImg" class="avatar-large" onerror="this.src='gamer.jpg'">
            <div class="profile-info">
                <span class="badge">PRO GAMER • RANK #1</span>
                <h1><?php echo htmlspecialchars($user['username']); ?></h1>
                <p style="color: #aaa; margin: 0 0 10px 0;">📧 <?php echo htmlspecialchars($user['email']); ?></p>
                <p style="color: #ddd; font-style: italic; margin: 0;">"<?php echo htmlspecialchars($bio ?: 'No bio set yet. Cyberpunk enthusiast & GTA runner.'); ?>"</p>
            </div>
        </div>

        <!-- Gamer Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value"><?php echo $favCount; ?></div>
                <div class="stat-label">Saved Watchlist</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?php echo $reviewCount; ?></div>
                <div class="stat-label">Reviews & Ratings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">PRO</div>
                <div class="stat-label">Membership Tier</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?php echo date('M Y', strtotime($user['created_at'])); ?></div>
                <div class="stat-label">Joined Platform</div>
            </div>
        </div>

        <!-- Settings Form -->
        <div class="settings-card">
            <h2>⚙️ Gamer Settings & Persona Customizer</h2>
            <form id="profileForm">
                <input type="hidden" name="action" value="update_profile">
                <input type="hidden" name="avatar" id="avatarInput" value="<?php echo htmlspecialchars($avatar); ?>">

                <div class="form-group">
                    <label>Select Avatar Icon</label>
                    <div class="avatar-presets">
                        <img src="avatar_cyborg.jpg" class="avatar-preset-img <?php echo $avatar==='avatar_cyborg.jpg'?'active':''; ?>" onclick="selectAvatar('avatar_cyborg.jpg', this)" alt="Cyborg Gamer">
                        <img src="avatar_synthwave.jpg" class="avatar-preset-img <?php echo $avatar==='avatar_synthwave.jpg'?'active':''; ?>" onclick="selectAvatar('avatar_synthwave.jpg', this)" alt="Synthwave Pilot">
                        <img src="avatar_outlaw.jpg" class="avatar-preset-img <?php echo $avatar==='avatar_outlaw.jpg'?'active':''; ?>" onclick="selectAvatar('avatar_outlaw.jpg', this)" alt="Outlaw Gunslinger">
                        <img src="gtavi_vice_city_art.jpg" class="avatar-preset-img <?php echo $avatar==='gtavi_vice_city_art.jpg'?'active':''; ?>" onclick="selectAvatar('gtavi_vice_city_art.jpg', this)" alt="Vice City">
                    </div>
                </div>

                <div class="form-group">
                    <label for="theme_preference">Neon Theme Accent</label>
                    <select name="theme_preference" id="theme_preference" class="form-control" onchange="applyThemePreview(this.value)">
                        <option value="cyberpunk" <?php echo $theme==='cyberpunk'?'selected':''; ?>>🩵 Cyberpunk Cyan</option>
                        <option value="neon_violet" <?php echo $theme==='neon_violet'?'selected':''; ?>>💜 Neon Violet</option>
                        <option value="emerald_matrix" <?php echo $theme==='emerald_matrix'?'selected':''; ?>>💚 Emerald Matrix</option>
                        <option value="solar_gold" <?php echo $theme==='solar_gold'?'selected':''; ?>>💛 Solar Flare Gold</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="bio">Gamer Bio / Slogan</label>
                    <textarea name="bio" id="bio" rows="3" class="form-control" placeholder="Write a short gamer bio..."><?php echo htmlspecialchars($bio); ?></textarea>
                </div>

                <h3 style="color: var(--accent-color); font-family: 'Rajdhani', sans-serif; margin-top: 30px;">🔐 Security & Password</h3>

                <div class="form-group">
                    <label for="current_password">Current Password (optional, required if changing password)</label>
                    <input type="password" name="current_password" id="current_password" class="form-control" placeholder="••••••••">
                </div>

                <div class="form-group">
                    <label for="new_password">New Password</label>
                    <input type="password" name="new_password" id="new_password" class="form-control" placeholder="Leave blank to keep current password">
                </div>

                <button type="submit" class="btn-save" id="saveBtn">SAVE CHANGES</button>
                <div id="toastMsg" class="toast-msg"></div>
            </form>
        </div>
    </div>

    <script>
        function selectAvatar(url, imgElement) {
            document.getElementById('avatarInput').value = url;
            document.getElementById('headerAvatarImg').src = url;
            document.querySelectorAll('.avatar-preset-img').forEach(el => el.classList.remove('active'));
            imgElement.classList.add('active');
        }

        function applyThemePreview(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('gamer_theme', theme);
        }

        document.getElementById('profileForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var form = this;
            var btn = document.getElementById('saveBtn');
            var toast = document.getElementById('toastMsg');
            btn.disabled = true;
            btn.textContent = "SAVING...";
            toast.style.display = 'none';

            var formData = new FormData(form);

            fetch('api.php', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                btn.textContent = "SAVE CHANGES";
                toast.textContent = data.message;
                toast.className = 'toast-msg ' + (data.success ? 'success' : 'error');
                toast.style.display = 'block';

                if (data.success && data.theme) {
                    applyThemePreview(data.theme);
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.textContent = "SAVE CHANGES";
                toast.textContent = "An error occurred while saving.";
                toast.className = 'toast-msg error';
                toast.style.display = 'block';
            });
        });
    </script>
</body>
</html>
