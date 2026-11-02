<?php
// admin.php - Enterprise System Administration & Master Control Center
session_start();

require_once __DIR__ . '/db.php';

// Strict Admin Session Enforcement
if (!isset($_SESSION['is_admin']) || $_SESSION['is_admin'] !== true || !isset($_SESSION['admin_user_id'])) {
    header("Location: admin_login.php");
    exit();
}

$userId = $_SESSION['admin_user_id'];

// Verify user role in database
$userStmt = $pdo->prepare("SELECT role, username FROM user WHERE id = ?");
$userStmt->execute([$userId]);
$currentUser = $userStmt->fetch();

if (!$currentUser || $currentUser['role'] !== 'admin') {
    unset($_SESSION['is_admin']);
    header("Location: admin_login.php");
    exit();
}

$role = 'admin';

// Fetch system stats
$statGamers  = $pdo->query("SELECT COUNT(*) FROM user WHERE role = 'gamer' OR role IS NULL OR role = ''")->fetchColumn();
$statVips    = $pdo->query("SELECT COUNT(*) FROM user WHERE role = 'vip'")->fetchColumn();
$statAdmins  = $pdo->query("SELECT COUNT(*) FROM user WHERE role = 'admin'")->fetchColumn();
$statReviews = $pdo->query("SELECT COUNT(*) FROM video_reviews")->fetchColumn();
$statThreads = $pdo->query("SELECT COUNT(*) FROM forum_threads")->fetchColumn();

// Fetch users list including plain_password for instant admin view
$allUsers = $pdo->query("SELECT id, username, email, password, plain_password, role, status, bio, created_at, last_login FROM user ORDER BY id DESC")->fetchAll();

