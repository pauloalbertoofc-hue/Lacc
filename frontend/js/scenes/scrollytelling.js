/**
 * LACC - Scrollytelling: Cena 1 (Hero) & Cena 2 (Rede Interdisciplinar)
 * Arquitetura desacoplada, data-driven e acessível
 */

(function () {
    'use strict';

    // Inicializa quando o DOM estiver pronto
    document.addEventListener('DOMContentLoaded', () => {
        // Aguarda carregar dados e bibliotecas
        setTimeout(() => {
            initScrollyExperience();
        }, 100);
    });

    function initScrollyExperience() {
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        
        // Renderiza nós dinâmicos da Cena 2
        renderInterdisciplinaryNetwork();

        // Se o usuário solicitou redução de movimento, mantém layout estático sem pinning
        if (reducedMotion) {
            setupStaticAccessibleLayout();
            return;
        }

        // Se o GSAP e ScrollTrigger estiverem disponíveis
        if (window.gsap && window.ScrollTrigger) {
            gsap.registerPlugin(ScrollTrigger);
            setupHeroTransition();
            setupInterdisciplinaryScrolly();
        } else {
            // Fallback elegante com IntersectionObserver nativo caso a CDN demore
            setupNativeScrollFallback();
        }
    }

    /**
     * Renderiza os 6 nós interdisciplinares e as linhas SVG baseados em LACC_DATA
     */
    function renderInterdisciplinaryNetwork() {
        const networkContainer = document.getElementById('interdisciplinary-network-stage');
        const svgCanvas = document.getElementById('interdisciplinary-svg-canvas');
        if (!networkContainer || !window.LACC_DATA) return;

        const areas = window.LACC_DATA.interdisciplinaryAreas || [];
        const isDesktop = window.innerWidth >= 768;

        // Limpa nós existentes
        networkContainer.querySelectorAll('.dynamic-area-node').forEach(el => el.remove());
        if (svgCanvas) svgCanvas.innerHTML = '';

        if (svgCanvas) {
            // Adiciona definição do gradiente dourado
            svgCanvas.innerHTML = `
                <defs>
                    <linearGradient id="goldenGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#fef3c7" stop-opacity="0.9" />
                        <stop offset="50%" stop-color="#f59e0b" stop-opacity="0.75" />
                        <stop offset="100%" stop-color="#b45309" stop-opacity="0.4" />
                    </linearGradient>
                    <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.8" />
                        <stop offset="100%" stop-color="#f59e0b" stop-opacity="0" />
                    </radialGradient>
                </defs>
            `;
        }

        areas.forEach((area, index) => {
            // 1. Criar linha SVG do centro (50%, 50%) até as coordenadas da área (no desktop)
            if (svgCanvas && isDesktop) {
                const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line.setAttribute('x1', '50%');
                line.setAttribute('y1', '50%');
                line.setAttribute('x2', `${area.x}%`);
                line.setAttribute('y2', `${area.y}%`);
                line.setAttribute('class', `lacc-network-line line-${area.id}`);
                line.setAttribute('id', `line-${area.id}`);
                
                // Configuração para efeito de desenho de traço (stroke-dash)
                line.style.strokeDasharray = '400';
                line.style.strokeDashoffset = '400';
                svgCanvas.appendChild(line);
            }

            // 2. Criar card interativo do nó da área
            const nodeEl = document.createElement('div');
            nodeEl.className = `dynamic-area-node lacc-area-node absolute z-20 group`;
            nodeEl.setAttribute('id', `node-${area.id}`);
            nodeEl.setAttribute('tabindex', '0');
            nodeEl.setAttribute('role', 'button');
            nodeEl.setAttribute('aria-label', `${area.title} - ${area.specialty}. ${area.desc}`);

            // Posicionamento absoluto no desktop ou fluxo relativo responsivo no mobile
            if (isDesktop) {
                nodeEl.style.left = `${area.x}%`;
                nodeEl.style.top = `${area.y}%`;
                nodeEl.style.transform = 'translate(-50%, -50%)';
            }

            const tagsHtml = area.tags.map(t => `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">${t}</span>`).join(' ');

            nodeEl.innerHTML = `
                <!-- Conector / Ponto Dourado -->
                <div class="flex items-center gap-2.5 bg-slate-900/90 hover:bg-slate-800/95 border border-slate-800 hover:border-amber-500/60 backdrop-blur-md px-3.5 py-2.5 rounded-2xl shadow-xl transition">
                    <div class="w-3.5 h-3.5 rounded-full lacc-node-core shrink-0"></div>
                    <div class="text-left">
                        <div class="flex items-center gap-1.5">
                            <span class="font-bold text-xs text-white leading-none">${area.title}</span>
                            <i data-lucide="${area.icon}" class="w-3 h-3 text-amber-400"></i>
                        </div>
                        <span class="text-[10px] text-slate-400 font-medium block mt-0.5">${area.specialty}</span>
                    </div>
                </div>

                <!-- Popover / Descrição Detalhada em Hover no Desktop -->
                <div class="lacc-node-popover absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-3.5 bg-slate-900/95 border border-amber-500/40 rounded-2xl shadow-2xl backdrop-blur-lg opacity-0 pointer-events-none transition z-30">
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

            networkContainer.appendChild(nodeEl);
        });

        // Reinicializa ícones Lucide nos novos nós
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /**
     * Transição suave da Cena 1 (Hero):
     * O título desvanece suavemente ao scroll enquanto o brasão permanece
     */
    function setupHeroTransition() {
        const heroText = document.getElementById('hero-foreground-content');
        if (!heroText) return;

        gsap.to(heroText, {
            scrollTrigger: {
                trigger: '#landing-hero',
                start: 'top top',
                end: 'bottom 40%',
                scrub: true
            },
            opacity: 0,
            y: -50,
            ease: 'power1.out'
        });
    }

    /**
     * Scrollytelling da Cena 2: A Interdisciplinaridade
     * Pinning suave que orquestra as linhas e nós conforme o progresso da rolagem
     */
    function setupInterdisciplinaryScrolly() {
        const sectionContainer = document.getElementById('scene-interdisciplinary-container');
        const pinStage = document.getElementById('scene-interdisciplinary-pin');
        if (!sectionContainer || !pinStage) return;

        const isDesktop = window.innerWidth >= 768;
        const areas = window.LACC_DATA.interdisciplinaryAreas || [];

        // Timeline sincronizada à rolagem com pinning nativo
        const tl = gsap.timeline({
            scrollTrigger: {
                trigger: sectionContainer,
                start: 'top top',
                end: isDesktop ? '+=220%' : '+=180%',
                pin: pinStage,
                scrub: 1,
                anticipatePin: 1
            }
        });

        // 1. Entrada da premissa: "O crime não é um fenômeno de uma única ciência"
        tl.fromTo('#interdisciplinary-quote', 
            { opacity: 0, scale: 0.95, y: 30 },
            { opacity: 1, scale: 1, y: 0, duration: 1, ease: 'power2.out' }
        );

        // 2. Pulso e iluminação do nó central (LACC Hub)
        tl.fromTo('#lacc-central-hub',
            { scale: 0.8, opacity: 0 },
            { scale: 1, opacity: 1, duration: 0.8, ease: 'back.out(1.5)' },
            '-=0.4'
        );

        // 3. Projeção das Linhas Douradas para cada ciência
        if (isDesktop) {
            areas.forEach((area) => {
                tl.to(`#line-${area.id}`, {
                    strokeDashoffset: 0,
                    opacity: 0.9,
                    duration: 0.8,
                    ease: 'power1.inOut'
                }, '-=0.6');

                tl.fromTo(`#node-${area.id}`,
                    { scale: 0.6, opacity: 0 },
                    { scale: 1, opacity: 1, duration: 0.7, ease: 'back.out(1.4)' },
                    '-=0.5'
                );
            });
        } else {
            // No mobile, revelação progressiva dos cards de áreas
            tl.fromTo('.dynamic-area-node',
                { opacity: 0, y: 20, scale: 0.95 },
                { opacity: 1, y: 0, scale: 1, stagger: 0.25, duration: 1.2, ease: 'power2.out' },
                '-=0.4'
            );
        }

        // 4. Convergência para "CONHECIMENTO INTERDISCIPLINAR"
        tl.fromTo('#interdisciplinary-synthesis',
            { opacity: 0, y: 25, scale: 0.95 },
            { opacity: 1, y: 0, scale: 1, duration: 1.2, ease: 'power2.out' },
            '+=0.2'
        );

        // 5. Suave transição de saída para devolver o scroll normal
        tl.to('#scene-interdisciplinary-pin', {
            opacity: 0.96,
            duration: 0.4
        });
    }

    /**
     * Fallback acessível para `prefers-reduced-motion`:
     * Exibe os nós e linhas sem pinning nem movimentos rápidos
     */
    function setupStaticAccessibleLayout() {
        const pinStage = document.getElementById('scene-interdisciplinary-pin');
        const quote = document.getElementById('interdisciplinary-quote');
        const hub = document.getElementById('lacc-central-hub');
        const synthesis = document.getElementById('interdisciplinary-synthesis');
        const lines = document.querySelectorAll('.lacc-network-line');
        const nodes = document.querySelectorAll('.dynamic-area-node');

        if (pinStage) pinStage.style.position = 'relative';
        if (quote) { quote.style.opacity = '1'; quote.style.transform = 'none'; }
        if (hub) { hub.style.opacity = '1'; hub.style.transform = 'none'; }
        if (synthesis) { synthesis.style.opacity = '1'; synthesis.style.transform = 'none'; }
        
        lines.forEach(l => {
            l.style.strokeDashoffset = '0';
            l.style.opacity = '0.8';
        });

        nodes.forEach(n => {
            n.style.opacity = '1';
            n.style.transform = 'translate(-50%, -50%)';
        });
    }

    /**
     * Fallback nativo caso GSAP não carregue por conexão lenta
     */
    function setupNativeScrollFallback() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setupStaticAccessibleLayout();
                }
            });
        }, { threshold: 0.2 });

        const section = document.getElementById('scene-interdisciplinary-container');
        if (section) observer.observe(section);
    }

    // Redimensionamento de janela (Debounce)
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            renderInterdisciplinaryNetwork();
            if (window.ScrollTrigger) {
                ScrollTrigger.refresh();
            }
        }, 250);
    });

})();
