<?php
require_once __DIR__ . '/security.php';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Controller Login</title>
    <link rel="stylesheet" href="style.css">
    <script src="server_sentinel.js"></script>
</head>
<body style="background-image: url('gaming.jpg'); background-size: cover; background-repeat: no-repeat; background-position: center;">
    <form id="loginForm" action="index3.php" method="post" class="form" aria-label="Login Form">
        <h1>LOGIN</h1>
        <?php echo csrf_input(); ?>

        <input type="text" name="username" class="box" placeholder="Enter your username or email" autocomplete="username" required>
        
        <div class="password-wrapper">
            <input type="password" name="password" id="loginPassword" class="box" placeholder="Enter your password" autocomplete="current-password" required>
            <button type="button" class="toggle-password" onclick="toggleVisibility('loginPassword', this)">👁️</button>
        </div>

        <input type="submit" value="LOGIN" id="submit">
        
        <div id="toastMessage" class="toast-notification"></div>

        <div class="forgot-link">
            <p><a href="forgot_password.php">Forgot Password?</a></p>
        </div>

        <div class="register-link">
            <p>Don't have an account? <a href="signup.php">Sign Up</a></p>
            <p style="margin-top: 15px; font-size: 0.8rem;"><a href="admin_login.php" style="color: #777; text-decoration: none;">🛡️ Administrator Login Portal</a></p>
        </div>
    </form>

    <script>
        function toggleVisibility(inputId, btn) {
            var input = document.getElementById(inputId);
            if (input.type === "password") {
                input.type = "text";
                btn.textContent = "🙈";
            } else {
                input.type = "password";
                btn.textContent = "👁️";
            }
        }

        // AJAX Form Submission (Fetch API)
        document.getElementById('loginForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var form = this;
            var submitBtn = document.getElementById('submit');
            var toast = document.getElementById('toastMessage');

            submitBtn.disabled = true;
            submitBtn.value = "LOGGING IN...";
            toast.className = "toast-notification";
            toast.style.display = "none";

            var formData = new FormData(form);

            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                toast.textContent = data.message;
                if (data.success) {
                    toast.className = "toast-notification success";
                    toast.style.display = "block";
                    setTimeout(function() {
                        window.location.href = data.redirect || 'Practise.php';
                    }, 1000);
                } else {
                    toast.className = "toast-notification error";
                    toast.style.display = "block";
                    submitBtn.disabled = false;
                    submitBtn.value = "LOGIN";
                }
            })
            .catch(function(error) {
                // Fallback submit if JSON not returned
                form.submit();
            });
        });
    </script>
</body>
</html>