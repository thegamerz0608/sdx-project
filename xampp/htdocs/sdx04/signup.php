<?php
require_once __DIR__ . '/security.php';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Controller Sign Up</title>
    <link rel="stylesheet" href="style1.css">
</head>
<body style="background-image: url('2.jpg'); background-size: cover; background-repeat: no-repeat; background-position: center;">
    <form id="signupForm" action="register_user.php" method="post" class="form" aria-label="Sign Up Form">
        <h1>SIGN UP</h1>
        <?php echo csrf_input(); ?>

        <input type="text" name="username" class="box" placeholder="Enter a username" autocomplete="username" required>
        <input type="email" name="email" class="box" placeholder="Enter your email" autocomplete="email" required>
        
        <div class="password-wrapper">
            <input type="password" name="password" id="signupPassword" class="box" placeholder="Create a password" autocomplete="new-password" minlength="6" required>
            <button type="button" class="toggle-password" onclick="toggleVisibility('signupPassword', this)">👁️</button>
        </div>

        <div class="password-wrapper">
            <input type="password" name="confirm_password" id="confirmPassword" class="box" placeholder="Confirm password" autocomplete="new-password" minlength="6" required>
            <button type="button" class="toggle-password" onclick="toggleVisibility('confirmPassword', this)">👁️</button>
        </div>

        <input type="submit" value="REGISTER" id="submit">

        <div id="toastMessage" class="toast-notification"></div>

        <div class="register-link">
            <p>Already have an account? <a href="index.php">LOGIN</a></p>
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
        document.getElementById('signupForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var form = this;
            var submitBtn = document.getElementById('submit');
            var toast = document.getElementById('toastMessage');

            submitBtn.disabled = true;
            submitBtn.value = "REGISTERING...";
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
                    }, 1200);
                } else {
                    toast.className = "toast-notification error";
                    toast.style.display = "block";
                    submitBtn.disabled = false;
                    submitBtn.value = "REGISTER";
                }
            })
            .catch(function(error) {
                form.submit();
            });
        });
    </script>
</body>
</html>