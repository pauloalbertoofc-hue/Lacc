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
    checkAuthState();
    initHeroParallax();
    initIcons();
});

function checkAuthState() {
    const isAuth = localStorage.getItem('lacc_auth') === 'true';
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');

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
    }
}

function toggleLandingDrawer() {
    const drawer = document.getElementById('landing-drawer');
    if (drawer) {
        drawer.classList.toggle('hidden');
        initIcons();
    }
}

function openLoginModal() {
    const isAuth = localStorage.getItem('lacc_auth') === 'true';
    if (isAuth) {
        // Se já está logado, entra direto no Dashboard!
        goToDashboard();
    } else {
        openModal('modal-login');
    }
}

function goToDashboard() {
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');
    if (landing) landing.classList.add('hidden');
    if (dashboard) dashboard.classList.remove('hidden');
    window.location.hash = '#dashboard';
    loadDashboard();
    initIcons();
}

async function submitLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;

    if (!email) {
        showToast('Por favor, informe seu e-mail.', 'error');
        return;
    }

    localStorage.setItem('lacc_auth', 'true');
    localStorage.setItem('lacc_user_email', email);

    closeModal('modal-login');
    goToDashboard();
    showToast('Bem-vindo à Área de Membros da LACC!');
}

function quickLoginDemo() {
    localStorage.setItem('lacc_auth', 'true');
    closeModal('modal-login');
    goToDashboard();
    showToast('Acesso de Membro concedido!');
}

function handleLogout() {
    localStorage.removeItem('lacc_auth');
    window.location.hash = '';
    const landing = document.getElementById('app-landing');
    const dashboard = document.getElementById('app-dashboard');
    if (landing) landing.classList.remove('hidden');
    if (dashboard) dashboard.classList.add('hidden');
    showToast('Você saiu da Área de Membros.', 'info');
    loadLandingEvents();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadLandingEvents() {
    try {
        const events = await api.getEvents();
        const container = document.getElementById('landing-events-container');
        if (!container) return;

        if (!events || events.length === 0) {
            container.innerHTML = '<div class="p-6 text-center text-slate-500 bg-slate-900/60 rounded-2xl border border-slate-800 text-xs">Nenhum evento cadastrado no momento. Fique atento às nossas redes!</div>';
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
    const crestWrapper = document.getElementById('hero-parallax-crest-wrapper');
    const crestImg = document.getElementById('hero-parallax-crest-img');
    const foreground = document.getElementById('hero-foreground-content');

    if (!hero || !crestWrapper) return;
    heroParallaxInitialized = true;

    // Detectar se o dispositivo possui cursor fino (desktop com mouse)
    const hasFinePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    let targetMouseX = 0;
    let targetMouseY = 0;
    let currentMouseX = 0;
    let currentMouseY = 0;

    let targetScrollY = window.scrollY || 0;
    let currentScrollY = window.scrollY || 0;

    // Interação sutil com o cursor (Desktop apenas)
    if (hasFinePointer) {
        hero.addEventListener('mousemove', (e) => {
            const rect = hero.getBoundingClientRect();
            // Ignora se o hero não estiver visível na janela
            if (rect.bottom < 0 || rect.top > window.innerHeight) return;

            // Posição normalizada de -1 a 1 em relação ao centro do hero
            const normX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
            const normY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;

            // Deslocamento sutil oposto ao cursor (máximo 16px horizontal, 12px vertical)
            targetMouseX = -normX * 16;
            targetMouseY = -normY * 12;
        }, { passive: true });

        hero.addEventListener('mouseleave', () => {
            // Retorna suavemente ao centro
            targetMouseX = 0;
            targetMouseY = 0;
        });
    }

    // Acompanhamento contínuo e passivo do scroll
    window.addEventListener('scroll', () => {
        targetScrollY = window.scrollY || window.pageYOffset || 0;
    }, { passive: true });

    // Loop de renderização fluida com LERP (Linear Interpolation) via requestAnimationFrame
    function renderParallax() {
        // Interpolação suave para mouse e scroll
        currentMouseX += (targetMouseX - currentMouseX) * 0.07;
        currentMouseY += (targetMouseY - currentMouseY) * 0.07;
        currentScrollY += (targetScrollY - currentScrollY) * 0.09;

        const heroHeight = hero.offsetHeight || 650;

        // Executar transformações apenas enquanto a seção estiver dentro/próxima da tela
        if (currentScrollY <= heroHeight + 150) {
            // 1. Brasão Parallax de Fundo
            // Deslocamento lento (~0.20x) + aumento sutil de escala (até 1.05x)
            const crestScrollY = currentScrollY * 0.20;
            const crestScale = 1 + Math.min(currentScrollY * 0.00025, 0.05);

            // Opacidade decresce progressivamente com a saída da tela
            const scrollFactor = Math.min(1, Math.max(0, currentScrollY / heroHeight));
            const crestOpacity = Math.max(0.03, 0.16 * (1 - scrollFactor * 0.75));

            const posX = currentMouseX.toFixed(2);
            const posY = (crestScrollY + currentMouseY).toFixed(2);

            crestWrapper.style.transform = `translate3d(${posX}px, ${posY}px, 0) scale(${crestScale.toFixed(4)})`;
            if (crestImg) {
                crestImg.style.opacity = crestOpacity.toFixed(3);
            }

            // 2. Conteúdo em Primeiro Plano (Texto e Botões)
            // Deslocamento em velocidade diferente (~0.40x) para criar profundidade tangível
            if (foreground) {
                const fgScrollY = currentScrollY * 0.40;
                const fgOpacity = Math.max(0, 1 - scrollFactor * 1.3);
                foreground.style.transform = `translate3d(0, ${fgScrollY.toFixed(2)}px, 0)`;
                foreground.style.opacity = fgOpacity.toFixed(3);
            }
        }

        requestAnimationFrame(renderParallax);
    }

    requestAnimationFrame(renderParallax);
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
// NAVEGAÇÃO ENTRE ABAS
// ==========================================
function navigateTo(viewId) {
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

