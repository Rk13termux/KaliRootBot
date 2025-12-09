/**
 * KaliRoot Admin Panel
 * Panel de administración para gestionar usuarios, suscripciones y recursos
 * Conecta directamente con Supabase (sin depender del bot)
 */

// ===== GLOBAL STATE =====
let supabaseClient = null;
let botToken = null;
let currentSection = 'overview';
let usersData = [];
let resourcesData = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 20;

// Telegram API credentials
let telegramApiId = '';
let telegramApiHash = '';
let telegramAppTitle = '';
let telegramShortName = '';

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', async () => {
    // Check if config.js was loaded with valid credentials
    if (window.ADMIN_CONFIG && window.ADMIN_CONFIG.auto_login &&
        window.ADMIN_CONFIG.supabase_url && window.ADMIN_CONFIG.supabase_key) {

        console.log('🔐 Config file detected, attempting auto-login...');
        await autoLoginFromConfig();
    } else {
        // No config file or auto_login disabled, show login form
        loadSavedCredentials();
        setupEventListeners();
    }
});

async function autoLoginFromConfig() {
    const config = window.ADMIN_CONFIG;

    try {
        // Initialize Supabase client
        supabaseClient = supabase.createClient(config.supabase_url, config.supabase_key);
        botToken = config.bot_token || null;

        // Test connection
        const { count, error } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true });

        if (error) throw error;

        // Set Telegram API credentials
        telegramApiId = config.telegram_api_id || '';
        telegramApiHash = config.telegram_api_hash || '';
        telegramAppTitle = config.telegram_app_title || '';
        telegramShortName = config.telegram_short_name || '';

        // Fill form values (for Settings section)
        document.getElementById('supabase-url').value = config.supabase_url;
        document.getElementById('supabase-key').value = config.supabase_key;
        document.getElementById('bot-token').value = config.bot_token || '';
        document.getElementById('telegram-api-id').value = telegramApiId;
        document.getElementById('telegram-api-hash').value = telegramApiHash;
        document.getElementById('telegram-app-title').value = telegramAppTitle;
        document.getElementById('telegram-short-name').value = telegramShortName;

        // Show dashboard
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');

        // Setup event listeners before loading data
        setupEventListeners();

        // Load initial data
        await loadDashboardData();

        console.log('✅ Auto-login successful!');
        showToast('Conectado automáticamente desde config.js', 'success');

    } catch (error) {
        console.error('❌ Auto-login failed:', error);
        // Fallback to manual login
        loadSavedCredentials();
        setupEventListeners();
        showLoginError('Auto-login falló: ' + error.message);
    }
}

function loadSavedCredentials() {
    const savedUrl = localStorage.getItem('supabase_url');
    const savedKey = localStorage.getItem('supabase_key');
    const savedBotToken = localStorage.getItem('bot_token');

    if (savedUrl) document.getElementById('supabase-url').value = savedUrl;
    if (savedKey) document.getElementById('supabase-key').value = savedKey;
    if (savedBotToken) document.getElementById('bot-token').value = savedBotToken;

    if (savedUrl && savedKey) {
        document.getElementById('remember-creds').checked = true;
    }
}

function setupEventListeners() {
    // Login
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    document.getElementById('logout-btn').addEventListener('click', handleLogout);

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateToSection(section);
        });
    });

    // Refresh
    document.getElementById('refresh-btn').addEventListener('click', refreshCurrentSection);

    // Mobile menu toggle
    document.getElementById('menu-toggle').addEventListener('click', () => {
        document.querySelector('.sidebar').classList.toggle('open');
    });

    // User search
    document.getElementById('user-search').addEventListener('input', debounce(filterUsers, 300));

    // Export users
    document.getElementById('export-users').addEventListener('click', exportUsersCSV);

    // Subscription filter
    document.getElementById('sub-filter').addEventListener('change', loadSubscriptions);

    // Add resource
    document.getElementById('add-resource-btn').addEventListener('click', () => openResourceModal());
    document.getElementById('save-resource-btn').addEventListener('click', saveResource);

    // Save user
    document.getElementById('save-user-btn').addEventListener('click', saveUserChanges);

    // Audit filter
    document.getElementById('audit-type-filter').addEventListener('change', loadAuditLog);

    // Modal close buttons
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });

    // Close modal on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeAllModals();
        });
    });
}

// ===== AUTHENTICATION =====
async function handleLogin() {
    const url = document.getElementById('supabase-url').value.trim();
    const key = document.getElementById('supabase-key').value.trim();
    const token = document.getElementById('bot-token').value.trim();
    const remember = document.getElementById('remember-creds').checked;

    if (!url || !key) {
        showLoginError('Por favor ingresa la URL y la API Key de Supabase');
        return;
    }

    const loginBtn = document.getElementById('login-btn');
    loginBtn.disabled = true;
    loginBtn.textContent = 'Conectando...';

    try {
        // Initialize Supabase client
        supabaseClient = supabase.createClient(url, key);
        botToken = token;

        // Test connection by fetching users count
        const { count, error } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true });

        if (error) throw error;

        // Save credentials if requested
        if (remember) {
            localStorage.setItem('supabase_url', url);
            localStorage.setItem('supabase_key', key);
            if (token) localStorage.setItem('bot_token', token);
        } else {
            localStorage.removeItem('supabase_url');
            localStorage.removeItem('supabase_key');
            localStorage.removeItem('bot_token');
        }

        // Show dashboard
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');

        // Load initial data
        await loadDashboardData();

        showToast('Conectado correctamente a Supabase', 'success');

    } catch (error) {
        console.error('Login error:', error);
        showLoginError('Error de conexión: ' + (error.message || 'Verifica tus credenciales'));
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = '🔐 Conectar';
    }
}

function handleLogout() {
    supabaseClient = null;
    botToken = null;
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
    showToast('Sesión cerrada', 'info');
}

function showLoginError(message) {
    const errorEl = document.getElementById('login-error');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 5000);
}

