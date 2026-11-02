<?php
// Practise.php - Pro Controller Gaming Showcase & Enterprise Hub
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';

$username = isset($_SESSION['username']) ? $_SESSION['username'] : 'Gamer';
$avatar   = isset($_SESSION['avatar']) ? $_SESSION['avatar'] : 'avatar_cyborg.jpg';
$theme    = isset($_SESSION['theme']) ? $_SESSION['theme'] : 'cyberpunk';
$role     = isset($_SESSION['role']) ? $_SESSION['role'] : 'gamer';
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Controller Gaming Showcase Hub</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link href="Practise.css" rel="stylesheet">
    <script src="server_sentinel.js"></script>
</head>
<body style="padding: 20px;">

    <div style="max-width: 1350px; margin: 0 auto;">
        
        <!-- Top Navigation Bar -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link active">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link">📰 News</a>
                <a href="forum.php" class="nav-link">💬 Forums</a>
                <a href="games.php" class="nav-link">💻 PC Specs</a>
                <a href="developer.php" class="nav-link">🔑 API</a>
                <a href="profile.php" class="nav-link">👤 Profile</a>

                <!-- User Pill -->
                <div class="user-pill">
                    <img src="<?php echo htmlspecialchars($avatar); ?>" alt="User Avatar" class="user-avatar-sm" onerror="this.src='avatar_cyborg.jpg'">
                    <span style="font-size: 14px; font-weight: 600; color: var(--accent-color);"><?php echo htmlspecialchars($username); ?></span>
                </div>

                <!-- Theme Switcher Dropdown -->
                <select id="themeQuickSelect" onchange="changeGlobalTheme(this.value)" style="background: rgba(0,0,0,0.6); color: var(--accent-color); border: 1px solid var(--border-glow); border-radius: 15px; padding: 6px 10px; font-family: 'Rajdhani', sans-serif; font-weight: 600; cursor: pointer;">
                    <option value="cyberpunk" <?php echo $theme==='cyberpunk'?'selected':''; ?>>🩵 Cyberpunk</option>
                    <option value="neon_violet" <?php echo $theme==='neon_violet'?'selected':''; ?>>💜 Neon Violet</option>
                    <option value="emerald_matrix" <?php echo $theme==='emerald_matrix'?'selected':''; ?>>💚 Emerald</option>
                    <option value="solar_gold" <?php echo $theme==='solar_gold'?'selected':''; ?>>💛 Solar Gold</option>
                </select>

                <!-- Audio FX Toggle -->
                <button id="soundToggleBtn" onclick="toggleAudio()" style="background: rgba(0,255,255,0.1); color: var(--accent-color); border: 1px solid var(--accent-color); border-radius: 50%; width: 36px; height: 36px; cursor: pointer; font-size: 16px; display: flex; justify-content: center; align-items: center;" title="Toggle UI Sound Effects">🔊</button>

                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <!-- GTA VI Countdown HUD -->
        <div class="countdown-hud">
            <div>
                <h3 class="hud-title">⚡ GRAND THEFT AUTO VI — COUNTDOWN HUD</h3>
                <p class="hud-sub">Live countdown to Vice City arrival & next-gen gameplay debut.</p>
            </div>
            <div class="timer-boxes">
                <div class="timer-box"><div class="timer-val" id="timerDays">420</div><div class="timer-lbl">DAYS</div></div>
                <div class="timer-box"><div class="timer-val" id="timerHours">14</div><div class="timer-lbl">HOURS</div></div>
                <div class="timer-box"><div class="timer-val" id="timerMins">32</div><div class="timer-lbl">MINS</div></div>
                <div class="timer-box"><div class="timer-val" id="timerSecs">45</div><div class="timer-lbl">SECS</div></div>
            </div>
        </div>

        <!-- Search & Filter Controls -->
        <div class="search-filter-section">
            <div class="search-bar">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" placeholder="Search game titles, trailers, or keywords..." oninput="debouncedFilterVideos()">
            </div>

            <div class="category-pills">
                <button class="cat-pill active" onclick="setFilter('All', this)">All Games</button>
                <button class="cat-pill" onclick="setFilter('GTA VI', this)">GTA VI</button>
                <button class="cat-pill" onclick="setFilter('GTA V', this)">GTA V</button>
                <button class="cat-pill" onclick="setFilter('Red Dead', this)">Red Dead</button>
                <button class="cat-pill" onclick="setFilter('Watchlist', this)">❤️ My Watchlist</button>
            </div>
        </div>

        <!-- Video Sections with Unique AI Gaming Assets -->
        <div id="videoContainer">
            <!-- GTA VI Section -->
            <div class="video-section-block" data-category="GTA VI">
                <h3 class="video-group">Grand Theft Auto VI</h3>
                <div class="videos-grid">
                    <div class="videos" data-id="VQRLujxTm3c" data-game="Grand Theft Auto VI" data-title="Trailer 2 Vice City Drive">
                        <button class="fav-btn" onclick="toggleFavorite('VQRLujxTm3c', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('VQRLujxTm3c', 'Grand Theft Auto VI - Vice City Neon Drive')">
                            <img class="video-img" src="gtavi_vice_city_art.jpg" alt="Grand Theft Auto VI Vice City Drive">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Grand Theft Auto VI</h4>
                            <span class="video-sub">Official Trailer 2 - Vice City (Click to Play)</span>
                        </div>
                    </div>

                    <div class="videos" data-id="QdBZY2fkU-0" data-game="Grand Theft Auto VI" data-title="Trailer 1 Lucia & Jason Reveal">
                        <button class="fav-btn" onclick="toggleFavorite('QdBZY2fkU-0', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('QdBZY2fkU-0', 'Grand Theft Auto VI - Lucia & Jason Reveal')">
                            <img class="video-img" src="gtavi_trailer2_art.jpg" alt="Grand Theft Auto VI Trailer 1">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Grand Theft Auto VI</h4>
                            <span class="video-sub">Official Trailer 1 Reveal (Click to Play)</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- GTA V Section -->
            <div class="video-section-block" data-category="GTA V">
                <h3 class="video-group">Grand Theft Auto V & Online</h3>
                <div class="videos-grid">
                    <div class="videos" data-id="VrJZmOerpCE" data-game="Grand Theft Auto V" data-title="Los Santos Ray Tracing Enhanced">
                        <button class="fav-btn" onclick="toggleFavorite('VrJZmOerpCE', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('VrJZmOerpCE', 'GTAV Enhanced Los Santos Skyline')">
                            <img class="video-img" src="gtav_los_santos_art.jpg" alt="Grand Theft Auto V Enhanced">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Grand Theft Auto V</h4>
                            <span class="video-sub">Experience GTAV Enhanced 4K</span>
                        </div>
                    </div>

                    <div class="videos" data-id="gta_online_heist" data-game="GTA V" data-title="GTA Online Tactical Heist">
                        <button class="fav-btn" onclick="toggleFavorite('gta_online_heist', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('VrJZmOerpCE', 'Grand Theft Auto Online - Stealth Heist Hangar')">
                            <img class="video-img" src="gta_online_heist_art.jpg" alt="Grand Theft Auto Online Heist">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Grand Theft Auto Online</h4>
                            <span class="video-sub">Tactical Heist Hangar (Click to Play)</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Red Dead Section -->
            <div class="video-section-block" data-category="Red Dead">
                <h3 class="video-group">Red Dead Online</h3>
                <div class="videos-grid">
                    <div class="videos" data-id="vFLHoGqL52A" data-game="Red Dead Online" data-title="Frontier Outlaw Sunset">
                        <button class="fav-btn" onclick="toggleFavorite('vFLHoGqL52A', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('vFLHoGqL52A', 'Red Dead Online - Frontier Outlaw')">
                            <img class="video-img" src="rdr_outlaw_art.jpg" alt="Red Dead Online Outlaw">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Red Dead Online</h4>
                            <span class="video-sub">Frontier Outlaw Sunset (Click to Play)</span>
                        </div>
                    </div>

                    <div class="videos" data-id="IYoTuQuvFyY" data-game="Red Dead Online" data-title="Moonshine Saloon Quick Draw">
                        <button class="fav-btn" onclick="toggleFavorite('IYoTuQuvFyY', this, event)">❤️</button>
                        <div class="video-thumb-container" onclick="openModal('IYoTuQuvFyY', 'Red Dead Online - Moonshine Saloon')">
                            <img class="video-img" src="rdr_saloon_art.jpg" alt="Red Dead Online Saloon">
                            <div class="play-overlay"><div class="play-icon-btn">▶</div></div>
                        </div>
                        <div class="video-info">
                            <h4 class="video-title">Red Dead Online</h4>
                            <span class="video-sub">Moonshine Saloon & Quick Draw</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Interactive Video Player & Live Review Modal -->
    <div id="videoModal" class="modal">
        <div class="modal-content-wrapper">
            <button class="close-modal-btn" onclick="closeModal()">&times;</button>
            
            <!-- Video Player Side -->
            <div class="modal-player-side">
                <div class="iframe-container">
                    <iframe id="videoPlayer" src="" allowfullscreen allow="autoplay"></iframe>
                </div>
            </div>

            <!-- Live Ratings & Comments Side -->
            <div class="modal-comments-side">
                <h3 id="modalVideoTitle" class="modal-title">Trailer Showcase</h3>

                <!-- Overview -->
                <div class="rating-overview">
                    <span style="font-size: 24px; color: #ffcc00;">⭐</span>
                    <div>
                        <div style="font-weight: 700; font-size: 18px;" id="avgRatingVal">5.0 / 5.0</div>
                        <div style="font-size: 12px; color: var(--text-sub);" id="totalReviewsVal">0 Gamer Reviews</div>
                    </div>
                </div>

                <!-- Rate & Comment Form -->
                <div style="margin-bottom: 15px;">
                    <div style="font-size: 13px; color: #aaa; margin-bottom: 5px;">Your Star Rating:</div>
                    <div class="star-rating-select" id="starRatingSelector">
                        <span onclick="setRating(1)">★</span>
                        <span onclick="setRating(2)">★</span>
                        <span onclick="setRating(3)">★</span>
                        <span onclick="setRating(4)">★</span>
                        <span onclick="setRating(5)" class="gold">★</span>
                    </div>

                    <textarea id="commentInput" rows="2" class="comment-input-box" placeholder="Post a review or comment on this trailer..."></textarea>
                    <button class="comment-post-btn" onclick="submitReview()">POST REVIEW</button>
                </div>

                <div style="font-size: 14px; font-weight: 700; color: var(--accent-color); border-bottom: 1px solid var(--border-glow); padding-bottom: 5px;">
                    COMMUNITY REVIEWS
                </div>

                <!-- Comments List -->
                <div class="comments-list" id="commentsList">
                    <div style="text-align: center; color: #777; font-size: 13px; padding: 20px;">Loading community reviews...</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Sound Synthesizer & Main Script -->
    <script>
        var currentVideoId = '';
        var selectedRating = 5;
        var audioEnabled = true;
        var userWatchlist = [];
        var audioCtx = null;

        function playBeep(freq, type, duration) {
            if (!audioEnabled) return;
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                var osc = audioCtx.createOscillator();
                var gain = audioCtx.createGain();
                osc.type = type || 'sine';
                osc.frequency.value = freq || 440;
                gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (duration || 0.1));
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + (duration || 0.1));
            } catch(e) {}
        }

        function toggleAudio() {
            audioEnabled = !audioEnabled;
            var btn = document.getElementById('soundToggleBtn');
            btn.textContent = audioEnabled ? '🔊' : '🔇';
            if (audioEnabled) playBeep(880, 'triangle', 0.15);
        }

        function changeGlobalTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('gamer_theme', theme);
            playBeep(600, 'sine', 0.1);
        }

        function loadFavorites() {
            fetch('api.php?action=get_favorites')
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        userWatchlist = data.favorites || [];
                        updateWatchlistUI();
                    }
                });
        }

        function updateWatchlistUI() {
            document.querySelectorAll('.videos').forEach(card => {
                var vidId = card.getAttribute('data-id');
                var favBtn = card.querySelector('.fav-btn');
                if (userWatchlist.includes(vidId)) {
                    favBtn.classList.add('active');
                } else {
                    favBtn.classList.remove('active');
                }
            });
        }

        function toggleFavorite(videoId, btn, event) {
            event.stopPropagation();
            playBeep(750, 'square', 0.1);
            var formData = new FormData();
            formData.append('action', 'toggle_favorite');
            formData.append('video_id', videoId);

            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        userWatchlist = data.favorites || [];
                        updateWatchlistUI();
                        if (currentActiveCategory === 'Watchlist') {
                            setFilter('Watchlist', document.querySelector('.cat-pill.active'));
                        }
                    }
                });
        }

        function openModal(videoId, title) {
            currentVideoId = videoId;
            document.getElementById('modalVideoTitle').textContent = title || 'Trailer Showcase';
            document.getElementById('videoPlayer').src = "https://www.youtube.com/embed/" + videoId + "?autoplay=1";
            document.getElementById('videoModal').style.display = "flex";
            playBeep(520, 'sine', 0.15);
            loadReviews(videoId);
        }

        function closeModal() {
            document.getElementById('videoModal').style.display = "none";
            document.getElementById('videoPlayer').src = "";
            currentVideoId = '';
            playBeep(350, 'sine', 0.1);
        }

        function setRating(rating) {
            selectedRating = rating;
            playBeep(400 + (rating * 100), 'triangle', 0.08);
            var stars = document.querySelectorAll('#starRatingSelector span');
            stars.forEach((s, idx) => {
                if (idx < rating) {
                    s.classList.add('gold');
                } else {
                    s.classList.remove('gold');
                }
            });
        }

        function loadReviews(videoId) {
            var commentsList = document.getElementById('commentsList');
            commentsList.innerHTML = '<div style="text-align: center; color: #777; font-size: 13px; padding: 20px;">Loading community reviews...</div>';

            fetch('api.php?action=get_reviews&video_id=' + encodeURIComponent(videoId))
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('avgRatingVal').textContent = (data.avg_rating || 5.0) + ' / 5.0';
                        document.getElementById('totalReviewsVal').textContent = (data.total_reviews || 0) + ' Gamer Reviews';

                        if (data.reviews.length > 0) {
                            commentsList.innerHTML = data.reviews.map(r => `
                                <div class="comment-item">
                                    <div class="comment-header">
                                        <span class="comment-user">👤 ${escapeHtml(r.username)}</span>
                                        <span>${'★'.repeat(r.rating)}</span>
                                    </div>
                                    <p class="comment-text">${escapeHtml(r.comment)}</p>
                                </div>
                            `).join('');
                        } else {
                            commentsList.innerHTML = '<div style="text-align: center; color: #777; font-size: 13px; padding: 20px;">No reviews yet. Be the first to leave a review!</div>';
                        }
                    }
                });
        }

        function submitReview() {
            var commentBox = document.getElementById('commentInput');
            var comment = commentBox.value.trim();
            if (!comment || !currentVideoId) return;

            playBeep(900, 'square', 0.15);
            var formData = new FormData();
            formData.append('action', 'add_review');
            formData.append('video_id', currentVideoId);
            formData.append('rating', selectedRating);
            formData.append('comment', comment);

            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        commentBox.value = '';
                        loadReviews(currentVideoId);
                    }
                });
        }

        function escapeHtml(text) {
            var map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
            return text.replace(/[&<>"']/g, function(m) { return map[m]; });
        }

        var currentActiveCategory = 'All';
        var searchDebounceTimer = null;

        function debouncedFilterVideos() {
            clearTimeout(searchDebounceTimer);
            searchDebounceTimer = setTimeout(filterVideos, 120);
        }

        function setFilter(category, btn) {
            currentActiveCategory = category;
            playBeep(650, 'sine', 0.08);
            document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterVideos();
        }

        function filterVideos() {
            var query = document.getElementById('searchInput').value.toLowerCase().trim();

            document.querySelectorAll('.videos').forEach(card => {
                var title = (card.getAttribute('data-title') || '').toLowerCase();
                var game  = (card.getAttribute('data-game') || '').toLowerCase();
                var vidId = card.getAttribute('data-id');

                var matchesSearch = title.includes(query) || game.includes(query);
                var matchesCat = true;

                if (currentActiveCategory === 'Watchlist') {
                    matchesCat = userWatchlist.includes(vidId);
                } else if (currentActiveCategory !== 'All') {
                    matchesCat = game.includes(currentActiveCategory.toLowerCase());
                }

                if (matchesSearch && matchesCat) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });

            document.querySelectorAll('.video-section-block').forEach(block => {
                var visibleCards = block.querySelectorAll('.videos[style="display: flex;"], .videos:not([style*="display: none"])');
                var totalHiddenCards = block.querySelectorAll('.videos[style*="display: none"]').length;
                var totalCards = block.querySelectorAll('.videos').length;

                if (totalHiddenCards === totalCards) {
                    block.style.display = 'none';
                } else {
                    block.style.display = 'block';
                }
            });
        }

        function updateCountdown() {
            var target = new Date("October 1, 2025 00:00:00").getTime();
            var now = new Date().getTime();
            var diff = target - now;
            if (diff < 0) diff = 0;

            var days = Math.floor(diff / (1000 * 60 * 60 * 24));
            var hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            var secs = Math.floor((diff % (1000 * 60)) / 1000);

            document.getElementById('timerDays').textContent = days;
            document.getElementById('timerHours').textContent = hours < 10 ? '0' + hours : hours;
            document.getElementById('timerMins').textContent = mins < 10 ? '0' + mins : mins;
            document.getElementById('timerSecs').textContent = secs < 10 ? '0' + secs : secs;
        }

        setInterval(updateCountdown, 1000);
        updateCountdown();

        window.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') closeModal();
        });

        document.addEventListener('DOMContentLoaded', function() {
            var savedTheme = localStorage.getItem('gamer_theme');
            if (savedTheme) {
                document.documentElement.setAttribute('data-theme', savedTheme);
                document.getElementById('themeQuickSelect').value = savedTheme;
            }
            loadFavorites();
        });
    </script>
</body>
</html>
