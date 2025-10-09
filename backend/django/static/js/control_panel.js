// Control Panel JavaScript
class ControlPanel {
    constructor() {
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.lastUpdatedElement = document.getElementById('last-updated');
        this.init();
    }

    init() {
        // Update last updated time
        this.updateTimestamp();
        setInterval(() => this.updateTimestamp(), 60000); // Update every minute

        // Add event listeners for keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.refreshStats();
                        break;
                    case 'm':
                        e.preventDefault();
                        this.focusMaintenanceMessage();
                        break;
                }
            }
        });

        // Auto-resize textareas
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            textarea.addEventListener('input', this.autoResize);
            this.autoResize.call(textarea);
        });

        // Initial tickets summary load (if container exists)
        try { refreshTickets(); } catch(_) {}
    }

    autoResize() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    }

    showLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'flex';
        }
    }

    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
    }

    updateTimestamp() {
        if (this.lastUpdatedElement) {
            const now = new Date();
            const timeString = now.toLocaleTimeString();
            this.lastUpdatedElement.textContent = timeString;
        }
    }

    focusMaintenanceMessage() {
        const messageField = document.getElementById('maintenance-message');
        if (messageField) {
            messageField.focus();
            messageField.select();
        }
    }

    async makeRequest(url, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            }
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || `HTTP error! status: ${response.status}`);
            }
            
            return result;
        } catch (error) {
            console.error('Request failed:', error);
            this.showNotification(error.message, 'error');
            throw error;
        }
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        // Add styles if not already present
        if (!document.getElementById('notification-styles')) {
            const styles = document.createElement('style');
            styles.id = 'notification-styles';
            styles.textContent = `
                .notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    min-width: 300px;
                    max-width: 500px;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                    z-index: 1001;
                    animation: slideIn 0.3s ease-out;
                }
                .notification-success {
                    background: #10b981;
                    color: white;
                }
                .notification-error {
                    background: #ef4444;
                    color: white;
                }
                .notification-info {
                    background: #3b82f6;
                    color: white;
                }
                .notification-content {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 1rem;
                }
                .notification-close {
                    background: none;
                    border: none;
                    color: inherit;
                    font-size: 1.25rem;
                    cursor: pointer;
                    padding: 0;
                    width: 24px;
                    height: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%;
                    opacity: 0.8;
                }
                .notification-close:hover {
                    opacity: 1;
                    background: rgba(255, 255, 255, 0.2);
                }
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                @media (max-width: 768px) {
                    .notification {
                        top: 10px;
                        right: 10px;
                        left: 10px;
                        min-width: auto;
                        max-width: none;
                    }
                }
            `;
            document.head.appendChild(styles);
        }

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize control panel
const controlPanel = new ControlPanel();

// Toggle maintenance mode
async function toggleMaintenance(enabled) {
    const messageField = document.getElementById('maintenance-message');
    const message = messageField ? messageField.value.trim() : '';
    
    if (enabled && !message) {
        controlPanel.showNotification('Please enter a maintenance message', 'error');
        if (messageField) messageField.focus();
        return;
    }

    controlPanel.showLoading();

    try {
        const result = await controlPanel.makeRequest('/adm/control-panel/maintenance/toggle/', 'POST', {
            enabled: enabled,
            message: message
        });

        if (result.success) {
            controlPanel.showNotification(result.message, 'success');
            // Update UI
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    } catch (error) {
        // Error already handled in makeRequest
    } finally {
        controlPanel.hideLoading();
    }
}

// Update jackpot cooldown
async function updateJackpotCooldown() {
    const hoursField = document.getElementById('cooldown-hours');
    if (!hoursField) return;

    const hours = parseInt(hoursField.value);
    if (!hours || hours < 1 || hours > 168) {
        controlPanel.showNotification('Hours must be between 1 and 168', 'error');
        hoursField.focus();
        return;
    }

    controlPanel.showLoading();

    try {
        const result = await controlPanel.makeRequest('/adm/control-panel/jackpot-cooldown/', 'POST', {
            hours: hours
        });

        if (result.success) {
            controlPanel.showNotification(result.message, 'success');
            // Update the current value display
            const currentValueElement = document.querySelector('.current-value');
            if (currentValueElement) {
                currentValueElement.textContent = `${hours}h`;
            }
        }
    } catch (error) {
        // Error already handled in makeRequest
    } finally {
        controlPanel.hideLoading();
    }
}

// Update announcement
async function updateAnnouncement() {
    const field = document.getElementById('announcement-message');
    if (!field) return;
    const message = field.value.trim();
    if (message.length > 255) {
        controlPanel.showNotification('Message too long (max 255)', 'error');
        return;
    }

    controlPanel.showLoading();
    try {
        const result = await controlPanel.makeRequest('/adm/control-panel/announcement/', 'POST', { message });
        if (result.success) {
            controlPanel.showNotification(result.message, 'success');
        }
    } catch (error) {
        // handled by makeRequest
    } finally {
        controlPanel.hideLoading();
    }
}

// Refresh stats
async function refreshStats() {
    controlPanel.showLoading();

    try {
        // Simple page reload for now - could be enhanced with AJAX
        window.location.reload();
    } catch (error) {
        controlPanel.hideLoading();
        controlPanel.showNotification('Failed to refresh stats', 'error');
    }
}

// Export logs (placeholder)
function exportLogs() {
    controlPanel.showNotification('Log export functionality coming soon', 'info');
}

// Clear cache (placeholder)
function clearCache() {
    controlPanel.showNotification('Cache clearing functionality coming soon', 'info');
}

// Enhanced form validation
document.addEventListener('DOMContentLoaded', function() {
    // Validate cooldown hours input
    const cooldownInput = document.getElementById('cooldown-hours');
    if (cooldownInput) {
        cooldownInput.addEventListener('input', function() {
            const value = parseInt(this.value);
            if (value < 1) {
                this.value = 1;
            } else if (value > 168) {
                this.value = 168;
            }
        });

        cooldownInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                updateJackpotCooldown();
            }
        });
    }

    // Validate maintenance message
    const maintenanceMessage = document.getElementById('maintenance-message');
    if (maintenanceMessage) {
        maintenanceMessage.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                toggleMaintenance(true);
            }
        });
    }
});

