import { getCookie } from "./utils.js";

window.addEventListener('pageshow', () => {
    hideLoadingIndicator();
});

document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.querySelector('.menu-toggle');
    const sideMenu = document.querySelector('.side-menu');

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('showNotification') === 'true') {
        showModeChangeNotification(getCurrentMode());
    }

    menuToggle.addEventListener('click', () => {
        menuToggle.classList.toggle('open');
        sideMenu.classList.toggle('open');
    });
    
    document.addEventListener('click', (e) => {
        if (!sideMenu.contains(e.target) && !menuToggle.contains(e.target) && sideMenu.classList.contains('open')) {
            sideMenu.classList.remove('open');
            menuToggle.classList.remove('open');
        }
    });
    
    const currentMode = getCurrentMode();
    console.log(`Current mode detected: ${currentMode}`);
    
    // 🔧 Check if wheel needs to be reloaded due to mode mismatch
    if (window.CURRENT_WHEEL_SLUG && currentMode !== window.CURRENT_WHEEL_SLUG && currentMode !== 'history') {
        console.log(`Mode mismatch: detected '${currentMode}' but wheel loaded is '${window.CURRENT_WHEEL_SLUG}', reloading...`);
        // Force page reload to load the correct wheel
        window.location.href = `/?mode=${currentMode}&t=${Date.now()}`;
        return; // Stop execution to avoid menu setup
    }
    
    updateActiveMenuItem(currentMode);
    
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', async () => {
            const option = item.getAttribute('data-option');
            if (option === 'history') {
                return;
            }
            
            // Check if already on this mode
            if (option === getCurrentMode()) {
                console.log(`Already on mode: ${option}`);
                return;
            }
            
            menuItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            console.log(`Selected option: ${option}`);
            showLoadingIndicator();
            
            try {
				const response = await fetch('/change_wheel_config/', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': getCookie('csrftoken')
					},
					body: JSON.stringify({ mode: option })
				});
				
				if (response.ok) {
					window.location.href = `/?mode=${option}&showNotification=true&t=${Date.now()}`;
				} else {
					console.error('Error changing mode:', response.statusText);
					hideLoadingIndicator();
					// Restore previous state on error
					updateActiveMenuItem(getCurrentMode());
				}
			} catch (error) {
				console.error('Error changing mode:', error);
				hideLoadingIndicator();
				// Restore previous state on error
				updateActiveMenuItem(getCurrentMode());
			}
        });
    });
});function getCurrentMode() {
    // /history route special case
    if (window.location.pathname.includes('/history')) return 'history';

    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode') || urlParams.get('wheel');

    const available = Array.isArray(window.AVAILABLE_WHEELS) ? window.AVAILABLE_WHEELS : [];
    
    // Check if URL mode is available
    if (mode && available.includes(mode)) {
        return mode;
    }
    
    // Fallback to first available wheel
    if (available.length === 0) {
        return 'history'; // no wheels => only history meaningful
    }
    
    return available[0];
}


// Update the active menu item based on current mode
function updateActiveMenuItem(currentMode) {
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => item.classList.remove('active'));
    
    const activeMenuItem = document.querySelector(`.menu-item[data-option="${currentMode}"]`);
    if (activeMenuItem) {
        activeMenuItem.classList.add('active');
        console.log(`Menu item activated: ${currentMode}`);
    } else {
        // Fallback: highlight first available wheel if any
        const first = document.querySelector('.menu-item[data-option]');
        if (first) {
            first.classList.add('active');
            console.warn(`Mode ${currentMode} not found, fallback to first item`);
        }
    }
}

export function showLoadingIndicator() {
    if (document.querySelector('.loading-indicator')) return;
    
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator';
    loadingIndicator.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text">Loading wheel...</div>
    `;
    document.body.appendChild(loadingIndicator);
}

export function hideLoadingIndicator() {
    const loadingIndicator = document.querySelector('.loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.remove();
    }
}

function showModeChangeNotification(mode) {
    if (!mode || mode === 'history') return;
    const existingNotification = document.querySelector('.mode-notification');
    if (existingNotification) existingNotification.remove();
    
    const notification = document.createElement('div');
    notification.className = 'mode-notification';
    
    // Map known dynamic titles
    const titleMap = window.WHEEL_TITLE_MAP || {};
    const friendly = titleMap[mode] || mode;

    notification.textContent = `Mode ${friendly} activated!`;

    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 100);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}