// ===== NAVIGATION =====
function navigateToSection(section) {
    currentSection = section;

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.toggle('active', sec.id === `section-${section}`);
    });

    // Update title
    const titles = {
        overview: 'Dashboard',
        users: 'Gestión de Usuarios',
        subscriptions: 'Suscripciones',
        resources: 'Recursos de Descarga',
        learning: 'Módulos de Aprendizaje',
        badges: 'Insignias',
        audit: 'Log de Auditoría'
    };
    document.getElementById('page-title').textContent = titles[section] || 'Dashboard';

    // Close mobile menu
    document.querySelector('.sidebar').classList.remove('open');

    // Load section data
    refreshCurrentSection();
}

async function refreshCurrentSection() {
    switch (currentSection) {
        case 'overview':
            await loadDashboardData();
            break;
        case 'users':
            await loadUsers();
            break;
        case 'subscriptions':
            await loadSubscriptions();
            break;
        case 'resources':
            await loadResources();
            break;
        case 'learning':
            await loadLearningModules();
            break;
        case 'badges':
            await loadBadges();
            break;
        case 'audit':
            await loadAuditLog();
            break;
    }
}

// ===== DASHBOARD DATA =====
async function loadDashboardData() {
    try {
        // Get users count
        const { count: usersCount } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true });

        // Get premium users
        const { count: premiumCount } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true })
            .eq('subscription_status', 'active');

        // Get total credits
        const { data: creditsData } = await supabaseClient
            .from('usuarios')
            .select('credit_balance');
        const totalCredits = creditsData?.reduce((sum, u) => sum + (u.credit_balance || 0), 0) || 0;

        // Get resources count
        let resourcesCount = 0;
        try {
            const { count } = await supabaseClient
                .from('download_resources')
                .select('*', { count: 'exact', head: true });
            resourcesCount = count || 0;
        } catch (e) {
            // Table might not exist yet
        }

        // Update UI
        document.getElementById('stat-users').textContent = usersCount || 0;
        document.getElementById('stat-premium').textContent = premiumCount || 0;
        document.getElementById('stat-credits').textContent = formatNumber(totalCredits);
        document.getElementById('stat-resources').textContent = resourcesCount;

        // Load recent activity
        await loadRecentActivity();

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error al cargar datos del dashboard', 'error');
    }
}

async function loadRecentActivity() {
    try {
        const { data, error } = await supabaseClient
            .from('audit_log')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(10);

        const container = document.getElementById('recent-activity');

        if (!data || data.length === 0) {
            container.innerHTML = '<p class="placeholder">No hay actividad reciente</p>';
            return;
        }

        container.innerHTML = data.map(item => `
            <div class="activity-item">
                <div class="activity-icon">${getActivityIcon(item.event_type)}</div>
                <div class="activity-text">
                    <strong>User ${item.user_id}</strong> - ${item.event_type}
                    ${item.details ? `<br><small>${JSON.stringify(item.details)}</small>` : ''}
                </div>
                <div class="activity-time">${formatDate(item.created_at)}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// ===== USERS MANAGEMENT =====
async function loadUsers() {
    try {
        const { data, error } = await supabaseClient
            .from('usuarios')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) throw error;

        usersData = data || [];
        renderUsersTable(usersData);

    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Error al cargar usuarios', 'error');
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-tbody');

    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No hay usuarios</td></tr>';
        return;
    }

    // Pagination
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    const paginatedUsers = users.slice(start, start + ITEMS_PER_PAGE);

    tbody.innerHTML = paginatedUsers.map(user => `
        <tr>
            <td><code>${user.user_id}</code></td>
            <td>${escapeHtml(user.first_name || '-')} ${escapeHtml(user.last_name || '')}</td>
            <td>${user.username ? '@' + escapeHtml(user.username) : '-'}</td>
            <td><strong>${user.credit_balance || 0}</strong></td>
            <td><span class="badge-status badge-${getStatusClass(user.subscription_status)}">${user.subscription_status || 'inactive'}</span></td>
            <td>${user.level || 1}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <button class="btn-secondary btn-sm" onclick="editUser(${user.user_id})">✏️</button>
                <button class="btn-secondary btn-sm" onclick="sendMessageToUser(${user.user_id})">💬</button>
            </td>
        </tr>
    `).join('');

    renderPagination(users.length, 'users-pagination');
}

function filterUsers() {
    const query = document.getElementById('user-search').value.toLowerCase();

    if (!query) {
        renderUsersTable(usersData);
        return;
    }

    const filtered = usersData.filter(user =>
        String(user.user_id).includes(query) ||
        (user.first_name && user.first_name.toLowerCase().includes(query)) ||
        (user.username && user.username.toLowerCase().includes(query))
    );

    renderUsersTable(filtered);
}

function editUser(userId) {
    const user = usersData.find(u => u.user_id === userId);
    if (!user) return;

    document.getElementById('edit-user-id').value = userId;
    document.getElementById('edit-user-credits').value = user.credit_balance || 0;
    document.getElementById('edit-user-sub-status').value = user.subscription_status || 'inactive';
    document.getElementById('edit-user-level').value = user.level || 1;
    document.getElementById('edit-user-xp').value = user.xp || 0;

    if (user.subscription_expiry_date) {
        const date = new Date(user.subscription_expiry_date);
        document.getElementById('edit-user-expiry').value = date.toISOString().slice(0, 16);
    }

    document.getElementById('modal-edit-user').classList.remove('hidden');
}

async function saveUserChanges() {
    const userId = parseInt(document.getElementById('edit-user-id').value);

    const updates = {
        credit_balance: parseInt(document.getElementById('edit-user-credits').value) || 0,
        subscription_status: document.getElementById('edit-user-sub-status').value,
        level: parseInt(document.getElementById('edit-user-level').value) || 1,
        xp: parseInt(document.getElementById('edit-user-xp').value) || 0
    };

    const expiry = document.getElementById('edit-user-expiry').value;
    if (expiry) {
        updates.subscription_expiry_date = new Date(expiry).toISOString();
    }

    try {
        const { error } = await supabaseClient
            .from('usuarios')
            .update(updates)
            .eq('user_id', userId);

        if (error) throw error;

        closeAllModals();
        showToast('Usuario actualizado correctamente', 'success');
        await loadUsers();

    } catch (error) {
        console.error('Error updating user:', error);
        showToast('Error al actualizar usuario', 'error');
    }
}

function exportUsersCSV() {
    if (!usersData.length) {
        showToast('No hay datos para exportar', 'error');
        return;
    }

    const headers = ['user_id', 'first_name', 'last_name', 'username', 'credit_balance', 'subscription_status', 'level', 'xp', 'created_at'];
    const csvContent = [
        headers.join(','),
        ...usersData.map(user => headers.map(h => `"${user[h] || ''}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kaliroot_users_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);

    showToast('Exportación completada', 'success');
}

async function sendMessageToUser(userId) {
    if (!botToken) {
        showToast('Configura el Bot Token para enviar mensajes', 'error');
        return;
    }

    const message = prompt('Mensaje a enviar al usuario:');
    if (!message) return;

    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: userId,
                text: message,
                parse_mode: 'HTML'
            })
        });

        const result = await response.json();

        if (result.ok) {
            showToast('Mensaje enviado correctamente', 'success');
        } else {
            throw new Error(result.description);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        showToast('Error al enviar mensaje: ' + error.message, 'error');
    }
}