// Keyboard shortcuts info
console.log(`
Control Panel Keyboard Shortcuts:
- Ctrl/Cmd + R: Refresh stats
- Ctrl/Cmd + M: Focus maintenance message
- Enter (in cooldown field): Update cooldown
- Ctrl/Cmd + Enter (in maintenance message): Enable maintenance
`);

// Performance monitoring
if ('performance' in window) {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`Control panel loaded in ${loadTime}ms`);
        }, 0);
    });
}

// ---- Tickets helpers ----
async function grantTicket() {
    const login = document.getElementById('ticket-login')?.value.trim();
    const wheel = document.getElementById('ticket-wheel')?.value.trim();
    if (!login || !wheel) {
        controlPanel.showNotification('Please provide both login and wheel slug', 'error');
        return;
    }
    controlPanel.showLoading();
    try {
        const res = await controlPanel.makeRequest('/adm/control-panel/tickets/grant/', 'POST', { login, wheel });
        if (res.success) {
            controlPanel.showNotification(`Ticket granted to ${res.ticket.user} for wheel ${res.ticket.wheel}`, 'success');
            refreshTickets();
        }
    } catch (_) {
        // handled
    } finally {
        controlPanel.hideLoading();
    }
}

async function refreshTickets() {
    try {
        const res = await controlPanel.makeRequest('/adm/control-panel/tickets/summary/', 'GET');
        if (!res.success) return;
        const target = document.getElementById('tickets-summary');
        if (!target) return;
        const unused = res.unused || [];
        const recent = res.recent || [];
        const unusedHtml = unused.length
            ? unused.map(u => `<li style="display:flex; justify-content:space-between; gap:.5rem;"><span><code>${u.wheel_slug}</code></span><b>${u.count}</b></li>`).join('')
            : '<li style="opacity:.7">No unused tickets</li>';
        const recentHtml = recent.length
            ? recent.map(t => `<li style="margin-bottom:.25rem;">
                    <div style="display:flex; justify-content:space-between; gap:.5rem;">
                        <span>#${t.id} ${t.user} → ${t.wheel} ${t.used_at ? '<span style="opacity:.7">(used)</span>' : ''}</span>
                        <small style="opacity:.7">by ${t.granted_by || 'n/a'}</small>
                    </div>
                </li>`).join('')
            : '<li style="opacity:.7">No recent grants</li>';
        target.innerHTML = `
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem;">
                <div>
                    <div style="font-weight:600; margin-bottom:.4rem; opacity:.9;">Unused tickets per wheel</div>
                    <ul style="list-style:none; padding-left:0; margin:0;">${unusedHtml}</ul>
                </div>
                <div>
                    <div style="font-weight:600; margin-bottom:.4rem; opacity:.9;">Recent grants</div>
                    <ul style="list-style:none; padding-left:0; margin:0;">${recentHtml}</ul>
                </div>
            </div>
        `;
    } catch (e) {
        // ignore
    }
}
