/**
 * LigaHub - Lógica da Aplicação SPA
 */

let currentView = 'dashboard';
let currentCategoryFilter = 'Todos';
let currentEventForAttendance = null;
let currentQrToken = null;
let leagueSettings = {};
let allMembersCache = [];

// ==========================================
// INICIALIZAÇÃO
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
    await loadSettings();
    await loadCMSContent();
    checkAuthState();
    initHeroParallax();
    initIcons();
});

function checkAuthState() {
    const isAuth = localStorage.getItem('lacc_auth') === 'true';
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');

    updateAdminVisibility();

    // Se o usuário estiver explicitamente acessando o hash #dashboard e estiver logado
    if (window.location.hash === '#dashboard' && isAuth) {
        if (landing) landing.classList.add('hidden');
        if (dashboard) dashboard.classList.remove('hidden');
        loadDashboard();
    } else {
        // Por padrão no link principal, SEMPRE abre a Tela Inicial pública da LACC!
        if (landing) landing.classList.remove('hidden');
        if (dashboard) dashboard.classList.add('hidden');
        loadLandingEvents();
        loadLandingFeaturedNews();
    }

    // Tratamento de redirecionamentos da rota /admin
    // Tratamento de parâmetros de URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('login') === 'admin') {
        openLoginModal();
        showToast('Faça login com uma conta administrativa para acessar o painel.', 'info');
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.get('login') === 'expired') {
        openLoginModal();
        showToast('Sua sessão expirou. Faça login novamente.', 'warning');
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (urlParams.has('verify_email')) {
        const token = urlParams.get('verify_email');
        window.history.replaceState({}, document.title, window.location.pathname);
        api.verifyEmail(token).then(res => {
            showToast(res.message || 'E-mail confirmado com sucesso!', 'success');
        }).catch(err => {
            showToast(err.message || 'Falha ao confirmar e-mail.', 'error');
        });
    } else if (urlParams.has('reset_token')) {
        const token = urlParams.get('reset_token');
        window.history.replaceState({}, document.title, window.location.pathname);
        const tokenField = document.getElementById('reset-token-field');
        if (tokenField) tokenField.value = token;
        openModal('modal-reset-password');
    } else if (urlParams.has('invite')) {
        const token = urlParams.get('invite');
        window.history.replaceState({}, document.title, window.location.pathname);
        api.getInviteInfo(token).then(info => {
            const tokenField = document.getElementById('invite-token-field');
            const emailField = document.getElementById('invite-email');
            const nameField = document.getElementById('invite-name');
            const greeting = document.getElementById('invite-greeting');
            if (tokenField) tokenField.value = token;
            if (emailField) emailField.value = info.email || '';
            if (nameField && info.name) nameField.value = info.name;
            if (greeting && info.name) greeting.innerText = `Olá, ${info.name}! Complete sua matrícula institucional`;
            openModal('modal-accept-invite');
        }).catch(err => {
            showToast(err.message || 'Convite inválido ou expirado.', 'error');
        });
    }
}

function toggleLandingDrawer() {
    const drawer = document.getElementById('landing-drawer');
    if (drawer) {
        const isCurrentlyHidden = drawer.classList.contains('hidden');
        drawer.classList.toggle('hidden');
        if (isCurrentlyHidden) {
            document.body.classList.add('overflow-hidden');
        } else {
            document.body.classList.remove('overflow-hidden');
        }
        initIcons();
    }
}

function toggleMobileSidebar() {
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    const drawer = document.getElementById('mobile-sidebar-drawer');
    if (backdrop && drawer) {
        const isClosed = drawer.classList.contains('-translate-x-full');
        if (isClosed) {
            backdrop.classList.remove('hidden');
            drawer.classList.remove('-translate-x-full');
            document.body.classList.add('overflow-hidden');
        } else {
            closeMobileSidebar();
        }
        initIcons();
    }
}

function closeMobileSidebar() {
    const backdrop = document.getElementById('mobile-sidebar-backdrop');
    const drawer = document.getElementById('mobile-sidebar-drawer');
    if (backdrop && drawer) {
        backdrop.classList.add('hidden');
        drawer.classList.add('-translate-x-full');
        document.body.classList.remove('overflow-hidden');
    }
}

function getCurrentUser() {
    try {
        return JSON.parse(localStorage.getItem('lacc_user') || 'null');
    } catch (e) {
        return null;
    }
}

function openLoginModal() {
    const isAuth = localStorage.getItem('lacc_auth') === 'true';
    if (isAuth) {
        const u = getCurrentUser();
        if (u && u.has_member_access) {
            goToDashboard('member');
        } else {
            goToDashboard('community');
        }
    } else {
        openModal('modal-login');
    }
}

function openCommunityLoginModal() {
    const isAuth = localStorage.getItem('lacc_auth') === 'true';
    if (isAuth) {
        goToDashboard('community');
    } else {
        openModal('modal-community-login');
    }
}

function openCommunityRegisterModal() {
    closeModal('modal-community-login');
    openModal('modal-community-register');
}

function goToDashboard(initialEnv = null) {
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');
    if (landing) landing.classList.add('hidden');
    if (dashboard) dashboard.classList.remove('hidden');

    const u = getCurrentUser();
    let targetEnv = initialEnv;
    if (!targetEnv) {
        targetEnv = (u && !u.has_member_access && u.has_community_access) ? 'community' : 'member';
    }

    switchEnvironment(targetEnv);
    initIcons();
}

async function submitLogin(e) {
    e.preventDefault();
    const emailInput = document.getElementById('login-email');
    const passwordInput = document.getElementById('login-password');
    const email = emailInput ? emailInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value : '';

    if (!email) {
        showToast('Por favor, informe seu e-mail.', 'error');
        return;
    }
    if (!password) {
        showToast('Por favor, informe sua senha de acesso.', 'error');
        return;
    }

    const submitBtn = document.getElementById('btn-login-submit');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Entrando...`;
    }

    try {
        const res = await api.login(email, password);
        localStorage.setItem('lacc_token', res.access_token);
        localStorage.setItem('lacc_user', JSON.stringify(res.user));
        localStorage.setItem('lacc_auth', 'true');
        localStorage.setItem('lacc_user_email', res.user.email);

        updateAdminVisibility();
        closeModal('modal-login');

        if (res.user.has_member_access) {
            goToDashboard('member');
            showToast(`Bem-vindo(a) à Área de Membros, ${res.user.name}!`);
        } else if (res.user.has_community_access) {
            goToDashboard('community');
            showToast(`Bem-vindo(a) à Comunidade LACC, ${res.user.name}!`);
        } else {
            goToDashboard();
            showToast(`Bem-vindo(a), ${res.user.name}!`);
        }
    } catch (err) {
        showToast(err.message || 'Falha na autenticação.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i data-lucide="log-in" class="w-4 h-4"></i><span>Entrar na Área de Membros</span>`;
            initIcons();
        }
    }
}

async function submitCommunityLogin(e) {
    e.preventDefault();
    const email = document.getElementById('comm-login-email')?.value.trim();
    const password = document.getElementById('comm-login-password')?.value;

    if (!email || !password) {
        showToast('Informe seu e-mail e senha.', 'error');
        return;
    }

    const btn = document.getElementById('btn-comm-login-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Entrando...`;
    }

    try {
        const res = await api.login(email, password);
        localStorage.setItem('lacc_token', res.access_token);
        localStorage.setItem('lacc_user', JSON.stringify(res.user));
        localStorage.setItem('lacc_auth', 'true');
        localStorage.setItem('lacc_user_email', res.user.email);

        updateAdminVisibility();
        closeModal('modal-community-login');
        goToDashboard('community');
        showToast(`Bem-vindo(a) à Comunidade, ${res.user.name}!`);
    } catch (err) {
        showToast(err.message || 'Falha no login comunitário.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="log-in" class="w-4 h-4"></i><span>Entrar na Comunidade</span>`;
            initIcons();
        }
    }
}

async function submitCommunityRegister(e) {
    e.preventDefault();
    const name = document.getElementById('comm-reg-name')?.value.trim();
    const email = document.getElementById('comm-reg-email')?.value.trim();
    const displayName = document.getElementById('comm-reg-display')?.value.trim();
    const institution = document.getElementById('comm-reg-institution')?.value.trim();
    const interests = document.getElementById('comm-reg-interests')?.value.trim();
    const password = document.getElementById('comm-reg-password')?.value;
    const confirmPassword = document.getElementById('comm-reg-confirm-password')?.value;

    if (!name || !email || !password || !confirmPassword) {
        showToast('Preencha os campos obrigatórios (*).', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showToast('A confirmação de senha não confere.', 'error');
        return;
    }

    const btn = document.getElementById('btn-comm-reg-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Criando conta...`;
    }

    try {
        const payload = {
            name,
            email,
            display_name: displayName || name,
            institution: institution || null,
            interests: interests || null,
            password,
            password_confirm: confirmPassword
        };
        const res = await api.registerCommunity(payload);
        closeModal('modal-community-register');
        showToast(res.message || 'Conta criada na Comunidade com sucesso!');

        // Tentar autenticação automática ou abrir modal de login
        try {
            const loginRes = await api.login(email, password);
            localStorage.setItem('lacc_token', loginRes.access_token);
            localStorage.setItem('lacc_user', JSON.stringify(loginRes.user));
            localStorage.setItem('lacc_auth', 'true');
            localStorage.setItem('lacc_user_email', loginRes.user.email);
            updateAdminVisibility();
            goToDashboard('community');
        } catch (authErr) {
            openCommunityLoginModal();
        }
    } catch (err) {
        showToast(err.message || 'Falha ao criar conta na Comunidade.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="user-plus" class="w-4 h-4"></i><span>Concluir Cadastro na Comunidade</span>`;
            initIcons();
        }
    }
}

// ----------------------------------------------------
// CADASTRO DE USUÁRIO (STATUS = PENDING)
// ----------------------------------------------------
function openRegisterModal() {
    closeModal('modal-login');
    openModal('modal-register');
}

async function submitRegister(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name')?.value.trim();
    const email = document.getElementById('reg-email')?.value.trim();
    const regNumber = document.getElementById('reg-number')?.value.trim();
    const course = document.getElementById('reg-course')?.value;
    const semester = document.getElementById('reg-semester')?.value;
    const password = document.getElementById('reg-password')?.value;
    const confirmPassword = document.getElementById('reg-confirm-password')?.value;

    if (!name || !email || !password || !confirmPassword) {
        showToast('Preencha todos os campos obrigatórios (*).', 'error');
        return;
    }

    if (password !== confirmPassword) {
        showToast('As senhas digitadas não conferem.', 'error');
        return;
    }

    if (password.length < 8) {
        showToast('A senha deve conter no mínimo 8 caracteres.', 'error');
        return;
    }

    const btn = document.getElementById('btn-register-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Enviando...`;
    }

    try {
        const res = await api.register({
            name,
            email,
            course,
            semester,
            registration_number: regNumber || null,
            password,
            password_confirm: confirmPassword
        });

        closeModal('modal-register');
        openModal('modal-pending-notice');
        showToast(res.message || 'Solicitação enviada com sucesso!');
        document.getElementById('form-register')?.reset();
    } catch (err) {
        showToast(err.message || 'Erro ao enviar cadastro.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="send" class="w-4 h-4"></i><span>Enviar Solicitação de Cadastro</span>`;
            initIcons();
        }
    }
}

// ----------------------------------------------------
// RECUPERAÇÃO DE SENHA
// ----------------------------------------------------
function openForgotPasswordModal() {
    closeModal('modal-login');
    openModal('modal-forgot-password');
}

async function submitForgotPassword(e) {
    e.preventDefault();
    const email = document.getElementById('forgot-email')?.value.trim();
    if (!email) {
        showToast('Informe o seu e-mail cadastrado.', 'error');
        return;
    }

    const btn = document.getElementById('btn-forgot-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Enviando...`;
    }

    try {
        const res = await api.forgotPassword(email);
        closeModal('modal-forgot-password');
        showToast(res.message || 'Instruções enviadas para seu e-mail!', 'info');
        document.getElementById('form-forgot-password')?.reset();
    } catch (err) {
        showToast(err.message || 'Erro ao processar solicitação.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="send" class="w-4 h-4"></i><span>Enviar Link de Redefinição</span>`;
            initIcons();
        }
    }
}

async function submitResetPassword(e) {
    e.preventDefault();
    const token = document.getElementById('reset-token-field')?.value.trim();
    const newPassword = document.getElementById('reset-new-password')?.value;
    const confirmPassword = document.getElementById('reset-confirm-password')?.value;

    if (!newPassword || !confirmPassword) {
        showToast('Preencha os campos de nova senha.', 'error');
        return;
    }
    if (newPassword !== confirmPassword) {
        showToast('A confirmação não confere com a nova senha.', 'error');
        return;
    }
    if (newPassword.length < 8) {
        showToast('A nova senha deve possuir no mínimo 8 caracteres.', 'error');
        return;
    }

    const btn = document.getElementById('btn-reset-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Salvando...`;
    }

    try {
        const res = await api.resetPassword({
            token,
            new_password: newPassword,
            confirm_password: confirmPassword
        });
        closeModal('modal-reset-password');
        openModal('modal-login');
        showToast(res.message || 'Senha redefinida com sucesso! Faça login agora.');
        document.getElementById('form-reset-password')?.reset();
    } catch (err) {
        showToast(err.message || 'Falha ao redefinir senha.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="check" class="w-4 h-4"></i><span>Salvar Nova Senha</span>`;
            initIcons();
        }
    }
}

// ----------------------------------------------------
// CONVITE DIRETO (ACEITE DE CONVITE)
// ----------------------------------------------------
async function submitAcceptInvite(e) {
    e.preventDefault();
    const token = document.getElementById('invite-token-field')?.value.trim();
    const name = document.getElementById('invite-name')?.value.trim();
    const course = document.getElementById('invite-course')?.value;
    const semester = document.getElementById('invite-semester')?.value;
    const password = document.getElementById('invite-password')?.value;
    const confirmPassword = document.getElementById('invite-confirm-password')?.value;

    if (!name || !password || !confirmPassword) {
        showToast('Preencha os dados obrigatórios.', 'error');
        return;
    }
    if (password !== confirmPassword) {
        showToast('A confirmação não confere com a senha.', 'error');
        return;
    }
    if (password.length < 8) {
        showToast('A senha deve conter no mínimo 8 caracteres.', 'error');
        return;
    }

    const btn = document.getElementById('btn-invite-submit');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin mr-2">⏳</span> Ativando conta...`;
    }

    try {
        const res = await api.acceptInvite({
            token,
            name,
            course,
            semester,
            password,
            confirm_password: confirmPassword
        });

        localStorage.setItem('lacc_token', res.access_token);
        localStorage.setItem('lacc_user', JSON.stringify(res.user));
        localStorage.setItem('lacc_auth', 'true');
        localStorage.setItem('lacc_user_email', res.user.email);

        closeModal('modal-accept-invite');
        updateAdminVisibility();
        goToDashboard();
        showToast(res.message || 'Conta ativada com sucesso!');
    } catch (err) {
        showToast(err.message || 'Erro ao aceitar convite.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="check-circle" class="w-4 h-4"></i><span>Ativar Conta e Entrar no Dashboard</span>`;
            initIcons();
        }
    }
}

// ----------------------------------------------------
// MEU PERFIL & SENHA DO MEMBRO LOGADO
// ----------------------------------------------------
async function loadMyProfile() {
    try {
        const me = await api.getMe();
        const cardName = document.getElementById('profile-card-name');
        const cardEmail = document.getElementById('profile-card-email');
        const cardRole = document.getElementById('profile-card-role');
        const cardReg = document.getElementById('profile-card-reg');
        const badgeStatus = document.getElementById('profile-badge-status');
        const avatarLetter = document.getElementById('profile-avatar-letter');

        if (cardName) cardName.innerText = me.name;
        if (cardEmail) cardEmail.innerText = me.email;
        if (cardRole) cardRole.innerText = me.role || 'Membro';
        if (avatarLetter) avatarLetter.innerText = (me.name || 'M')[0].toUpperCase();

        if (cardReg) {
            cardReg.innerText = me.registration_number ? `Matrícula: ${me.registration_number}` : 'Matrícula: Não informada';
        }

        if (badgeStatus) {
            const st = (me.status || 'active').toLowerCase();
            badgeStatus.innerText = st === 'active' ? 'Ativo' : (st === 'pending' ? 'Pendente' : 'Suspenso');
            if (st === 'active') {
                badgeStatus.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
            } else {
                badgeStatus.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30';
            }
        }

        const phoneInput = document.getElementById('my-profile-phone');
        const courseInput = document.getElementById('my-profile-course');
        const semInput = document.getElementById('my-profile-semester');
        const notesInput = document.getElementById('my-profile-notes');

        if (phoneInput) phoneInput.value = me.phone || '';
        if (courseInput) courseInput.value = me.course || '';
        if (semInput) semInput.value = me.semester || '';
        if (notesInput) notesInput.value = me.notes || '';
    } catch (err) {
        showToast('Erro ao carregar dados do perfil.', 'error');
    }
}

async function submitMyProfile(e) {
    e.preventDefault();
    const phone = document.getElementById('my-profile-phone')?.value;
    const course = document.getElementById('my-profile-course')?.value;
    const semester = document.getElementById('my-profile-semester')?.value;
    const notes = document.getElementById('my-profile-notes')?.value;

    const btn = document.getElementById('btn-save-profile');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Salvando...';
    }

    try {
        const res = await api.updateProfile({ phone, course, semester, notes });
        showToast(res.message || 'Dados atualizados com sucesso!');
        loadMyProfile();
    } catch (err) {
        showToast(err.message || 'Erro ao atualizar dados.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Salvar Dados Pessoais';
        }
    }
}

async function submitMyPassword(e) {
    e.preventDefault();
    const currentPass = document.getElementById('my-pass-current')?.value;
    const newPass = document.getElementById('my-pass-new')?.value;
    const confirmPass = document.getElementById('my-pass-confirm')?.value;

    if (!currentPass || !newPass || !confirmPass) {
        showToast('Preencha todos os campos de senha.', 'error');
        return;
    }
    if (newPass !== confirmPass) {
        showToast('A confirmação não confere com a nova senha.', 'error');
        return;
    }
    if (newPass.length < 8) {
        showToast('A nova senha deve ter no mínimo 8 caracteres.', 'error');
        return;
    }

    const btn = document.getElementById('btn-save-password');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Atualizando...';
    }

    try {
        const res = await api.changePassword(currentPass, newPass, confirmPass);
        showToast(res.message || 'Senha alterada com sucesso!');
        document.getElementById('form-my-password')?.reset();
    } catch (err) {
        showToast(err.message || 'Erro ao alterar senha.', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Atualizar Senha';
        }
    }
}

