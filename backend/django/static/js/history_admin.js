// History Administration JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize modal handlers
    initializeModals();
    
    // Initialize action buttons
    initializeActionButtons();
    
    // Initialize marks indicators
    initializeMarksIndicators();
    
    // Convert UTC timestamps to user's local time
    convertTimestampsToLocal();
});

// Convert UTC timestamps to user's local timezone
function convertTimestampsToLocal() {
    document.querySelectorAll('.timestamp').forEach(function(el) {
        const utc = el.dataset.utc;
        if (utc) {
            const local = formatTimestampToLocal(utc);
            el.textContent = local;
        }
    });
}

// Utility function to format timestamp to local time
function formatTimestampToLocal(timestamp) {
    try {
        // Handle both ISO strings and regular timestamp formats
        let date;
        if (typeof timestamp === 'string') {
            // If it's an ISO string, ensure it has the Z suffix for UTC
            if (timestamp.includes('T') && !timestamp.includes('Z') && !timestamp.includes('+')) {
                timestamp += 'Z';
            }
        }
        date = new Date(timestamp);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.error('Invalid timestamp:', timestamp);
            return timestamp; // Return original if can't parse
        }
        
        return date.toLocaleString();
    } catch (error) {
        console.error('Error formatting timestamp:', error, timestamp);
        return timestamp;
    }
}

// Modal management
function initializeModals() {
    const modals = document.querySelectorAll('.modal');
    const closeButtons = document.querySelectorAll('.close');
    const closeModalButtons = document.querySelectorAll('[data-close-modal]');
    
    // Close modal when clicking the X button
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modalId = this.getAttribute('data-modal');
            closeModal(modalId);
        });
    });
    
    // Close modal when clicking close button
    closeModalButtons.forEach(button => {
        button.addEventListener('click', function() {
            const modalId = this.getAttribute('data-close-modal');
            closeModal(modalId);
        });
    });
    
    // Close modal when clicking outside
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            modals.forEach(modal => {
                if (modal.style.display === 'block') {
                    closeModal(modal.id);
                }
            });
        }
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Action buttons initialization
function initializeActionButtons() {
    // View details buttons
    document.querySelectorAll('.view-details').forEach(button => {
        button.addEventListener('click', function() {
            const historyId = this.getAttribute('data-history-id');
            viewHistoryDetails(historyId);
        });
    });
    
    // Add mark buttons
    document.querySelectorAll('.add-mark').forEach(button => {
        button.addEventListener('click', function() {
            const historyId = this.getAttribute('data-history-id');
            openAddMarkModal(historyId);
        });
    });
    
    // Cancel entry buttons
    document.querySelectorAll('.cancel-entry').forEach(button => {
        button.addEventListener('click', function() {
            const historyId = this.getAttribute('data-history-id');
            openCancelModal(historyId);
        });
    });
    
    // Form submissions
    document.getElementById('markForm').addEventListener('submit', handleMarkSubmission);
    document.getElementById('cancelForm').addEventListener('submit', handleCancelSubmission);
}

// Marks indicators initialization
function initializeMarksIndicators() {
    document.querySelectorAll('.marks-indicator').forEach(indicator => {
        const historyId = indicator.getAttribute('data-history-id');
        const markCount = indicator.querySelector('.mark-count');
        
        if (markCount) {
            indicator.addEventListener('click', function() {
                viewHistoryDetails(historyId, 'marks');
            });
        }
    });
}