// ===== SUBSCRIPTIONS =====
async function loadSubscriptions() {
    try {
        const filter = document.getElementById('sub-filter').value;

        let query = supabaseClient
            .from('usuarios')
            .select('user_id, first_name, username, subscription_status, subscription_expiry_date, nowpayments_invoice_id, updated_at')
            .order('updated_at', { ascending: false });

        if (filter !== 'all') {
            if (filter === 'expired') {
                query = query.lt('subscription_expiry_date', new Date().toISOString());
            } else {
                query = query.eq('subscription_status', filter);
            }
        }

        const { data, error } = await query;

        if (error) throw error;

        const tbody = document.getElementById('subs-tbody');

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading">No hay suscripciones</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(sub => `
            <tr>
                <td>${escapeHtml(sub.first_name || 'User')} (${sub.user_id})</td>
                <td><span class="badge-status badge-${getStatusClass(sub.subscription_status)}">${sub.subscription_status || 'inactive'}</span></td>
                <td>${formatDate(sub.updated_at)}</td>
                <td>${sub.subscription_expiry_date ? formatDate(sub.subscription_expiry_date) : '-'}</td>
                <td><code>${sub.nowpayments_invoice_id || '-'}</code></td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="editUser(${sub.user_id})">✏️</button>
                    <button class="btn-secondary btn-sm" onclick="activateSubscription(${sub.user_id})">✅</button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading subscriptions:', error);
        showToast('Error al cargar suscripciones', 'error');
    }
}

async function activateSubscription(userId) {
    if (!confirm('¿Activar suscripción por 30 días para este usuario?')) return;

    try {
        const expiryDate = new Date();
        expiryDate.setDate(expiryDate.getDate() + 30);

        const { error } = await supabaseClient
            .from('usuarios')
            .update({
                subscription_status: 'active',
                subscription_expiry_date: expiryDate.toISOString()
            })
            .eq('user_id', userId);

        if (error) throw error;

        showToast('Suscripción activada correctamente', 'success');
        await loadSubscriptions();

    } catch (error) {
        console.error('Error activating subscription:', error);
        showToast('Error al activar suscripción', 'error');
    }
}

// ===== RESOURCES MANAGEMENT =====
async function loadResources() {
    try {
        const { data, error } = await supabaseClient
            .from('download_resources')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            if (error.code === '42P01') {
                // Table doesn't exist
                document.getElementById('resources-grid').innerHTML = `
                    <div class="resource-placeholder">
                        <p>⚠️ La tabla <code>download_resources</code> no existe.</p>
                        <p>Ejecuta el script <code>create_resources_table.sql</code> en Supabase.</p>
                    </div>
                `;
                return;
            }
            throw error;
        }

        resourcesData = data || [];
        renderResourcesGrid();

    } catch (error) {
        console.error('Error loading resources:', error);
        showToast('Error al cargar recursos', 'error');
    }
}

function renderResourcesGrid() {
    const grid = document.getElementById('resources-grid');

    if (!resourcesData.length) {
        grid.innerHTML = '<div class="resource-placeholder">No hay recursos. ¡Agrega el primero!</div>';
        return;
    }

    grid.innerHTML = resourcesData.map(resource => `
        <div class="resource-card-admin">
            <div class="resource-header">
                <div class="resource-icon-large">${resource.icon || '📦'}</div>
                <div class="resource-info">
                    <div class="resource-title">${escapeHtml(resource.title)}</div>
                    <div class="resource-desc">${escapeHtml(resource.description || '')}</div>
                    <div class="resource-meta">
                        <span>📁 ${resource.file_size || 'N/A'}</span>
                        <span>📂 ${resource.category || 'general'}</span>
                        <span class="badge-status ${resource.is_active ? 'badge-active' : 'badge-inactive'}">
                            ${resource.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                    </div>
                </div>
            </div>
            <div class="resource-footer">
                <div class="resource-stats">📥 ${resource.download_count || 0} descargas</div>
                <div class="resource-actions">
                    <button class="btn-secondary btn-sm" onclick="testResourceLink('${resource.drive_file_id}')">🔗</button>
                    <button class="btn-secondary btn-sm" onclick="editResource(${resource.id})">✏️</button>
                    <button class="btn-danger btn-sm" onclick="deleteResource(${resource.id})">🗑️</button>
                </div>
            </div>
        </div>
    `).join('');
}