function updateAdminVisibility() {
    const adminEntry = document.getElementById('admin-platform-entry');
    const mobileSuperAdminBtn = document.getElementById('mobile-superadmin-btn');
    const mobileBottomSuperAdmin = document.getElementById('mobile-bottom-superadmin-btn');
    const commBtn = document.getElementById('nav-btn-communication');
    const athenaBtn = document.getElementById('nav-btn-athena');

    const isAuth = localStorage.getItem('lacc_auth') === 'true' || !!localStorage.getItem('lacc_token');

    try {
        const userStr = localStorage.getItem('lacc_user');
        let user = userStr ? JSON.parse(userStr) : null;

        // Se estiver autenticado e não tiver o objeto de usuário completo salvo em cache, usa o email em localStorage
        if (!user && isAuth) {
            const savedEmail = localStorage.getItem('lacc_user_email') || 'paulo.alberto.ofc@gmail.com';
            user = {
                email: savedEmail,
                is_superadmin: savedEmail.toLowerCase() === 'paulo.alberto.ofc@gmail.com',
                is_admin: true,
                roles: ['superadmin', 'diretor', 'comunicacao']
            };
        }

        if (user) {
            const emailStr = String(user.email || '').toLowerCase();
            const roleStr = String(user.role || '').toLowerCase();
            const perms = Array.isArray(user.permissions) ? user.permissions : [];
            const roles = Array.isArray(user.roles) 
                ? user.roles.map(r => (typeof r === 'object' && r ? (r.slug || r.name || '') : String(r)).toLowerCase()) 
                : [];

            const isSuperAdmin = user.is_superadmin || emailStr === 'paulo.alberto.ofc@gmail.com' || roleStr === 'superadmin' || roles.includes('superadmin') || roles.includes('super_admin');
            const isAdmin = user.is_admin || isSuperAdmin;

            // Entrada desktop (Admin ou Superadmin)
            if (adminEntry) {
                if (isAdmin) {
                    adminEntry.classList.remove('hidden');
                } else {
                    adminEntry.classList.add('hidden');
                }
            }

            // Botões Mobile liberados exclusivamente para Super Admin (Paulo Alberto)
            if (mobileSuperAdminBtn) {
                if (isSuperAdmin) {
                    mobileSuperAdminBtn.classList.remove('hidden');
                    mobileSuperAdminBtn.classList.add('inline-flex');
                } else {
                    mobileSuperAdminBtn.classList.add('hidden');
                    mobileSuperAdminBtn.classList.remove('inline-flex');
                }
            }

            if (mobileBottomSuperAdmin) {
                if (isSuperAdmin) {
                    mobileBottomSuperAdmin.classList.remove('hidden');
                    mobileBottomSuperAdmin.classList.add('flex');
                } else {
                    mobileBottomSuperAdmin.classList.add('hidden');
                    mobileBottomSuperAdmin.classList.remove('flex');
                }
            }

            // Entrada de Athena IA (Exclusivo para Diretoria e Administração da LACC)
            if (athenaBtn) {
                const directorRoles = [
                    'director', 'diretor', 'diretoria', 'presidente', 'presidencia',
                    'vice_presidente', 'vice_presidencia', 'comunicacao', 'pesquisa',
                    'eventos', 'tesouraria', 'tesoureiro', 'secretaria', 'secretario',
                    'admin', 'superadmin', 'super_admin'
                ];
                const isDirector = isAdmin || isSuperAdmin ||
                    roles.some(r => directorRoles.includes(r)) ||
                    directorRoles.includes(roleStr) ||
                    perms.includes('athena.access') ||
                    perms.includes('*');

                if (isDirector) {
                    athenaBtn.classList.remove('hidden');
                    athenaBtn.classList.add('flex');
                } else {
                    athenaBtn.classList.add('hidden');
                    athenaBtn.classList.remove('flex');
                }
            }

            // Entrada de Comunicação
            if (commBtn) {
                const canComm = isAdmin || perms.includes('communication.view') || roles.includes('comunicacao') || roleStr === 'comunicacao';
                if (canComm) {
                    commBtn.classList.remove('hidden');
                } else {
                    commBtn.classList.add('hidden');
                }
            }
            initIcons();
            return;
        }
    } catch (e) {
        console.error('Erro em updateAdminVisibility:', e);
    }

    if (adminEntry) adminEntry.classList.add('hidden');
    if (mobileSuperAdminBtn) {
        mobileSuperAdminBtn.classList.add('hidden');
        mobileSuperAdminBtn.classList.remove('inline-flex');
    }
    if (mobileBottomSuperAdmin) {
        mobileBottomSuperAdmin.classList.add('hidden');
        mobileBottomSuperAdmin.classList.remove('flex');
    }
    if (athenaBtn) {
        athenaBtn.classList.add('hidden');
        athenaBtn.classList.remove('flex');
    }
    if (commBtn) commBtn.classList.add('hidden');
}

function handleLogout() {
    localStorage.removeItem('lacc_auth');
    localStorage.removeItem('lacc_token');
    localStorage.removeItem('lacc_user');
    localStorage.removeItem('lacc_user_email');
    updateAdminVisibility();
    window.location.hash = '';
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');
    if (dashboard) dashboard.classList.add('hidden');
    if (landing) landing.classList.remove('hidden');
    showToast('Você saiu da Área de Membros.');
    loadLandingEvents();
    loadLandingFeaturedNews();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// INTEGRAÇÃO COM O CMS DA HOME (PUBLIC & PREVIEW)
// ==========================================
async function loadCMSContent() {
    try {
        const isPreview = new URLSearchParams(window.location.search).get('preview') === 'true';
        const endpoint = isPreview ? '/api/content/preview' : '/api/content/public';
        const res = await fetch(endpoint);
        if (!res.ok) return;
        const data = await res.json();
        applyCMSContent(data);
    } catch (e) {
        console.warn('CMS: Usando conteúdo institucional padrão do HTML.', e);
    }
}

function applyCMSContent(cmsData) {
    if (!cmsData) return;

    // 1. Hero Institucional
    const heroSec = cmsData.hero;
    if (heroSec && (heroSec.content || heroSec.draft_data)) {
        const h = heroSec.content || heroSec.draft_data;
        const badgeEl = document.getElementById('landing-badge-faculdade');
        if (badgeEl && h.badge) badgeEl.innerText = h.badge;

        const titleEl = document.getElementById('landing-main-title');
        if (titleEl && h.title) {
            if (h.title.toUpperCase().includes('CIÊNCIAS CRIMINAIS')) {
                titleEl.innerHTML = `LIGA ACADÊMICA DE<br><span class="text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-amber-200">CIÊNCIAS CRIMINAIS</span>`;
            } else {
                titleEl.innerText = h.title;
            }
        }

        const descEl = document.getElementById('landing-main-desc');
        if (descEl && h.subtitle) descEl.innerText = h.subtitle;

        if (h.primary_btn_text) {
            const primaryBtn = document.querySelector('#hero-foreground-content button span');
            if (primaryBtn) primaryBtn.innerText = h.primary_btn_text;
        }
        if (h.secondary_btn_text) {
            const secondaryBtn = document.querySelector('#hero-foreground-content a span');
            if (secondaryBtn) secondaryBtn.innerText = h.secondary_btn_text;
        }
        if (h.scroll_cue) {
            const scrollCue = document.querySelector('#hero-foreground-content .text-amber-400\\/80');
            if (scrollCue) scrollCue.innerText = h.scroll_cue;
        }
    }

    // 2. Introdução da Rede Interdisciplinar
    const introSec = cmsData.interdisciplinary_intro;
    if (introSec && (introSec.content || introSec.draft_data)) {
        const intro = introSec.content || introSec.draft_data;
        const quoteH2 = document.querySelector('#interdisciplinary-quote h2');
        if (quoteH2 && intro.headline) {
            quoteH2.innerText = `“${intro.headline.replace(/^“|”$/g, '')}”`;
        }

        const quoteP = document.querySelector('#interdisciplinary-quote p');
        if (quoteP && intro.subheadline) quoteP.innerText = intro.subheadline;
    }

    // 3. Ciências Criminais na Prática (Pilares de Formação)
    const pillarsSec = cmsData.about_pillars;
    if (pillarsSec && (pillarsSec.content || pillarsSec.draft_data)) {
        const ap = pillarsSec.content || pillarsSec.draft_data;
        const badge = document.querySelector('#landing-about span');
        if (badge && ap.badge) badge.innerText = ap.badge;

        const title = document.querySelector('#landing-about h2');
        if (title && ap.title) title.innerText = ap.title;

        const subtitle = document.querySelector('#landing-about p');
        if (subtitle && ap.subtitle) subtitle.innerText = ap.subtitle;

        if (Array.isArray(ap.pillars) && ap.pillars.length > 0) {
            const container = document.getElementById('landing-pillars-container');
            if (container) {
                const colorMap = [
                    { bg: 'bg-blue-500/10', text: 'text-blue-400' },
                    { bg: 'bg-purple-500/10', text: 'text-purple-400' },
                    { bg: 'bg-emerald-500/10', text: 'text-emerald-400' },
                    { bg: 'bg-amber-500/10', text: 'text-amber-400' }
                ];
                container.innerHTML = ap.pillars.map((p, idx) => {
                    const c = colorMap[idx % colorMap.length];
                    const icon = p.icon || 'scale';
                    return `
                        <div class="bg-slate-900/70 p-6 rounded-3xl border border-slate-800/80 hover:border-slate-700 transition space-y-3">
                            <div class="w-12 h-12 rounded-2xl ${c.bg} ${c.text} flex items-center justify-center">
                                <i data-lucide="${icon}" class="w-6 h-6"></i>
                            </div>
                            <h3 class="font-bold text-lg text-white">${p.title}</h3>
                            <p class="text-xs text-slate-400 leading-relaxed">${p.desc}</p>
                        </div>
                    `;
                }).join('');
                if (window.lucide) lucide.createIcons();
            }
        }
    }

    // 4. Rodapé
    const footerSec = cmsData.footer;
    if (footerSec && (footerSec.content || footerSec.draft_data)) {
        const f = footerSec.content || footerSec.draft_data;
        const nameEl = document.getElementById('landing-footer-name');
        if (nameEl && f.name) nameEl.innerText = f.name;

        const uniEl = document.getElementById('landing-footer-uni');
        if (uniEl && f.institution) uniEl.innerText = f.institution;
    }
}

// Ouvinte para mensagens de preview instantâneo via postMessage do Editor CMS
window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'LACC_CMS_PREVIEW_SYNC') {
        applyCMSContent(event.data.sections);
    }
});

async function loadLandingEvents() {
    try {
        const events = await api.getEvents();
        const container = document.getElementById('landing-events-container');
        if (!container) return;

        if (!events || events.length === 0) {
            container.innerHTML = `
                <div class="p-8 text-center bg-slate-900/60 rounded-3xl border border-slate-800/80 text-slate-400 space-y-2">
                    <div class="w-10 h-10 rounded-2xl bg-slate-800/80 text-amber-400/80 mx-auto flex items-center justify-center border border-slate-700/50">
                        <i data-lucide="calendar" class="w-5 h-5"></i>
                    </div>
                    <p class="text-sm font-semibold text-slate-300">Nenhuma atividade pública cadastrada no momento.</p>
                    <p class="text-xs text-slate-500 max-w-md mx-auto">Acompanhe nossas comunicações institucionais e canais oficiais para os próximos simpósios, debates e grupos de estudo.</p>
                </div>
            `;
            initIcons();
            return;
        }

        container.innerHTML = events.slice(0, 3).map(ev => `
            <div class="flex items-center justify-between p-4 bg-slate-900/70 hover:bg-slate-900 rounded-2xl border border-slate-800 transition">
                <div class="flex items-center gap-3.5">
                    <div class="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex flex-col items-center justify-center font-bold">
                        <span class="text-sm leading-none">${formatDay(ev.date)}</span>
                        <span class="text-[10px] uppercase font-semibold mt-0.5">${formatMonthShort(ev.date)}</span>
                    </div>
                    <div>
                        <h4 class="font-bold text-white text-sm leading-snug">${ev.title}</h4>
                        <div class="text-xs text-slate-400 flex items-center gap-2 mt-1">
                            <span><i data-lucide="clock" class="w-3 h-3 inline"></i> ${ev.time}</span>
                            <span>•</span>
                            <span><i data-lucide="map-pin" class="w-3 h-3 inline"></i> ${ev.location || 'Auditório'}</span>
                            <span>•</span>
                            <span class="text-emerald-400 font-semibold">${ev.hours}h</span>
                        </div>
                    </div>
                </div>
                <a href="/checkin.html" class="px-3 py-1.5 rounded-xl bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500 hover:text-white text-xs font-semibold transition hidden sm:inline-flex items-center gap-1">
                    <span>Check-in</span>
                    <i data-lucide="qr-code" class="w-3.5 h-3.5"></i>
                </a>
            </div>
        `).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar eventos da landing:', err);
    }
}

async function loadLandingFeaturedNews() {
    const container = document.getElementById('landing-news-container');
    if (!container) return;

    try {
        const news = await api.getFeaturedNews();
        if (!news || news.length === 0) {
            container.innerHTML = `
                <div class="col-span-full p-8 text-center bg-slate-900/60 rounded-3xl border border-slate-800/80 text-slate-400 space-y-2">
                    <div class="w-10 h-10 rounded-2xl bg-slate-800/80 text-amber-400/80 mx-auto flex items-center justify-center border border-slate-700/50">
                        <i data-lucide="newspaper" class="w-5 h-5"></i>
                    </div>
                    <p class="text-sm font-semibold text-slate-300">Nenhuma matéria publicada no momento.</p>
                    <p class="text-xs text-slate-500 max-w-md mx-auto">Em breve novas análises, precedentes criminais e publicações científicas estarão disponíveis aqui.</p>
                </div>
            `;
            initIcons();
            return;
        }

        container.innerHTML = news.map(art => `
            <a href="/noticias?art=${encodeURIComponent(art.slug)}" class="bg-slate-900/80 hover:bg-slate-900 rounded-2xl border border-slate-800 hover:border-amber-500/40 transition group flex flex-col justify-between overflow-hidden shadow-lg">
                <div>
                    <div class="h-44 bg-slate-950 overflow-hidden relative">
                        ${art.cover_image_url 
                            ? `<img src="${art.cover_image_url}" alt="${art.title}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">`
                            : `<div class="w-full h-full flex items-center justify-center bg-slate-900 text-slate-700"><i data-lucide="newspaper" class="w-10 h-10"></i></div>`
                        }
                        <div class="absolute top-3 left-3">
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" style="background-color: ${art.category_color}25; color: ${art.category_color}; border: 1px solid ${art.category_color}40;">
                                ${art.category_name}
                            </span>
                        </div>
                    </div>
                    <div class="p-5 space-y-2">
                        <h4 class="text-base font-bold text-white group-hover:text-amber-400 transition line-clamp-2 leading-snug">
                            ${art.title}
                        </h4>
                        <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                            ${art.summary}
                        </p>
                    </div>
                </div>
                <div class="px-5 pb-4 pt-2 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
                    <span>${art.published_at ? art.published_at.substring(0, 10) : ''}</span>
                    <span class="text-amber-400 font-bold group-hover:translate-x-1 transition inline-flex items-center gap-1">
                        Ler Artigo →
                    </span>
                </div>
            </a>
        `).join('');
        initIcons();
    } catch (err) {
        console.warn('Erro ao carregar notícias na landing:', err);
    }
}

// ==========================================
// HERO PARALLAX INTERATIVO (LACC)
// ==========================================
let heroParallaxInitialized = false;

function initHeroParallax() {
    if (heroParallaxInitialized) return;

    // Respeitar preferência do sistema operacional para redução de movimento
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const hero = document.getElementById('landing-hero');
    const crestImg = document.getElementById('hero-parallax-crest-img');
    if (!hero || !crestImg) return;
    heroParallaxInitialized = true;

    // Detectar se o dispositivo possui cursor fino (desktop com mouse)
    const hasFinePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!hasFinePointer) return;

    let targetMouseX = 0;
    let targetMouseY = 0;
    let currentMouseX = 0;
    let currentMouseY = 0;

    // Interação sutil com o cursor (Desktop apenas)
    hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) return;

        // Posição normalizada de -1 a 1 em relação ao centro do hero
        const normX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
        const normY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;

        // Deslocamento suave e discreto (máximo 12px horizontal, 8px vertical)
        targetMouseX = -normX * 12;
        targetMouseY = -normY * 8;
    }, { passive: true });

    hero.addEventListener('mouseleave', () => {
        targetMouseX = 0;
        targetMouseY = 0;
    });

    // Loop de amortecimento fluido via requestAnimationFrame
    function renderMouseParallax() {
        currentMouseX += (targetMouseX - currentMouseX) * 0.08;
        currentMouseY += (targetMouseY - currentMouseY) * 0.08;

        if (crestImg) {
            crestImg.style.transform = `translate3d(${currentMouseX.toFixed(2)}px, ${currentMouseY.toFixed(2)}px, 0)`;
        }

        requestAnimationFrame(renderMouseParallax);
    }

    requestAnimationFrame(renderMouseParallax);
}

function initIcons() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

// ==========================================
// TOAST NOTIFICATIONS
// ==========================================
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-emerald-600' : (type === 'error' ? 'bg-rose-600' : 'bg-slate-800');
    const iconName = type === 'success' ? 'check-circle' : (type === 'error' ? 'alert-circle' : 'info');

    toast.className = `${bgClass} text-white px-4 py-3 rounded-2xl shadow-xl flex items-center gap-3 text-sm pointer-events-auto toast-enter`;
    toast.innerHTML = `
        <i data-lucide="${iconName}" class="w-5 h-5 shrink-0"></i>
        <span class="flex-1 font-medium">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
    `;
    container.appendChild(toast);
    initIcons();

    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('opacity-0', 'transition', 'duration-300');
            setTimeout(() => toast.remove(), 300);
        }
    }, 4000);
}

// ==========================================
// CHAVEAMENTO DE AMBIENTE & COMUNIDADE
// ==========================================
let currentEnvironment = 'member'; // 'member' | 'community'

