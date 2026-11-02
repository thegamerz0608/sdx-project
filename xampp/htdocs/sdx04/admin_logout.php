<?php
// admin_logout.php - Admin Session Logout Processor
session_start();

unset($_SESSION['is_admin']);
unset($_SESSION['admin_user_id']);
unset($_SESSION['admin_username']);

header("Location: admin_login.php");
exit();
?>