function openResourceModal(resourceId = null) {
    const modal = document.getElementById('modal-resource');
    const title = document.getElementById('resource-modal-title');

    if (resourceId) {
        const resource = resourcesData.find(r => r.id === resourceId);
        if (!resource) return;

        title.textContent = '✏️ Editar Recurso';
        document.getElementById('resource-id').value = resource.id;
        document.getElementById('resource-title').value = resource.title || '';
        document.getElementById('resource-icon').value = resource.icon || '📦';
        document.getElementById('resource-description').value = resource.description || '';
        document.getElementById('resource-drive-id').value = resource.drive_file_id || '';
        document.getElementById('resource-size').value = resource.file_size || '';
        document.getElementById('resource-image').value = resource.image_url || '';
        document.getElementById('resource-category').value = resource.category || 'tools';
        document.getElementById('resource-active').checked = resource.is_active !== false;
    } else {
        title.textContent = '➕ Nuevo Recurso';
        document.getElementById('resource-id').value = '';
        document.getElementById('resource-title').value = '';
        document.getElementById('resource-icon').value = '📦';
        document.getElementById('resource-description').value = '';
        document.getElementById('resource-drive-id').value = '';
        document.getElementById('resource-size').value = '';
        document.getElementById('resource-image').value = '';
        document.getElementById('resource-category').value = 'tools';
        document.getElementById('resource-active').checked = true;
    }

    modal.classList.remove('hidden');
}

function editResource(resourceId) {
    openResourceModal(resourceId);
}

async function saveResource() {
    const id = document.getElementById('resource-id').value;
    const title = document.getElementById('resource-title').value.trim();
    const driveId = document.getElementById('resource-drive-id').value.trim();

    if (!title || !driveId) {
        showToast('Título y Drive ID son obligatorios', 'error');
        return;
    }

    const resourceData = {
        title,
        icon: document.getElementById('resource-icon').value || '📦',
        description: document.getElementById('resource-description').value,
        drive_file_id: driveId,
        file_size: document.getElementById('resource-size').value || 'N/A',
        image_url: document.getElementById('resource-image').value || null,
        category: document.getElementById('resource-category').value,
        is_active: document.getElementById('resource-active').checked
    };

    try {
        let error;

        if (id) {
            // Update
            ({ error } = await supabaseClient
                .from('download_resources')
                .update(resourceData)
                .eq('id', parseInt(id)));
        } else {
            // Insert
            ({ error } = await supabaseClient
                .from('download_resources')
                .insert([resourceData]));
        }

        if (error) throw error;

        closeAllModals();
        showToast(id ? 'Recurso actualizado' : 'Recurso creado', 'success');
        await loadResources();

    } catch (error) {
        console.error('Error saving resource:', error);
        showToast('Error al guardar: ' + error.message, 'error');
    }
}

async function deleteResource(resourceId) {
    if (!confirm('¿Eliminar este recurso definitivamente?')) return;

    try {
        const { error } = await supabaseClient
            .from('download_resources')
            .delete()
            .eq('id', resourceId);

        if (error) throw error;

        showToast('Recurso eliminado', 'success');
        await loadResources();

    } catch (error) {
        console.error('Error deleting resource:', error);
        showToast('Error al eliminar', 'error');
    }
}

function testResourceLink(driveId) {
    const url = `https://drive.google.com/uc?export=download&id=${driveId}`;
    window.open(url, '_blank');
}

// ===== LEARNING MODULES =====
async function loadLearningModules() {
    try {
        const { data, error } = await supabaseClient
            .from('user_modules')
            .select('*')
            .order('completed_at', { ascending: false })
            .limit(100);

        const tbody = document.getElementById('modules-tbody');

        if (error) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">Error: ' + error.message + '</td></tr>';
            return;
        }

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No hay módulos completados</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(m => `
            <tr>
                <td>${m.id}</td>
                <td>${m.user_id}</td>
                <td>Módulo #${m.module_id}</td>
                <td>${formatDate(m.completed_at)}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading modules:', error);
    }
}

// ===== BADGES =====
async function loadBadges() {
    try {
        const { data, error } = await supabaseClient
            .from('badges')
            .select('*')
            .order('id', { ascending: true });

        const grid = document.getElementById('badges-grid');

        if (error) {
            grid.innerHTML = '<div class="badge-placeholder">Error: ' + error.message + '</div>';
            return;
        }

        if (!data || data.length === 0) {
            grid.innerHTML = '<div class="badge-placeholder">No hay insignias definidas</div>';
            return;
        }

        grid.innerHTML = data.map(badge => `
            <div class="badge-card">
                <div class="badge-icon">${badge.icon || '🏆'}</div>
                <div class="badge-name">${escapeHtml(badge.name)}</div>
                <div class="badge-desc">${escapeHtml(badge.description || '')}</div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading badges:', error);
    }
}