function switchEnvironment(env) {
    const u = getCurrentUser();
    const btnMember = document.getElementById('btn-env-member');
    const btnCommunity = document.getElementById('btn-env-community');
    const viewCommunity = document.getElementById('view-community');

    if (env === 'member') {
        if (u && !u.has_member_access && !u.is_superadmin) {
            showToast('Acesso restrito: Sua conta possui acesso apenas à Comunidade Aberta. Solicite admissão para a Área de Membros.', 'warning');
            switchEnvironment('community');
            return;
        }

        currentEnvironment = 'member';
        window.location.hash = '#dashboard';

        if (btnMember) {
            btnMember.className = 'flex-1 py-1.5 px-2 rounded-lg font-semibold transition flex items-center justify-center gap-1.5 bg-emerald-600 text-white shadow-sm';
        }
        if (btnCommunity) {
            btnCommunity.className = 'flex-1 py-1.5 px-2 rounded-lg font-semibold transition flex items-center justify-center gap-1.5 text-slate-400 hover:text-cyan-300';
        }

        if (viewCommunity) viewCommunity.classList.add('hidden');
        navigateTo('dashboard');
    } else {
        currentEnvironment = 'community';
        window.location.hash = '#community';

        if (btnMember) {
            btnMember.className = 'flex-1 py-1.5 px-2 rounded-lg font-semibold transition flex items-center justify-center gap-1.5 text-slate-400 hover:text-emerald-300';
        }
        if (btnCommunity) {
            btnCommunity.className = 'flex-1 py-1.5 px-2 rounded-lg font-semibold transition flex items-center justify-center gap-1.5 bg-cyan-600 text-white shadow-sm';
        }

        // Esconder seções institucionais de membros e exibir Comunidade
        document.querySelectorAll('#view-container > section').forEach(sec => {
            if (sec.id === 'view-community') {
                sec.classList.remove('hidden');
            } else {
                sec.classList.add('hidden');
            }
        });

        // Atualizar destaque na sidebar
        document.querySelectorAll('#desktop-nav .nav-btn').forEach(btn => {
            if (btn.getAttribute('data-nav') === 'community') {
                btn.className = 'nav-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-semibold transition bg-cyan-600 text-white shadow-sm mb-2';
            } else {
                btn.className = 'nav-btn w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition text-slate-300 hover:bg-slate-800 hover:text-white';
            }
        });

        loadCommunityProfile();
    }
    initIcons();
}

async function loadCommunityProfile() {
    const u = getCurrentUser();
    if (!u) return;

    const nameEl = document.getElementById('comm-profile-display-name');
    const avatarEl = document.getElementById('comm-profile-avatar');
    const instEl = document.getElementById('comm-profile-inst');
    const bioEl = document.getElementById('comm-profile-bio');
    const roleBadge = document.getElementById('comm-profile-role-badge');
    const statusBadge = document.getElementById('comm-profile-status-badge');
    const interestsEl = document.getElementById('comm-profile-interests');
    const promptEl = document.getElementById('comm-activate-prompt');

    if (!u.has_community_access) {
        if (nameEl) nameEl.innerText = u.name;
        if (avatarEl) avatarEl.innerText = (u.name || 'M')[0].toUpperCase();
        if (instEl) instEl.innerText = 'Liga Acadêmica de Ciências Criminais (LACC)';
        if (bioEl) bioEl.innerText = 'Perfil comunitário público ainda não ativado.';
        if (roleBadge) roleBadge.innerText = 'Membro Institucional';
        if (statusBadge) statusBadge.innerText = 'Inativo na Comunidade';
        if (promptEl) promptEl.classList.remove('hidden');
        return;
    }

    if (promptEl) promptEl.classList.add('hidden');

    try {
        const profile = await api.getMyCommunityProfile();
        if (nameEl) nameEl.innerText = profile.display_name || u.name;
        if (avatarEl) avatarEl.innerText = (profile.display_name || u.name)[0].toUpperCase();
        if (instEl) instEl.innerText = profile.institution || 'Instituição não informada';
        if (bioEl) bioEl.innerText = profile.bio || 'Sem biografia cadastrada.';
        if (roleBadge) roleBadge.innerText = profile.community_role === 'moderator' ? 'Moderador' : 'Participante';
        if (statusBadge) statusBadge.innerText = profile.status === 'active' ? 'Ativo' : profile.status;
        if (interestsEl) interestsEl.innerText = `Interesses: ${profile.interests || 'Geral'}`;

        const editName = document.getElementById('comm-edit-display-name');
        const editInst = document.getElementById('comm-edit-institution');
        const editCity = document.getElementById('comm-edit-city');
        const editInterests = document.getElementById('comm-edit-interests');
        const editBio = document.getElementById('comm-edit-bio');
        if (editName) editName.value = profile.display_name || '';
        if (editInst) editInst.value = profile.institution || '';
        if (editCity) editCity.value = profile.city ? `${profile.city}${profile.state ? ' - ' + profile.state : ''}` : '';
        if (editInterests) editInterests.value = profile.interests || '';
        if (editBio) editBio.value = profile.bio || '';
    } catch (e) {
        console.warn('Erro ao carregar perfil comunitário:', e);
    }
}

async function activateMyCommunityProfile() {
    const u = getCurrentUser();
    if (!u) return;

    try {
        await api.activateCommunityProfile({ display_name: u.name });
        u.has_community_access = true;
        localStorage.setItem('lacc_user', JSON.stringify(u));
        showToast('Perfil na Comunidade ativado com sucesso!');
        loadCommunityProfile();
    } catch (err) {
        showToast(err.message || 'Erro ao ativar perfil comunitário.', 'error');
    }
}

async function submitEditCommunityProfile(e) {
    e.preventDefault();
    const displayName = document.getElementById('comm-edit-display-name')?.value.trim();
    const institution = document.getElementById('comm-edit-institution')?.value.trim();
    const city = document.getElementById('comm-edit-city')?.value.trim();
    const interests = document.getElementById('comm-edit-interests')?.value.trim();
    const bio = document.getElementById('comm-edit-bio')?.value.trim();

    try {
        const payload = {
            display_name: displayName,
            institution: institution || null,
            city: city || null,
            interests: interests || null,
            bio: bio || null
        };
        await api.updateMyCommunityProfile(payload);
        closeModal('modal-edit-community-profile');
        showToast('Perfil comunitário atualizado com sucesso!');
        loadCommunityProfile();
    } catch (err) {
        showToast(err.message || 'Falha ao atualizar perfil comunitário.', 'error');
    }
}

// ==========================================
// NAVEGAÇÃO ENTRE ABAS
// ==========================================
function navigateTo(viewId) {
    if (typeof closeMobileSidebar === 'function') {
        closeMobileSidebar();
    }
    if (viewId === 'community') {
        switchEnvironment('community');
        return;
    }

    const u = getCurrentUser();
    if (viewId !== 'profile' && u && !u.has_member_access && !u.is_superadmin) {
        showToast('Acesso restrito: Este recurso exige vínculo institucional ativo de membro da LACC.', 'warning');
        switchEnvironment('community');
        return;
    }

    if (viewId === 'athena') {
        const directorRoles = [
            'director', 'diretor', 'diretoria', 'presidente', 'presidencia',
            'vice_presidente', 'vice_presidencia', 'comunicacao', 'pesquisa',
            'eventos', 'tesouraria', 'tesoureiro', 'secretaria', 'secretario',
            'admin', 'superadmin', 'super_admin'
        ];
        const perms = Array.isArray(u?.permissions) ? u.permissions : [];
        const roles = Array.isArray(u?.roles) 
            ? u.roles.map(r => (typeof r === 'object' && r ? (r.slug || r.name || '') : String(r)).toLowerCase()) 
            : [];
        const roleStr = String(u?.role || '').toLowerCase();
        const emailStr = String(u?.email || '').toLowerCase();

        const isSuper = u?.is_superadmin || emailStr === 'paulo.alberto.ofc@gmail.com' || roleStr === 'superadmin' || roles.includes('superadmin') || roles.includes('super_admin');
        const isAdm = u?.is_admin || isSuper;

        const isDirector = isAdm || isSuper ||
            roles.some(r => directorRoles.includes(r)) ||
            directorRoles.includes(roleStr) ||
            perms.includes('athena.access') ||
            perms.includes('*');

        if (!isDirector) {
            showToast('Acesso restrito: O sistema cognitivo Athena é de uso exclusivo da Diretoria e Administração da LACC.', 'warning');
            navigateTo('dashboard');
            return;
        }
    }

    currentView = viewId;

    // Esconder todas as seções
    document.querySelectorAll('#view-container > section').forEach(sec => {
        sec.classList.add('hidden');
    });

    // Mostrar seção ativa
    const activeSec = document.getElementById(`view-${viewId}`);
    if (activeSec) {
        activeSec.classList.remove('hidden');
    }

    // Atualizar Sidebar Desktop
    document.querySelectorAll('#desktop-nav .nav-btn').forEach(btn => {
        if (btn.getAttribute('data-nav') === viewId) {
            btn.className = 'nav-btn w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition bg-brand-600 text-white shadow-sm';
        } else {
            btn.className = 'nav-btn w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition text-slate-300 hover:bg-slate-800 hover:text-white';
        }
    });

    // Atualizar Mobile Nav
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
        if (btn.getAttribute('data-nav') === viewId) {
            btn.classList.add('text-brand-600');
            btn.classList.remove('text-slate-400');
        } else {
            btn.classList.remove('text-brand-600');
            btn.classList.add('text-slate-400');
        }
    });

    // Carregar dados da view
    if (viewId === 'dashboard') loadDashboard();
    else if (viewId === 'members') loadMembers();
    else if (viewId === 'attendance') loadAttendanceView();
    else if (viewId === 'tasks') loadTasks();
    else if (viewId === 'materials') loadMaterials();
    else if (viewId === 'finances') loadFinances();
    else if (viewId === 'settings') fillSettingsForm();
    else if (viewId === 'profile') loadMyProfile();
    else if (viewId === 'communication') loadCommunicationView();
    else if (viewId === 'athena') loadAthenaView();

    initIcons();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// CONFIGURAÇÕES
