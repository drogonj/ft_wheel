const csrftoken = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1];
const wheelSelect = document.getElementById('wheel-select');
const tbody = document.querySelector('#sectors-table tbody');
const rowTpl = document.getElementById('row-template');
const statusEl = document.getElementById('status');
let currentWheel = null;
let sectors = [];

// Simple status message helper
function setStatus(msg, ok=true){
  statusEl.textContent = msg;
  statusEl.style.color = ok ? '#4ade80' : '#f87171';
}


// Fetch available wheels and populate the select dropdown
async function fetchWheels(){
  // Fetch available wheels and populate the select dropdown
  const r = await fetch('/adm/wheels/', { headers: { 'Accept':'application/json' } });
  const j = await r.json();

  wheelSelect.innerHTML='';

  Object.keys(j.configs).forEach(slug=>{
    const meta=j.configs[slug];
    const opt=document.createElement('option');
    opt.value=slug; opt.textContent=meta.title || slug; wheelSelect.appendChild(opt);
  });

  if(!currentWheel && wheelSelect.options.length){
    currentWheel = wheelSelect.value;
  }
  if(currentWheel){
    wheelSelect.value = currentWheel;
  }
  if(currentWheel) loadWheel(currentWheel);
}


// Build a table row for a sector
function buildRow(sector){
  // Create a new row for the sector
  const node = rowTpl.content.firstElementChild.cloneNode(true);
  node.querySelector('.label-input').value = sector.label || '';

  const colorInput = node.querySelector('.color-input');
  colorInput.value = sector.color || '';
  colorInput.style.borderColor = sector.color || '#000';

  colorInput.addEventListener('input', () => {
    colorInput.style.borderColor = colorInput.value || '#000';
  });

  node.querySelector('.message-input').value = sector.message || '';
  
  // Handle function and args fields
  node.querySelector('.function-input').value = sector.function || 'builtins.default';
  
  // Convert args object to JSON string for display
  let argsStr = '';
  if (sector.args && typeof sector.args === 'object') {
    try {
      argsStr = JSON.stringify(sector.args);
    } catch(e) {
      argsStr = '{}';
    }
  } else {
    argsStr = '{}';
  }

  // Set the args input value
  node.querySelector('.args-input').value = argsStr;
  node.querySelector('.del').addEventListener('click', ()=>{
    node.remove();
    syncFromTable();
    reindex();
  });

  node.querySelector('.dup').addEventListener('click', ()=>{
    syncFromTable();
    // Extract current values from this row's inputs, not the original sector data
    const currentData = {
      label: node.querySelector('.label-input').value.trim(),
      color: node.querySelector('.color-input').value.trim(),
      message: node.querySelector('.message-input').value.trim() || null,
      function: node.querySelector('.function-input').value.trim() || 'builtins.default',
      args: ( ()=>{
        const argsStr = node.querySelector('.args-input').value.trim();
        if(!argsStr) return {};
        try {
          return JSON.parse(argsStr);
        } catch(e) {
          console.warn('Invalid JSON in args, using empty object:', e);
          return {};
        }
      })()
    };
    const newNode = buildRow(currentData);
    node.after(newNode);
    syncFromTable();
    reindex();
    setStatus('Sector duplicated');
  });

  addDragHandlers(node);
  return node;
}


// Reindex the rows after any change
function reindex(){
  [...tbody.children].forEach((tr,i)=>{
    tr.querySelector('.idx').textContent = i+1;
  });
}


// Sync the sectors array from the current table rows
function syncFromTable(){
  sectors = [...tbody.children].map(tr=>({
    label: tr.querySelector('.label-input').value.trim(),
    color: tr.querySelector('.color-input').value.trim(),
    message: tr.querySelector('.message-input').value.trim() || null,
    function: tr.querySelector('.function-input').value.trim() || 'builtins.default',

    args: ( ()=>{
      const argsStr = tr.querySelector('.args-input').value.trim();
      if(!argsStr) return {};
      try {
        return JSON.parse(argsStr);
      } catch(e) {
        console.warn('Invalid JSON in args for row, using empty object:', e);
        return {};
      }
    })()

  }));
}


// Load a wheel by name
async function loadWheel(name){
  currentWheel = name;

  setStatus('Loading...');
  const r = await fetch(`/adm/wheels/${name}/`);
  const j = await r.json();

  sectors = j.ordered || [];
  // update meta fields
  document.getElementById('edit-wheel-url').value = j.file.url || j.file.slug || name;
  document.getElementById('edit-wheel-title').value = j.file.title || name;
  tbody.innerHTML='';

  sectors.forEach(s=> tbody.appendChild(buildRow(s)) );
  reindex();
  setStatus(`Wheel '${name}' loaded (${sectors.length} sectors)`);
}


