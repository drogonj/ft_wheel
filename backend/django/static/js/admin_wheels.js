const csrftoken = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1];
const wheelSelect = document.getElementById('wheel-select');
const tbody = document.querySelector('#sectors-table tbody');
const cardsContainer = document.getElementById('sectors-cards');
const rowTpl = document.getElementById('row-template');
const cardTpl = document.getElementById('card-template');
const statusEl = document.getElementById('status');
let currentWheel = null;
let sectors = [];
let isMobile = false;

// Check if we're in mobile mode
function checkMobile() {
  isMobile = window.innerWidth < 1088; // 68rem breakpoint
  return isMobile;
}

// Update mobile state on resize
window.addEventListener('resize', () => {
  const wasMobile = isMobile;
  checkMobile();
  if (wasMobile !== isMobile) {
    // Re-render content when switching between mobile/desktop
    renderSectors();
  }
});

// Initialize mobile check
checkMobile();

// Enhanced status message helper with auto-dismiss
function setStatus(msg, type='info') {
  statusEl.textContent = msg;
  statusEl.className = 'status-display';
  
  switch(type) {
    case 'success':
      statusEl.classList.add('success');
      break;
    case 'error':
      statusEl.classList.add('error');
      break;
    default:
      // info/neutral styling
      break;
  }
  
  // Auto-clear after 5 seconds for non-error messages
  if (type !== 'error') {
    setTimeout(() => {
      if (statusEl.textContent === msg) {
        statusEl.textContent = '';
        statusEl.className = 'status-display';
      }
    }, 5000);
  }
  
  // Scroll status into view on mobile
  if (isMobile && type === 'error') {
    statusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

// Add loading state management
function setLoading(element, isLoading) {
  if (isLoading) {
    element.classList.add('loading');
    element.disabled = true;
  } else {
    element.classList.remove('loading');
    element.disabled = false;
  }
}

// Enhanced validation for JSON inputs
function validateJSON(jsonString, fieldName = 'JSON') {
  if (!jsonString.trim()) return { valid: true, data: {} };
  
  try {
    const parsed = JSON.parse(jsonString);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return { valid: false, error: `${fieldName} must be an object` };
    }
    return { valid: true, data: parsed };
  } catch (e) {
    return { valid: false, error: `Invalid ${fieldName}: ${e.message}` };
  }
}

// Add form validation before save
function validateSectors() {
  const errors = [];
  
  sectors.forEach((sector, index) => {
    if (!sector.label || !sector.label.trim()) {
      errors.push(`Sector #${index + 1}: Label is required`);
    }
    
    if (!sector.color || !sector.color.match(/^#[0-9A-Fa-f]{6}$/)) {
      errors.push(`Sector #${index + 1}: Invalid color format`);
    }
    
    if (sector.function && !sector.function.trim()) {
      errors.push(`Sector #${index + 1}: Function cannot be empty`);
    }
  });
  
  return errors;
}

// Fetch available wheels and populate the select dropdown
async function fetchWheels(){
  try {
    const r = await fetch('/adm/wheels/', { headers: { 'Accept':'application/json' }, cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();

    wheelSelect.innerHTML='';

    if (Object.keys(j.configs).length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No wheels available';
      wheelSelect.appendChild(opt);
      return;
    }

    Object.keys(j.configs).forEach(slug=>{
      const meta = j.configs[slug];
      const opt = document.createElement('option');
      opt.value = slug;
      opt.textContent = `${meta.title || slug} (${meta.count} sectors)`;
      wheelSelect.appendChild(opt);
    });

    if(!currentWheel && wheelSelect.options.length){
      currentWheel = wheelSelect.value;
    }
    if(currentWheel){
      wheelSelect.value = currentWheel;
    }
    if(currentWheel) loadWheel(currentWheel);
  } catch (error) {
    console.error('Failed to fetch wheels:', error);
    setStatus('Failed to load wheels', 'error');
  }
}

// Build a table row for a sector
function buildRow(sector, index) {
  const node = rowTpl.content.firstElementChild.cloneNode(true);
  
  // Set index
  node.querySelector('.idx').textContent = index + 1;
  
  // Set input values
  node.querySelector('.label-input').value = sector.label || '';

  const colorInput = node.querySelector('.color-input');
  colorInput.value = sector.color || '#FFFFFF';
  colorInput.style.borderColor = sector.color || '#FFFFFF';

  colorInput.addEventListener('input', () => {
    colorInput.style.borderColor = colorInput.value || '#FFFFFF';
  });

  node.querySelector('.message-input').value = sector.message || '';
  node.querySelector('.function-input').value = sector.function || 'builtins.default';
  
  // Convert args object to JSON string for display
  let argsStr = '{}';
  if (sector.args && typeof sector.args === 'object') {
    try {
      argsStr = JSON.stringify(sector.args);
    } catch(e) {
      console.warn('Invalid args object:', e);
      argsStr = '{}';
    }
  }
  node.querySelector('.args-input').value = argsStr;

  // Add event listeners with proper classes
  const delBtn = node.querySelector('.del');
  delBtn.className = 'del btn btn-danger';
  delBtn.addEventListener('click', () => {
    deleteSector(index);
  });

  const dupBtn = node.querySelector('.dup');
  dupBtn.className = 'dup btn btn-secondary';
  dupBtn.addEventListener('click', () => {
    duplicateSector(index);
  });

  addDragHandlers(node);
  return node;
}

// Build a card for mobile view
function buildCard(sector, index) {
  const node = cardTpl.content.firstElementChild.cloneNode(true);
  
  // Set index
  node.querySelector('.card-index').textContent = `#${index + 1}`;
  
  // Set input values
  node.querySelector('.label-input').value = sector.label || '';
  
  const colorInput = node.querySelector('.color-input');
  const colorPreview = node.querySelector('.color-preview');
  colorInput.value = sector.color || '#FFFFFF';
  colorPreview.style.backgroundColor = sector.color || '#FFFFFF';
  
  colorInput.addEventListener('input', () => {
    colorPreview.style.backgroundColor = colorInput.value || '#FFFFFF';
  });

  node.querySelector('.message-input').value = sector.message || '';
  node.querySelector('.function-input').value = sector.function || 'builtins.default';
  
  // Convert args object to JSON string for display
  let argsStr = '{}';
  if (sector.args && typeof sector.args === 'object') {
    try {
      argsStr = JSON.stringify(sector.args);
    } catch(e) {
      console.warn('Invalid args object:', e);
      argsStr = '{}';
    }
  }
  node.querySelector('.args-input').value = argsStr;

  // Add event listeners with proper classes
  const delBtn = node.querySelector('.del');
  delBtn.className = 'del btn btn-danger';
  delBtn.addEventListener('click', () => {
    deleteSector(index);
  });

  const dupBtn = node.querySelector('.dup');
  dupBtn.className = 'dup btn btn-secondary';
  dupBtn.addEventListener('click', () => {
    duplicateSector(index);
  });

  // Store index for drag operations
  node.dataset.sectorIndex = index;
  addCardDragHandlers(node);
  
  return node;
}

// Delete a sector by index
function deleteSector(index) {
  if (index >= 0 && index < sectors.length) {
    sectors.splice(index, 1);
    renderSectors();
    setStatus(`Sector #${index + 1} deleted`, 'success');
  }
}

// Duplicate a sector by index
function duplicateSector(index) {
  if (index >= 0 && index < sectors.length) {
    // Get current values from UI
    syncFromUI();
    
    // Clone the sector data
    const originalSector = sectors[index];
    const clonedSector = {
      label: originalSector.label,
      color: originalSector.color,
      message: originalSector.message,
      function: originalSector.function,
      args: {...originalSector.args}
    };
    
    // Insert after the original
    sectors.splice(index + 1, 0, clonedSector);
    renderSectors();
    setStatus(`Sector #${index + 1} duplicated`, 'success');
  }
}

// Render sectors in the appropriate view (table or cards)
function renderSectors() {
  if (isMobile) {
    // Mobile: use cards
    tbody.innerHTML = '';
    cardsContainer.innerHTML = '';
    
    sectors.forEach((sector, index) => {
      cardsContainer.appendChild(buildCard(sector, index));
    });
  } else {
    // Desktop: use table
    cardsContainer.innerHTML = '';
    tbody.innerHTML = '';
    
    sectors.forEach((sector, index) => {
      tbody.appendChild(buildRow(sector, index));
    });
  }
}

// Sync the sectors array from the current UI (table or cards)
function syncFromUI() {
  if (isMobile) {
    // Sync from cards
    sectors = [...cardsContainer.children].map((card, index) => ({
      label: card.querySelector('.label-input').value.trim(),
      color: card.querySelector('.color-input').value.trim(),
      message: card.querySelector('.message-input').value.trim() || null,
      function: card.querySelector('.function-input').value.trim() || 'builtins.default',
      args: (() => {
        const argsStr = card.querySelector('.args-input').value.trim();
        if (!argsStr) return {};
        try {
          return JSON.parse(argsStr);
        } catch(e) {
          console.warn(`Invalid JSON in args for card ${index}, using empty object:`, e);
          return {};
        }
      })()
    }));
  } else {
    // Sync from table
    sectors = [...tbody.children].map((tr, index) => ({
      label: tr.querySelector('.label-input').value.trim(),
      color: tr.querySelector('.color-input').value.trim(),
      message: tr.querySelector('.message-input').value.trim() || null,
      function: tr.querySelector('.function-input').value.trim() || 'builtins.default',
      args: (() => {
        const argsStr = tr.querySelector('.args-input').value.trim();
        if (!argsStr) return {};
        try {
          return JSON.parse(argsStr);
        } catch(e) {
          console.warn(`Invalid JSON in args for row ${index}, using empty object:`, e);
          return {};
        }
      })()
    }));
  }
}

// Load a wheel by name
async function loadWheel(name) {
  if (!name) return;
  
  currentWheel = name;
  setStatus('Loading wheel...');
  
  try {
    const r = await fetch(`/adm/wheels/${name}/`, { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json();

    sectors = j.ordered || [];
    
    // Update meta fields
    document.getElementById('edit-wheel-url').value = j.file.url || j.file.slug || name;
    document.getElementById('edit-wheel-title').value = j.file.title || name;
    
    renderSectors();
    setStatus(`Wheel '${name}' loaded (${sectors.length} sectors)`, 'success');
  } catch (error) {
    console.error('Failed to load wheel:', error);
    setStatus(`Failed to load wheel '${name}'`, 'error');
  }
}

// Event Listeners
document.getElementById('wheel-select').addEventListener('change', e => {
  loadWheel(e.target.value);
});

document.getElementById('add-sector').addEventListener('click', () => {
  // Add a new empty sector
  const newSector = { 
    label: 'New Sector', 
    color: '#FFFFFF', 
    message: 'You won something!', 
    function: 'builtins.default', 
    args: {} 
  };
  sectors.push(newSector);
  renderSectors();
  setStatus('New sector added', 'success');
});

// Save current sectors to backend
document.getElementById('save-sectors').addEventListener('click', async () => {
  if (!currentWheel) {
    setStatus('No wheel selected', 'error');
    return;
  }
  
  // Sync and validate
  syncFromUI();
  const validationErrors = validateSectors();
  
  if (validationErrors.length > 0) {
    setStatus(`Validation errors: ${validationErrors.join(', ')}`, 'error');
    return;
  }
  
  const saveBtn = document.getElementById('save-sectors');
  setLoading(saveBtn, true);
  setStatus('Saving...');

  try {
    const resp = await fetch(`/adm/wheels/${currentWheel}/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      },
      body: JSON.stringify({ sectors })
    });

    if (!resp.ok) {
      const errorData = await resp.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${resp.status}`);
    }

    const j = await resp.json();
    setStatus(`✅ Saved successfully (${j.sectors?.length || 0} sectors)`, 'success');
    
    // Vibrate on mobile for success feedback
    if (navigator.vibrate && isMobile) {
      navigator.vibrate(100);
    }
  } catch (error) {
    console.error('Save error:', error);
    setStatus(`❌ Save error: ${error.message}`, 'error');
    
    // Vibrate on mobile for error feedback
    if (navigator.vibrate && isMobile) {
      navigator.vibrate([100, 50, 100]);
    }
  } finally {
    setLoading(saveBtn, false);
  }
});

// Create a new wheel
document.getElementById('create-wheel').addEventListener('click', async () => {
  const url = document.getElementById('new-wheel-url').value.trim();
  const title = document.getElementById('new-wheel-title').value.trim();

  if (!url) {
    setStatus('URL is required', 'error');
    return;
  }

  setStatus('Creating wheel...');
  
  try {
    const r = await fetch('/adm/wheels/create/', { 
      method: 'POST', 
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      }, 
      body: JSON.stringify({url, title}) 
    });
    
    if (!r.ok) {
      const errorData = await r.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${r.status}`);
    }

    document.getElementById('new-wheel-url').value = '';
    document.getElementById('new-wheel-title').value = '';

    await fetchWheels();
    setStatus('Wheel created', 'success');
  } catch (error) {
    console.error('Create error:', error);
    setStatus(`Create error: ${error.message}`, 'error');
  }
});

// Update current wheel meta (title, url)
document.getElementById('update-wheel-meta').addEventListener('click', async () => {
  if (!currentWheel) {
    setStatus('No wheel selected', 'error');
    return;
  }

  const urlField = document.getElementById('edit-wheel-url').value.trim();
  const titleField = document.getElementById('edit-wheel-title').value.trim();

  if (!urlField) {
    setStatus('URL is required', 'error');
    return;
  }

  setStatus('Updating metadata...');
  syncFromUI();
  
  try {
    const r = await fetch(`/adm/wheels/${currentWheel}/`, { 
      method: 'POST', 
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken
      }, 
      body: JSON.stringify({ sectors, url: urlField, title: titleField }) 
    });
    
    if (!r.ok) {
      const errorData = await r.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${r.status}`);
    }

    await fetchWheels();
    currentWheel = urlField.toLowerCase().replace(/\s+/g,'_');
    setStatus('Metadata updated', 'success');
  } catch (error) {
    console.error('Meta update error:', error);
    setStatus(`Update error: ${error.message}`, 'error');
  }
});

// Delete current wheel
document.getElementById('delete-wheel').addEventListener('click', async () => {
  if (!currentWheel) {
    setStatus('No wheel selected', 'error');
    return;
  }
  
  if (!confirm(`Delete wheel '${currentWheel}'?\n\nThis action cannot be undone.`)) return;
  
  setStatus('Deleting wheel...');

  try {
    const r = await fetch(`/adm/wheels/${currentWheel}/delete/`, { 
      method: 'POST', 
      headers: {'X-CSRFToken': csrftoken} 
    });
    
    if (!r.ok) {
      const errorData = await r.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${r.status}`);
    }

    currentWheel = null;
    sectors = [];
    await fetchWheels();
    setStatus('Wheel deleted', 'success');
  } catch (error) {
    console.error('Delete error:', error);
    setStatus(`Delete error: ${error.message}`, 'error');
  }
});

// Download current wheel as JSON
document.getElementById('download-wheel').addEventListener('click', () => {
  if (!currentWheel) {
    setStatus('No wheel selected', 'error');
    return;
  }
  window.location.href = `/adm/wheels/${currentWheel}/download/`;
});

// Upload wheel from JSON file
document.getElementById('upload-wheel').addEventListener('click', async () => {
  const fileInput = document.getElementById('upload-file');
  fileInput.value = '';
  fileInput.click();
});

document.getElementById('upload-file').addEventListener('change', async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  if (file.type && file.type !== 'application/json') {
    setStatus('Please select a JSON file', 'error');
    return;
  }

  setStatus('Uploading wheel...');
  const form = new FormData();
  form.append('file', file);

  try {
    const r = await fetch('/adm/wheels/upload/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken },
      body: form
    });

    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${r.status}`);
    }
    const j = await r.json();
    setStatus(`Uploaded wheel '${j.url}'`, 'success');

    // Set as current before refreshing list so the refresh loads the new wheel
    if (j.url) {
      currentWheel = j.url;
    }
    await fetchWheels();
  } catch (error) {
    console.error('Upload error:', error);
    setStatus(`Upload error: ${error.message}`, 'error');
  }
});

// Drag & drop reordering for table rows
let dragEl = null;
function addDragHandlers(tr) {
  const handle = tr.querySelector('.drag-handle');
  if (!handle) return;

  handle.setAttribute('draggable', 'true');
  handle.addEventListener('dragstart', e => { 
    tr.classList.add('dragging'); 
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', 'drag');
    window._draggingRow = tr;
  });

  handle.addEventListener('dragend', () => { 
    tr.classList.remove('dragging'); 
    window._draggingRow = null; 
    syncFromUI();
    renderSectors(); // Re-render to update indices
  });

  tr.addEventListener('dragover', e => { 
    if (!window._draggingRow) return; 
    e.preventDefault(); 
    const after = getDragAfterElement(e.clientY); 
    const dragging = window._draggingRow; 
    if (after == null) { 
      tbody.appendChild(dragging);
    } else { 
      tbody.insertBefore(dragging, after);
    } 
  });
}

// Drag & drop for mobile cards
function addCardDragHandlers(card) {
  const handle = card.querySelector('.drag-handle');
  if (!handle) return;

  handle.setAttribute('draggable', 'true');
  handle.addEventListener('dragstart', e => { 
    card.classList.add('dragging'); 
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', 'drag');
    window._draggingCard = card;
  });

  handle.addEventListener('dragend', () => { 
    card.classList.remove('dragging'); 
    window._draggingCard = null; 
    syncFromUI();
    renderSectors(); // Re-render to update indices
  });

  card.addEventListener('dragover', e => { 
    if (!window._draggingCard) return; 
    e.preventDefault(); 
    const after = getCardDragAfterElement(e.clientY); 
    const dragging = window._draggingCard; 
    if (after == null) { 
      cardsContainer.appendChild(dragging);
    } else { 
      cardsContainer.insertBefore(dragging, after);
    } 
  });
}

// Helper to get the element after which the dragged table row should be placed
function getDragAfterElement(y) {
  const els = [...tbody.querySelectorAll('tr:not(.dragging)')];
  return els.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    } else { 
      return closest; 
    }
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Helper to get the element after which the dragged card should be placed
function getCardDragAfterElement(y) {
  const els = [...cardsContainer.querySelectorAll('.sector-card:not(.dragging)')];
  return els.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    } else { 
      return closest; 
    }
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Initialize
fetchWheels();