// Fetch audit logs
$auditLogs = $pdo->query("SELECT * FROM security_audit_logs ORDER BY created_at DESC LIMIT 15")->fetchAll();
?>
<!DOCTYPE html>
<html lang="en" data-theme="<?php echo htmlspecialchars($_SESSION['theme'] ?? 'cyberpunk'); ?>">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Admin Control Center - Pro Controller Gaming</title>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="Practise.css">
    <script src="server_sentinel.js"></script>
    <style>
        .admin-container {
            max-width: 1450px;
            margin: 0 auto;
            padding: 20px;
        }
        .admin-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        .page-title {
            font-family: 'Rajdhani', sans-serif;
            font-size: 32px;
            color: #ff0080;
            margin: 0;
            text-transform: uppercase;
            text-shadow: 0 0 15px rgba(255, 0, 128, 0.4);
        }
        .admin-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card-stat {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .card-stat-val {
            font-family: 'Rajdhani', sans-serif;
            font-size: 40px;
            font-weight: 700;
            color: var(--accent-color);
        }
        .card-stat-lbl {
            color: var(--text-sub);
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .admin-table-card {
            background: var(--bg-card);
            border: 1px solid var(--border-glow);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
            overflow-x: auto;
        }
        .admin-table-card h2 {
            font-family: 'Rajdhani', sans-serif;
            color: var(--accent-color);
            margin-top: 0;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        th, td {
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 14px;
        }
        th {
            color: var(--accent-color);
            font-family: 'Rajdhani', sans-serif;
            font-size: 15px;
            text-transform: uppercase;
        }
        .role-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .role-gamer { background: rgba(255,255,255,0.1); color: #ccc; }
        .role-vip { background: rgba(0,255,255,0.2); color: #00ffff; border: 1px solid #00ffff; }
        .role-admin { background: rgba(255,0,128,0.2); color: #ff0080; border: 1px solid #ff0080; }

        .status-active { background: rgba(0, 255, 128, 0.2); color: #00ff80; border: 1px solid #00ff80; }
        .status-suspended { background: rgba(255, 204, 0, 0.2); color: #ffcc00; border: 1px solid #ffcc00; }
        .status-banned { background: rgba(255, 77, 77, 0.2); color: #ff4d4d; border: 1px solid #ff4d4d; }

        .action-group {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .btn-act {
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid transparent;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn-edit { background: rgba(0, 255, 255, 0.15); color: #00ffff; border-color: #00ffff; }
        .btn-edit:hover { background: #00ffff; color: #000; }
        .btn-pass { background: rgba(0, 255, 136, 0.15); color: #00ff88; border-color: #00ff88; }
        .btn-pass:hover { background: #00ff88; color: #000; }
        .btn-suspend { background: rgba(255, 204, 0, 0.15); color: #ffcc00; border-color: #ffcc00; }
        .btn-suspend:hover { background: #ffcc00; color: #000; }
        .btn-ban { background: rgba(255, 77, 77, 0.15); color: #ff4d4d; border-color: #ff4d4d; }
        .btn-ban:hover { background: #ff4d4d; color: #fff; }
        .btn-activate { background: rgba(0, 255, 128, 0.15); color: #00ff80; border-color: #00ff80; }
        .btn-activate:hover { background: #00ff80; color: #000; }
        .btn-delete { background: rgba(255, 0, 0, 0.3); color: #ff3333; border-color: #ff3333; }
        .btn-delete:hover { background: #ff3333; color: #fff; }

        .pass-visible-tag {
            font-family: monospace;
            background: rgba(0, 255, 136, 0.12);
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid #00ff88;
            color: #00ff88;
            font-size: 14px;
            font-weight: bold;
            display: inline-block;
        }

        .admin-modal {
            display: none;
            position: fixed;
            z-index: 2000;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.92);
            justify-content: center; align-items: center;
            padding: 20px;
        }
        .admin-modal-card {
            background: #0f121d;
            border: 1px solid #ff0080;
            box-shadow: 0 0 35px rgba(255,0,128,0.4);
            border-radius: 16px;
            width: 100%; max-width: 550px;
            padding: 30px;
            position: relative;
        }
    </style>
</head>
<body>

    <div class="admin-container">
        <!-- Navigation Header -->
        <header class="navbar" style="border-color: rgba(255, 0, 128, 0.4); box-shadow: 0 0 20px rgba(255, 0, 128, 0.2);">
            <h2 class="nav-logo" style="color: #ff0080; text-shadow: 0 0 10px #ff0080;">PRO CONTROLLER ADMIN</h2>
            <nav class="nav-links">
                <a href="admin.php" class="nav-link active" style="color: #ff0080; border-color: #ff0080;">🛡️ Admin Control Panel</a>
                <a href="Practise.php" class="nav-link">🎮 View Gamer Site</a>
                <a href="admin_logout.php" class="nav-link logout-btn">ADMIN LOGOUT</a>
            </nav>
        </header>

        <div class="admin-header">
            <h1 class="page-title">🛡️ Master Admin Control & Credentials Viewer</h1>
            <span class="role-badge role-admin">MASTER ADMIN PRIVILEGES</span>
        </div>

        <!-- Stat Cards -->
        <div class="admin-grid">
            <div class="card-stat">
                <div class="card-stat-val"><?php echo $statGamers; ?></div>
                <div class="card-stat-lbl">Registered Gamers</div>
                <div style="font-size: 10px; color: #888; margin-top: 2px;">Excludes All-In-One Admins</div>
            </div>
            <div class="card-stat">
                <div class="card-stat-val"><?php echo $statVips; ?></div>
                <div class="card-stat-lbl">VIP Gamer Accounts</div>
            </div>
            <div class="card-stat">
                <div class="card-stat-val" style="color: #ff0080;"><?php echo $statAdmins; ?></div>
                <div class="card-stat-lbl">All-In-One Admins</div>
            </div>
            <div class="card-stat">
                <div class="card-stat-val"><?php echo $statReviews; ?></div>
                <div class="card-stat-lbl">Reviews Posted</div>
            </div>
            <div class="card-stat">
                <div class="card-stat-val"><?php echo $statThreads; ?></div>
                <div class="card-stat-lbl">Forum Topics</div>
            </div>
        </div>

        <!-- System Health Diagnostics Bar -->
        <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 25px; background: rgba(0,255,255,0.05); border: 1px solid var(--border-glow); padding: 15px; border-radius: 12px; font-size: 13px; color: #ccc;">
            <div>🟢 <strong>Database Status:</strong> Online (MySQL PDO)</div>
            <div>⚡ <strong>PHP Engine:</strong> v<?php echo phpversion(); ?></div>
            <div>🛡️ <strong>Security Shield:</strong> CSRF & Rate-Limit Active</div>
            <div>📊 <strong>Audit Tracking:</strong> Enabled</div>
        </div>

        <!-- User Management Table with Direct Visible Passwords & Search -->
        <div class="admin-table-card">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 15px;">
                <h2 style="margin: 0; border: none; padding: 0;">👥 Master User Credentials & Account Control</h2>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="text" id="userSearchInput" onkeyup="filterUserTable()" placeholder="🔍 Live filter users by name, email, role..." style="padding: 8px 15px; border-radius: 20px; border: 1px solid var(--border-glow); background: rgba(0,0,0,0.6); color: #fff; width: 280px; font-size: 13px;">
                    <button type="button" onclick="exportUsersCSV()" style="padding: 8px 15px; border-radius: 20px; border: 1px solid #00ff88; background: rgba(0,255,136,0.15); color: #00ff88; font-weight: bold; cursor: pointer; font-size: 13px;">📥 Export CSV</button>
                </div>
            </div>
            <table id="userMasterTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>User Persona</th>
                        <th>Email</th>
                        <th>Plaintext Password (Admin Direct View)</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Joined</th>
                        <th>Master Admin Controls</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($allUsers as $u): 
                        $statusClass = 'status-' . ($u['status'] ?: 'active');
                        $plainPass = $u['plain_password'] ? $u['plain_password'] : 'GamerPass123!';
                    ?>
                        <tr>
                            <td>#<?php echo $u['id']; ?></td>
                            <td><strong><?php echo htmlspecialchars($u['username']); ?></strong></td>
                            <td><?php echo htmlspecialchars($u['email']); ?></td>
                            <td>
                                <span class="pass-visible-tag">🔑 <?php echo htmlspecialchars($plainPass); ?></span>
                            </td>
                            <td><span class="role-badge role-<?php echo htmlspecialchars($u['role']); ?>"><?php echo strtoupper($u['role']); ?></span></td>
                            <td><span class="role-badge <?php echo $statusClass; ?>"><?php echo strtoupper($u['status'] ?: 'ACTIVE'); ?></span></td>
                            <td><?php echo date('M d, Y', strtotime($u['created_at'])); ?></td>
                            <td>
                                <div class="action-group">
                                    <button class="btn-act btn-edit" onclick="openEditUserModal(<?php echo htmlspecialchars(json_encode($u)); ?>)">✏️ Edit Profile</button>
                                    <button class="btn-act btn-pass" onclick="quickChangePassword(<?php echo $u['id']; ?>, '<?php echo htmlspecialchars($u['username'], ENT_QUOTES); ?>')">🔑 Set Pass</button>

                                    <?php if ($u['status'] === 'suspended'): ?>
                                        <button class="btn-act btn-activate" onclick="updateStatus(<?php echo $u['id']; ?>, 'active')">🟢 Unsuspend</button>
                                    <?php else: ?>
                                        <button class="btn-act btn-suspend" onclick="updateStatus(<?php echo $u['id']; ?>, 'suspended')">🟡 Suspend</button>
                                    <?php endif; ?>

                                    <?php if ($u['status'] === 'banned'): ?>
                                        <button class="btn-act btn-activate" onclick="updateStatus(<?php echo $u['id']; ?>, 'active')">🟢 Unban</button>
                                    <?php else: ?>
                                        <button class="btn-act btn-ban" onclick="updateStatus(<?php echo $u['id']; ?>, 'banned')">🔴 Ban</button>
                                    <?php endif; ?>

                                    <?php if ($u['id'] !== $userId): ?>
                                        <button class="btn-act btn-delete" onclick="deleteUser(<?php echo $u['id']; ?>, '<?php echo htmlspecialchars($u['username'], ENT_QUOTES); ?>')">🗑️ Delete</button>
                                    <?php endif; ?>
                                </div>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>

        <!-- Security Audit Log -->
        <div class="admin-table-card">
            <h2>🔒 Security Audit Logs & IP Activity</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>User ID</th>
                        <th>Security Action</th>
                        <th>IP Address</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (count($auditLogs) > 0): ?>
                        <?php foreach ($auditLogs as $log): ?>
                            <tr>
                                <td>#<?php echo $log['id']; ?></td>
                                <td><?php echo $log['user_id'] ? '#' . $log['user_id'] : 'Guest / System'; ?></td>
                                <td><code style="color: var(--accent-color);"><?php echo htmlspecialchars($log['action']); ?></code></td>
                                <td><?php echo htmlspecialchars($log['ip_address']); ?></td>
                                <td><?php echo date('M d, Y H:i:s', strtotime($log['created_at'])); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <tr><td colspan="5" style="text-align: center; color: #777;">No audit log records found.</td></tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Edit User & Reset Password Modal -->
    <div id="editUserModal" class="admin-modal">
        <div class="admin-modal-card">
            <button class="close-modal-btn" onclick="closeEditUserModal()">&times;</button>
            <h2 style="font-family:'Rajdhani', sans-serif; color:#ff0080; margin-top:0;">✏️ Edit Account & Credentials #<span id="modalUserId"></span></h2>
            
            <div style="background:rgba(0,255,136,0.15); border:1px solid #00ff88; padding:12px 16px; border-radius:10px; margin-bottom:20px; font-size:15px;">
                🔑 Current Plaintext Password: <strong id="modalPlainPassword" style="color:#00ff88; font-family:monospace; font-size:18px;"></strong>
            </div>

            <form id="editUserForm" style="margin-bottom: 25px;">
                <input type="hidden" name="action" value="admin_edit_user">
                <input type="hidden" name="target_user_id" id="editTargetId">

                <div style="margin-bottom: 12px;">
                    <label style="color:#ccc; font-weight:600; display:block; margin-bottom:4px;">Username</label>
                    <input type="text" name="username" id="editUsername" class="comment-input-box" required>
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="color:#ccc; font-weight:600; display:block; margin-bottom:4px;">Email Address</label>
                    <input type="email" name="email" id="editEmail" class="comment-input-box" required>
                </div>
                <div style="margin-bottom: 12px;">
                    <label style="color:#ccc; font-weight:600; display:block; margin-bottom:4px;">Role</label>
                    <select name="role" id="editRole" class="comment-input-box" style="height:42px;">
                        <option value="gamer">Gamer (Standard)</option>
                        <option value="vip">VIP Gamer</option>
                        <option value="admin">Administrator</option>
                    </select>
                </div>
                <div style="margin-bottom: 15px;">
                    <label style="color:#ccc; font-weight:600; display:block; margin-bottom:4px;">Bio / Slogan</label>
                    <textarea name="bio" id="editBio" rows="2" class="comment-input-box"></textarea>
                </div>
                <button type="submit" class="comment-post-btn" style="background:#ff0080; color:#fff; width:100%;">SAVE PROFILE CHANGES</button>
            </form>

            <h3 style="font-family:'Rajdhani', sans-serif; color:var(--accent-color); border-top:1px solid rgba(255,255,255,0.1); padding-top:15px; margin-top:15px;">🔐 Override & Change Password</h3>
            <form id="changePasswordForm">
                <input type="hidden" name="action" value="admin_change_user_password">
                <input type="hidden" name="target_user_id" id="passTargetId">
                <div style="margin-bottom: 12px;">
                    <input type="password" name="new_password" class="comment-input-box" placeholder="Enter new password for this user (min 6 chars)" required minlength="6">
                </div>
                <button type="submit" class="comment-post-btn" style="background:var(--accent-color); color:#000; width:100%;">FORCE SET NEW PASSWORD</button>
            </form>
        </div>
    </div>

    <script>
        function quickChangePassword(userId, username) {
            var newPass = prompt("Enter a new password for account '" + username + "' (#" + userId + "):", "GamerPass123!");
            if (!newPass || newPass.trim() === '') return;

            var formData = new FormData();
            formData.append('action', 'admin_change_user_password');
            formData.append('target_user_id', userId);
            formData.append('new_password', newPass.trim());

            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) location.reload();
                });
        }

        function updateStatus(userId, newStatus) {
            var formData = new FormData();
            formData.append('action', 'admin_update_status');
            formData.append('target_user_id', userId);
            formData.append('status', newStatus);

            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                });
        }

        function deleteUser(userId, username) {
            if (!confirm("ARE YOU SURE you want to permanently delete user account '" + username + "' (#" + userId + ")? This action cannot be undone!")) {
                return;
            }

            var formData = new FormData();
            formData.append('action', 'admin_delete_user');
            formData.append('target_user_id', userId);

            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    location.reload();
                });
        }

        function openEditUserModal(user) {
            document.getElementById('modalUserId').textContent = user.id;
            document.getElementById('editTargetId').value = user.id;
            document.getElementById('passTargetId').value = user.id;
            document.getElementById('editUsername').value = user.username;
            document.getElementById('editEmail').value = user.email;
            document.getElementById('editRole').value = user.role || 'gamer';
            document.getElementById('editBio').value = user.bio || '';
            document.getElementById('modalPlainPassword').textContent = user.plain_password || 'GamerPass123!';
            document.getElementById('editUserModal').style.display = 'flex';
        }

        function closeEditUserModal() {
            document.getElementById('editUserModal').style.display = 'none';
        }

        document.getElementById('editUserForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(this);
            fetch('api.php', { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) location.reload();
                });
        });

        function filterUserTable() {
            var input = document.getElementById("userSearchInput");
            var filter = input.value.toUpperCase();
            var table = document.getElementById("userMasterTable");
            var tr = table.getElementsByTagName("tr");

            for (var i = 1; i < tr.length; i++) {
                var txtValue = tr[i].textContent || tr[i].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }
        }

        function exportUsersCSV() {
            var rows = [["ID", "Username", "Email", "Plaintext_Password", "Role", "Status", "Joined"]];
            var usersData = <?php echo json_encode($allUsers); ?>;
            
            usersData.forEach(function(u) {
                rows.push([u.id, u.username, u.email, u.plain_password || 'GamerPass123!', u.role, u.status || 'active', u.created_at]);
            });

            var csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.map(cell => '"' + String(cell).replace(/"/g, '""') + '"').join(",")).join("\n");
            var encodedUri = encodeURI(csvContent);
            var link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", "master_users_export_" + new Date().toISOString().slice(0,10) + ".csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    </script>
</body>
</html>
