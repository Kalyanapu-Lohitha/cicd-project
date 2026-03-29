let currentFilter = '';

async function api(url, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  return { res, data: await res.json() };
}

async function loadStats() {
  const { data } = await api('/api/stats');
  document.querySelector('#stat-total .stat-num').textContent   = data.total;
  document.querySelector('#stat-pending .stat-num').textContent  = data.pending;
  document.querySelector('#stat-progress .stat-num').textContent = data.in_progress;
  document.querySelector('#stat-done .stat-num').textContent     = data.done;
}

async function loadCategories() {
  const { data } = await api('/api/categories');
  const sel = document.getElementById('new-category');
  sel.innerHTML = '<option value="">No category</option>';
  data.categories.forEach(c => {
    const o = document.createElement('option');
    o.value = c.id; o.textContent = c.name;
    sel.appendChild(o);
  });
}

async function loadTasks(filter = '') {
  const url = '/api/tasks' + (filter ? '?' + filter : '');
  const { data } = await api(url);
  const list = document.getElementById('task-list');
  if (!data.tasks.length) {
    list.innerHTML = '<div class="empty-state"><strong>No tasks found</strong><p>Add one above to get started</p></div>';
    return;
  }
  list.innerHTML = data.tasks.map(t => `
    <div class="task-card ${t.status === 'done' ? 'done-task' : ''}" id="task-${t.id}">
      <div class="task-check ${t.status === 'done' ? 'checked' : ''}" onclick="toggleDone(${t.id}, '${t.status}')"></div>
      <div class="task-body">
        <div class="task-title ${t.status === 'done' ? 'crossed' : ''}">${t.title}</div>
        ${t.description ? `<div class="task-desc">${t.description}</div>` : ''}
        <div class="task-meta">
          <span class="badge badge-${t.priority}">${t.priority}</span>
          <span class="badge badge-${t.status}">${t.status.replace('_', ' ')}</span>
          ${t.due_date ? `<span class="task-due">Due: ${t.due_date}</span>` : ''}
        </div>
      </div>
      <div class="task-actions">
        <select class="btn btn-ghost btn-sm" onchange="changeStatus(${t.id}, this.value)">
          <option value="pending"     ${t.status==='pending'     ? 'selected' : ''}>Pending</option>
          <option value="in_progress" ${t.status==='in_progress' ? 'selected' : ''}>In progress</option>
          <option value="done"        ${t.status==='done'        ? 'selected' : ''}>Done</option>
        </select>
        <button class="btn btn-danger btn-sm" onclick="deleteTask(${t.id})">Delete</button>
      </div>
    </div>`).join('');
}

async function createTask() {
  const title    = document.getElementById('new-title').value.trim();
  const priority = document.getElementById('new-priority').value;
  const desc     = document.getElementById('new-desc').value.trim();
  const due      = document.getElementById('new-due').value;
  const cat      = document.getElementById('new-category').value;
  if (!title) { showFormMsg('Title is required', 'error'); return; }
  const { res } = await api('/api/tasks', 'POST', {
    title, priority, description: desc,
    due_date: due || null, category_id: cat || null
  });
  if (res.ok) {
    document.getElementById('new-title').value = '';
    document.getElementById('new-desc').value  = '';
    document.getElementById('new-due').value   = '';
    showFormMsg('Task added!', 'success');
    loadTasks(currentFilter); loadStats();
  } else { showFormMsg('Failed to add task', 'error'); }
}

async function deleteTask(id) {
  if (!confirm('Delete this task?')) return;
  await api(`/api/tasks/${id}`, 'DELETE');
  loadTasks(currentFilter); loadStats();
}

async function changeStatus(id, status) {
  await api(`/api/tasks/${id}`, 'PUT', { status });
  loadTasks(currentFilter); loadStats();
}

async function toggleDone(id, currentStatus) {
  const newStatus = currentStatus === 'done' ? 'pending' : 'done';
  await api(`/api/tasks/${id}`, 'PUT', { status: newStatus });
  loadTasks(currentFilter); loadStats();
}

async function doLogout() {
  await api('/auth/logout', 'POST');
  window.location.href = '/login';
}

function showFormMsg(text, type) {
  const el = document.getElementById('form-msg');
  el.textContent = text;
  el.className = 'msg ' + type;
  setTimeout(() => el.className = 'msg hidden', 2500);
}

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    loadTasks(currentFilter);
  });
});

loadStats(); loadCategories(); loadTasks();