// ===== AUDIT LOG =====
async function loadAuditLog() {
    try {
        const filter = document.getElementById('audit-type-filter').value;

        let query = supabaseClient
            .from('audit_log')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(100);

        if (filter !== 'all') {
            query = query.eq('event_type', filter);
        }

        const { data, error } = await query;

        const tbody = document.getElementById('audit-tbody');

        if (error) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">Error: ' + error.message + '</td></tr>';
            return;
        }

        if (!data || data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No hay logs</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(log => `
            <tr>
                <td>${formatDate(log.created_at)}</td>
                <td>${log.user_id || '-'}</td>
                <td><code>${log.event_type}</code></td>
                <td><small>${JSON.stringify(log.details || {})}</small></td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading audit log:', error);
    }
}

// ===== UTILITIES =====
function closeAllModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatNumber(num) {
    return new Intl.NumberFormat('es-ES').format(num);
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function getStatusClass(status) {
    const classes = {
        active: 'active',
        pending: 'pending',
        inactive: 'inactive',
        expired: 'expired'
    };
    return classes[status] || 'inactive';
}

function getActivityIcon(eventType) {
    const icons = {
        user_created: '👤',
        add_credits: '💰',
        deduct_credit: '💸',
        subscription_activated: '💎',
        module_completed: '📚'
    };
    return icons[eventType] || '📝';
}

function renderPagination(totalItems, containerId) {
    const container = document.getElementById(containerId);
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <button ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">← Anterior</button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
    }

    html += `
        <button ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">Siguiente →</button>
    `;

    container.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    renderUsersTable(usersData);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Make functions available globally for onclick handlers
window.editUser = editUser;
window.sendMessageToUser = sendMessageToUser;
window.activateSubscription = activateSubscription;
window.editResource = editResource;
window.deleteResource = deleteResource;
window.testResourceLink = testResourceLink;
window.changePage = changePage;

// ===== TELEGRAM API CREDENTIALS FUNCTIONS =====

function loadSavedTelegramCredentials() {
    telegramApiId = localStorage.getItem('telegram_api_id') || '';
    telegramApiHash = localStorage.getItem('telegram_api_hash') || '';
    telegramAppTitle = localStorage.getItem('telegram_app_title') || '';
    telegramShortName = localStorage.getItem('telegram_short_name') || '';

    if (telegramApiId) document.getElementById('telegram-api-id').value = telegramApiId;
    if (telegramApiHash) document.getElementById('telegram-api-hash').value = telegramApiHash;
    if (telegramAppTitle) document.getElementById('telegram-app-title').value = telegramAppTitle;
    if (telegramShortName) document.getElementById('telegram-short-name').value = telegramShortName;
}

function saveTelegramCredentials() {
    telegramApiId = document.getElementById('telegram-api-id').value.trim();
    telegramApiHash = document.getElementById('telegram-api-hash').value.trim();
    telegramAppTitle = document.getElementById('telegram-app-title').value.trim();
    telegramShortName = document.getElementById('telegram-short-name').value.trim();

    if (document.getElementById('remember-creds').checked) {
        localStorage.setItem('telegram_api_id', telegramApiId);
        localStorage.setItem('telegram_api_hash', telegramApiHash);
        localStorage.setItem('telegram_app_title', telegramAppTitle);
        localStorage.setItem('telegram_short_name', telegramShortName);
    }
}

// Update loadSavedCredentials to also load Telegram API credentials
const originalLoadSavedCredentials = loadSavedCredentials;
function loadSavedCredentialsExtended() {
    originalLoadSavedCredentials();
    loadSavedTelegramCredentials();
}

// Replace the original function call
document.addEventListener('DOMContentLoaded', () => {
    loadSavedCredentialsExtended();
});

// Modify handleLogin to also save Telegram credentials
const originalHandleLogin = handleLogin;
async function handleLoginExtended() {
    saveTelegramCredentials();
    await originalHandleLogin();
    loadSettingsSection();
}

// Override the login button handler
document.getElementById('login-btn').removeEventListener('click', handleLogin);
document.getElementById('login-btn').addEventListener('click', handleLoginExtended);

// ===== TOGGLE SECTION (COLLAPSIBLE) =====
function toggleSection(element) {
    const content = element.nextElementSibling;
    if (content) {
        content.classList.toggle('collapsed');
    }
}
window.toggleSection = toggleSection;

// ===== TOGGLE PASSWORD VISIBILITY =====
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.type = input.type === 'password' ? 'text' : 'password';
    }
}
window.togglePasswordVisibility = togglePasswordVisibility;

// ===== SETTINGS SECTION =====
function loadSettingsSection() {
    // Fill in settings fields
    const supabaseUrl = document.getElementById('supabase-url').value;

    if (document.getElementById('settings-supabase-url')) {
        document.getElementById('settings-supabase-url').value = supabaseUrl;
    }
    if (document.getElementById('settings-bot-token')) {
        document.getElementById('settings-bot-token').value = botToken || '';
    }
    if (document.getElementById('settings-api-id')) {
        document.getElementById('settings-api-id').value = telegramApiId;
    }
    if (document.getElementById('settings-api-hash')) {
        document.getElementById('settings-api-hash').value = telegramApiHash;
    }
    if (document.getElementById('settings-app-title')) {
        document.getElementById('settings-app-title').value = telegramAppTitle;
    }
    if (document.getElementById('settings-short-name')) {
        document.getElementById('settings-short-name').value = telegramShortName;
    }

    // Generate env vars preview
    generateEnvVarsPreview();
}

function generateEnvVarsPreview() {
    const supabaseUrl = document.getElementById('supabase-url').value;
    const supabaseKey = document.getElementById('supabase-key').value;

    const envVars = `# ====== KALIROOT BOT ENVIRONMENT VARIABLES ======
# Generated from Admin Panel on ${new Date().toISOString().split('T')[0]}

# ===== SUPABASE =====
SUPABASE_URL=${supabaseUrl}
SUPABASE_ANON_KEY=${supabaseKey}
SUPABASE_SERVICE_KEY=${supabaseKey}

# ===== TELEGRAM BOT =====
TELEGRAM_BOT_TOKEN=${botToken || 'YOUR_BOT_TOKEN'}

# ===== TELEGRAM API (for advanced features) =====
TELEGRAM_API_ID=${telegramApiId || 'YOUR_API_ID'}
TELEGRAM_API_HASH=${telegramApiHash || 'YOUR_API_HASH'}
TELEGRAM_APP_TITLE=${telegramAppTitle || 'kaliroot'}
TELEGRAM_SHORT_NAME=${telegramShortName || 'kaliroot'}

# ===== OTHER CONFIGS =====
LOG_LEVEL=INFO
DEFAULT_CREDITS_ON_REGISTER=20
`;

    const envContent = document.getElementById('env-vars-content');
    if (envContent) {
        envContent.textContent = envVars;
    }

    return envVars;
}

function copyEnvVars() {
    const envVars = generateEnvVarsPreview();
    navigator.clipboard.writeText(envVars).then(() => {
        showToast('Variables de entorno copiadas al portapapeles', 'success');
    }).catch(err => {
        showToast('Error al copiar: ' + err, 'error');
    });
}
window.copyEnvVars = copyEnvVars;

function downloadEnvFile() {
    const envVars = generateEnvVarsPreview();
    const blob = new Blob([envVars], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '.env';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Archivo .env descargado', 'success');
}
window.downloadEnvFile = downloadEnvFile;

// Add settings to navigation titles
const originalNavigateToSection = navigateToSection;
function navigateToSectionExtended(section) {
    currentSection = section;

    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(sec => {
        sec.classList.toggle('active', sec.id === `section-${section}`);
    });

    // Update title
    const titles = {
        overview: 'Dashboard',
        users: 'Gestión de Usuarios',
        subscriptions: 'Suscripciones',
        resources: 'Recursos de Descarga',
        learning: 'Módulos de Aprendizaje',
        badges: 'Insignias',
        audit: 'Log de Auditoría',
        telegram: 'Telegram Manager',
        settings: 'Configuración'
    };
    document.getElementById('page-title').textContent = titles[section] || 'Dashboard';

    // Close mobile menu
    document.querySelector('.sidebar').classList.remove('open');

    // Load section data
    if (section === 'settings') {
        loadSettingsSection();
    } else if (section === 'telegram') {
        loadTelegramData();
    } else {
        refreshCurrentSection();
    }
}

// Override navigate function
window.navigateToSection = navigateToSectionExtended;

// Re-attach event listeners with the new function
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const section = item.dataset.section;
        navigateToSectionExtended(section);
    });
});

// ===== TELEGRAM FUNCTIONS =====

async function loadTelegramData() {
    if (!botToken) {
        showToast('Bot Token no configurado', 'error');
        return;
    }

    await Promise.all([
        getBotInfo(),
        getWebhookInfo(),
        loadTelegramStats()
    ]);
}
window.loadTelegramData = loadTelegramData;

async function getBotInfo() {
    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/getMe`);
        const data = await response.json();

        if (data.ok) {
            const bot = data.result;
            document.getElementById('bot-name').textContent = bot.first_name;
            document.getElementById('bot-username').textContent = '@' + bot.username;
            document.getElementById('bot-id').textContent = bot.id;
            document.getElementById('bot-can-join').textContent = bot.can_join_groups ? '✅ Sí' : '❌ No';
            document.getElementById('bot-can-read').textContent = bot.can_read_all_group_messages ? '✅ Sí' : '❌ No';
            document.getElementById('bot-inline').textContent = bot.supports_inline_queries ? '✅ Sí' : '❌ No';
        } else {
            showToast('Error al obtener info del bot: ' + data.description, 'error');
        }
    } catch (error) {
        console.error('Error getting bot info:', error);
        showToast('Error de conexión con Telegram API', 'error');
    }
}

