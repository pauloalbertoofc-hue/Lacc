/**
 * LigaHub - Cliente de API
 */
const API_BASE = '/api';

const api = {
    async request(endpoint, options = {}) {
        try {
            const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
            const headers = options.headers || {};
            
            // Injeção automática de Token JWT Bearer
            const token = localStorage.getItem('lacc_token');
            if (token && !headers['Authorization']) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            if (!(options.body instanceof FormData) && !headers['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }

            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                // Se a sessão expirou e estamos no admin, redireciona para login
                if (window.location.pathname.startsWith('/admin')) {
                    localStorage.removeItem('lacc_token');
                    localStorage.removeItem('lacc_auth');
                    window.location.href = '/?login=expired';
                }
            }

            if (!response.ok) {
                let errorMsg = `Erro ${response.status}: ${response.statusText}`;
                try {
                    const errData = await response.json();
                    if (errData && errData.detail) {
                        errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
                    }
                } catch (e) {}
                throw new Error(errorMsg);
            }

            // Se for exportação de arquivo ou blob
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/csv')) {
                return await response.blob();
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },

    // Configurações
    getSettings() {
        return this.request('/settings');
    },
    updateSettings(data) {
        return this.request('/settings', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    uploadLogo(formData) {
        return this.request('/settings/logo', {
            method: 'POST',
            body: formData
        });
    },
    deleteLogo() {
        return this.request('/settings/logo', {
            method: 'DELETE'
        });
    },

    // Dashboard
    getDashboardStats() {
        return this.request('/dashboard/stats');
    },

    // Membros
    getMembers(params = {}) {
        const query = new URLSearchParams();
        if (params.search) query.append('search', params.search);
        if (params.role) query.append('role', params.role);
        if (params.status) query.append('status', params.status);
        const qs = query.toString() ? `?${query.toString()}` : '';
        return this.request(`/members${qs}`);
    },
    getMember(id) {
        return this.request(`/members/${id}`);
    },
    createMember(data) {
        return this.request('/members', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    updateMember(id, data) {
        return this.request(`/members/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    deleteMember(id) {
        return this.request(`/members/${id}`, {
            method: 'DELETE'
        });
    },

    // Eventos & Aulas
    getEvents() {
        return this.request('/events');
    },
    getEvent(id) {
        return this.request(`/events/${id}`);
    },
    createEvent(data) {
        return this.request('/events', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    updateEvent(id, data) {
        return this.request(`/events/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    deleteEvent(id) {
        return this.request(`/events/${id}`, {
            method: 'DELETE'
        });
    },

    // Presenças
    updateEventAttendance(eventId, memberIds) {
        return this.request(`/events/${eventId}/attendance`, {
            method: 'POST',
            body: JSON.stringify({ event_id: eventId, member_ids: memberIds })
        });
    },
    checkin(eventToken, memberId) {
        return this.request('/attendance/checkin', {
            method: 'POST',
            body: JSON.stringify({ event_token: eventToken, member_id: memberId })
        });
    },
    getAttendanceSummary() {
        return this.request('/attendance/summary');
    },

    // Tarefas / Kanban
    getTasks() {
        return this.request('/tasks');
    },
    createTask(data) {
        return this.request('/tasks', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    updateTaskStatus(id, status) {
        return this.request(`/tasks/${id}/status?status=${encodeURIComponent(status)}`, {
            method: 'PATCH'
        });
    },
    updateTask(id, data) {
        return this.request(`/tasks/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    deleteTask(id) {
        return this.request(`/tasks/${id}`, {
            method: 'DELETE'
        });
    },

    // Materiais / Biblioteca
    getMaterials(category = null) {
        const qs = category && category !== 'Todos' ? `?category=${encodeURIComponent(category)}` : '';
        return this.request(`/materials${qs}`);
    },
    createMaterial(data) {
        return this.request('/materials', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    uploadMaterial(formData) {
        return this.request('/materials/upload', {
            method: 'POST',
            body: formData
        });
    },
    deleteMaterial(id) {
        return this.request(`/materials/${id}`, {
            method: 'DELETE'
        });
    },

    // Finanças
    getFinances() {
        return this.request('/finances');
    },
    createFinance(data) {
        return this.request('/finances', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    deleteFinance(id) {
        return this.request(`/finances/${id}`, {
            method: 'DELETE'
        });
    },

    // Autenticação e Sessão
    login(email, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },
    register(data) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    verifyEmail(token) {
        return this.request('/auth/verify-email', {
            method: 'POST',
            body: JSON.stringify({ token })
        });
    },
    forgotPassword(email) {
        return this.request('/auth/forgot-password', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    },
    resetPassword(data) {
        return this.request('/auth/reset-password', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    getInviteInfo(token) {
        return this.request(`/auth/invite/${token}`);
    },
    acceptInvite(data) {
        return this.request('/auth/accept-invite', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    updateProfile(data) {
        return this.request('/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    changePassword(currentPassword, newPassword, confirmPassword) {
        return this.request('/auth/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });
    },
    getMe() {
        return this.request('/auth/me');
    },

    // Painel Administrativo / RBAC
    checkAdmin() {
        return this.request('/admin/check');
    },
    getAdminOverview() {
        return this.request('/admin/overview');
    },
    getAdminUsers() {
        return this.request('/admin/users');
    },
    getAdminMembers(params = {}) {
        const q = new URLSearchParams();
        if (params.q) q.append('q', params.q);
        if (params.status) q.append('status_filter', params.status);
        if (params.role) q.append('role_filter', params.role);
        return this.request(`/admin/members?${q.toString()}`);
    },
    updateMemberStatus(id, status, reason = null) {
        return this.request(`/admin/members/${id}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status, reason })
        });
    },
    getAccessRequests() {
        return this.request('/admin/requests');
    },
    approveAccessRequest(id) {
        return this.request(`/admin/requests/${id}/approve`, {
            method: 'POST'
        });
    },
    rejectAccessRequest(id, reason) {
        return this.request(`/admin/requests/${id}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    },
    createInvite(data) {
        return this.request('/admin/invites', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    getInvites() {
        return this.request('/admin/invites');
    },
    revokeInvite(id) {
        return this.request(`/admin/invites/${id}`, {
            method: 'DELETE'
        });
    },
    updateUserRoles(userId, roleIds) {
        return this.request(`/admin/users/${userId}/roles`, {
            method: 'PUT',
            body: JSON.stringify({ role_ids: roleIds })
        });
    },
    getAdminRoles() {
        return this.request('/admin/roles');
    },
    getAdminAudit(limit = 50) {
        return this.request(`/admin/audit?limit=${limit}`);
    }
};

