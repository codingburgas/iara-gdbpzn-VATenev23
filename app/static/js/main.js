// Main JavaScript for the application

// Global Loading State Management
const LoadingState = {
    bar: document.getElementById('loading-bar'),
    container: document.getElementById('loading-bar-container'),
    
    start: function() {
        if (this.container) {
            this.container.style.display = 'block';
            this.bar.style.width = '0%';
            setTimeout(() => { this.bar.style.width = '30%'; }, 10);
            setTimeout(() => { this.bar.style.width = '70%'; }, 500);
        }
    },
    
    finish: function() {
        if (this.container) {
            this.bar.style.width = '100%';
            setTimeout(() => {
                this.container.style.display = 'none';
                this.bar.style.width = '0%';
            }, 500);
        }
    }
};

// Intercept all fetch requests to show loading bar
const originalFetch = window.fetch;
window.fetch = function() {
    LoadingState.start();
    return originalFetch.apply(this, arguments)
        .then(response => {
            LoadingState.finish();
            return response;
        })
        .catch(error => {
            LoadingState.finish();
            throw error;
        });
};

// Show loading bar on page navigation
window.onbeforeunload = function() {
    LoadingState.start();
};

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