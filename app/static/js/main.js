// Main JavaScript for the application

// Notification count update
function updateNotificationCount() {
    fetch('/staff/notifications/count')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notification-badge');
            if (badge) {
                if (data.count > 0) {
                    badge.style.display = 'inline';
                    badge.textContent = data.count;
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(error => console.error('Error fetching notifications:', error));
}

// Mobile menu close after click (for better UX)
document.addEventListener('DOMContentLoaded', function() {
    // Close mobile menu when a link is clicked
    const navbarCollapse = document.querySelector('.navbar-collapse');
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (navbarCollapse.classList.contains('show')) {
                navbarCollapse.classList.remove('show');
            }
        });
    });

    // Initialize notification count
    if (typeof updateNotificationCount === 'function') {
        updateNotificationCount();
        setInterval(updateNotificationCount, 30000);
    }
});

// Table row click handler (optional)
document.querySelectorAll('.clickable-row').forEach(row => {
    row.addEventListener('click', function() {
        window.location.href = this.dataset.href;
    });
});

// Confirm dialog helper
function confirmAction(message) {
    return confirm(message);
}