// TIMER for next spin
document.getElementById('wheel-select').addEventListener('change', e=>{
  loadWheel(e.target.value);
});


// Timer variables
document.getElementById('add-sector').addEventListener('click', ()=>{
  // Add a new empty sector
  const s = { label:'', color:'#FFFFFF', message:'', function:'builtins.default', args:{} };
  tbody.appendChild(buildRow(s));
  syncFromTable();
  reindex();
});


// Save current sectors to backend
document.getElementById('save-sectors').addEventListener('click', async ()=>{
  // Save current sectors to backend
  syncFromTable();
  setStatus('Saving...');

  const resp = await fetch(`/adm/wheels/${currentWheel}/`, {
    method:'POST',
    headers:{'Content-Type':'application/json','X-CSRFToken':csrftoken},
    body: JSON.stringify({ sectors })
  });

  if(!resp.ok){
    setStatus('Save error', false); return;
  }

  const j = await resp.json();
  setStatus('Saved ('+ (j.sectors?.length||0) +' sectors)');
});


// Create a new wheel
document.getElementById('create-wheel').addEventListener('click', async ()=>{
  const url = document.getElementById('new-wheel-url').value.trim();
  const title = document.getElementById('new-wheel-title').value.trim();

  if(!url) return;

  setStatus('Creating wheel...');
  const r = await fetch('/adm/wheels/create/', { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':csrftoken}, body: JSON.stringify({url, title}) });
  if(!r.ok){ setStatus('Create error', false); return; }

  document.getElementById('new-wheel-url').value='';
  document.getElementById('new-wheel-title').value='';

  await fetchWheels();
  setStatus('Wheel created');
});


// Update current wheel meta (title, url)
document.getElementById('update-wheel-meta').addEventListener('click', async ()=>{
  if(!currentWheel) return;

  const urlField = document.getElementById('edit-wheel-url').value.trim();
  const titleField = document.getElementById('edit-wheel-title').value.trim();

  setStatus('Updating meta...');
  syncFromTable();
  const r = await fetch(`/adm/wheels/${currentWheel}/`, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':csrftoken}, body: JSON.stringify({ sectors, url: urlField, title: titleField }) });
  if(!r.ok){ setStatus('Meta update error', false); return; }

  await fetchWheels();
  currentWheel = urlField.toLowerCase().replace(/\s+/g,'_');
  setStatus('Meta updated');
});


// Delete current wheel
document.getElementById('delete-wheel').addEventListener('click', async ()=>{
  if(!currentWheel) return;
  if(!confirm('Delete wheel '+currentWheel+'?')) return;
  setStatus('Deleting...');

  const r = await fetch(`/adm/wheels/${currentWheel}/delete/`, { method:'POST', headers:{'X-CSRFToken':csrftoken} });
  if(!r.ok){ setStatus('Delete error', false); return; }

  currentWheel=null;
  await fetchWheels();
  setStatus('Wheel deleted');
});


// Download current wheel as JSON
const downloadBtn = document.getElementById('download-wheel');
if (downloadBtn) {
  downloadBtn.addEventListener('click', () => {
    if(!currentWheel) return;
    window.location.href = `/adm/wheels/${currentWheel}/download/`;
  });
}


// Drag & drop reordering
let dragEl=null;
function addDragHandlers(tr){
  // Add drag and drop handlers to a table row
  const handle = tr.querySelector('.drag-handle');
  if(!handle) return; // safety

  // Make the handle draggable
  handle.setAttribute('draggable','true');
  handle.addEventListener('dragstart', e=>{ 
    tr.classList.add('dragging'); 
    e.dataTransfer.effectAllowed='move';
    e.dataTransfer.setData('text/plain','drag');
    window._draggingRow = tr;
  });

  // Clean up on drag end
  handle.addEventListener('dragend', ()=>{ 
    tr.classList.remove('dragging'); 
    window._draggingRow=null; 
    syncFromTable(); reindex(); 
  });

  // Handle dragover on tbody to reorder rows
  tr.addEventListener('dragover', e=>{ 
    if(!window._draggingRow) return; 
    e.preventDefault(); 
    const after = getDragAfterElement(e.clientY); 
    const dragging = window._draggingRow; 
    if(after==null){ tbody.appendChild(dragging);} else { tbody.insertBefore(dragging, after);} 
  });
}


// Helper to get the element after which the dragged element should be placed
function getDragAfterElement(y){
  const els=[...tbody.querySelectorAll('tr:not(.dragging)')];

  // Find the element closest to the dragged element
  return els.reduce((closest,child)=>{
    const box=child.getBoundingClientRect();
    const offset = y - box.top - box.height/2;
    if(offset < 0 && offset > closest.offset){
      return { offset, element: child };
    } else { return closest; }
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}


// Initial fetch of wheels
fetchWheels();