async function getWebhookInfo() {
    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/getWebhookInfo`);
        const data = await response.json();

        if (data.ok) {
            const webhook = data.result;
            const container = document.getElementById('webhook-info');

            const hasWebhook = webhook.url && webhook.url.length > 0;

            container.innerHTML = `
                <div style="margin-bottom: 12px;">
                    <span class="webhook-status ${hasWebhook ? 'active' : 'inactive'}">
                        ${hasWebhook ? '🟢 Activo' : '🔴 Inactivo'}
                    </span>
                </div>
                <div class="label">URL del Webhook:</div>
                <div class="value"><code>${webhook.url || 'No configurado'}</code></div>
                ${webhook.last_error_message ? `
                    <div class="label" style="margin-top: 12px; color: var(--accent-red);">Último error:</div>
                    <div class="value" style="color: var(--accent-red);">${webhook.last_error_message}</div>
                ` : ''}
                <div class="label" style="margin-top: 12px;">Updates pendientes:</div>
                <div class="value">${webhook.pending_update_count || 0}</div>
            `;

            // Update pending updates stat
            document.getElementById('tg-pending-updates').textContent = webhook.pending_update_count || 0;
        }
    } catch (error) {
        console.error('Error getting webhook info:', error);
    }
}
window.getWebhookInfo = getWebhookInfo;

async function deleteWebhook() {
    if (!confirm('¿Eliminar el webhook? El bot dejará de recibir actualizaciones hasta que se configure de nuevo.')) return;

    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/deleteWebhook`);
        const data = await response.json();

        if (data.ok) {
            showToast('Webhook eliminado correctamente', 'success');
            await getWebhookInfo();
        } else {
            showToast('Error: ' + data.description, 'error');
        }
    } catch (error) {
        showToast('Error de conexión', 'error');
    }
}
window.deleteWebhook = deleteWebhook;

async function loadTelegramStats() {
    try {
        // Get users count from our database
        const { count: usersCount } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true });

        document.getElementById('tg-total-users').textContent = usersCount || 0;

        // Get active chats (users with recent activity)
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        const { count: activeChats } = await supabaseClient
            .from('usuarios')
            .select('*', { count: 'exact', head: true })
            .gte('updated_at', thirtyDaysAgo.toISOString());

        document.getElementById('tg-total-chats').textContent = activeChats || 0;

        // Messages today from audit log
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const { count: messagesToday } = await supabaseClient
            .from('audit_log')
            .select('*', { count: 'exact', head: true })
            .gte('created_at', today.toISOString());

        document.getElementById('tg-messages-today').textContent = messagesToday || 0;

    } catch (error) {
        console.error('Error loading telegram stats:', error);
    }
}