// View history details
async function viewHistoryDetails(historyId, section = null) {
    try {
        showLoadingSpinner('Loading details...');
        
        const response = await fetch(`/adm/history/${historyId}/details/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        displayHistoryDetails(data, section);
        openModal('detailsModal');
        
    } catch (error) {
        console.error('Error fetching history details:', error);
        showNotification('Failed to load history details', 'error');
    } finally {
        hideLoadingSpinner();
    }
}

function displayHistoryDetails(data, highlightSection = null) {
    const content = document.getElementById('detailsContent');
    
    // Determine status display
    let statusDisplay;
    let statusClass;
    if (data.is_cancelled) {
        statusDisplay = 'CANCELLED';
        statusClass = 'status-cancelled';
    } else if (data.success === false) {
        statusDisplay = 'ERROR';
        statusClass = 'status-error';
    } else {
        statusDisplay = 'SUCCESS';
        statusClass = 'status-success';
    }
    
    // Convert timestamps to local time
    const localTimestamp = formatTimestampToLocal(data.timestamp);
    const localCancelledAt = data.cancelled_at ? formatTimestampToLocal(data.cancelled_at) : null;
    
    let html = `
        <div class="detail-group">
            <h4>Basic Information</h4>
            <div class="detail-value">
                <strong>ID:</strong> ${data.id}<br>
                <strong>Timestamp:</strong> ${localTimestamp}<br>
                <strong>User:</strong> ${data.user}<br>
                <strong>Wheel:</strong> ${data.wheel}<br>
                <strong>Prize:</strong> <span>${data.details || 'No details'}</span><br>
                <strong>Function:</strong> ${data.function_name || 'Unknown'}
            </div>
        </div>
        
        <div class="detail-group">
            <h4>Execution Status</h4>
            <div class="detail-value">
                <strong>Status:</strong> <span class="${statusClass}">${statusDisplay}</span><br>
                ${data.is_cancelled ? `
                    <strong>Cancelled At:</strong> ${localCancelledAt}<br>
                    <strong>Cancelled By:</strong> ${data.cancelled_by}<br>
                    <strong>Reason:</strong> ${data.cancellation_reason || 'No reason provided'}<br>
                ` : ''}
                <strong>Can be cancelled:</strong> ${data.can_be_cancelled ? 'Yes' : 'No'}
            </div>
        </div>
        
        <div class="detail-group">
            <h4>Response Data</h4>
            <div class="detail-value">
                <strong>Message:</strong><br>
                <div class="response-data">${data.r_message || 'No message'}</div>
                <strong>Data:</strong><br>
                <div class="response-data">
                    ${data.r_data ? `<pre>${JSON.stringify(data.r_data, null, 2)}</pre>` : 'No data'}
                </div>
            </div>
        </div>
        
        <div class="detail-group ${highlightSection === 'marks' ? 'highlight' : ''}">
            <h4>Validation Marks (${data.marks_count})</h4>
            <div class="detail-value">
                ${data.marks.length > 0 ? data.marks.map(mark => {
                    const localMarkTime = formatTimestampToLocal(mark.marked_at);
                    return `
                    <div class="mark-item">
                        <strong>${mark.user}</strong> (${mark.role}) - ${localMarkTime}
                        ${mark.note ? `<br><em>"${mark.note}"</em>` : ''}
                    </div>
                `;}).join('<hr>') : 'No marks yet'}
            </div>
        </div>
    `;
    
    content.innerHTML = html;
}

// Add mark functionality
function openAddMarkModal(historyId) {
    document.getElementById('markForm').setAttribute('data-history-id', historyId);
    document.getElementById('markNote').value = '';
    openModal('markModal');
}

async function handleMarkSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const historyId = form.getAttribute('data-history-id');
    const note = document.getElementById('markNote').value.trim();
    
    try {
        showLoadingSpinner('Adding mark...');
        
        const response = await fetch(`/adm/history/${historyId}/mark/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ note: note })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update marks indicator in the table
        updateMarksIndicator(historyId, data.marks_count, data.marks);
        
        showNotification(data.message, 'success');
        closeModal('markModal');
        
    } catch (error) {
        console.error('Error adding mark:', error);
        showNotification(`Failed to add mark: ${error.message}`, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

// Cancel entry functionality
function openCancelModal(historyId) {
    document.getElementById('cancelForm').setAttribute('data-history-id', historyId);
    document.getElementById('cancelReason').value = '';
    openModal('cancelModal');
}

async function handleCancelSubmission(e) {
    e.preventDefault();
    
    const form = e.target;
    const historyId = form.getAttribute('data-history-id');
    const reason = document.getElementById('cancelReason').value.trim();
    
    if (!reason) {
        showNotification('Please provide a reason for cancellation', 'error');
        return;
    }
    
    try {
        showLoadingSpinner('Cancelling entry...');
        
        const response = await fetch(`/adm/history/${historyId}/cancel/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ reason: reason })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            alert(`Error: ${errorData.error || `HTTP ${response.status}`}`);
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update the row to show cancelled status
        updateHistoryRowStatus(historyId, true);
        
        showNotification(data.message, 'success');
        closeModal('cancelModal');
        
        // Refresh page after 2 seconds to show updated data
        setTimeout(() => {
            window.location.reload();
        }, 2000);
        
    } catch (error) {
        console.error('Error cancelling entry:', error);
        showNotification(`Failed to cancel entry: ${error.message}`, 'error');
    } finally {
        hideLoadingSpinner();
    }
}

// UI helper functions
function updateMarksIndicator(historyId, marksCount, marksData) {
    const row = document.querySelector(`[data-history-id="${historyId}"]`);
    if (row) {
        const marksCell = row.querySelector('.marks-indicator');
        if (marksCell) {
            if (marksCount > 0) {
                marksCell.innerHTML = `
                    <span class="mark-count">${marksCount}</span>
                    <span class="mark-icon">✓</span>
                `;
                marksCell.title = 'Click to view marks';
            } else {
                marksCell.innerHTML = '<span class="no-marks">—</span>';
                marksCell.title = '';
            }
        }
    }
}

function updateHistoryRowStatus(historyId, isCancelled) {
    const row = document.querySelector(`[data-history-id="${historyId}"]`);
    if (row) {
        if (isCancelled) {
            row.classList.add('cancelled');
            const statusCell = row.querySelector('.status');
            if (statusCell) {
                statusCell.innerHTML = '<span class="status-cancelled">CANCELLED</span>';
            }
            
            // Remove cancel button
            const cancelButton = row.querySelector('.cancel-entry');
            if (cancelButton) {
                cancelButton.remove();
            }
        }
    }
}

function showLoadingSpinner(message = 'Loading...') {
    // Simple loading implementation
    const existingSpinner = document.getElementById('loadingSpinner');
    if (existingSpinner) {
        existingSpinner.remove();
    }
    
    const spinner = document.createElement('div');
    spinner.id = 'loadingSpinner';
    spinner.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
        color: white;
        font-size: 18px;
    `;
    spinner.innerHTML = `<div>${message}</div>`;
    document.body.appendChild(spinner);
}

function hideLoadingSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.remove();
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 4px;
        color: white;
        font-weight: bold;
        z-index: 10001;
        max-width: 400px;
        word-wrap: break-word;
    `;
    
    // Set background color based on type
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#28a745';
            break;
        case 'error':
            notification.style.backgroundColor = '#dc3545';
            break;
        case 'warning':
            notification.style.backgroundColor = '#ffc107';
            notification.style.color = '#333';
            break;
        default:
            notification.style.backgroundColor = '#007bff';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
    
    // Allow manual dismissal by clicking
    notification.addEventListener('click', () => {
        notification.remove();
    });
}