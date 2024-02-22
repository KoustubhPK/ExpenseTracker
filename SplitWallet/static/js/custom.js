// Include Slick JS and CSS in your template
// You can add these files locally or use CDN
// Example using CDN:
// <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/slick-carousel@1.8.1/slick/slick.css"/>
// <script src="https://cdn.jsdelivr.net/npm/slick-carousel@1.8.1/slick/slick.min.js"></script>

// Initialize Slick on the form
// Store the selected user in local storage on change
document.getElementById('user_select').addEventListener('change', function() {
  var selectedUserId = this.value;
  localStorage.setItem('selected_user_id', selectedUserId);
});

// Retrieve the selected user from local storage on page load
document.addEventListener('DOMContentLoaded', function() {
  var selectedUserId = localStorage.getItem('selected_user_id');
  if (selectedUserId) {
    document.getElementById('user_select').value = selectedUserId;
  }
});