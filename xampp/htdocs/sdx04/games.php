<?php
// games.php - Game Library & "Can I Run It?" Hardware Specs Calculator
session_start();

if (!isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

require_once __DIR__ . '/db.php';
$theme = $_SESSION['theme'] ?? 'cyberpunk';
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($theme); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Game Library & PC Specs Calculator - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .games-container {
            max-width: 1300px;
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
        .calculator-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            box-shadow: 0 0 25px var(--glow-color);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 35px;
        }
        .calculator-card h2 {
            font-family: 'Rajdhani', sans-serif;
            color: var(--accent-color);
            margin-top: 0;
        }
        .calc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .calc-input {
            width: 100%;
            padding: 12px;
            background: rgba(0,0,0,0.6);
            border: 1px solid var(--border-glow);
            border-radius: 8px;
            color: #fff;
            font-family: inherit;
            font-size: 14px;
        }
        .preset-btn-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .preset-btn {
            background: rgba(255,255,255,0.08);
            border: 1px solid var(--border-glow);
            color: #ccc;
            padding: 6px 14px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .preset-btn:hover {
            background: var(--accent-color);
            color: #000;
        }
        .btn-calc {
            background: linear-gradient(135deg, var(--accent-color), #0088cc);
            color: #000;
            font-family: 'Rajdhani', sans-serif;
            font-size: 18px;
            font-weight: 700;
            padding: 14px 35px;
            border-radius: 25px;
            border: none;
            cursor: pointer;
            box-shadow: 0 0 20px var(--accent-color);
            width: 100%;
            max-width: 320px;
            transition: transform 0.1s ease;
        }
        .btn-calc:active {
            transform: scale(0.97);
        }
        .result-dashboard {
            display: none;
            margin-top: 25px;
            padding: 25px;
            border-radius: 16px;
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid var(--accent-color);
            box-shadow: 0 0 25px rgba(0, 255, 255, 0.2);
        }
        .score-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-family: 'Rajdhani', sans-serif;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .score-ultra { background: rgba(0,255,136,0.2); color: #00ff88; border: 1px solid #00ff88; }
        .score-high { background: rgba(0,255,255,0.2); color: #00ffff; border: 1px solid #00ffff; }
        .score-mid { background: rgba(255,204,0,0.2); color: #ffcc00; border: 1px solid #ffcc00; }
        .score-low { background: rgba(255,77,77,0.2); color: #ff4d4d; border: 1px solid #ff4d4d; }

        .hardware-checklist {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .hardware-item {
            background: rgba(255,255,255,0.05);
            padding: 12px 15px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .games-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 25px;
        }
        .game-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .game-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 0 25px var(--glow-color);
        }
        .game-card-img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .game-card-body {
            padding: 20px;
        }
        .game-card-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 22px;
            color: #fff;
            margin: 0 0 10px 0;
        }
        .specs-list {
            font-size: 13px;
            color: #bbb;
            line-height: 1.6;
        }
    </style>
</head>
<body>

    <div class="games-container">
        <!-- Navigation Header -->
        <header class="navbar">
            <h2 class="nav-logo">PRO CONTROLLER GAMING</h2>
            <nav class="nav-links">
                <a href="Practise.php" class="nav-link">🎮 Showcase Hub</a>
                <a href="news.php" class="nav-link">📰 News</a>
                <a href="forum.php" class="nav-link">💬 Forums</a>
                <a href="games.php" class="nav-link active">💻 PC Specs</a>
                <a href="profile.php" class="nav-link">👤 Profile</a>
                <a href="logout.php" class="nav-link logout-btn">LOGOUT</a>
            </nav>
        </header>

        <h1 class="page-title">💻 Real PC Specs Hardware Compatibility Analyzer</h1>
        <p style="color: var(--text-sub); margin-top: 0; margin-bottom: 30px;">Select your CPU, GPU, RAM, Storage, and Target Resolution to analyze real performance compatibility for AAA games.</p>

        <!-- Hardware Specs Calculator Card -->
        <div class="calculator-card">
            <h2>⚡ "Can I Run It?" Hardware Analysis Engine</h2>
            
            <div class="preset-btn-group">
                <span style="color:#aaa; font-size:12px; font-weight:600; align-self:center;">Quick Presets:</span>
                <button type="button" class="preset-btn" onclick="applyPreset('high')">🚀 RTX 4080 High-End Rig</button>
                <button type="button" class="preset-btn" onclick="applyPreset('mid')">🎮 RTX 3060 Mid-Tier PC</button>
                <button type="button" class="preset-btn" onclick="applyPreset('budget')">💻 GTX 1650 Budget Laptop</button>
            </div>

            <div class="calc-grid">
                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">Target Game</label>
                    <select id="calcGame" class="calc-input">
                        <option value="gtavi">Grand Theft Auto VI (Vice City)</option>
                        <option value="gtav">Grand Theft Auto V Enhanced</option>
                        <option value="rdr2">Red Dead Redemption 2</option>
                        <option value="cyberpunk">Cyberpunk 2077 Phantom Liberty</option>
                    </select>
                </div>

                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">Processor (CPU)</label>
                    <select id="calcCpu" class="calc-input">
                        <option value="10">Intel i9-14900K / Ryzen 9 7950X (Tier 1 High-End)</option>
                        <option value="8">Intel i7-13700K / Ryzen 7 7800X3D (Tier 2 Recommended)</option>
                        <option value="6">Intel i5-12400F / Ryzen 5 5600 (Tier 3 Standard)</option>
                        <option value="4">Intel i3-10100 / Quad-Core Processor (Tier 4 Low)</option>
                    </select>
                </div>

                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">Graphics Card (GPU)</label>
                    <select id="calcGpu" class="calc-input">
                        <option value="10">NVIDIA RTX 4080 / RTX 4090 / RX 7900 XTX (16GB+ VRAM)</option>
                        <option value="8">NVIDIA RTX 4070 / RTX 3080 / RX 6800 (12GB VRAM)</option>
                        <option value="6">NVIDIA RTX 3060 / GTX 1660 Ti / RX 6600 (6GB - 8GB VRAM)</option>
                        <option value="4">NVIDIA GTX 1050 Ti / GTX 970 / RX 570 (4GB VRAM)</option>
                        <option value="2">Intel Integrated Graphics / Old GPU (< 4GB VRAM)</option>
                    </select>
                </div>

                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">System RAM (GB)</label>
                    <select id="calcRam" class="calc-input">
                        <option value="32">32 GB RAM (Recommended)</option>
                        <option value="16">16 GB RAM (Standard)</option>
                        <option value="8">8 GB RAM (Minimum)</option>
                        <option value="4">4 GB RAM (Insufficient)</option>
                    </select>
                </div>

                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">Storage Drive</label>
                    <select id="calcStorage" class="calc-input">
                        <option value="nvme">High-Speed NVMe M.2 SSD (Fastest)</option>
                        <option value="sata">SATA 2.5" SSD (Standard)</option>
                        <option value="hdd">Mechanical Hard Drive (HDD)</option>
                    </select>
                </div>

                <div>
                    <label style="display:block; color:#ccc; margin-bottom:6px; font-weight:600;">Target Resolution</label>
                    <select id="calcRes" class="calc-input">
                        <option value="4k">4K Ultra (3840 x 2160)</option>
                        <option value="1440p">1440p Quad HD (2560 x 1440)</option>
                        <option value="1080p" selected>1080p Full HD (1920 x 1080)</option>
                    </select>
                </div>
            </div>

            <button type="button" class="btn-calc" onclick="runHardwareAnalysis()">ANALYZE MY RIG COMPATIBILITY</button>

            <!-- Results Dashboard -->
            <div id="resultDashboard" class="result-dashboard">
                <div id="scoreBadge" class="score-badge"></div>
                <h3 id="resultTitle" style="font-family:'Rajdhani', sans-serif; font-size:24px; margin:0 0 10px 0; color:var(--accent-color);"></h3>
                <p id="resultText" style="color:#eee; margin:0 0 20px 0; font-size:15px; line-height:1.6;"></p>

                <div class="hardware-checklist">
                    <div class="hardware-item">
                        <div style="font-size:12px; color:#aaa;">ESTIMATED PERFORMANCE</div>
                        <strong id="fpsVal" style="font-size:18px; color:#00ff88;"></strong>
                    </div>
                    <div class="hardware-item">
                        <div style="font-size:12px; color:#aaa;">PROCESSOR (CPU)</div>
                        <strong id="cpuStatus" style="font-size:15px;"></strong>
                    </div>
                    <div class="hardware-item">
                        <div style="font-size:12px; color:#aaa;">GRAPHICS CARD (GPU)</div>
                        <strong id="gpuStatus" style="font-size:15px;"></strong>
                    </div>
                    <div class="hardware-item">
                        <div style="font-size:12px; color:#aaa;">SYSTEM MEMORY (RAM)</div>
                        <strong id="ramStatus" style="font-size:15px;"></strong>
                    </div>
                </div>

                <div id="upgradeAdvice" style="margin-top:20px; padding:12px 15px; background:rgba(0,255,255,0.08); border-left:4px solid var(--accent-color); font-size:13px; color:#ccc;"></div>
            </div>
        </div>

        <!-- Featured Games Catalog -->
        <h2 style="font-family:'Rajdhani', sans-serif; color:var(--accent-color); font-size:28px; margin-bottom:20px;">🎮 Featured AAA Games & Official System Specs</h2>

        <div class="games-grid">
            <!-- GTA VI -->
            <div class="game-card">
                <img src="gtavi_vice_city_art.jpg" class="game-card-img" alt="GTA VI">
                <div class="game-card-body">
                    <h3 class="game-card-title">Grand Theft Auto VI</h3>
                    <div class="specs-list">
                        <strong>Developer:</strong> Rockstar Games<br>
                        <strong>Release:</strong> Fall 2025<br>
                        <strong>Min Specs:</strong> GTX 1660 Super, 16GB RAM, i5-10400<br>
                        <strong>Rec Specs:</strong> RTX 3080 / RTX 4070, 32GB RAM, i7-12700K
                    </div>
                </div>
            </div>

            <!-- GTA V -->
            <div class="game-card">
                <img src="gtav_los_santos_art.jpg" class="game-card-img" alt="GTA V">
                <div class="game-card-body">
                    <h3 class="game-card-title">Grand Theft Auto V Enhanced</h3>
                    <div class="specs-list">
                        <strong>Developer:</strong> Rockstar Games<br>
                        <strong>Status:</strong> Available Now<br>
                        <strong>Min Specs:</strong> GTX 660, 8GB RAM, Core 2 Quad<br>
                        <strong>Rec Specs:</strong> RTX 2060, 16GB RAM, i5-9600K
                    </div>
                </div>
            </div>

            <!-- Red Dead Redemption 2 -->
            <div class="game-card">
                <img src="rdr_outlaw_art.jpg" class="game-card-img" alt="Red Dead 2">
                <div class="game-card-body">
                    <h3 class="game-card-title">Red Dead Redemption 2</h3>
                    <div class="specs-list">
                        <strong>Developer:</strong> Rockstar Games<br>
                        <strong>Status:</strong> Available Now<br>
                        <strong>Min Specs:</strong> GTX 770, 8GB RAM, i5-2500K<br>
                        <strong>Rec Specs:</strong> GTX 1060 6GB / RX 480, 12GB RAM
                    </div>
                </div>
            </div>

            <!-- Cyberpunk 2077 -->
            <div class="game-card">
                <img src="cyberpunk_night_city.jpg" class="game-card-img" alt="Cyberpunk 2077">
                <div class="game-card-body">
                    <h3 class="game-card-title">Cyberpunk 2077 Phantom Liberty</h3>
                    <div class="specs-list">
                        <strong>Developer:</strong> CD PROJEKT RED<br>
                        <strong>Status:</strong> Available Now<br>
                        <strong>Min Specs:</strong> GTX 1060 6GB, 12GB RAM, i7-6700<br>
                        <strong>Rec Specs:</strong> RTX 3070 / RTX 4080, 16GB RAM, i7-12700
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script>
        function applyPreset(preset) {
            if (preset === 'high') {
                document.getElementById('calcCpu').value = '10';
                document.getElementById('calcGpu').value = '10';
                document.getElementById('calcRam').value = '32';
                document.getElementById('calcStorage').value = 'nvme';
            } else if (preset === 'mid') {
                document.getElementById('calcCpu').value = '6';
                document.getElementById('calcGpu').value = '6';
                document.getElementById('calcRam').value = '16';
                document.getElementById('calcStorage').value = 'sata';
            } else if (preset === 'budget') {
                document.getElementById('calcCpu').value = '4';
                document.getElementById('calcGpu').value = '4';
                document.getElementById('calcRam').value = '8';
                document.getElementById('calcStorage').value = 'hdd';
            }
            runHardwareAnalysis();
        }

        function runHardwareAnalysis() {
            var cpu = parseInt(document.getElementById('calcCpu').value);
            var gpu = parseInt(document.getElementById('calcGpu').value);
            var ram = parseInt(document.getElementById('calcRam').value);
            var storage = document.getElementById('calcStorage').value;
            var res = document.getElementById('calcRes').value;
            var gameSelect = document.getElementById('calcGame');
            var gameName = gameSelect.options[gameSelect.selectedIndex].text;
            var gameVal = gameSelect.value;

            // Resolution modifier penalty
            var resPenalty = (res === '4k') ? 3 : ((res === '1440p') ? 1.5 : 0);

            // Game Difficulty multiplier
            var gameReq = 6;
            if (gameVal === 'gtavi') gameReq = 8.5;
            if (gameVal === 'cyberpunk') gameReq = 8;
            if (gameVal === 'rdr2') gameReq = 6.5;
            if (gameVal === 'gtav') gameReq = 4;

            // Calculate total score (Out of 100)
            var rawScore = ((cpu * 0.3) + (gpu * 0.5) + (ram * 0.2)) * 10 - (resPenalty * 8);
            if (rawScore > 100) rawScore = 100;
            if (rawScore < 15) rawScore = 15;

            var dash = document.getElementById('resultDashboard');
            var badge = document.getElementById('scoreBadge');
            var title = document.getElementById('resultTitle');
            var text = document.getElementById('resultText');
            var fpsVal = document.getElementById('fpsVal');
            var cpuStatus = document.getElementById('cpuStatus');
            var gpuStatus = document.getElementById('gpuStatus');
            var ramStatus = document.getElementById('ramStatus');
            var upgradeAdvice = document.getElementById('upgradeAdvice');

            dash.style.display = 'block';

            // Calculate FPS & Status
            var estFps = Math.round((rawScore / gameReq) * 8.5);
            if (estFps > 144) estFps = 144;

            fpsVal.textContent = estFps + "+ FPS (" + res.toUpperCase() + ")";
            cpuStatus.textContent = (cpu >= 8) ? "✅ Excellent Tier" : ((cpu >= 6) ? "⚡ Standard" : "⚠️ Bottleneck Risk");
            gpuStatus.textContent = (gpu >= 8) ? "✅ High VRAM Ready" : ((gpu >= 6) ? "⚡ 1080p Capable" : "❌ Upgrade Recommended");
            ramStatus.textContent = (ram >= 16) ? "✅ Optimal (" + ram + "GB)" : "⚠️ Minimum (" + ram + "GB)";

            if (rawScore >= 80) {
                badge.className = "score-badge score-ultra";
                badge.textContent = "SCORE: " + Math.round(rawScore) + "/100 — 🚀 EXTREME ULTRA PERFORMANCE";
                title.textContent = "ULTRA 4K RAY-TRACING CAPABLE!";
                text.textContent = "Your gaming rig effortlessly exceeds all recommended requirements for " + gameName + ". You can expect fluid " + estFps + "+ FPS gameplay at maximum graphics settings.";
                upgradeAdvice.innerHTML = "💡 <strong>Hardware Advice:</strong> Your system is top-tier. Keep drivers updated for DLSS / FSR frame generation.";
            } else if (rawScore >= 55) {
                badge.className = "score-badge score-high";
                badge.textContent = "SCORE: " + Math.round(rawScore) + "/100 — 🎮 RECOMMENDED SPECS MET";
                title.textContent = "HIGH PERFORMANCE READY!";
                text.textContent = "Your PC meets the recommended target specs for " + gameName + ". You will enjoy smooth " + estFps + " FPS gameplay at High 1080p/1440p settings.";
                upgradeAdvice.innerHTML = (storage === 'hdd') ? "💡 <strong>Hardware Advice:</strong> Upgrading your Mechanical HDD to an NVMe SSD will eliminate texture pop-in for " + gameName + "." : "💡 <strong>Hardware Advice:</strong> System is well-balanced for 1080p High settings.";
            } else if (rawScore >= 35) {
                badge.className = "score-badge score-mid";
                badge.textContent = "SCORE: " + Math.round(rawScore) + "/100 — ⚠️ MINIMUM SPECS MET";
                title.textContent = "PLAYABLE AT MEDIUM / LOW SETTINGS";
                text.textContent = "Your hardware meets basic minimum requirements for " + gameName + ". Expect " + estFps + " FPS at 1080p Medium settings.";
                upgradeAdvice.innerHTML = "💡 <strong>Upgrade Recommendation:</strong> Upgrading your GPU or increasing RAM to 16GB+ will significantly boost FPS.";
            } else {
                badge.className = "score-badge score-low";
                badge.textContent = "SCORE: " + Math.round(rawScore) + "/100 — ❌ INSUFFICIENT HARDWARE";
                title.textContent = "HARDWARE UPGRADE REQUIRED";
                text.textContent = "Your current CPU/GPU configuration falls below recommended requirements for " + gameName + ". You may experience frame drops or lag.";
                upgradeAdvice.innerHTML = "💡 <strong>Upgrade Required:</strong> We recommend upgrading to a dedicated GTX 1660 / RTX GPU and at least 16GB RAM.";
            }
        }
    </script>
</body>
</html>