async function searchChat() {
    const query = document.getElementById('chat-search').value.trim();
    if (!query) {
        showToast('Ingresa un @username o ID de chat', 'error');
        return;
    }

    try {
        // Try to get chat info
        const response = await fetch(`https://api.telegram.org/bot${botToken}/getChat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: query })
        });

        const data = await response.json();

        const resultContainer = document.getElementById('chat-search-result');

        if (data.ok) {
            const chat = data.result;
            const type = chat.type === 'private' ? '👤 Privado' :
                chat.type === 'group' ? '👥 Grupo' :
                    chat.type === 'supergroup' ? '👥 Supergrupo' :
                        chat.type === 'channel' ? '📢 Canal' : chat.type;

            resultContainer.classList.remove('hidden');
            resultContainer.innerHTML = `
                <div class="chat-info">
                    <div class="chat-avatar">${chat.type === 'channel' ? '📢' : chat.type === 'private' ? '👤' : '👥'}</div>
                    <div class="chat-details">
                        <h4>${escapeHtml(chat.title || chat.first_name || 'Sin nombre')}</h4>
                        <p>${chat.username ? '@' + chat.username : 'Sin username'}</p>
                    </div>
                </div>
                <div class="chat-meta">
                    <span>Tipo: <strong>${type}</strong></span>
                    <span>ID: <strong>${chat.id}</strong></span>
                    ${chat.members_count ? `<span>Miembros: <strong>${chat.members_count}</strong></span>` : ''}
                </div>
                <div style="margin-top: 12px;">
                    <button class="btn-secondary btn-sm" onclick="sendMessageToChat('${chat.id}')">💬 Enviar mensaje</button>
                    ${chat.type !== 'private' ? `<button class="btn-secondary btn-sm" onclick="getChatMemberCount('${chat.id}')">👥 Ver miembros</button>` : ''}
                </div>
            `;
        } else {
            resultContainer.classList.remove('hidden');
            resultContainer.innerHTML = `
                <div style="color: var(--accent-red);">
                    ❌ ${data.description || 'Chat no encontrado'}
                </div>
                <p style="color: var(--text-muted); margin-top: 8px; font-size: 12px;">
                    Asegúrate de que el bot esté en el chat o usa el ID numérico.
                </p>
            `;
        }
    } catch (error) {
        console.error('Error searching chat:', error);
        showToast('Error de conexión', 'error');
    }
}
window.searchChat = searchChat;

async function sendMessageToChat(chatId) {
    const message = prompt('Mensaje a enviar:');
    if (!message) return;

    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: chatId,
                text: message,
                parse_mode: 'HTML'
            })
        });

        const data = await response.json();

        if (data.ok) {
            showToast('Mensaje enviado correctamente', 'success');
        } else {
            showToast('Error: ' + data.description, 'error');
        }
    } catch (error) {
        showToast('Error de conexión', 'error');
    }
}
window.sendMessageToChat = sendMessageToChat;

async function getChatMemberCount(chatId) {
    try {
        const response = await fetch(`https://api.telegram.org/bot${botToken}/getChatMemberCount`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });

        const data = await response.json();

        if (data.ok) {
            showToast(`El chat tiene ${data.result} miembros`, 'info');
        } else {
            showToast('Error: ' + data.description, 'error');
        }
    } catch (error) {
        showToast('Error de conexión', 'error');
    }
}
window.getChatMemberCount = getChatMemberCount;

function previewBroadcast() {
    const message = document.getElementById('broadcast-message').value;
    if (!message) {
        showToast('Escribe un mensaje primero', 'error');
        return;
    }

    // Show preview in a modal or alert
    const preview = document.createElement('div');
    preview.innerHTML = message;
    alert('Vista previa del mensaje:\n\n' + preview.textContent);
}
window.previewBroadcast = previewBroadcast;

async function sendBroadcast() {
    const message = document.getElementById('broadcast-message').value.trim();
    const target = document.getElementById('broadcast-target').value;

    if (!message) {
        showToast('Escribe un mensaje primero', 'error');
        return;
    }

    const confirmMsg = `¿Enviar mensaje a ${target === 'all' ? 'TODOS los usuarios' : target === 'premium' ? 'usuarios PREMIUM' : 'usuarios FREE'}?`;
    if (!confirm(confirmMsg)) return;

    try {
        // Get users based on target
        let query = supabaseClient.from('usuarios').select('user_id');

        if (target === 'premium') {
            query = query.eq('subscription_status', 'active');
        } else if (target === 'free') {
            query = query.or('subscription_status.is.null,subscription_status.neq.active');
        }

        const { data: users, error } = await query;

        if (error) throw error;

        if (!users || users.length === 0) {
            showToast('No hay usuarios para enviar', 'error');
            return;
        }

        showToast(`Enviando a ${users.length} usuarios...`, 'info');

        let sent = 0;
        let failed = 0;

        for (const user of users) {
            try {
                const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chat_id: user.user_id,
                        text: message,
                        parse_mode: 'HTML'
                    })
                });

                const data = await response.json();
                if (data.ok) {
                    sent++;
                } else {
                    failed++;
                }

                // Small delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 50));

            } catch (e) {
                failed++;
            }
        }

        showToast(`Broadcast completado: ${sent} enviados, ${failed} fallidos`, sent > 0 ? 'success' : 'error');

    } catch (error) {
        console.error('Error sending broadcast:', error);
        showToast('Error al enviar broadcast', 'error');
    }
}
window.sendBroadcast = sendBroadcast;

// ===== MTPROTO API (Backend Python) =====
const MTPROTO_API_URL = 'http://localhost:8081/api';

// Check if MTProto API is available
async function checkMTProtoAPI() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/health`, { timeout: 2000 });
        return response.ok;
    } catch {
        return false;
    }
}

// Check MTProto auth status
async function checkMTProtoAuth() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/auth/status`);
        const data = await response.json();
        return data;
    } catch {
        return { authorized: false, error: 'API no disponible' };
    }
}

// Send phone code for MTProto auth
async function sendMTProtoCode(phone) {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/auth/code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone })
        });
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message };
    }
}
window.sendMTProtoCode = sendMTProtoCode;

// Verify MTProto code
async function verifyMTProtoCode(phone, code, password = null) {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/auth/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, code, password })
        });
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message };
    }
}
window.verifyMTProtoCode = verifyMTProtoCode;

// Get MTProto Stats
async function getMTProtoStats() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/stats`);
        if (!response.ok) throw new Error('Not authorized');
        return await response.json();
    } catch {
        return null;
    }
}

// Get MTProto Channels
async function getMTProtoChannels() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/channels`);
        if (!response.ok) throw new Error('Not authorized');
        return await response.json();
    } catch {
        return { channels: [], count: 0 };
    }
}

