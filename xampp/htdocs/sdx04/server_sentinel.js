/* server_sentinel.js - Enterprise Real-Time Server & Network Interceptor System */
(function() {
    'use strict';

    var isServerDown = false;
    var reconnectTimer = null;
    var countdownSecs = 5;

    // Inject System Error HUD Overlay DOM
    function injectServerDownOverlay() {
        if (document.getElementById('serverDownModal')) return;

        var modalHTML = `
        <div id="serverDownModal" style="display:none; position:fixed; z-index:99999; top:0; left:0; width:100%; height:100%; background:rgba(5, 6, 10, 0.94); backdrop-filter:blur(15px); justify-content:center; align-items:center; font-family:'Inter', sans-serif;">
            <div style="background:#111420; border:2px solid #ff3366; box-shadow:0 0 45px rgba(255, 51, 102, 0.5); border-radius:20px; width:90%; max-width:520px; padding:35px; text-align:center; position:relative; animation:pulseModal 2s infinite ease-in-out;">
                <div style="font-size:55px; margin-bottom:15px; text-shadow:0 0 20px #ff3366;">⚡</div>
                <h2 style="font-family:'Rajdhani', sans-serif; font-size:28px; color:#ff3366; margin:0 0 10px 0; text-transform:uppercase; letter-spacing:1px;">SERVER UNREACHABLE</h2>
                <p style="color:#ffffff; font-size:15px; line-height:1.6; margin-bottom:20px;">
                    Something went wrong or the server connection was lost.<br>
                    <span style="color:#a0aec0; font-size:13px;">Please check your network or ensure the local web server is running.</span>
                </p>
                <div style="background:rgba(255, 51, 102, 0.1); border:1px solid rgba(255, 51, 102, 0.3); padding:12px; border-radius:10px; margin-bottom:25px; font-size:13px; color:#ff8099;">
                    🔄 Automatic reconnection attempt in <strong id="sentinelCountdown" style="color:#ffffff; font-size:16px;">5</strong> seconds...
                </div>
                <button type="button" onclick="window.ServerSentinel.retryConnection()" style="background:linear-gradient(135deg, #ff3366, #e60039); color:#ffffff; font-weight:700; border:none; padding:12px 30px; border-radius:25px; font-size:14px; cursor:pointer; text-transform:uppercase; box-shadow:0 0 20px rgba(255,51,102,0.6); transition:all 0.2s;">
                    🔄 RETRY CONNECTION NOW
                </button>
            </div>
        </div>
        <style>
            @keyframes pulseModal {
                0% { box-shadow: 0 0 25px rgba(255, 51, 102, 0.4); }
                50% { box-shadow: 0 0 50px rgba(255, 51, 102, 0.8); }
                100% { box-shadow: 0 0 25px rgba(255, 51, 102, 0.4); }
            }
        </style>`;

        var container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container.firstElementChild);
    }

    function showServerDownHUD(reason) {
        if (isServerDown) return;
        isServerDown = true;
        injectServerDownOverlay();

        var modal = document.getElementById('serverDownModal');
        if (modal) modal.style.display = 'flex';

        startReconnectCountdown();
    }

    function hideServerDownHUD() {
        if (!isServerDown) return;
        isServerDown = false;

        var modal = document.getElementById('serverDownModal');
        if (modal) modal.style.display = 'none';

        if (reconnectTimer) clearInterval(reconnectTimer);
    }

    function startReconnectCountdown() {
        countdownSecs = 5;
        var el = document.getElementById('sentinelCountdown');
        if (el) el.textContent = countdownSecs;

        if (reconnectTimer) clearInterval(reconnectTimer);

        reconnectTimer = setInterval(function() {
            countdownSecs--;
            if (el) el.textContent = countdownSecs;

            if (countdownSecs <= 0) {
                clearInterval(reconnectTimer);
                checkServerHealth();
            }
        }, 1000);
    }

    function checkServerHealth() {
        fetch('api.php?action=get_favorites', { method: 'HEAD', cache: 'no-store' })
            .then(function(response) {
                if (response.ok || response.status < 500) {
                    hideServerDownHUD();
                } else {
                    showServerDownHUD('Server 5xx error');
                }
            })
            .catch(function(err) {
                showServerDownHUD('Network/Server disconnect');
            });
    }

    // 1. Intercept Global Window Fetch API
    var originalFetch = window.fetch;
    window.fetch = function() {
        return originalFetch.apply(this, arguments)
            .then(function(response) {
                if (response.status >= 500) {
                    showServerDownHUD('HTTP ' + response.status);
                }
                return response;
            })
            .catch(function(error) {
                showServerDownHUD('Fetch Connection Failure');
                throw error;
            });
    };

    // 2. Intercept Global XMLHttpRequest (AJAX)
    var originalXHR = window.XMLHttpRequest;
    function CustomXHR() {
        var xhr = new originalXHR();
        xhr.addEventListener('error', function() {
            showServerDownHUD('XHR Connection Error');
        });
        xhr.addEventListener('load', function() {
            if (xhr.status >= 500) {
                showServerDownHUD('XHR HTTP ' + xhr.status);
            }
        });
        return xhr;
    }
    window.XMLHttpRequest = CustomXHR;

    // 3. Browser Online/Offline Network Listeners
    window.addEventListener('offline', function() {
        showServerDownHUD('Browser Offline');
    });

    window.addEventListener('online', function() {
        checkServerHealth();
    });

    // 4. Heartbeat Server Ping Every 15 Seconds
    setInterval(checkServerHealth, 15000);

    // Initial DOM Ready Bind
    document.addEventListener('DOMContentLoaded', injectServerDownOverlay);

    // Export Public API
    window.ServerSentinel = {
        triggerDown: showServerDownHUD,
        retryConnection: function() {
            var el = document.getElementById('sentinelCountdown');
            if (el) el.textContent = '...';
            checkServerHealth();
        }
    };
})();