// ==========================================
async function loadSettings() {
    try {
        leagueSettings = await api.getSettings();
        
        // Textos
        const sigla = leagueSettings.league_sigla || 'LACC';
        const name = leagueSettings.league_name || 'Liga Acadêmica de Ciências Criminais';
        const uni = leagueSettings.university || 'Faculdade Serra Dourada';
        const year = leagueSettings.management_year || '2026';

        // Dashboard
        const elSideSigla = document.getElementById('sidebar-sigla');
        if (elSideSigla) elSideSigla.innerText = sigla;
        const elMobSigla = document.getElementById('mobile-sigla');
        if (elMobSigla) elMobSigla.innerText = sigla;
        const elSideName = document.getElementById('sidebar-league-name');
        if (elSideName) elSideName.innerText = name;
        const elMobName = document.getElementById('mobile-league-name');
        if (elMobName) elMobName.innerText = name;
        const elSideYear = document.getElementById('sidebar-year');
        if (elSideYear) elSideYear.innerText = year;
        const elDashWelcome = document.getElementById('dash-welcome-title');
        if (elDashWelcome) elDashWelcome.innerText = name;

        // Tela Inicial Pública (Landing Page)
        const elLandNavTitle = document.getElementById('landing-nav-title');
        if (elLandNavTitle) elLandNavTitle.innerText = name;
        const elLandNavSub = document.getElementById('landing-nav-sub');
        if (elLandNavSub) elLandNavSub.innerText = uni;
        const elLandMainTitle = document.getElementById('landing-main-title');
        if (elLandMainTitle) elLandMainTitle.innerText = name;
        const elLandBadge = document.getElementById('landing-badge-faculdade');
        if (elLandBadge) elLandBadge.innerText = `${uni} • Gestão ${year}`;
        const elLandFootName = document.getElementById('landing-footer-name');
        if (elLandFootName) elLandFootName.innerText = `${name} (${sigla})`;
        const elLandFootUni = document.getElementById('landing-footer-uni');
        if (elLandFootUni) elLandFootUni.innerText = uni;
        const elDrawerCopy = document.getElementById('drawer-year-copy');
        if (elDrawerCopy) elDrawerCopy.innerText = `© ${year} ${sigla} • ${uni}`;

        // Brasão / Logo
        const logoUrl = leagueSettings.league_logo_url;
        
        // Elementos Dashboard
        const sidebarImg = document.getElementById('sidebar-logo-img');
        const sidebarSigla = document.getElementById('sidebar-sigla');
        const mobileImg = document.getElementById('mobile-logo-img');
        const mobileSigla = document.getElementById('mobile-sigla');
        const previewImg = document.getElementById('setting-logo-preview');
        const emptyState = document.getElementById('setting-logo-empty');
        const btnRemove = document.getElementById('btn-remove-logo');

        // Elementos Landing & Login
        const landNavLogo = document.getElementById('landing-nav-logo');
        const landNavSigla = document.getElementById('landing-nav-sigla');
        const landHeroLogo = document.getElementById('landing-hero-logo');
        const landHeroSigla = document.getElementById('landing-hero-sigla');
        const heroParallaxCrestImg = document.getElementById('hero-parallax-crest-img');
        const centralHubLogo = document.getElementById('central-hub-logo');
        const loginLogoImg = document.getElementById('login-logo-img');
        const loginLogoSigla = document.getElementById('login-logo-sigla');

        if (landNavSigla) landNavSigla.innerText = sigla;
        if (landHeroSigla) landHeroSigla.innerText = sigla;
        if (loginLogoSigla) loginLogoSigla.innerText = sigla;

        if (logoUrl) {
            // Exibir imagem no menu lateral e mobile do dashboard
            if (sidebarImg) { sidebarImg.src = logoUrl; sidebarImg.classList.remove('hidden'); }
            if (sidebarSigla) sidebarSigla.classList.add('hidden');
            if (mobileImg) { mobileImg.src = logoUrl; mobileImg.classList.remove('hidden'); }
            if (mobileSigla) mobileSigla.classList.add('hidden');
            if (previewImg) { previewImg.src = logoUrl; previewImg.classList.remove('hidden'); }
            if (emptyState) emptyState.classList.add('hidden');
            if (btnRemove) btnRemove.classList.remove('hidden');

            // Exibir imagem na landing page, hero parallax, rede central e modal de login
            if (landNavLogo) { landNavLogo.src = logoUrl; landNavLogo.classList.remove('hidden'); }
            if (landNavSigla) landNavSigla.classList.add('hidden');
            if (landHeroLogo) { landHeroLogo.src = logoUrl; landHeroLogo.classList.remove('hidden'); }
            if (landHeroSigla) landHeroSigla.classList.add('hidden');
            if (heroParallaxCrestImg) { heroParallaxCrestImg.src = logoUrl; heroParallaxCrestImg.classList.remove('hidden'); }
            if (centralHubLogo) { centralHubLogo.src = logoUrl; centralHubLogo.classList.remove('hidden'); }
            if (loginLogoImg) { loginLogoImg.src = logoUrl; loginLogoImg.classList.remove('hidden'); }
            if (loginLogoSigla) loginLogoSigla.classList.add('hidden');
        } else {
            // Voltar para a sigla de texto
            if (sidebarImg) sidebarImg.classList.add('hidden');
            if (sidebarSigla) sidebarSigla.classList.remove('hidden');
            if (mobileImg) mobileImg.classList.add('hidden');
            if (mobileSigla) mobileSigla.classList.remove('hidden');
            if (previewImg) previewImg.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            if (btnRemove) btnRemove.classList.add('hidden');

            if (landNavLogo) landNavLogo.classList.add('hidden');
            if (landNavSigla) landNavSigla.classList.remove('hidden');
            if (landHeroLogo) landHeroLogo.classList.add('hidden');
            if (landHeroSigla) landHeroSigla.classList.remove('hidden');
            if (heroParallaxCrestImg) heroParallaxCrestImg.classList.add('hidden');
            if (centralHubLogo) centralHubLogo.classList.add('hidden');
            if (loginLogoImg) loginLogoImg.classList.add('hidden');
            if (loginLogoSigla) loginLogoSigla.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Erro ao carregar configurações:', err);
    }
}

async function uploadLogoFile(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await api.uploadLogo(formData);
        showToast(res.message || 'Brasão da Liga anexado com sucesso!');
        await loadSettings();
        initIcons();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function removeLogoFile() {
    if (!confirm('Deseja remover o brasão da liga? A sigla em texto voltará a ser exibida.')) return;
    try {
        const res = await api.deleteLogo();
        showToast(res.message || 'Brasão removido.');
        await loadSettings();
        initIcons();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function fillSettingsForm() {
    document.getElementById('setting-league-name').value = leagueSettings.league_name || '';
    document.getElementById('setting-league-sigla').value = leagueSettings.league_sigla || '';
    document.getElementById('setting-management-year').value = leagueSettings.management_year || '';
    document.getElementById('setting-university').value = leagueSettings.university || '';
    document.getElementById('setting-min-attendance').value = leagueSettings.min_attendance_percent || '75';
    document.getElementById('setting-monthly-fee').value = leagueSettings.monthly_fee || '30.00';
}

async function saveSettings(e) {
    e.preventDefault();
    const data = {
        league_name: document.getElementById('setting-league-name').value,
        league_sigla: document.getElementById('setting-league-sigla').value,
        management_year: document.getElementById('setting-management-year').value,
        university: document.getElementById('setting-university').value,
        min_attendance_percent: document.getElementById('setting-min-attendance').value,
        monthly_fee: document.getElementById('setting-monthly-fee').value,
    };

    try {
        await api.updateSettings(data);
        await loadSettings();
        showToast('Configurações da Liga salvas com sucesso!');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 1. DASHBOARD
// ==========================================
async function loadDashboard() {
    updateAdminVisibility();
    try {
        const stats = await api.getDashboardStats();

        // KPIs
        document.getElementById('kpi-members').innerText = stats.total_active_members;
        document.getElementById('kpi-total-members').innerText = `Total: ${stats.total_members} cadastrados`;
        document.getElementById('kpi-attendance').innerText = `${stats.avg_attendance}%`;
        document.getElementById('kpi-balance').innerText = `R$ ${stats.balance.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        document.getElementById('kpi-income').innerText = `+R$ ${stats.income.toLocaleString('pt-BR', { minimumFractionDigits: 0 })}`;
        document.getElementById('kpi-expense').innerText = `-R$ ${stats.expense.toLocaleString('pt-BR', { minimumFractionDigits: 0 })}`;
        document.getElementById('kpi-tasks').innerText = stats.pending_tasks.length;

        // Sidebar mini stats
        document.getElementById('sidebar-balance').innerText = `R$ ${stats.balance.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        document.getElementById('sidebar-attendance-avg').innerText = `${stats.avg_attendance}%`;

        // Próximos Encontros
        const eventsContainer = document.getElementById('dash-upcoming-events');
        if (!stats.upcoming_events || stats.upcoming_events.length === 0) {
            eventsContainer.innerHTML = `
                <div class="text-center py-6 text-slate-400 text-xs">
                    Nenhum encontro agendado para os próximos dias.
                </div>
            `;
        } else {
            eventsContainer.innerHTML = stats.upcoming_events.map(ev => `
                <div class="flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100/80 rounded-xl transition border border-slate-100">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-brand-50 text-brand-600 flex flex-col items-center justify-center font-bold">
                            <span class="text-xs">${formatDay(ev.date)}</span>
                            <span class="text-[10px] uppercase font-semibold text-brand-400">${formatMonthShort(ev.date)}</span>
                        </div>
                        <div>
                            <h4 class="font-bold text-slate-800 text-sm leading-snug">${ev.title}</h4>
                            <div class="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                                <span><i data-lucide="clock" class="w-3 h-3 inline"></i> ${ev.time}</span>
                                <span>•</span>
                                <span><i data-lucide="map-pin" class="w-3 h-3 inline"></i> ${ev.location || 'Auditório'}</span>
                                <span>•</span>
                                <span class="text-emerald-600 font-semibold">${ev.hours}h</span>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="projectQrCode('${ev.qr_code_token}', '${ev.title}')" class="px-2.5 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold flex items-center gap-1.5 transition">
                            <i data-lucide="qr-code" class="w-3.5 h-3.5"></i>
                            <span class="hidden sm:inline">QR Code</span>
                        </button>
                        <button onclick="openAttendanceModal(${ev.id}, '${ev.title}')" class="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition">
                            <i data-lucide="check-square" class="w-3.5 h-3.5"></i>
                            <span class="hidden sm:inline">Lista</span>
                        </button>
                    </div>
                </div>
            `).join('');
        }

        // Tarefas Pendentes
        const tasksContainer = document.getElementById('dash-pending-tasks');
        if (!stats.pending_tasks || stats.pending_tasks.length === 0) {
            tasksContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Nenhuma tarefa pendente! Tudo em dia.</div>';
        } else {
            tasksContainer.innerHTML = stats.pending_tasks.map(t => {
                const priorityBadge = t.priority === 'alta' 
                    ? '<span class="text-[10px] font-bold bg-rose-50 text-rose-600 px-2 py-0.5 rounded-full">Alta</span>'
                    : '<span class="text-[10px] font-medium bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">Média</span>';
                
                return `
                    <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
                        <div class="space-y-1">
                            <div class="flex items-center gap-2">
                                ${priorityBadge}
                                <span class="text-xs font-semibold text-slate-500">${t.department}</span>
                            </div>
                            <p class="text-sm font-semibold text-slate-800">${t.title}</p>
                            <span class="text-xs text-slate-400 block">Responsável: ${t.assignee_name || 'Geral'}</span>
                        </div>
                        <button onclick="quickCompleteTask(${t.id})" title="Marcar como concluída" class="p-2 rounded-lg bg-white hover:bg-emerald-50 text-slate-400 hover:text-emerald-600 border border-slate-200 transition">
                            <i data-lucide="check" class="w-4 h-4"></i>
                        </button>
                    </div>
                `;
            }).join('');
        }

        // Materiais Recentes
        const matContainer = document.getElementById('dash-recent-materials');
        if (!stats.recent_materials || stats.recent_materials.length === 0) {
            matContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Nenhum documento adicionado ainda.</div>';
        } else {
            matContainer.innerHTML = stats.recent_materials.map(m => `
                <a href="${m.external_url || '#'}" target="_blank" class="flex items-center justify-between p-3 bg-slate-50 hover:bg-brand-50/50 rounded-xl transition border border-slate-100 group">
                    <div class="flex items-center gap-2.5 overflow-hidden">
                        <div class="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                            <i data-lucide="file-text" class="w-4 h-4"></i>
                        </div>
                        <div class="truncate">
                            <h5 class="text-xs font-bold text-slate-800 truncate group-hover:text-brand-600">${m.title}</h5>
                            <span class="text-[10px] text-slate-400 uppercase font-semibold">${m.category}</span>
                        </div>
                    </div>
                    <i data-lucide="external-link" class="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-600 shrink-0"></i>
                </a>
            `).join('');
        }

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar dashboard:', err);
    }
}

// ==========================================
// 2. MEMBROS & DIRETORIA
// ==========================================
let searchDebounceTimer = null;
function debounceMemberSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(loadMembers, 250);
}

async function loadMembers() {
    try {
        const search = document.getElementById('member-search-input').value;
        const role = document.getElementById('member-filter-role').value;
        const status = document.getElementById('member-filter-status').value;

        const members = await api.getMembers({ search, role, status });
        allMembersCache = members;

        const container = document.getElementById('members-list-container');
        if (members.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12 text-slate-400 text-sm">
                    Nenhum membro encontrado com os filtros atuais.
                </div>
            `;
            return;
        }

        container.innerHTML = members.map(m => {
            const initials = m.name.split(' ').map(n => n[0]).slice(0, 2).join('');
            const statusBadge = m.status === 'Ativo' 
                ? '<span class="text-[10px] font-bold bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full">Ativo</span>'
                : '<span class="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">' + m.status + '</span>';

            const cleanPhone = m.phone ? m.phone.replace(/\D/g, '') : '';
            const waLink = cleanPhone ? `https://wa.me/55${cleanPhone}` : null;

            return `
                <div class="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm hover:shadow transition flex flex-col justify-between">
                    <div>
                        <div class="flex items-start justify-between gap-3 mb-3">
                            <div class="flex items-center gap-3">
                                <div class="w-11 h-11 rounded-2xl flex items-center justify-center text-white font-bold text-sm shadow-sm" style="background-color: ${m.avatar_color || '#2563EB'}">
                                    ${initials}
                                </div>
                                <div>
                                    <h3 class="font-bold text-slate-900 text-sm leading-tight">${m.name}</h3>
                                    <span class="inline-block text-xs font-semibold text-brand-600 mt-0.5">${m.role}</span>
                                </div>
                            </div>
                            ${statusBadge}
                        </div>

                        <div class="text-xs text-slate-500 space-y-1.5 my-3">
                            <div class="flex items-center gap-2 truncate">
                                <i data-lucide="mail" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                                <span class="truncate">${m.email}</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <i data-lucide="graduation-cap" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                                <span>${m.course} • ${m.semester || '1º Período'}</span>
                            </div>
                        </div>
                    </div>

                    <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            ${waLink ? `
                                <a href="${waLink}" target="_blank" title="Conversar no WhatsApp" class="p-2 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-100 transition">
                                    <i data-lucide="message-circle" class="w-4 h-4"></i>
                                </a>
                            ` : ''}
                            <button onclick="viewMemberDetails(${m.id})" title="Ver histórico de horas e frequência" class="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition flex items-center gap-1">
                                <i data-lucide="award" class="w-3.5 h-3.5"></i> Horas
                            </button>
                        </div>
                        <div class="flex items-center gap-1">
                            <button onclick="editMember(${m.id})" title="Editar" class="p-1.5 text-slate-400 hover:text-brand-600 transition">
                                <i data-lucide="pencil" class="w-4 h-4"></i>
                            </button>
                            <button onclick="deleteMember(${m.id})" title="Excluir" class="p-1.5 text-slate-400 hover:text-rose-600 transition">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar membros:', err);
    }
}

async function submitMember(e) {
    e.preventDefault();
    const id = document.getElementById('member-id').value;
    const data = {
        name: document.getElementById('member-name').value,
        email: document.getElementById('member-email').value,
        phone: document.getElementById('member-phone').value,
        role: document.getElementById('member-role').value,
        status: document.getElementById('member-status').value,
        course: document.getElementById('member-course').value,
        semester: document.getElementById('member-semester').value,
        notes: document.getElementById('member-notes').value
    };

    try {
        if (id) {
            await api.updateMember(id, data);
            showToast('Membro atualizado com sucesso!');
        } else {
            await api.createMember(data);
            showToast('Novo membro cadastrado com sucesso!');
        }
        closeModal('modal-member');
        loadMembers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function editMember(id) {
    try {
        const m = await api.getMember(id);
        document.getElementById('member-id').value = m.id;
        document.getElementById('member-name').value = m.name;
        document.getElementById('member-email').value = m.email;
        document.getElementById('member-phone').value = m.phone || '';
        document.getElementById('member-role').value = m.role;
        document.getElementById('member-status').value = m.status;
        document.getElementById('member-course').value = m.course || 'Medicina';
        document.getElementById('member-semester').value = m.semester || '';
        document.getElementById('member-notes').value = m.notes || '';
        
        document.getElementById('modal-member-title').innerText = 'Editar Membro';
        openModal('modal-member');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteMember(id) {
    if (!confirm('Deseja realmente remover este membro da liga?')) return;
    try {
        await api.deleteMember(id);
        showToast('Membro removido com sucesso.');
        loadMembers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function viewMemberDetails(id) {
    try {
        const m = await api.getMember(id);
        document.getElementById('detail-name').innerText = m.name;
        document.getElementById('detail-role-course').innerText = `${m.role} • ${m.course} (${m.semester || '1º Período'})`;
        document.getElementById('detail-frequence').innerText = `${m.frequence_pct}%`;
        document.getElementById('detail-hours').innerText = `${m.total_hours}h`;

        const avatar = document.getElementById('detail-avatar');
        avatar.style.backgroundColor = m.avatar_color || '#2563EB';
        avatar.innerText = m.name.split(' ').map(n => n[0]).slice(0, 2).join('');

        const historyList = document.getElementById('detail-history-list');
        if (!m.attendance_history || m.attendance_history.length === 0) {
            historyList.innerHTML = '<div class="text-slate-400 text-center py-4">Nenhuma presença registrada ainda.</div>';
        } else {
            historyList.innerHTML = m.attendance_history.map(h => {
                const isPres = h.status === 'Presente';
                const statusBadge = isPres
                    ? '<span class="text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded">Presente (+ ' + h.hours + 'h)</span>'
                    : '<span class="text-slate-500 bg-slate-100 px-2 py-0.5 rounded">' + h.status + '</span>';
                
                return `
                    <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <div>
                            <div class="font-semibold text-slate-800">${h.title}</div>
                            <div class="text-[11px] text-slate-400">${formatDate(h.date)} • ${h.event_type}</div>
                        </div>
                        ${statusBadge}
                    </div>
                `;
            }).join('');
        }

        openModal('modal-member-details');
        initIcons();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function exportMembersCSV() {
    try {
        const blob = await api.request('/members/export/csv');
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `membros_liga_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Planilha de membros exportada!');
    } catch (err) {
        showToast('Erro ao exportar planilha', 'error');
    }
}

// ==========================================
// 3. FREQUÊNCIA & EVENTOS
// ==========================================
function switchAttendanceTab(tab) {
    const btnEvents = document.getElementById('subtab-events');
    const btnSummary = document.getElementById('subtab-summary');
    const panelEvents = document.getElementById('attendance-events-panel');
    const panelSummary = document.getElementById('attendance-summary-panel');

    if (tab === 'events') {
        btnEvents.className = 'py-2.5 font-semibold text-sm border-b-2 border-brand-600 text-brand-600 transition';
        btnSummary.className = 'py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition';
        panelEvents.classList.remove('hidden');
        panelSummary.classList.add('hidden');
        loadEvents();
    } else {
        btnEvents.className = 'py-2.5 font-semibold text-sm border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition';
        btnSummary.className = 'py-2.5 font-semibold text-sm border-b-2 border-brand-600 text-brand-600 transition';
        panelEvents.classList.add('hidden');
        panelSummary.classList.remove('hidden');
        loadAttendanceSummary();
    }
}

async function loadAttendanceView() {
    loadEvents();
}

async function loadEvents() {
    try {
        const events = await api.getEvents();
        const container = document.getElementById('events-list-container');

        if (events.length === 0) {
            container.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400 text-sm">Nenhum evento cadastrado.</div>';
            return;
        }

        container.innerHTML = events.map(ev => `
            <div class="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm flex flex-col justify-between">
                <div>
                    <div class="flex items-start justify-between gap-2 mb-2">
                        <span class="text-xs font-bold uppercase tracking-wider text-brand-600 bg-brand-50 px-2.5 py-0.5 rounded-full">${ev.event_type}</span>
                        <div class="flex items-center gap-1">
                            <span class="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">${ev.hours}h computadas</span>
                        </div>
                    </div>
                    <h3 class="font-bold text-slate-800 text-base leading-snug my-1.5">${ev.title}</h3>
                    <p class="text-xs text-slate-500 line-clamp-2 mb-3">${ev.description || 'Sem descrição adicional.'}</p>
                    
                    <div class="space-y-1 text-xs text-slate-500 pt-2 border-t border-slate-100">
                        <div><i data-lucide="calendar" class="w-3.5 h-3.5 inline text-slate-400"></i> ${formatDate(ev.date)} às ${ev.time}</div>
                        <div><i data-lucide="map-pin" class="w-3.5 h-3.5 inline text-slate-400"></i> ${ev.location || 'Local a definir'}</div>
                        <div class="text-emerald-700 font-semibold"><i data-lucide="users" class="w-3.5 h-3.5 inline"></i> ${ev.present_count || 0} membros presentes</div>
                    </div>
                </div>

                <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button onclick="projectQrCode('${ev.qr_code_token}', '${ev.title}')" class="flex-1 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm transition">
                        <i data-lucide="qr-code" class="w-4 h-4"></i> QR Code
                    </button>
                    <button onclick="openAttendanceModal(${ev.id}, '${ev.title}')" class="flex-1 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition">
                        <i data-lucide="check-square" class="w-4 h-4"></i> Lista
                    </button>
                    <button onclick="deleteEvent(${ev.id})" title="Excluir Aula" class="p-2 rounded-xl text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar eventos:', err);
    }
}

async function submitEvent(e) {
    e.preventDefault();
    const data = {
        title: document.getElementById('event-title').value,
        event_type: document.getElementById('event-type').value,
        hours: parseFloat(document.getElementById('event-hours').value),
        date: document.getElementById('event-date').value,
        time: document.getElementById('event-time').value,
        location: document.getElementById('event-location').value,
        description: document.getElementById('event-description').value
    };

    try {
        await api.createEvent(data);
        showToast('Encontro criado com sucesso!');
        closeModal('modal-event');
        loadEvents();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteEvent(id) {
    if (!confirm('Excluir esta aula e todo seu registro de frequência?')) return;
    try {
        await api.deleteEvent(id);
        showToast('Aula excluída.');
        loadEvents();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Projeção do QR Code
function projectQrCode(token, title) {
    currentQrToken = token;
    document.getElementById('qr-event-title').innerText = title;
    document.getElementById('qr-token-display').innerText = `Token: ${token}`;

    const container = document.getElementById('qrcode-canvas');
    container.innerHTML = '';

    const checkinUrl = `${window.location.origin}/checkin.html?token=${token}`;

    new QRCode(container, {
        text: checkinUrl,
        width: 220,
        height: 220,
        colorDark: "#0f172a",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });

    openModal('modal-qrcode');
}

function openCheckinDirectly() {
    if (currentQrToken) {
        window.open(`/checkin.html?token=${currentQrToken}`, '_blank');
    }
}

// Modal de Marcação de Presença Manual em Lote
async function openAttendanceModal(eventId, eventTitle) {
    currentEventForAttendance = eventId;
    document.getElementById('att-modal-event-title').innerText = `Presença: ${eventTitle}`;

    try {
        const ev = await api.getEvent(eventId);
        const container = document.getElementById('att-members-checkboxes');
        
        let presentCount = 0;
        container.innerHTML = ev.attendees.map(m => {
            const isPresent = m.status === 'Presente';
            if (isPresent) presentCount++;

            return `
                <label class="flex items-center justify-between p-2.5 hover:bg-slate-50 rounded-xl cursor-pointer transition">
                    <div class="flex items-center gap-3">
                        <input type="checkbox" name="att-member" value="${m.member_id}" ${isPresent ? 'checked' : ''} onchange="updateAttendanceCount()" class="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500">
                        <div>
                            <span class="text-sm font-semibold text-slate-800">${m.name}</span>
                            <span class="text-xs text-slate-400 block">${m.role}</span>
                        </div>
                    </div>
                    <span class="text-xs text-slate-400">${m.checkin_time ? formatTime(m.checkin_time) : ''}</span>
                </label>
            `;
        }).join('');

        document.getElementById('att-present-count').innerText = presentCount;
        openModal('modal-attendance-list');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function updateAttendanceCount() {
    const checked = document.querySelectorAll('input[name="att-member"]:checked').length;
    document.getElementById('att-present-count').innerText = checked;
}

function toggleAllAttendance(check) {
    document.querySelectorAll('input[name="att-member"]').forEach(cb => {
        cb.checked = check;
    });
    updateAttendanceCount();
}

async function saveEventAttendance() {
    if (!currentEventForAttendance) return;
    const selectedIds = Array.from(document.querySelectorAll('input[name="att-member"]:checked')).map(cb => parseInt(cb.value));

    try {
        await api.updateEventAttendance(currentEventForAttendance, selectedIds);
        showToast('Presenças atualizadas com sucesso!');
        closeModal('modal-attendance-list');
        loadEvents();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadAttendanceSummary() {
    try {
        const minPct = parseFloat(leagueSettings.min_attendance_percent || '75');
        document.getElementById('summary-meta-badge').innerText = `${minPct}%`;

        const summary = await api.getAttendanceSummary();
        const tbody = document.getElementById('attendance-summary-tbody');

        if (summary.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-slate-400 text-xs">Nenhum dado encontrado.</td></tr>';
            return;
        }

        tbody.innerHTML = summary.map(m => {
            const isEligible = m.frequency_percent >= minPct;
            const certBadge = isEligible
                ? '<span class="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full"><i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i> Apto</span>'
                : '<span class="inline-flex items-center gap-1 text-xs font-semibold text-rose-600 bg-rose-50 px-2.5 py-1 rounded-full"><i data-lucide="alert-circle" class="w-3.5 h-3.5"></i> Inapto</span>';

            const pctColor = isEligible ? 'text-emerald-600' : 'text-rose-500';

            return `
                <tr class="hover:bg-slate-50/80 transition">
                    <td class="px-5 py-3 font-semibold text-slate-800">${m.name}</td>
                    <td class="px-4 py-3 text-slate-600 text-xs">${m.role}</td>
                    <td class="px-4 py-3 text-center text-slate-600 text-xs">${m.presents} / ${m.total_events}</td>
                    <td class="px-4 py-3 font-bold ${pctColor}">${m.frequency_percent}%</td>
                    <td class="px-4 py-3 text-center font-semibold text-brand-600">${m.total_hours}h</td>
                    <td class="px-4 py-3 text-center">${certBadge}</td>
                </tr>
            `;
        }).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar resumo de frequência:', err);
    }
}

// ==========================================
// 4. KANBAN / TAREFAS
// ==========================================
async function loadTasks() {
    try {
        const tasks = await api.getTasks();

        // Popular select de membros no modal de tarefas
        const selectAssignee = document.getElementById('task-assignee');
        if (selectAssignee && allMembersCache.length > 0) {
            selectAssignee.innerHTML = '<option value="">Não atribuído</option>' + 
                allMembersCache.map(m => `<option value="${m.id}">${m.name} (${m.role})</option>`).join('');
        }

        const cols = {
            todo: document.getElementById('kanban-todo'),
            in_progress: document.getElementById('kanban-in_progress'),
            done: document.getElementById('kanban-done')
        };

        cols.todo.innerHTML = '';
        cols.in_progress.innerHTML = '';
        cols.done.innerHTML = '';

        let cnts = { todo: 0, in_progress: 0, done: 0 };

        tasks.forEach(t => {
            cnts[t.status] = (cnts[t.status] || 0) + 1;

            const priorityPills = {
                alta: '<span class="text-[10px] font-bold bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full">Alta</span>',
                media: '<span class="text-[10px] font-medium bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">Média</span>',
                baixa: '<span class="text-[10px] font-medium bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">Baixa</span>'
            };

            const card = document.createElement('div');
            card.className = 'bg-white p-4 rounded-xl border border-slate-200 shadow-sm kanban-card space-y-2.5';
            card.innerHTML = `
                <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-1.5">
                        ${priorityPills[t.priority] || ''}
                        <span class="text-[11px] font-semibold text-slate-500">${t.department}</span>
                    </div>
                    <button onclick="deleteTask(${t.id})" class="text-slate-300 hover:text-rose-500 transition"><i data-lucide="trash" class="w-3.5 h-3.5"></i></button>
                </div>
                <h4 class="font-bold text-slate-800 text-sm leading-snug">${t.title}</h4>
                ${t.description ? `<p class="text-xs text-slate-500 line-clamp-2">${t.description}</p>` : ''}
                
                <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                    <span class="flex items-center gap-1">
                        <i data-lucide="user" class="w-3.5 h-3.5"></i>
                        <span class="truncate max-w-[100px]">${t.assignee_name || 'Livre'}</span>
                    </span>
                    ${t.due_date ? `<span><i data-lucide="calendar" class="w-3 h-3 inline"></i> ${formatDayMonth(t.due_date)}</span>` : ''}
                </div>

                <!-- Botões para mover coluna -->
                <div class="flex justify-end gap-1.5 pt-1">
                    ${t.status !== 'todo' ? `
                        <button onclick="moveTask(${t.id}, '${t.status === 'done' ? 'in_progress' : 'todo'}')" title="Mover para trás" class="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs">
                            <i data-lucide="arrow-left" class="w-3 h-3"></i>
                        </button>
                    ` : ''}
                    ${t.status !== 'done' ? `
                        <button onclick="moveTask(${t.id}, '${t.status === 'todo' ? 'in_progress' : 'done'}')" title="Avançar etapa" class="p-1 rounded bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-semibold flex items-center gap-1">
                            <span>Avançar</span> <i data-lucide="arrow-right" class="w-3 h-3"></i>
                        </button>
                    ` : ''}
                </div>
            `;
            if (cols[t.status]) {
                cols[t.status].appendChild(card);
            }
        });

        document.getElementById('task-cnt-todo').innerText = cnts.todo;
        document.getElementById('task-cnt-in_progress').innerText = cnts.in_progress;
        document.getElementById('task-cnt-done').innerText = cnts.done;

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar tarefas:', err);
    }
}

async function moveTask(id, newStatus) {
    try {
        await api.updateTaskStatus(id, newStatus);
        loadTasks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function quickCompleteTask(id) {
    try {
        await api.updateTaskStatus(id, 'done');
        showToast('Tarefa marcada como concluída!');
        loadDashboard();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitTask(e) {
    e.preventDefault();
    const data = {
        title: document.getElementById('task-title').value,
        description: document.getElementById('task-desc').value,
        department: document.getElementById('task-dept').value,
        priority: document.getElementById('task-priority').value,
        assignee_id: document.getElementById('task-assignee').value ? parseInt(document.getElementById('task-assignee').value) : null,
        due_date: document.getElementById('task-due-date').value || null
    };

    try {
        await api.createTask(data);
        showToast('Tarefa adicionada ao quadro!');
        closeModal('modal-task');
        loadTasks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteTask(id) {
    if (!confirm('Deseja excluir esta tarefa?')) return;
    try {
        await api.deleteTask(id);
        showToast('Tarefa excluída.');
        loadTasks();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 5. MATERIAIS & BIBLIOTECA
// ==========================================
function filterMaterials(category) {
    currentCategoryFilter = category;
    document.querySelectorAll('.mat-filter-btn').forEach(btn => {
        if (btn.innerText.includes(category) || (category === 'Todos' && btn.innerText === 'Todos')) {
            btn.className = 'mat-filter-btn px-4 py-1.5 rounded-full text-xs font-semibold bg-brand-600 text-white transition shadow-sm';
        } else {
            btn.className = 'mat-filter-btn px-4 py-1.5 rounded-full text-xs font-medium bg-white text-slate-600 hover:bg-slate-100 border border-slate-200 transition';
        }
    });
    loadMaterials();
}

async function loadMaterials() {
    try {
        const materials = await api.getMaterials(currentCategoryFilter);
        const container = document.getElementById('materials-grid-container');

        if (materials.length === 0) {
            container.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400 text-sm">Nenhum documento cadastrado nesta categoria.</div>';
            return;
        }

        container.innerHTML = materials.map(m => {
            const isLocalUpload = m.file_path !== null;
            const openLink = m.external_url || '#';

            return `
                <div class="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-sm hover:shadow transition flex flex-col justify-between">
                    <div>
                        <div class="flex items-center justify-between mb-3">
                            <span class="text-[10px] uppercase font-bold tracking-wider text-brand-700 bg-brand-50 px-2.5 py-0.5 rounded-full">${m.category}</span>
                            <button onclick="deleteMaterial(${m.id})" class="text-slate-300 hover:text-rose-500 transition"><i data-lucide="trash" class="w-3.5 h-3.5"></i></button>
                        </div>
                        <h4 class="font-bold text-slate-900 text-sm leading-snug mb-1">${m.title}</h4>
                        <p class="text-xs text-slate-500 mb-3 line-clamp-2">${m.description || 'Sem descrição.'}</p>
                        ${m.author_or_speaker ? `<span class="text-xs text-slate-400 block"><i data-lucide="user-check" class="w-3 h-3 inline"></i> ${m.author_or_speaker}</span>` : ''}
                    </div>

                    <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span class="text-[11px] text-slate-400">${formatDate(m.uploaded_at)}</span>
                        <a href="${openLink}" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold shadow-sm transition">
                            <span>${isLocalUpload ? 'Baixar Arquivo' : 'Acessar Link'}</span>
                            <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                        </a>
                    </div>
                </div>
            `;
        }).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar materiais:', err);
    }
}

function toggleMatType(type) {
    if (type === 'link') {
        document.getElementById('mat-link-field').classList.remove('hidden');
        document.getElementById('mat-file-field').classList.add('hidden');
    } else {
        document.getElementById('mat-link-field').classList.add('hidden');
        document.getElementById('mat-file-field').classList.remove('hidden');
    }
}

async function submitMaterial(e) {
    e.preventDefault();
    const type = document.querySelector('input[name="mat-type"]:checked').value;
    const title = document.getElementById('mat-title').value;
    const category = document.getElementById('mat-category').value;
    const author = document.getElementById('mat-author').value;
    const desc = document.getElementById('mat-desc').value;

    try {
        if (type === 'link') {
            await api.createMaterial({
                title,
                category,
                file_type: 'link',
                external_url: document.getElementById('mat-url').value,
                description: desc,
                author_or_speaker: author
            });
        } else {
            const fileInput = document.getElementById('mat-file');
            if (!fileInput.files[0]) {
                alert('Selecione um arquivo para envio!');
                return;
            }
            const formData = new FormData();
            formData.append('title', title);
            formData.append('category', category);
            formData.append('author_or_speaker', author);
            formData.append('description', desc);
            formData.append('file', fileInput.files[0]);

            await api.uploadMaterial(formData);
        }

        showToast('Documento adicionado à biblioteca!');
        closeModal('modal-material');
        loadMaterials();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteMaterial(id) {
    if (!confirm('Deseja excluir este material da biblioteca?')) return;
    try {
        await api.deleteMaterial(id);
        showToast('Documento excluído.');
        loadMaterials();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// 6. FINANCEIRO
// ==========================================
async function loadFinances() {
    try {
        const data = await api.getFinances();
        
        document.getElementById('fin-balance').innerText = `R$ ${data.balance.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        document.getElementById('fin-income').innerText = `R$ ${data.income.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        document.getElementById('fin-expense').innerText = `R$ ${data.expense.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

        const tbody = document.getElementById('finances-tbody');
        if (data.transactions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-slate-400 text-xs">Nenhuma movimentação registrada.</td></tr>';
            return;
        }

        tbody.innerHTML = data.transactions.map(t => {
            const isIncome = t.type === 'income';
            const typeBadge = isIncome
                ? '<span class="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full text-xs font-semibold">Entrada</span>'
                : '<span class="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full text-xs font-semibold">Saída</span>';

            const valueDisplay = isIncome
                ? `+ R$ ${t.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
                : `- R$ ${t.amount.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

            const valueColor = isIncome ? 'text-emerald-600' : 'text-rose-600';

            return `
                <tr class="hover:bg-slate-50 transition">
                    <td class="px-5 py-3 text-xs text-slate-500">${formatDate(t.date)}</td>
                    <td class="px-4 py-3">${typeBadge}</td>
                    <td class="px-4 py-3 text-xs font-semibold text-slate-700">${t.category}</td>
                    <td class="px-4 py-3 text-xs text-slate-800">${t.description}</td>
                    <td class="px-5 py-3 text-right font-bold text-sm ${valueColor}">${valueDisplay}</td>
                    <td class="px-4 py-3 text-center">
                        <button onclick="deleteFinance(${t.id})" class="text-slate-300 hover:text-rose-600 transition"><i data-lucide="trash-2" class="w-4 h-4"></i></button>
                    </td>
                </tr>
            `;
        }).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar finanças:', err);
    }
}

async function submitFinance(e) {
    e.preventDefault();
    const data = {
        type: document.getElementById('fin-type').value,
        amount: parseFloat(document.getElementById('fin-amount').value),
        category: document.getElementById('fin-category').value,
        date: document.getElementById('fin-date').value,
        description: document.getElementById('fin-desc').value
    };

    try {
        await api.createFinance(data);
        showToast('Lançamento registrado com sucesso!');
        closeModal('modal-finance');
        loadFinances();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteFinance(id) {
    if (!confirm('Deseja excluir este lançamento financeiro?')) return;
    try {
        await api.deleteFinance(id);
        showToast('Lançamento excluído.');
        loadFinances();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// UTILITÁRIOS E MODAIS
// ==========================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        initIcons();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return dateStr;
    } catch (e) {
        return dateStr;
    }
}

function formatDay(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    return parts.length === 3 ? parts[2] : '';
}

function formatDayMonth(dateStr) {
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}` : dateStr;
}

function formatMonthShort(dateStr) {
    if (!dateStr) return '';
    const months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        const mIdx = parseInt(parts[1], 10) - 1;
        return months[mIdx] || '';
    }
    return '';
}

function formatTime(isoTime) {
    if (!isoTime) return '';
    try {
        const d = new Date(isoTime);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '';
    }
}

// ==========================================
// COMPARTILHAMENTO E CÓPIA DO SITE
// ==========================================
function openShareModal() {
    const origin = window.location.origin;
    const urlInput = document.getElementById('share-site-url');
    if (urlInput) {
        urlInput.value = origin;
    }

    // Gerar QR Code do site
    const qrBox = document.getElementById('share-qrcode-box');
    if (qrBox) {
        qrBox.innerHTML = '';
        new QRCode(qrBox, {
            text: origin,
            width: 170,
            height: 170,
            colorDark: "#0f172a",
            colorLight: "#f8fafc",
            correctLevel: QRCode.CorrectLevel.H
        });
    }

    openModal('modal-share');
}

async function copySiteLink() {
    const origin = window.location.origin;
    try {
        await navigator.clipboard.writeText(origin);
        const btnText = document.getElementById('btn-copy-text');
        if (btnText) {
            btnText.innerText = 'Copiado!';
            setTimeout(() => { btnText.innerText = 'Copiar Link'; }, 2500);
        }
        showToast('Link do site copiado para a área de transferência!');
    } catch (err) {
        // Fallback usando seleção de texto
        const urlInput = document.getElementById('share-site-url');
        if (urlInput) {
            urlInput.select();
            document.execCommand('copy');
            showToast('Link do site copiado!');
        }
    }
}

function shareOnWhatsApp() {
    const origin = window.location.origin;
    const leagueName = leagueSettings.league_name || 'Liga Acadêmica';
    const text = `*${leagueName}*\nAcesse a plataforma da nossa liga para verificar cronograma de aulas, frequência e atividades:\n${origin}`;
    const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
    window.open(waUrl, '_blank');
}

async function triggerNativeShare() {
    const origin = window.location.origin;
    const leagueName = leagueSettings.league_name || 'Liga Acadêmica';

    if (navigator.share) {
        try {
            await navigator.share({
                title: leagueName,
                text: `Acesse o portal da ${leagueName}:`,
                url: origin
            });
        } catch (err) {
            if (err.name !== 'AbortError') {
                copySiteLink();
            }
        }
    } else {
        copySiteLink();
    }
}

// ==========================================
// CENTRAL DE COMUNICAÇÃO & GESTÃO EDITORIAL
// ==========================================
let currentCommTab = 'overview';
let cachedNewsCategories = [];
let cachedPublishedArticles = [];
let cachedEventsForNl = [];
let nlPreviewCurrentEditionId = null;

function switchCommTab(tabId) {
    currentCommTab = tabId;

    // Atualizar botões de sub-abas
    document.querySelectorAll('#comm-subnav .comm-tab-btn').forEach(btn => {
        btn.className = 'comm-tab-btn px-4 py-2 rounded-xl text-xs font-medium transition text-slate-600 hover:bg-slate-100 flex items-center gap-2';
    });
    const activeBtn = document.getElementById(`comm-tab-${tabId}`);
    if (activeBtn) {
        activeBtn.className = 'comm-tab-btn px-4 py-2 rounded-xl text-xs font-bold transition bg-brand-600 text-white shadow-sm flex items-center gap-2';
    }

    // Ocultar todos os sub-painéis
    document.querySelectorAll('.comm-subpanel').forEach(p => p.classList.add('hidden'));

    // Mostrar sub-painel selecionado
    const activePanel = document.getElementById(`comm-panel-${tabId}`);
    if (activePanel) {
        activePanel.classList.remove('hidden');
    }

    // Carregar dados específicos da aba
    if (tabId === 'overview') loadCommunicationOverview();
    else if (tabId === 'news') loadInternalNewsTable();
    else if (tabId === 'pitches') loadPitchesTable();
    else if (tabId === 'newsletter') loadNewslettersTable();
    else if (tabId === 'calendar') loadCalendarView();
    else if (tabId === 'media') loadMediaAssetsView();
    else if (tabId === 'subscribers') loadSubscribersTable();

    initIcons();
}

async function loadCommunicationView() {
    try {
        await loadCategoriesCache();
        switchCommTab(currentCommTab || 'overview');
    } catch (err) {
        console.error('Erro ao inicializar Central de Comunicação:', err);
    }
}

async function loadCategoriesCache() {
    try {
        cachedNewsCategories = await api.getNewsCategories();
        // Popular selects
        const catSelects = ['news-input-category', 'pitch-input-category', 'comm-news-filter-cat'];
        catSelects.forEach(selId => {
            const el = document.getElementById(selId);
            if (!el) return;
            const currentVal = el.value;
            const isFilter = selId.includes('filter');
            el.innerHTML = isFilter ? '<option value="">Todas as Categorias</option>' : '';
            cachedNewsCategories.forEach(c => {
                if (c.is_active || !isFilter) {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.name;
                    el.appendChild(opt);
                }
            });
            if (currentVal) el.value = currentVal;
        });
    } catch (e) {
        console.warn('Erro ao carregar categorias:', e);
    }
}

// 1. Visão Geral
async function loadCommunicationOverview() {
    try {
        const data = await api.getCommunicationOverview();
        const k = data.kpis || {};

        const elPub = document.getElementById('comm-kpi-published');
        if (elPub) elPub.innerText = k.published_articles || 0;
        const elDraft = document.getElementById('comm-kpi-drafts');
        if (elDraft) elDraft.innerText = (k.drafts || 0) + (k.pending_review || 0);
        const elPitches = document.getElementById('comm-kpi-pitches');
        if (elPitches) elPitches.innerText = k.active_pitches || 0;
        const elSubs = document.getElementById('comm-kpi-subscribers');
        if (elSubs) elSubs.innerText = k.active_subscribers || 0;

        // Próxima Newsletter
        const nl = data.next_newsletter;
        const elNlTitle = document.getElementById('comm-overview-nl-title');
        const elNlDesc = document.getElementById('comm-overview-nl-desc');
        if (elNlTitle && elNlDesc) {
            if (nl) {
                elNlTitle.innerText = `Edição #${nl.edition_number}: ${nl.title}`;
                elNlDesc.innerText = `Status: ${nl.status.toUpperCase()} ${nl.scheduled_for ? '• Agendada para ' + nl.scheduled_for : ''}`;
            } else {
                elNlTitle.innerText = 'Nenhuma edição em preparação';
                elNlDesc.innerText = 'Crie a próxima edição referenciando notícias e eventos publicados na Liga.';
            }
        }

        // Matérias recentes
        const elRecentNews = document.getElementById('comm-overview-recent-news');
        if (elRecentNews) {
            if (!data.recent_articles || data.recent_articles.length === 0) {
                elRecentNews.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Nenhuma matéria registrada ainda.</div>';
            } else {
                elRecentNews.innerHTML = data.recent_articles.map(art => {
                    const statusBadge = getStatusBadge(art.editorial_status);
                    return `
                        <div class="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-100 transition">
                            <div class="space-y-1 truncate pr-2">
                                <div class="flex items-center gap-2">
                                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="background-color: ${art.category_color}15; color: ${art.category_color};">${art.category_name}</span>
                                    ${statusBadge}
                                </div>
                                <h4 class="text-xs font-bold text-slate-800 truncate">${art.title}</h4>
                                <span class="text-[10px] text-slate-400 block">Por ${art.author_name}</span>
                            </div>
                            <button onclick="openNewsEditorModal(${art.id})" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 transition shrink-0">
                                Abrir
                            </button>
                        </div>
                    `;
                }).join('');
            }
        }

        // Pautas prioritárias
        const elPitchesList = document.getElementById('comm-overview-priority-pitches');
        if (elPitchesList) {
            if (!data.priority_pitches || data.priority_pitches.length === 0) {
                elPitchesList.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Nenhuma pauta pendente registrada.</div>';
            } else {
                elPitchesList.innerHTML = data.priority_pitches.map(p => `
                    <div class="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-100 transition">
                        <div class="space-y-1 truncate pr-2">
                            <div class="flex items-center gap-2">
                                <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${p.priority === 'alta' ? 'bg-rose-50 text-rose-600' : 'bg-amber-50 text-amber-700'}">${p.priority}</span>
                                <span class="text-[10px] text-slate-500">${p.category_name || 'Geral'}</span>
                            </div>
                            <h4 class="text-xs font-bold text-slate-800 truncate">${p.title}</h4>
                            <span class="text-[10px] text-slate-400 block">Responsável: ${p.assignee_name || 'A definir'}</span>
                        </div>
                        <button onclick="convertPitchToNews(${p.id})" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 transition shrink-0">
                            Escrever →
                        </button>
                    </div>
                `).join('');
            }
        }

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar Visão Geral da Comunicação:', err);
    }
}

function getStatusBadge(st) {
    const map = {
        'draft': '<span class="text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">Rascunho</span>',
        'review': '<span class="text-[10px] font-bold bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded-full">Em Revisão</span>',
        'approved': '<span class="text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">Aprovado</span>',
        'scheduled': '<span class="text-[10px] font-bold bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full">Agendado</span>',
        'published': '<span class="text-[10px] font-bold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">Publicado</span>',
        'archived': '<span class="text-[10px] font-bold bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full">Arquivado</span>'
    };
    return map[st] || `<span class="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">${st}</span>`;
}

// 2. Notícias & Matérias
async function loadInternalNewsTable() {
    const tableBody = document.getElementById('comm-news-table-body');
    if (!tableBody) return;

    const statusFilter = document.getElementById('comm-news-filter-status')?.value || '';
    const catFilter = document.getElementById('comm-news-filter-cat')?.value || '';
    const search = document.getElementById('comm-news-search')?.value || '';

    try {
        const rows = await api.getInternalNews({ status: statusFilter, category_id: catFilter, search });
        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-slate-400 text-xs">Nenhuma matéria encontrada com os filtros selecionados.</td></tr>';
            return;
        }

        tableBody.innerHTML = rows.map(art => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3.5 max-w-xs">
                    <div class="font-bold text-slate-800 line-clamp-1">${art.title}</div>
                    <div class="text-[11px] text-slate-400 line-clamp-1 mt-0.5">${art.summary}</div>
                    ${art.is_featured ? '<span class="inline-block mt-1 text-[9px] bg-amber-50 text-amber-700 font-bold px-1.5 py-0.2 rounded">★ Destaque Home</span>' : ''}
                </td>
                <td class="p-3.5 whitespace-nowrap">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="background-color: ${art.category_color}15; color: ${art.category_color};">
                        ${art.category_name}
                    </span>
                </td>
                <td class="p-3.5 whitespace-nowrap text-slate-700 font-medium">
                    ${art.author_name}
                </td>
                <td class="p-3.5 text-center whitespace-nowrap">
                    ${getStatusBadge(art.editorial_status)}
                </td>
                <td class="p-3.5 text-center whitespace-nowrap">
                    <span class="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                        ${art.sources_count} fontes
                    </span>
                </td>
                <td class="p-3.5 text-center whitespace-nowrap text-slate-400 text-[11px]">
                    ${art.updated_at ? art.updated_at.substring(0, 10) : ''}
                </td>
                <td class="p-3.5 text-right whitespace-nowrap space-x-1">
                    <button onclick="openNewsEditorModal(${art.id})" title="Editar" class="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">
                        <i data-lucide="edit" class="w-3.5 h-3.5"></i>
                    </button>
                    ${art.editorial_status === 'draft' ? `
                        <button onclick="submitNewsForReviewAction(${art.id})" title="Submeter p/ Revisão" class="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700">
                            <i data-lucide="send" class="w-3.5 h-3.5"></i>
                        </button>
                    ` : ''}
                    ${art.editorial_status === 'review' ? `
                        <button onclick="openNewsReviewModal(${art.id}, '${escapeQuote(art.title)}')" title="Avaliar Revisão" class="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700">
                            <i data-lucide="check-square" class="w-3.5 h-3.5"></i>
                        </button>
                    ` : ''}
                    ${(art.editorial_status === 'approved' || art.editorial_status === 'draft') ? `
                        <button onclick="openNewsPublishPrompt(${art.id})" title="Publicar Notícia" class="p-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700">
                            <i data-lucide="globe" class="w-3.5 h-3.5"></i>
                        </button>
                    ` : ''}
                    ${art.editorial_status === 'published' ? `
                        <button onclick="openNewsCorrectionModal(${art.id})" title="Adicionar Nota de Retificação" class="p-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700">
                            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                        </button>
                    ` : ''}
                    ${art.editorial_status !== 'archived' ? `
                        <button onclick="archiveNewsAction(${art.id})" title="Arquivar" class="p-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 text-slate-400 hover:text-rose-600">
                            <i data-lucide="archive" class="w-3.5 h-3.5"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');

        initIcons();
    } catch (err) {
        console.error('Erro ao carregar notícias internas:', err);
    }
}

function escapeQuote(str) {
    return String(str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// 3. Editor de Notícia & Fontes
async function openNewsEditorModal(articleId = null) {
    await loadCategoriesCache();
    const form = document.getElementById('form-news-article');
    if (!form) return;
    form.reset();

    const elId = document.getElementById('news-edit-id');
    const elTitleModal = document.getElementById('modal-news-title');
    const sourcesList = document.getElementById('news-sources-list');
    sourcesList.innerHTML = '';

    if (!articleId) {
        elId.value = '';
        elTitleModal.innerText = 'Nova Notícia / Matéria Científica';
        addSourceRow(); // Adiciona 1 linha vazia
        openModal('modal-news-editor');
        return;
    }

    try {
        const art = await api.getNewsArticleDetail(articleId);
        elId.value = art.id;
        elTitleModal.innerText = `Editar Matéria #${art.id}`;

        document.getElementById('news-input-title').value = art.title || '';
        document.getElementById('news-input-subtitle').value = art.subtitle || '';
        document.getElementById('news-input-summary').value = art.summary || '';
        document.getElementById('news-input-cover').value = art.cover_image_url || '';
        document.getElementById('news-input-cover-credit').value = art.cover_image_caption || '';
        document.getElementById('news-input-cover-alt').value = art.cover_image_alt || '';
        document.getElementById('news-input-content').value = art.content_markdown || '';
        document.getElementById('news-input-category').value = art.category_id;
        document.getElementById('news-input-tags').value = (art.tags || []).join(', ');
        document.getElementById('news-input-coauthors').value = art.coauthors_text || '';
        document.getElementById('news-input-featured').checked = !!art.is_featured;

        // Popular fontes
        if (art.sources && art.sources.length > 0) {
            art.sources.forEach(src => addSourceRow(src));
        } else {
            addSourceRow();
        }

        openModal('modal-news-editor');
    } catch (err) {
        showToast('Erro ao carregar detalhes da matéria: ' + err.message, 'error');
    }
}

function addSourceRow(src = null) {
    const list = document.getElementById('news-sources-list');
    if (!list) return;

    const row = document.createElement('div');
    row.className = 'news-source-row grid grid-cols-1 sm:grid-cols-12 gap-2 bg-slate-900/90 p-2.5 rounded-lg border border-slate-800 items-center';
    row.innerHTML = `
        <div class="sm:col-span-4">
            <input type="text" placeholder="Título da Fonte / Decisão / Lei *" required class="src-title w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white" value="${src ? (src.title || '') : ''}">
        </div>
        <div class="sm:col-span-3">
            <select class="src-type w-full px-2 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white">
                <option value="legislacao" ${src && src.source_type === 'legislacao' ? 'selected' : ''}>Legislação / Código</option>
                <option value="decisao_judicial" ${src && src.source_type === 'decisao_judicial' ? 'selected' : ''}>Decisão Judicial / Acórdão</option>
                <option value="artigo_cientifico" ${src && src.source_type === 'artigo_cientifico' ? 'selected' : ''}>Artigo Científico</option>
                <option value="livro" ${src && src.source_type === 'livro' ? 'selected' : ''}>Livro / Doutrina</option>
                <option value="documento_oficial" ${src && src.source_type === 'documento_oficial' ? 'selected' : ''}>Documento Oficial</option>
                <option value="relatorio" ${src && src.source_type === 'relatorio' ? 'selected' : ''}>Relatório Técnico / Pericial</option>
                <option value="noticia_externa" ${src && src.source_type === 'noticia_externa' ? 'selected' : ''}>Notícia Externa</option>
                <option value="base_dados" ${src && src.source_type === 'base_dados' ? 'selected' : ''}>Base de Dados</option>
                <option value="outra" ${!src || src.source_type === 'outra' ? 'selected' : ''}>Outra Referência</option>
            </select>
        </div>
        <div class="sm:col-span-4">
            <input type="url" placeholder="URL da Fonte (se houver)" class="src-url w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-slate-200" value="${src ? (src.url || '') : ''}">
        </div>
        <div class="sm:col-span-1 flex justify-end">
            <button type="button" onclick="this.closest('.news-source-row').remove()" class="p-1 text-slate-400 hover:text-rose-400">
                <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
        </div>
    `;
    list.appendChild(row);
    initIcons();
}

async function submitNewsArticle(e) {
    e.preventDefault();
    const id = document.getElementById('news-edit-id').value;

    const sources = [];
    document.querySelectorAll('.news-source-row').forEach(row => {
        const title = row.querySelector('.src-title')?.value.trim();
        const type = row.querySelector('.src-type')?.value;
        const url = row.querySelector('.src-url')?.value.trim();
        if (title) {
            sources.push({
                title,
                source_type: type || 'outra',
                url: url || null
            });
        }
    });

    const tagsStr = document.getElementById('news-input-tags').value;
    const tags = tagsStr.split(',').map(t => t.trim()).filter(Boolean);

    const payload = {
        title: document.getElementById('news-input-title').value.trim(),
        subtitle: document.getElementById('news-input-subtitle').value.trim() || null,
        summary: document.getElementById('news-input-summary').value.trim(),
        cover_image_url: document.getElementById('news-input-cover').value.trim() || null,
        cover_image_caption: document.getElementById('news-input-cover-credit').value.trim() || null,
        cover_image_alt: document.getElementById('news-input-cover-alt').value.trim() || null,
        content_markdown: document.getElementById('news-input-content').value.trim(),
        category_id: parseInt(document.getElementById('news-input-category').value),
        tags: tags,
        coauthors_text: document.getElementById('news-input-coauthors').value.trim() || null,
        is_featured: document.getElementById('news-input-featured').checked,
        sources: sources
    };

    try {
        if (id) {
            await api.updateNewsArticle(id, payload);
            showToast('Matéria atualizada com sucesso!');
        } else {
            await api.createNewsArticle(payload);
            showToast('Matéria salva como rascunho com sucesso!');
        }
        closeModal('modal-news-editor');
        loadInternalNewsTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message || 'Falha ao salvar matéria.', 'error');
    }
}

async function submitNewsForReviewAction(articleId) {
    if (!confirm('Deseja submeter esta matéria para revisão editorial/científica?')) return;
    try {
        await api.submitNewsReview(articleId, { notes: 'Submetido para revisão geral.' });
        showToast('Matéria encaminhada para revisão com sucesso!');
        loadInternalNewsTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openNewsReviewModal(articleId, title) {
    document.getElementById('review-news-id').value = articleId;
    document.getElementById('review-news-title').innerText = title;
    document.getElementById('review-news-notes').value = '';
    openModal('modal-news-review');
}

async function submitReviewAction(e) {
    e.preventDefault();
    const id = document.getElementById('review-news-id').value;
    const decision = document.querySelector('input[name="review_decision"]:checked')?.value || 'approved';
    const notes = document.getElementById('review-news-notes').value.trim();

    try {
        await api.reviewNewsArticle(id, { review_status: decision, review_notes: notes });
        showToast(decision === 'approved' ? 'Matéria aprovada com sucesso!' : 'Ajustes solicitados ao autor.');
        closeModal('modal-news-review');
        loadInternalNewsTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function openNewsPublishPrompt(articleId) {
    if (confirm('Deseja publicar esta matéria imediatamente no portal público e na Home?')) {
        try {
            await api.publishNewsArticle(articleId, { publish_now: true });
            showToast('Matéria publicada com sucesso!');
            loadInternalNewsTable();
            loadCommunicationOverview();
        } catch (err) {
            showToast(err.message, 'error');
        }
    }
}

function openNewsCorrectionModal(articleId) {
    document.getElementById('correction-news-id').value = articleId;
    document.getElementById('correction-notice-text').value = '';
    openModal('modal-news-correction');
}

async function submitNewsCorrection(e) {
    e.preventDefault();
    const id = document.getElementById('correction-news-id').value;
    const notice = document.getElementById('correction-notice-text').value.trim();
    try {
        await api.addNewsCorrection(id, notice);
        showToast('Nota de retificação registrada com sucesso!');
        closeModal('modal-news-correction');
        loadInternalNewsTable();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function archiveNewsAction(articleId) {
    if (!confirm('Tem certeza de que deseja arquivar esta matéria? Ela não será mais exibida no portal público.')) return;
    try {
        await api.archiveNewsArticle(articleId);
        showToast('Matéria arquivada com sucesso.');
        loadInternalNewsTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 4. Pautas
async function loadPitchesTable() {
    const tableBody = document.getElementById('comm-pitches-table-body');
    if (!tableBody) return;

    const statusFilter = document.getElementById('comm-pitches-filter-status')?.value || '';
    try {
        const rows = await api.getPitches(statusFilter);
        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-slate-400 text-xs">Nenhuma pauta cadastrada.</td></tr>';
            return;
        }

        tableBody.innerHTML = rows.map(p => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3.5 max-w-xs">
                    <div class="font-bold text-slate-800">${p.title}</div>
                    <div class="text-[11px] text-slate-400 line-clamp-1 mt-0.5">${p.description || ''}</div>
                </td>
                <td class="p-3.5 whitespace-nowrap">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="background-color: ${p.category_color || '#38bdf8'}15; color: ${p.category_color || '#38bdf8'};">
                        ${p.category_name || 'Geral'}
                    </span>
                </td>
                <td class="p-3.5 text-center whitespace-nowrap">
                    <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${p.priority === 'alta' ? 'bg-rose-50 text-rose-600' : (p.priority === 'media' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-600')}">
                        ${p.priority}
                    </span>
                </td>
                <td class="p-3.5 whitespace-nowrap text-slate-700 font-medium">${p.assignee_name || 'A definir'}</td>
                <td class="p-3.5 text-center whitespace-nowrap text-slate-500">${p.deadline || '-'}</td>
                <td class="p-3.5 text-center whitespace-nowrap">
                    <span class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">${p.status}</span>
                </td>
                <td class="p-3.5 text-right whitespace-nowrap">
                    <button onclick="convertPitchToNews(${p.id})" class="px-2.5 py-1 text-xs font-bold rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 transition">
                        ${p.converted_article_id ? 'Ver Matéria' : 'Escrever Matéria →'}
                    </button>
                </td>
            </tr>
        `).join('');
        initIcons();
    } catch (err) {
        console.error('Erro ao carregar pautas:', err);
    }
}

async function openPitchModal(pitchId = null) {
    await loadCategoriesCache();
    const form = document.getElementById('form-pitch');
    if (!form) return;
    form.reset();
    document.getElementById('pitch-edit-id').value = '';

    // Carregar membros no select
    try {
        const members = await api.getMembers();
        const assigneeSelect = document.getElementById('pitch-input-assignee');
        if (assigneeSelect) {
            assigneeSelect.innerHTML = '<option value="">A Definir</option>';
            members.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.name;
                assigneeSelect.appendChild(opt);
            });
        }
    } catch (e) {}

    openModal('modal-pitch-editor');
}

async function submitPitch(e) {
    e.preventDefault();
    const payload = {
        title: document.getElementById('pitch-input-title').value.trim(),
        category_id: parseInt(document.getElementById('pitch-input-category').value) || null,
        priority: document.getElementById('pitch-input-priority').value,
        assignee_id: parseInt(document.getElementById('pitch-input-assignee').value) || null,
        deadline: document.getElementById('pitch-input-deadline').value || null,
        description: document.getElementById('pitch-input-desc').value.trim() || null,
        initial_sources: document.getElementById('pitch-input-sources').value.trim() || null
    };

    try {
        await api.createPitch(payload);
        showToast('Pauta registrada com sucesso!');
        closeModal('modal-pitch-editor');
        loadPitchesTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function convertPitchToNews(pitchId) {
    try {
        const res = await api.convertPitch(pitchId);
        showToast('Pauta convertida em matéria!');
        switchCommTab('news');
        openNewsEditorModal(res.article_id);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 5. Newsletter
async function loadNewslettersTable() {
    const tableBody = document.getElementById('comm-newsletters-table-body');
    if (!tableBody) return;

    try {
        const list = await api.getNewsletters();
        if (!list || list.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">Nenhuma edição de Newsletter cadastrada.</td></tr>';
            return;
        }

        tableBody.innerHTML = list.map(n => `
            <tr class="hover:bg-slate-50 transition">
                <td class="p-3.5 font-bold text-slate-800">#${n.edition_number} • ${n.title}</td>
                <td class="p-3.5 text-slate-600">${n.email_subject}</td>
                <td class="p-3.5 text-center font-semibold text-indigo-600">${n.blocks_count} blocos</td>
                <td class="p-3.5 text-center">${getStatusBadge(n.status)}</td>
                <td class="p-3.5 text-center text-slate-400 text-xs">${n.sent_at ? n.sent_at.substring(0, 10) : '-'}</td>
                <td class="p-3.5 text-right whitespace-nowrap space-x-1">
                    <button onclick="openNewsletterBuilderModal(${n.id})" title="Editar Blocos" class="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700">
                        <i data-lucide="edit" class="w-3.5 h-3.5"></i>
                    </button>
                    <button onclick="openNewsletterPreview(${n.id})" title="Preview" class="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700">
                        <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                    </button>
                </td>
            </tr>
        `).join('');
        initIcons();
    } catch (err) {
        console.error('Erro ao carregar newsletters:', err);
    }
}

async function openNewsletterBuilderModal(editionId = null) {
    const form = document.getElementById('form-newsletter-edition');
    if (!form) return;
    form.reset();
    document.getElementById('newsletter-edit-id').value = '';
    const blocksList = document.getElementById('newsletter-blocks-list');
    blocksList.innerHTML = '';

    // Carregar matérias publicadas para os selects de referência
    try {
        cachedPublishedArticles = await api.getPublicNews({ limit: 50 });
        const dashStats = await api.getDashboardStats();
        cachedEventsForNl = dashStats.upcoming_events || [];
    } catch (e) {}

    if (!editionId) {
        // Sugerir próximo número de edição
        try {
            const list = await api.getNewsletters();
            const nextNum = list.length > 0 ? (Math.max(...list.map(n => n.edition_number)) + 1) : 1;
            document.getElementById('nl-input-number').value = nextNum;
            document.getElementById('nl-input-title').value = `LACC em Foco — Edição #${nextNum < 10 ? '0' + nextNum : nextNum}`;
            document.getElementById('nl-input-subject').value = `🔍 [LACC em Foco #${nextNum}] Destaques em Ciências Criminais`;
        } catch (e) {}

        // Blocos padrão iniciais
        addNewsletterBlock('header');
        addNewsletterBlock('editorial');
        if (cachedPublishedArticles.length > 0) {
            addNewsletterBlock('news_ref', { article_id: cachedPublishedArticles[0].id });
        }
        openModal('modal-newsletter-builder');
        return;
    }

    try {
        const ed = await api.getNewsletterDetail(editionId);
        document.getElementById('newsletter-edit-id').value = ed.id;
        document.getElementById('nl-input-number').value = ed.edition_number;
        document.getElementById('nl-input-title').value = ed.title;
        document.getElementById('nl-input-subject').value = ed.email_subject;
        document.getElementById('nl-input-preheader').value = ed.preheader_text || '';
        document.getElementById('nl-input-editorial').value = ed.editorial_text || '';

        if (ed.blocks && ed.blocks.length > 0) {
            ed.blocks.forEach(b => addNewsletterBlock(b.block_type, b.content));
        }
        openModal('modal-newsletter-builder');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function addNewsletterBlock(type, content = {}) {
    const container = document.getElementById('newsletter-blocks-list');
    if (!container) return;

    const blockCard = document.createElement('div');
    blockCard.className = 'nl-block-item p-3.5 bg-slate-900 rounded-xl border border-slate-800 space-y-2';
    blockCard.setAttribute('data-type', type);

    let innerHtml = `
        <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="text-[11px] font-bold uppercase text-indigo-400 flex items-center gap-1.5">
                <i data-lucide="layers" class="w-3 h-3"></i> Bloco: ${type}
            </span>
            <button type="button" onclick="this.closest('.nl-block-item').remove()" class="text-slate-500 hover:text-rose-400 p-1">
                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
        </div>
    `;

    if (type === 'header') {
        innerHtml += `
            <div>
                <label class="block text-[11px] text-slate-400 mb-1">Subtítulo / Tagline do Cabeçalho</label>
                <input type="text" class="blk-tagline w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white" value="${content.tagline || 'Boletim Semanal de Ciências Criminais da LACC'}">
            </div>
        `;
    } else if (type === 'editorial') {
        innerHtml += `
            <div>
                <label class="block text-[11px] text-slate-400 mb-1">Texto da Carta Editorial</label>
                <textarea rows="2" class="blk-editorial-text w-full p-2 text-xs rounded bg-slate-800 border border-slate-700 text-white">${content.text || ''}</textarea>
            </div>
        `;
    } else if (type === 'news_ref') {
        const options = cachedPublishedArticles.map(a => `<option value="${a.id}" ${content.article_id === a.id ? 'selected' : ''}>[${a.category_name}] ${a.title}</option>`).join('');
        innerHtml += `
            <div>
                <label class="block text-[11px] text-slate-400 mb-1">Selecionar Matéria Publicada (Referência Dinâmica)</label>
                <select class="blk-news-id w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white">
                    ${options || '<option value="">Nenhuma matéria publicada disponível</option>'}
                </select>
            </div>
        `;
    } else if (type === 'event_ref') {
        const evOptions = cachedEventsForNl.map(e => `<option value="${e.id}" ${content.event_id === e.id ? 'selected' : ''}>${e.title} (${e.date})</option>`).join('');
        innerHtml += `
            <div>
                <label class="block text-[11px] text-slate-400 mb-1">Selecionar Evento da Liga (Referência)</label>
                <select class="blk-event-id w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white">
                    ${evOptions || '<option value="">Nenhum evento futuro cadastrado</option>'}
                </select>
            </div>
        `;
    } else if (type === 'text') {
        innerHtml += `
            <div>
                <label class="block text-[11px] text-slate-400 mb-1">Texto do Bloco</label>
                <textarea rows="2" class="blk-text w-full p-2 text-xs rounded bg-slate-800 border border-slate-700 text-white">${content.text || ''}</textarea>
            </div>
        `;
    } else if (type === 'button') {
        innerHtml += `
            <div class="grid grid-cols-2 gap-2">
                <div>
                    <label class="block text-[11px] text-slate-400 mb-1">Texto do Botão</label>
                    <input type="text" class="blk-btn-label w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white" value="${content.label || 'Acessar Artigo Completo'}">
                </div>
                <div>
                    <label class="block text-[11px] text-slate-400 mb-1">URL de Destino</label>
                    <input type="url" class="blk-btn-url w-full px-2.5 py-1.5 text-xs rounded bg-slate-800 border border-slate-700 text-white" value="${content.url || 'https://lacc.edu.br'}">
                </div>
            </div>
        `;
    }

    blockCard.innerHTML = innerHtml;
    container.appendChild(blockCard);
    initIcons();
}

async function submitNewsletterEdition(e) {
    e.preventDefault();
    const id = document.getElementById('newsletter-edit-id').value;

    const blocks = [];
    document.querySelectorAll('.nl-block-item').forEach((bEl, idx) => {
        const bType = bEl.getAttribute('data-type');
        const bContent = {};
        if (bType === 'header') bContent.tagline = bEl.querySelector('.blk-tagline')?.value;
        else if (bType === 'editorial') bContent.text = bEl.querySelector('.blk-editorial-text')?.value;
        else if (bType === 'news_ref') bContent.article_id = parseInt(bEl.querySelector('.blk-news-id')?.value);
        else if (bType === 'event_ref') bContent.event_id = parseInt(bEl.querySelector('.blk-event-id')?.value);
        else if (bType === 'text') bContent.text = bEl.querySelector('.blk-text')?.value;
        else if (bType === 'button') {
            bContent.label = bEl.querySelector('.blk-btn-label')?.value;
            bContent.url = bEl.querySelector('.blk-btn-url')?.value;
        }

        blocks.push({
            block_type: bType,
            order_index: idx,
            content: bContent
        });
    });

    const payload = {
        edition_number: parseInt(document.getElementById('nl-input-number').value),
        title: document.getElementById('nl-input-title').value.trim(),
        email_subject: document.getElementById('nl-input-subject').value.trim(),
        preheader_text: document.getElementById('nl-input-preheader').value.trim() || null,
        editorial_text: document.getElementById('nl-input-editorial').value.trim() || null,
        blocks: blocks
    };

    try {
        if (id) {
            await api.updateNewsletter(id, payload);
            showToast('Edição da Newsletter atualizada com sucesso!');
        } else {
            const res = await api.createNewsletter(payload);
            showToast('Edição criada com sucesso!');
            nlPreviewCurrentEditionId = res.id;
        }
        closeModal('modal-newsletter-builder');
        loadNewslettersTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function previewCurrentNewsletter() {
    const id = document.getElementById('newsletter-edit-id').value;
    if (!id) {
        showToast('Salve a edição antes de gerar o preview com dados referenciados.', 'warning');
        return;
    }
    openNewsletterPreview(id);
}

async function openNewsletterPreview(editionId) {
    nlPreviewCurrentEditionId = editionId;
    try {
        const res = await api.getNewsletterPreviewHtml(editionId);
        const frame = document.getElementById('nl-preview-frame');
        if (frame) {
            frame.srcdoc = res.html;
        }
        openModal('modal-newsletter-preview');
    } catch (err) {
        showToast('Erro ao carregar preview: ' + err.message, 'error');
    }
}

function setNlPreviewMode(mode) {
    const frame = document.getElementById('nl-preview-frame');
    const btnDesk = document.getElementById('btn-nl-prev-desktop');
    const btnMob = document.getElementById('btn-nl-prev-mobile');
    if (!frame) return;

    if (mode === 'mobile') {
        frame.style.maxWidth = '375px';
        btnMob.className = 'px-3 py-1 rounded-md font-bold bg-indigo-600 text-white';
        btnDesk.className = 'px-3 py-1 rounded-md font-medium text-slate-400 hover:text-white';
    } else {
        frame.style.maxWidth = '600px';
        btnDesk.className = 'px-3 py-1 rounded-md font-bold bg-indigo-600 text-white';
        btnMob.className = 'px-3 py-1 rounded-md font-medium text-slate-400 hover:text-white';
    }
}

async function sendNlTestEmail() {
    if (!nlPreviewCurrentEditionId) return;
    const email = document.getElementById('nl-test-email')?.value.trim();
    if (!email) {
        showToast('Por favor, digite um e-mail para o teste.', 'warning');
        return;
    }

    const btn = document.getElementById('btn-send-nl-test');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Enviando...';
    }

    try {
        const res = await api.sendNewsletterTest(nlPreviewCurrentEditionId, email);
        showToast(res.message);
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Disparar Teste';
        }
    }
}

// 6. Calendário
async function loadCalendarView() {
    const listEl = document.getElementById('comm-calendar-list');
    if (!listEl) return;

    try {
        const items = await api.getEditorialCalendar();
        if (!items || items.length === 0) {
            listEl.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs">Nenhum evento ou prazo agendado no calendário.</div>';
            return;
        }

        // Ordenar por data
        items.sort((a, b) => (a.date || '').localeCompare(b.date || ''));

        listEl.innerHTML = items.map(it => {
            const badgeType = it.item_type === 'pitch'
                ? '<span class="text-[10px] bg-amber-50 text-amber-700 font-bold px-2 py-0.5 rounded-full">Pauta (Prazo)</span>'
                : (it.item_type === 'event'
                    ? '<span class="text-[10px] bg-emerald-50 text-emerald-700 font-bold px-2 py-0.5 rounded-full">Evento LACC</span>'
                    : '<span class="text-[10px] bg-indigo-50 text-indigo-700 font-bold px-2 py-0.5 rounded-full">Notícia</span>');

            return `
                <div class="flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 rounded-xl border border-slate-100 transition">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-10 rounded-lg bg-slate-200 text-slate-700 flex flex-col items-center justify-center font-bold text-xs">
                            <span>${(it.date || '').substring(8, 10)}</span>
                            <span class="text-[9px] uppercase text-slate-400">${(it.date || '').substring(5, 7)}</span>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                ${badgeType}
                                <span class="text-xs text-slate-400">${it.date || 'Sem data'}</span>
                            </div>
                            <h4 class="text-xs font-bold text-slate-800 mt-0.5">${it.title}</h4>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        initIcons();
    } catch (err) {
        console.error('Erro ao carregar calendário:', err);
    }
}

// 7. Biblioteca de Mídia
async function loadMediaAssetsView() {
    const grid = document.getElementById('comm-media-grid');
    if (!grid) return;

    try {
        const assets = await api.getMediaAssets();
        if (!assets || assets.length === 0) {
            grid.innerHTML = '<div class="col-span-full text-center py-8 text-slate-400 text-xs">Nenhum arquivo na biblioteca de mídia.</div>';
            return;
        }

        grid.innerHTML = assets.map(m => `
            <div class="bg-white rounded-xl border border-slate-200 overflow-hidden group shadow-sm flex flex-col justify-between">
                <div class="h-28 bg-slate-100 overflow-hidden relative">
                    <img src="${m.file_path}" alt="${m.alt_text || ''}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                </div>
                <div class="p-2.5 space-y-1">
                    <h5 class="text-[11px] font-bold text-slate-800 truncate" title="${m.original_name}">${m.original_name}</h5>
                    <p class="text-[10px] text-slate-400 truncate">${m.alt_text || 'Sem texto alternativo'}</p>
                    <div class="flex items-center justify-between pt-1 border-t border-slate-100">
                        <button onclick="copyMediaUrl('${m.file_path}')" class="text-[10px] text-brand-600 font-bold hover:underline">
                            Copiar URL
                        </button>
                        <button onclick="deleteMediaItem(${m.id})" class="text-slate-400 hover:text-rose-600 p-1">
                            <i data-lucide="trash" class="w-3 h-3"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        initIcons();
    } catch (err) {
        console.error('Erro ao carregar mídia:', err);
    }
}

function openMediaUploadModal() {
    const form = document.getElementById('form-media-upload');
    if (form) form.reset();
    openModal('modal-media-upload');
}

async function submitMediaUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('media-upload-file');
    if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Por favor, selecione um arquivo de imagem.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('alt_text', document.getElementById('media-upload-alt').value.trim());
    formData.append('credit', document.getElementById('media-upload-credit').value.trim());

    const btn = document.getElementById('btn-submit-media');
    if (btn) {
        btn.disabled = true;
        btn.innerText = 'Enviando...';
    }

    try {
        const res = await api.uploadMediaAsset(formData);
        showToast(res.message);
        closeModal('modal-media-upload');
        loadMediaAssetsView();

        // Se estiver com o editor de matéria aberto, preenche o campo de imagem automaticamente!
        const coverInput = document.getElementById('news-input-cover');
        if (coverInput && !coverInput.value) {
            coverInput.value = res.url;
            document.getElementById('news-input-cover-alt').value = res.alt_text || '';
        }
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = 'Enviar Imagem';
        }
    }
}

async function deleteMediaItem(id) {
    if (!confirm('Deseja excluir esta imagem da biblioteca de mídia?')) return;
    try {
        await api.deleteMediaAsset(id);
        showToast('Imagem removida com sucesso.');
        loadMediaAssetsView();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function copyMediaUrl(url) {
    const fullUrl = url.startsWith('http') ? url : (window.location.origin + url);
    navigator.clipboard.writeText(fullUrl).then(() => {
        showToast('URL da imagem copiada para a área de transferência!');
    }).catch(() => {
        showToast('URL: ' + fullUrl);
    });
}

// 8. Assinantes (LGPD)
async function loadSubscribersTable() {
    const tableBody = document.getElementById('comm-subscribers-table-body');
    if (!tableBody) return;

    const statusFilter = document.getElementById('comm-subscribers-filter-status')?.value || '';
    try {
        const rows = await api.getSubscribers(statusFilter);
        if (!rows || rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">Nenhum assinante encontrado.</td></tr>';
            return;
        }

        tableBody.innerHTML = rows.map(s => {
            const stBadge = s.status === 'active'
                ? '<span class="text-[10px] font-bold bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">Ativo</span>'
                : (s.status === 'unsubscribed'
                    ? '<span class="text-[10px] font-bold bg-rose-50 text-rose-700 px-2 py-0.5 rounded-full">Cancelado</span>'
                    : '<span class="text-[10px] font-bold bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full">Aguardando Confirmação</span>');

            return `
                <tr class="hover:bg-slate-50 transition">
                    <td class="p-3.5 font-semibold text-slate-800">${s.email}</td>
                    <td class="p-3.5 text-center">${stBadge}</td>
                    <td class="p-3.5 text-slate-500">${s.consent_source || 'landing_page'}</td>
                    <td class="p-3.5 text-center text-slate-400 text-xs">${s.created_at ? s.created_at.substring(0, 10) : '-'}</td>
                    <td class="p-3.5 text-center text-slate-400 text-xs">${s.confirmed_at ? s.confirmed_at.substring(0, 10) : '-'}</td>
                    <td class="p-3.5 text-right whitespace-nowrap space-x-1">
                        ${s.status === 'active' ? `
                            <button onclick="updateSubscriberStatusAction(${s.id}, 'unsubscribed')" title="Descadastrar" class="px-2 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 text-slate-600">
                                Cancelar
                            </button>
                        ` : `
                            <button onclick="updateSubscriberStatusAction(${s.id}, 'active')" title="Reativar" class="px-2 py-1 text-xs rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold">
                                Reativar
                            </button>
                        `}
                        <button onclick="deleteSubscriberAction(${s.id})" title="Exclusão LGPD" class="p-1 rounded text-slate-400 hover:text-rose-600">
                            <i data-lucide="trash" class="w-3.5 h-3.5"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
        initIcons();
    } catch (err) {
        console.error('Erro ao carregar assinantes:', err);
    }
}

async function updateSubscriberStatusAction(id, newStatus) {
    try {
        await api.updateSubscriberStatus(id, newStatus);
        showToast('Status do assinante atualizado.');
        loadSubscribersTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteSubscriberAction(id) {
    if (!confirm('ATENÇÃO (LGPD): Deseja excluir definitivamente este assinante e todo o registro associado da base de dados?')) return;
    try {
        await api.deleteSubscriber(id);
        showToast('Assinante excluído conforme conformidade LGPD.');
        loadSubscribersTable();
        loadCommunicationOverview();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// ATHENA COGNITIVE MULTI-AGENT CORE - CLIENT
// ==========================================
let athenaCurrentTab = 'chat';
let athenaCurrentSessionId = null;

function loadAthenaView() {
    initIcons();
    const promptInput = document.getElementById('athena-prompt-input');
    if (promptInput) {
        promptInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('form-athena-chat')?.requestSubmit();
            }
        });
    }
    if (athenaCurrentTab === 'studio') loadAthenaStudioProjects();
    else if (athenaCurrentTab === 'projects') loadAthenaProjects();
    else if (athenaCurrentTab === 'status') loadAthenaHardwareStatus();
}

function switchAthenaTab(tabName) {
    athenaCurrentTab = tabName;
    ['chat', 'studio', 'projects', 'status'].forEach(t => {
        const btn = document.getElementById(`athena-tab-btn-${t}`);
        const panel = document.getElementById(`athena-panel-${t}`);
        if (btn) {
            if (t === tabName) {
                btn.className = 'px-4 py-2.5 rounded-t-xl border-b-2 border-amber-600 text-amber-700 font-bold transition flex items-center gap-2';
            } else {
                btn.className = 'px-4 py-2.5 rounded-t-xl border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition flex items-center gap-2';
            }
        }
        if (panel) {
            if (t === tabName) panel.classList.remove('hidden');
            else panel.classList.add('hidden');
        }
    });

    if (tabName === 'studio') loadAthenaStudioProjects();
    else if (tabName === 'projects') loadAthenaProjects();
    else if (tabName === 'status') loadAthenaHardwareStatus();
    initIcons();
}

function sendQuickAthenaPrompt(promptText) {
    const input = document.getElementById('athena-prompt-input');
    if (input) {
        input.value = promptText;
        switchAthenaTab('chat');
        document.getElementById('form-athena-chat')?.requestSubmit();
    }
}

function resetAthenaChat() {
    const list = document.getElementById('athena-messages-list');
    if (list) {
        list.innerHTML = `
            <div class="flex gap-4 max-w-4xl">
                <div class="w-9 h-9 rounded-2xl bg-amber-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0 shadow-lg mt-1">
                    <i data-lucide="bot" class="w-5 h-5"></i>
                </div>
                <div class="space-y-3 flex-1">
                    <div class="bg-slate-800/90 border border-slate-700/80 rounded-2xl rounded-tl-sm p-5 text-slate-100 shadow-md">
                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-700/60">
                            <span class="font-bold text-amber-300 text-xs flex items-center gap-1.5">
                                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i> Athena Cognitive Core
                            </span>
                            <span class="text-[10px] text-slate-400 font-mono">Conselho LACC</span>
                        </div>
                        <p class="text-sm leading-relaxed text-slate-200">
                            Nova sessão iniciada. O Kernel Cognitivo e os 7 especialistas do Conselho estão prontos para deliberar.
                        </p>
                    </div>
                </div>
            </div>
        `;
        initIcons();
    }
    const input = document.getElementById('athena-prompt-input');
    if (input) input.value = '';
    athenaCurrentSessionId = null;
    showToast('Nova sessão iniciada com a Athena.');
}

async function submitAthenaPrompt(event) {
    event.preventDefault();
    const input = document.getElementById('athena-prompt-input');
    const prompt = input?.value.trim();
    if (!prompt) return;

    const dutySelect = document.getElementById('athena-select-duty');
    const dutyScope = dutySelect?.value || null;

    const btn = document.getElementById('btn-athena-submit');
    const thinking = document.getElementById('athena-thinking-indicator');
    const thinkingText = document.getElementById('athena-thinking-text');
    const messagesList = document.getElementById('athena-messages-list');

    // 1. Renderiza o balão do Usuário
    const userBubble = document.createElement('div');
    userBubble.className = 'flex justify-end gap-3';
    userBubble.innerHTML = `
        <div class="max-w-2xl bg-gradient-to-r from-amber-600 to-amber-700 text-slate-950 font-medium rounded-2xl rounded-tr-sm p-4 shadow-lg text-sm">
            <div class="flex items-center justify-between pb-1 mb-1 border-b border-amber-500/40 text-[11px] font-bold text-slate-900">
                <span>Diretoria</span>
                <span class="text-[10px] opacity-80">${new Date().toLocaleTimeString().slice(0, 5)}</span>
            </div>
            <div class="whitespace-pre-wrap">${escapeHtml(prompt)}</div>
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-800 text-amber-300 font-bold text-xs flex items-center justify-center shrink-0 border border-slate-700">
            VOCÊ
        </div>
    `;
    messagesList.appendChild(userBubble);
    messagesList.scrollTop = messagesList.scrollHeight;

    // Limpa o input
    input.value = '';
    if (btn) btn.disabled = true;
    if (thinking) {
        thinking.classList.remove('hidden');
        thinkingText.innerText = 'Kernel acionando Percepção e Agente de Encargo...';
    }

    // Efeito de pulso de etapas cognitivas
    const stageTimer1 = setTimeout(() => {
        if (thinkingText) thinkingText.innerText = 'Logos & Justitia deliberando fundamentação científica e dogmática...';
    }, 400);
    const stageTimer2 = setTimeout(() => {
        if (thinkingText) thinkingText.innerText = 'Sophia & Musa construindo narrativa, roteiro e ritmo visual...';
    }, 900);
    const stageTimer3 = setTimeout(() => {
        if (thinkingText) thinkingText.innerText = 'Critias realizando auditoria anti-alucinação e validação de fontes...';
    }, 1400);

    if (!athenaCurrentSessionId) {
        athenaCurrentSessionId = 'session_' + Date.now();
    }

    try {
        const resp = await api.athenaExecute(prompt, dutyScope, athenaCurrentSessionId);
        clearTimeout(stageTimer1);
        clearTimeout(stageTimer2);
        clearTimeout(stageTimer3);

        const data = resp.data || {};
        const task = data.task || {};
        if (task.session_id) athenaCurrentSessionId = task.session_id;
        const result = task.result || {};
        const workflow = data.workflow || {};
        const steps = workflow.steps || [];

        // 2. Renderiza o balão de resposta da Athena
        const athenaBubble = document.createElement('div');
        athenaBubble.className = 'flex gap-4 max-w-4xl animate-fade-in';

        // Especialistas utilizados
        const agentsPills = steps.map(s => {
            const name = s.agent_id.replace('duty_', '').replace('council_', '').replace('exec_', '').toUpperCase();
            return `<span class="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] text-amber-300 font-mono">${name}</span>`;
        }).join(' ');

        // Referências verificadas
        let refsHtml = '';
        const refs = result.references || [];
        if (refs.length > 0) {
            refsHtml = `
                <div class="mt-4 pt-3 border-t border-slate-700/60">
                    <h5 class="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                        <i data-lucide="shield-check" class="w-3.5 h-3.5 text-emerald-400"></i> Fontes & Referências Verificadas
                    </h5>
                    <div class="space-y-1.5">
                        ${refs.map(r => `
                            <div class="p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80 text-xs flex items-start justify-between gap-3">
                                <div>
                                    <div class="font-bold text-slate-100">${escapeHtml(r.title)}</div>
                                    <div class="text-[11px] text-slate-400">${escapeHtml(r.author_or_institution || r.source_type)}</div>
                                    ${r.notes ? `<div class="text-[10px] text-slate-500 mt-0.5 italic">${escapeHtml(r.notes)}</div>` : ''}
                                </div>
                                ${r.url ? `
                                    <a href="${r.url}" target="_blank" class="px-2 py-1 rounded bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 text-[10px] font-bold shrink-0">
                                        Abrir Fonte ↗
                                    </a>
                                ` : '<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[9px] font-mono shrink-0">VERIFICADO</span>'}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Avisos (se houver)
        let warningsHtml = '';
        const warnings = result.warnings || [];
        if (warnings.length > 0) {
            warningsHtml = `
                <div class="mt-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2">
                    <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-400 shrink-0 mt-0.5"></i>
                    <div>
                        ${warnings.map(w => `<div>${escapeHtml(w)}</div>`).join('')}
                    </div>
                </div>
            `;
        }

        // Renderização formatada do markdown
        const formattedBody = formatAthenaMarkdown(result.content || 'Resultado concluído.');

        athenaBubble.innerHTML = `
            <div class="w-9 h-9 rounded-2xl bg-amber-500/20 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0 shadow-lg mt-1">
                <i data-lucide="bot" class="w-5 h-5"></i>
            </div>
            <div class="space-y-2 flex-1">
                <div class="bg-slate-800/95 border border-slate-700/80 rounded-2xl rounded-tl-sm p-5 text-slate-100 shadow-xl space-y-3">
                    
                    <!-- Header do Card de Resposta -->
                    <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-slate-700/60 text-xs">
                        <div class="flex items-center gap-2">
                            <span class="font-extrabold text-amber-300 flex items-center gap-1.5">
                                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i> ${escapeHtml(task.title || 'Proposta Athena')}
                            </span>
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">DRAFT</span>
                        </div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-[10px] text-slate-400 font-mono">${data.execution_time_ms || 0}ms</span>
                        </div>
                    </div>

                    <!-- Agentes Coordenados -->
                    <div class="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-400">
                        <span>Especialistas:</span>
                        ${agentsPills}
                    </div>

                    <!-- Conteúdo Principal Formatado -->
                    <div class="athena-markdown-body text-sm leading-relaxed text-slate-200 space-y-3">
                        ${formattedBody}
                    </div>

                    <!-- Referências e Avisos -->
                    ${refsHtml}
                    ${warningsHtml}

                    <!-- Ações Rápidas de Rodapé -->
                    <div class="pt-3 border-t border-slate-700/60 flex flex-wrap items-center justify-between gap-2">
                        <div class="flex items-center gap-2">
                            <button onclick="copyAthenaText(this)" class="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold transition flex items-center gap-1.5">
                                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                                <span>Copiar Proposta</span>
                            </button>
                            ${data.project_id ? `
                                <button onclick="switchAthenaTab('studio')" class="px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-bold transition flex items-center gap-1.5">
                                    <i data-lucide="film" class="w-3.5 h-3.5"></i>
                                    <span>Ver no Studio</span>
                                </button>
                            ` : ''}
                        </div>
                        <span class="text-[10px] text-slate-400 italic">Athena Cognitive Core • LACC</span>
                    </div>

                </div>
            </div>
        `;
        messagesList.appendChild(athenaBubble);
        messagesList.scrollTop = messagesList.scrollHeight;
        initIcons();

    } catch (err) {
        clearTimeout(stageTimer1);
        clearTimeout(stageTimer2);
        clearTimeout(stageTimer3);
        showToast(err.message || 'Falha ao processar requisição na Athena.', 'error');
        
        const errBubble = document.createElement('div');
        errBubble.className = 'flex gap-4 max-w-4xl';
        errBubble.innerHTML = `
            <div class="w-9 h-9 rounded-2xl bg-rose-500/20 text-rose-400 flex items-center justify-center shrink-0 border border-rose-500/30 mt-1">
                <i data-lucide="alert-circle" class="w-5 h-5"></i>
            </div>
            <div class="bg-rose-950/40 border border-rose-800 rounded-2xl p-4 text-rose-200 text-xs space-y-1">
                <div class="font-bold text-rose-300">Falha no Processamento Cognitivo</div>
                <div>${escapeHtml(err.message || 'Erro de comunicação.')}</div>
            </div>
        `;
        messagesList.appendChild(errBubble);
        messagesList.scrollTop = messagesList.scrollHeight;
        initIcons();
    } finally {
        if (btn) btn.disabled = false;
        if (thinking) thinking.classList.add('hidden');
    }
}

function copyAthenaText(btn) {
    const card = btn.closest('.bg-slate-800\\/95') || btn.closest('.bg-slate-800');
    const body = card?.querySelector('.athena-markdown-body');
    if (body) {
        navigator.clipboard.writeText(body.innerText).then(() => {
            showToast('Texto da proposta copiado para a área de transferência!');
            btn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i><span>Copiado!</span>';
            initIcons();
            setTimeout(() => {
                btn.innerHTML = '<i data-lucide="copy" class="w-3.5 h-3.5"></i><span>Copiar Proposta</span>';
                initIcons();
            }, 2500);
        });
    }
}

function formatAthenaMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    
    // Títulos
    html = html.replace(/^### (.*$)/gim, '<h3 class="text-base font-bold text-amber-300 mt-3 mb-1">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="text-lg font-extrabold text-white mt-4 mb-2 pb-1 border-b border-slate-700">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="text-xl font-extrabold text-amber-400 mt-4 mb-2 pb-1 border-b border-slate-700">$1</h1>');
    
    // Negrito e Itálico
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong class="font-bold text-white">$1</strong>');
    html = html.replace(/\*(.*?)\*/gim, '<em class="italic text-slate-300">$1</em>');
    html = html.replace(/`([^`]+)`/gim, '<code class="bg-slate-900 px-1.5 py-0.5 rounded text-amber-300 font-mono text-xs border border-slate-700">$1</code>');
    
    // Alertas GitHub
    html = html.replace(/&gt; \[!NOTE\]\n&gt; (.*)/gim, '<div class="p-3 my-2 rounded-xl bg-blue-950/50 border border-blue-800 text-blue-200 text-xs">💡 $1</div>');
    html = html.replace(/&gt; (.*)/gim, '<blockquote class="border-l-4 border-amber-500 pl-3 my-2 text-slate-300 italic text-xs">$1</blockquote>');
    
    // Linhas horizontais
    html = html.replace(/^---$/gim, '<hr class="border-slate-700 my-4">');

    // Quebras de linha normais
    html = html.replace(/\n\n/g, '<br><br>');
    return html;
}

// ==========================================
// ATHENA STUDIO & PROJETOS
// ==========================================
async function loadAthenaStudioProjects() {
    const list = document.getElementById('athena-studio-projects-list');
    if (!list) return;
    list.innerHTML = '<div class="col-span-2 text-center py-8 text-slate-400 text-xs">Buscando projetos audiovisuais da Athena...</div>';

    try {
        const resp = await api.athenaListProjects('comunicacao');
        const projs = (resp.projects || []).filter(p => p.project_type === 'video' || p.project_type === 'script');

        if (projs.length === 0) {
            list.innerHTML = `
                <div class="col-span-2 text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200 p-6 space-y-3">
                    <i data-lucide="film" class="w-10 h-10 text-slate-300 mx-auto"></i>
                    <h4 class="font-bold text-slate-700 text-sm">Nenhum projeto de vídeo ativo</h4>
                    <p class="text-xs text-slate-500 max-w-md mx-auto">Peça no chat da Athena para gerar um roteiro de Reel e ele será automaticamente catalogado aqui.</p>
                    <button onclick="sendQuickAthenaPrompt('Crie um Reel de 60 segundos sobre cadeia de custódia digital.')" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow transition">
                        Criar Primeiro Reel
                    </button>
                </div>
            `;
            initIcons();
            return;
        }

        list.innerHTML = projs.map(p => `
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 text-white shadow-lg space-y-3 flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between gap-2 mb-1.5">
                        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                            ${p.project_type === 'video' ? '🎬 Reel 9:16' : '📜 Roteiro'}
                        </span>
                        <span class="text-[10px] text-slate-400 font-mono">${p.status.toUpperCase()}</span>
                    </div>
                    <h4 class="font-extrabold text-sm text-white">${escapeHtml(p.title)}</h4>
                    <p class="text-xs text-slate-400 line-clamp-3 mt-1.5">${escapeHtml(p.content_text ? p.content_text.slice(0, 140) + '...' : 'Sem descrição.')}</p>
                </div>
                <div class="pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span class="text-[11px] text-slate-500">${p.created_at ? p.created_at.slice(0, 10) : ''}</span>
                    <button onclick="triggerAthenaRender('${p.id}')" class="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition flex items-center gap-1.5">
                        <i data-lucide="download" class="w-3.5 h-3.5"></i>
                        <span>Gerar Pacote</span>
                    </button>
                </div>
            </div>
        `).join('');
        initIcons();
    } catch (err) {
        list.innerHTML = `<div class="col-span-2 text-center py-6 text-rose-500 text-xs">Erro ao carregar studio: ${escapeHtml(err.message)}</div>`;
    }
}

async function triggerAthenaRender(projectId) {
    try {
        showToast('Preparando pacote local de cartelas e manifesto...');
        const res = await api.athenaRenderVideo(projectId, [
            { scene_number: 1, title: 'Gancho', duration_seconds: 5 },
            { scene_number: 2, title: 'Desenvolvimento', duration_seconds: 40 },
            { scene_number: 3, title: 'Conclusão', duration_seconds: 15 }
        ]);
        showToast('Pacote de vídeo gerado com sucesso no acervo local!');
    } catch (err) {
        showToast(err.message || 'Erro na renderização.', 'error');
    }
}

async function loadAthenaProjects() {
    const tbody = document.getElementById('athena-projects-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">Carregando projetos da Athena...</td></tr>';

    try {
        const resp = await api.athenaListProjects();
        const projs = resp.projects || [];
        if (projs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-400 text-xs">Nenhum projeto salvo no histórico.</td></tr>';
            return;
        }

        tbody.innerHTML = projs.map(p => `
            <tr class="hover:bg-slate-50 transition text-xs">
                <td class="p-3.5 font-bold text-slate-800">${escapeHtml(p.title)}</td>
                <td class="p-3.5"><span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px]">${p.project_type}</span></td>
                <td class="p-3.5 text-slate-500 capitalize">${p.department || 'Geral'}</td>
                <td class="p-3.5 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200 uppercase">${p.status}</span></td>
                <td class="p-3.5 text-center text-slate-400">${p.created_at ? p.created_at.slice(0, 10) : '-'}</td>
                <td class="p-3.5 text-right whitespace-nowrap">
                    <button onclick="alert('Visualização do Projeto: ' + ${JSON.stringify(p.title)})" class="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold">
                        Ver Detalhes
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-rose-500 text-xs">Erro: ${escapeHtml(err.message)}</td></tr>`;
    }
}

async function loadAthenaHardwareStatus() {
    const jsonBox = document.getElementById('athena-status-json');
    if (!jsonBox) return;
    jsonBox.innerText = 'Consultando diagnósticos de hardware e modelos locais...';

    try {
        const resp = await api.athenaGetStatus();
        jsonBox.innerText = JSON.stringify(resp, null, 2);
    } catch (err) {
        jsonBox.innerText = `Erro ao obter status: ${err.message}`;
    }
}