// Get MTProto Groups
async function getMTProtoGroups() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/groups`);
        if (!response.ok) throw new Error('Not authorized');
        return await response.json();
    } catch {
        return { groups: [], count: 0 };
    }
}

// Get MTProto Dialogs
async function getMTProtoDialogs() {
    try {
        const response = await fetch(`${MTPROTO_API_URL}/dialogs?limit=100`);
        if (!response.ok) throw new Error('Not authorized');
        return await response.json();
    } catch {
        return { dialogs: [], count: 0 };
    }
}

// Update Telegram section with MTProto data
async function updateTelegramWithMTProto() {
    const apiAvailable = await checkMTProtoAPI();

    if (!apiAvailable) {
        console.log('MTProto API no disponible, usando solo Bot API');
        return false;
    }

    const authStatus = await checkMTProtoAuth();

    if (!authStatus.authorized) {
        // Show auth required message
        showMTProtoAuthUI();
        return false;
    }

    // Load MTProto data
    const [stats, channels, groups] = await Promise.all([
        getMTProtoStats(),
        getMTProtoChannels(),
        getMTProtoGroups()
    ]);

    if (stats) {
        // Update stats in UI
        document.getElementById('tg-total-chats').textContent = stats.total_dialogs || 0;

        // Add MTProto-specific stats if elements exist
        const mtprotoStatsContainer = document.getElementById('mtproto-stats');
        if (mtprotoStatsContainer) {
            mtprotoStatsContainer.innerHTML = `
                <div class="quick-stat">
                    <span class="quick-stat-icon">📢</span>
                    <span class="quick-stat-value">${stats.channels || 0}</span>
                    <span class="quick-stat-label">Canales</span>
                </div>
                <div class="quick-stat">
                    <span class="quick-stat-icon">👥</span>
                    <span class="quick-stat-value">${stats.supergroups || 0}</span>
                    <span class="quick-stat-label">Supergrupos</span>
                </div>
                <div class="quick-stat">
                    <span class="quick-stat-icon">🤖</span>
                    <span class="quick-stat-value">${stats.bots || 0}</span>
                    <span class="quick-stat-label">Bots</span>
                </div>
                <div class="quick-stat">
                    <span class="quick-stat-icon">👑</span>
                    <span class="quick-stat-value">${stats.admin_channels || 0}</span>
                    <span class="quick-stat-label">Admin en Canales</span>
                </div>
            `;
        }
    }

    // Update channels list
    if (channels.count > 0) {
        const channelsList = document.getElementById('chats-list');
        if (channelsList) {
            channelsList.innerHTML = `
                <h4 style="margin-bottom: 12px;">📢 Canales Administrados (${channels.count})</h4>
                ${channels.channels.map(ch => `
                    <div class="chat-item">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 24px;">📢</span>
                            <div>
                                <strong>${escapeHtml(ch.name)}</strong>
                                ${ch.username ? `<br><small>@${ch.username}</small>` : ''}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: var(--accent-blue);">${ch.participants_count || '?'} miembros</span>
                            ${ch.is_creator ? '<br><small style="color: var(--accent-green);">👑 Creador</small>' : ''}
                            ${ch.is_admin && !ch.is_creator ? '<br><small style="color: var(--accent-yellow);">⭐ Admin</small>' : ''}
                        </div>
                    </div>
                `).join('')}
                
                ${groups.count > 0 ? `
                    <h4 style="margin: 20px 0 12px;">👥 Grupos (${groups.count})</h4>
                    ${groups.groups.slice(0, 10).map(g => `
                        <div class="chat-item">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span style="font-size: 24px;">👥</span>
                                <div>
                                    <strong>${escapeHtml(g.name)}</strong>
                                    ${g.username ? `<br><small>@${g.username}</small>` : ''}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <span style="color: var(--accent-blue);">${g.participants_count || '?'} miembros</span>
                            </div>
                        </div>
                    `).join('')}
                ` : ''}
            `;
        }
    }

    return true;
}

function showMTProtoAuthUI() {
    const container = document.getElementById('chats-list');
    if (!container) return;

    container.innerHTML = `
        <div class="card" style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(59, 130, 246, 0.1)); padding: 20px;">
            <h4 style="margin-bottom: 12px;">🔐 Autenticación Telegram API</h4>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">
                Para acceder a canales y grupos administrados, necesitas autenticarte con tu cuenta de Telegram.
            </p>
            <div class="form-group">
                <label>Número de teléfono (con código de país)</label>
                <input type="text" id="mtproto-phone" placeholder="+51912345678" style="max-width: 300px;">
            </div>
            <button class="btn-primary" onclick="startMTProtoAuth()">📲 Enviar código</button>
            
            <div id="mtproto-code-form" class="hidden" style="margin-top: 16px;">
                <div class="form-group">
                    <label>Código de verificación</label>
                    <input type="text" id="mtproto-code" placeholder="12345" style="max-width: 200px;">
                </div>
                <div class="form-group hidden" id="mtproto-2fa-group">
                    <label>Contraseña 2FA (si está habilitada)</label>
                    <input type="password" id="mtproto-password" placeholder="Tu contraseña" style="max-width: 300px;">
                </div>
                <button class="btn-primary" onclick="completeMTProtoAuth()">✅ Verificar</button>
            </div>
        </div>
    `;
}

async function startMTProtoAuth() {
    const phone = document.getElementById('mtproto-phone').value.trim();
    if (!phone) {
        showToast('Ingresa tu número de teléfono', 'error');
        return;
    }

    showToast('Enviando código...', 'info');
    const result = await sendMTProtoCode(phone);

    if (result.success) {
        showToast('Código enviado a tu Telegram', 'success');
        document.getElementById('mtproto-code-form').classList.remove('hidden');
    } else {
        showToast('Error: ' + (result.detail || result.error), 'error');
    }
}
window.startMTProtoAuth = startMTProtoAuth;

async function completeMTProtoAuth() {
    const phone = document.getElementById('mtproto-phone').value.trim();
    const code = document.getElementById('mtproto-code').value.trim();
    const password = document.getElementById('mtproto-password').value.trim();

    if (!code) {
        showToast('Ingresa el código', 'error');
        return;
    }

    showToast('Verificando...', 'info');
    const result = await verifyMTProtoCode(phone, code, password || null);

    if (result.success) {
        showToast('¡Autenticado correctamente!', 'success');
        // Reload telegram data
        loadTelegramData();
    } else if (result.detail && result.detail.includes('2FA')) {
        document.getElementById('mtproto-2fa-group').classList.remove('hidden');
        showToast('Se requiere contraseña 2FA', 'info');
    } else {
        showToast('Error: ' + (result.detail || result.error), 'error');
    }
}
window.completeMTProtoAuth = completeMTProtoAuth;

// Enhanced loadTelegramData to include MTProto
const originalLoadTelegramData = loadTelegramData;
async function loadTelegramDataEnhanced() {
    // First load bot API data
    await originalLoadTelegramData();

    // Then try to load MTProto data
    await updateTelegramWithMTProto();
}

// Override the function
window.loadTelegramData = loadTelegramDataEnhanced;
