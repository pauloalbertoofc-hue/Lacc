/**
 * LACC - Scrollytelling Refinado: Narrativa de Scroll, Transição Hero → Hub e Rede Interdisciplinar
 * Motion design sutil, ritmo institucional, momento de contemplação e scrollspy
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            initScrollytellingExperience();
        }, 120);
    });

    function initScrollytellingExperience() {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        
        // 1. Renderizar os nós e linhas da rede
        renderInterdisciplinaryNetwork();

        // 2. Inicializar Scrollspy da barra de navegação e drawer
        initScrollspy();

        // 3. Suporte a cliques diretos em âncoras da navbar
        initSmoothAnchors();

        // 4. Se o usuário solicitou redução de movimento, aplicar layout estático
        if (prefersReducedMotion) {
            setupReducedMotionLayout();
            return;
        }

        // 5. Se GSAP e ScrollTrigger estiverem disponíveis, orquestrar a timeline
        if (window.gsap && window.ScrollTrigger) {
            gsap.registerPlugin(ScrollTrigger);
            setupHeroParallaxAndMorph();
            setupInterdisciplinaryTimeline();
            setupConventionalSectionsEntrance();
        } else {
            setupFallbackLayout();
        }
    }

    /**
     * Renderização Data-Driven da Rede Interdisciplinar (Desktop e Mobile)
     */
    function renderInterdisciplinaryNetwork() {
        const stage = document.getElementById('interdisciplinary-network-stage');
        const svgCanvas = document.getElementById('interdisciplinary-svg-canvas');
        if (!stage || !window.LACC_DATA) return;

        const areas = window.LACC_DATA.interdisciplinaryAreas || [];
        const isDesktop = window.innerWidth >= 768;

        // Limpar nós existentes
        stage.querySelectorAll('.dynamic-area-node').forEach(el => el.remove());
        if (svgCanvas) svgCanvas.innerHTML = '';

        if (svgCanvas) {
            svgCanvas.innerHTML = `
                <defs>
                    <linearGradient id="goldenGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#fef3c7" stop-opacity="0.95" />
                        <stop offset="50%" stop-color="#f59e0b" stop-opacity="0.8" />
                        <stop offset="100%" stop-color="#b45309" stop-opacity="0.4" />
                    </linearGradient>
                </defs>
            `;
        }

        areas.forEach((area) => {
            // Linha SVG conectando o centro à coordenada do nó
            if (svgCanvas && isDesktop) {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', '50%');
                line.setAttribute('y1', '50%');
                line.setAttribute('x2', `${area.x}%`);
                line.setAttribute('y2', `${area.y}%`);
                line.setAttribute('class', `lacc-network-line line-${area.id}`);
                line.setAttribute('id', `line-${area.id}`);
                line.style.strokeDasharray = '400';
                line.style.strokeDashoffset = '400';
                svgCanvas.appendChild(line);
            }

            // Card / Nó da disciplina
            const nodeEl = document.createElement('div');
            nodeEl.className = `dynamic-area-node lacc-area-node absolute z-20 group`;
            nodeEl.setAttribute('id', `node-${area.id}`);
            nodeEl.setAttribute('tabindex', '0');
            nodeEl.setAttribute('role', 'button');
            nodeEl.setAttribute('aria-label', `${area.title} - ${area.specialty}: ${area.desc}`);

            // Previne navegação indesejada ao clicar
            nodeEl.addEventListener('click', (e) => {
                e.preventDefault();
                // Em telas touch, alterna o popover informativo
                if (window.innerWidth < 768) {
                    const pop = nodeEl.querySelector('.lacc-node-popover');
                    if (pop) {
                        pop.classList.toggle('opacity-100');
                        pop.classList.toggle('pointer-events-auto');
                    }
                }
            });

            // Posicionamento no desktop vs mobile
            if (isDesktop) {
                nodeEl.style.left = `${area.x}%`;
                nodeEl.style.top = `${area.y}%`;
                nodeEl.style.transform = 'translate(-50%, -50%)';
            }

            const tagsHtml = area.tags.map(t => `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">${t}</span>`).join(' ');

            nodeEl.innerHTML = `
                <!-- Conector e Ponto Dourado -->
                <div class="flex items-center gap-2.5 bg-slate-900/90 hover:bg-slate-800/95 border border-slate-800 hover:border-amber-500/60 backdrop-blur-md px-3.5 py-2 rounded-2xl shadow-xl transition-all select-none">
                    <div class="w-3.5 h-3.5 rounded-full lacc-node-core shrink-0"></div>
                    <div class="text-left">
                        <div class="flex items-center gap-1.5">
                            <span class="font-bold text-xs text-white leading-none">${area.title}</span>
                            <i data-lucide="${area.icon}" class="w-3 h-3 text-amber-400"></i>
                        </div>
                        <span class="text-[10px] text-slate-400 font-medium block mt-0.5">${area.specialty}</span>
                    </div>
                </div>

                <!-- Popover de Inspeção Intelectual no Desktop -->
                <div class="lacc-node-popover absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3.5 bg-slate-900/95 border border-amber-500/40 rounded-2xl shadow-2xl backdrop-blur-lg opacity-0 pointer-events-none transition-all z-30">
                    <div class="text-xs font-bold text-amber-300 flex items-center gap-1.5 mb-1">
                        <i data-lucide="${area.icon}" class="w-3.5 h-3.5 text-amber-400"></i>
                        <span>${area.title} na LACC</span>
                    </div>
                    <p class="text-[11px] text-slate-300 leading-relaxed mb-2">${area.desc}</p>
                    <div class="flex flex-wrap gap-1">
                        ${tagsHtml}
                    </div>
                    <div class="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-amber-500/40"></div>
                </div>
            `;

            stage.appendChild(nodeEl);
        });

        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /**
     * Transição Hero → Núcleo LACC
     * Cria a ilusão contínua do Brasão do Hero convergindo para o núcleo central da rede
     */
    function setupHeroParallaxAndMorph() {
        const hero = document.getElementById('landing-hero');
        const heroFg = document.getElementById('hero-foreground-content');
        const heroCrest = document.getElementById('hero-parallax-crest-wrapper');
        const heroCrestImg = document.getElementById('hero-parallax-crest-img');
        if (!hero || !heroFg || !heroCrest) return;

        // Animação dos textos e botões do Hero esmaecendo ao início do scroll
        gsap.to(heroFg, {
            scrollTrigger: {
                trigger: hero,
                start: 'top top',
                end: 'bottom 45%',
                scrub: 0.8
            },
            opacity: 0,
            y: -55,
            ease: 'power1.out'
        });

        // O Brasão do hero se desloca sutilmente com profundidade e reduz para alinhar ao hub
        gsap.to(heroCrest, {
            scrollTrigger: {
                trigger: hero,
                start: 'top top',
                end: 'bottom top',
                scrub: 1
            },
            y: 80,
            scale: 0.85,
            opacity: 0.35,
            ease: 'power1.inOut'
        });
    }

    /**
     * Construção Progressiva da Rede, Conexões e Momento de Contemplação
     */
    function setupInterdisciplinaryTimeline() {
        const container = document.getElementById('scene-interdisciplinary-container');
        const pinStage = document.getElementById('scene-interdisciplinary-pin');
        if (!container || !pinStage) return;

        const isDesktop = window.innerWidth >= 768;
        const areas = window.LACC_DATA.interdisciplinaryAreas || [];

        // Distância confortável de scroll (permite construção pausada + contemplação)
        const scrollDistance = isDesktop ? '+=280%' : '+=200%';

        const tl = gsap.timeline({
            scrollTrigger: {
                trigger: container,
                start: 'top top',
                end: scrollDistance,
                pin: pinStage,
                scrub: 1,
                anticipatePin: 1
            }
        });

        // FASE 1: O Núcleo Central LACC se estabelece (Ilusão do Brasão chegando e focando)
        tl.fromTo('#lacc-central-hub',
            { scale: 2.2, opacity: 0.25 },
            { scale: 1.0, opacity: 1.0, duration: 1.2, ease: 'power2.out' }
        );

        // Abertura da citação com a premissa epistemológica
        tl.fromTo('#interdisciplinary-quote',
            { opacity: 0, y: 25, scale: 0.95 },
            { opacity: 1, y: 0, scale: 1, duration: 1.0, ease: 'power2.out' },
            '-=0.6'
        );

        // FASE 2: Construção da Rede com as conexões nascendo do núcleo
        // Sequência planejada: Direito → Criminologia → Psicologia → Medicina → Farmácia → Perícia
        const sequenceOrder = ['direito', 'criminologia', 'psicologia', 'medicina', 'farmacia', 'pericia'];

        if (isDesktop) {
            sequenceOrder.forEach((id) => {
                const line = document.getElementById(`line-${id}`);
                const node = document.getElementById(`node-${id}`);

                if (line && node) {
                    // Linha projeta-se do centro
                    tl.to(line, {
                        strokeDashoffset: 0,
                        opacity: 0.85,
                        duration: 0.9,
                        ease: 'power1.inOut'
                    }, '-=0.4');

                    // Nó surge com scale suave e glow controlado
                    tl.fromTo(node,
                        { scale: 0.7, opacity: 0 },
                        { scale: 1.0, opacity: 1.0, duration: 0.8, ease: 'back.out(1.3)' },
                        '-=0.5'
                    );
                }
            });
        } else {
            // Em telas mobile: entrada sequencial dos cards conectados
            tl.fromTo('.dynamic-area-node',
                { opacity: 0, y: 20, scale: 0.9 },
                { opacity: 1, y: 0, scale: 1, stagger: 0.35, duration: 1.2, ease: 'power2.out' },
                '-=0.3'
            );
        }

        // Revelação do selo de síntese "CONHECIMENTO INTERDISCIPLINAR"
        tl.fromTo('#interdisciplinary-synthesis',
            { opacity: 0, y: 20, scale: 0.95 },
            { opacity: 1, y: 0, scale: 1, duration: 1.0, ease: 'power2.out' },
            '+=0.1'
        );

        // FASE 3: MOMENTO DE CONTEMPLAÇÃO (Intervalo estável para absorção visual)
        // Durante este trecho de rolagem, a composição permanece estável e iluminada
        tl.to({}, { duration: 2.2 });

        // FASE 4: Saída Suave para devolver o scroll convencional
        tl.to(pinStage, {
            opacity: 0,
            y: -30,
            duration: 1.0,
            ease: 'power1.in'
        });
    }

    /**
     * Volta ao Site Convencional: Entrada suave da seção "Ciências Criminais na Prática"
     */
    function setupConventionalSectionsEntrance() {
        const aboutContent = document.querySelector('#landing-about .max-w-5xl');
        if (aboutContent) {
            gsap.from(aboutContent, {
                scrollTrigger: {
                    trigger: '#landing-about',
                    start: 'top 80%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 35,
                duration: 0.9,
                ease: 'power2.out'
            });
        }
    }

    /**
     * Scrollspy: Atualiza automaticamente o indicador ativo na navbar e no drawer
     */
    function initScrollspy() {
        const sections = [
            { id: 'landing-hero', navKey: 'landing-hero' },
            { id: 'areas', navKey: 'areas' },
            { id: 'landing-about', navKey: 'landing-about' },
            { id: 'landing-events', navKey: 'landing-events' }
        ];

        function updateNavState() {
            const scrollPos = window.scrollY + 220;
            let activeKey = 'landing-hero';

            for (let i = 0; i < sections.length; i++) {
                const sec = document.getElementById(sections[i].id);
                if (sec) {
                    const top = sec.offsetTop;
                    const height = sec.offsetHeight;
                    if (scrollPos >= top && scrollPos < top + height) {
                        activeKey = sections[i].navKey;
                    }
                }
            }

            // Atualiza links desktop
            document.querySelectorAll('.nav-item-desktop').forEach(link => {
                const key = link.getAttribute('data-nav');
                if (key === activeKey) {
                    link.className = 'nav-item-desktop py-1 text-amber-400 font-bold border-b-2 border-amber-400 transition';
                } else {
                    link.className = 'nav-item-desktop py-1 text-slate-300 hover:text-amber-400 border-b-2 border-transparent transition';
                }
            });

            // Atualiza links drawer
            document.querySelectorAll('.nav-item-drawer').forEach(link => {
                const key = link.getAttribute('data-drawer-nav');
                if (key === activeKey) {
                    link.className = 'nav-item-drawer flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-amber-300 bg-amber-500/10 border-l-2 border-amber-400 transition';
                } else {
                    link.className = 'nav-item-drawer flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800/80 border-l-2 border-transparent transition';
                }
            });
        }

        window.addEventListener('scroll', updateNavState, { passive: true });
        updateNavState();
    }

    /**
     * Suporte para rolagem suave ao clicar em links da navbar (sem conflito com pinning)
     */
    function initSmoothAnchors() {
        document.querySelectorAll('a[href^="#"]').forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href').substring(1);
                const targetEl = document.getElementById(targetId);
                if (targetEl) {
                    e.preventDefault();
                    const yOffset = -70; // altura do cabeçalho fixo
                    const y = targetEl.getBoundingClientRect().top + window.pageYOffset + yOffset;
                    window.scrollTo({ top: y, behavior: 'smooth' });
                }
            });
        });
    }

    /**
     * Acessibilidade: Layout estático para `prefers-reduced-motion`
     */
    function setupReducedMotionLayout() {
        const pinStage = document.getElementById('scene-interdisciplinary-pin');
        const quote = document.getElementById('interdisciplinary-quote');
        const hub = document.getElementById('lacc-central-hub');
        const synthesis = document.getElementById('interdisciplinary-synthesis');
        const lines = document.querySelectorAll('.lacc-network-line');
        const nodes = document.querySelectorAll('.dynamic-area-node');

        if (pinStage) {
            pinStage.style.position = 'relative';
            pinStage.style.opacity = '1';
            pinStage.style.transform = 'none';
        }
        if (quote) { quote.style.opacity = '1'; quote.style.transform = 'none'; }
        if (hub) { hub.style.opacity = '1'; hub.style.transform = 'none'; }
        if (synthesis) { synthesis.style.opacity = '1'; synthesis.style.transform = 'none'; }

        lines.forEach(l => {
            l.style.strokeDashoffset = '0';
            l.style.opacity = '0.85';
        });

        nodes.forEach(n => {
            n.style.opacity = '1';
            n.style.transform = 'translate(-50%, -50%)';
        });
    }

    function setupFallbackLayout() {
        setupReducedMotionLayout();
    }

    // Recalcular layout no redimensionamento da janela
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            renderInterdisciplinaryNetwork();
            if (window.ScrollTrigger) {
                ScrollTrigger.refresh();
            }
        }, 200);
    });

})();
