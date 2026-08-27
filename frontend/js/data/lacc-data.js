/**
 * LACC - Dados Modulares da Home Institucional
 * Estrutura data-driven para permitir adição e remoção de áreas, pesquisas e comunidade
 */
window.LACC_DATA = {
    // CENA 2: Rede Interdisciplinar de Ciências Criminais
    interdisciplinaryAreas: [
        {
            id: "direito",
            title: "Direito",
            specialty: "Penal & Processual",
            tags: ["Garantismo", "Tipicidade", "Contraditório"],
            icon: "scale",
            desc: "Dogmática penal, teoria do delito, garantias fundamentais e processo penal constitucional perante os tribunais superiores.",
            // Posições percentuais no canvas SVG (desktop)
            x: 82,
            y: 50
        },
        {
            id: "criminologia",
            title: "Criminologia",
            specialty: "Crítica & Empírica",
            tags: ["Etiologia Criminal", "Controle Social", "Vitimologia"],
            icon: "microscope",
            desc: "Análise sociológica do crime, política criminal, vitimização e os impactos institucionais do sistema penitenciário.",
            x: 68,
            y: 82
        },
        {
            id: "pericia",
            title: "Perícia Criminal",
            specialty: "Forense & Vestígios",
            tags: ["Local de Crime", "Balística", "Cadeia de Custódia"],
            icon: "search",
            desc: "Exame técnico da materialidade delitiva, balística forense, vestígios físicos e preservação probatória.",
            x: 32,
            y: 82
        },
        {
            id: "farmacia",
            title: "Farmácia Forense",
            specialty: "Toxicologia & Análises",
            tags: ["Química Forense", "Drogas de Abuso", "Venenos"],
            icon: "flask-conical",
            desc: "Identificação laboratorial de substâncias entorpecentes, dosagens toxicológicas e química analítica forense.",
            x: 18,
            y: 50
        },
        {
            id: "psicologia",
            title: "Psicologia Forense",
            specialty: "Comportamento & Avaliação",
            tags: ["Falsas Memórias", "Testemunho", "Avaliação Pericial"],
            icon: "brain",
            desc: "Estudo da psicologia do testemunho, confiabilidade da memória em reconhecimentos e avaliação da capacidade psíquica.",
            x: 32,
            y: 18
        },
        {
            id: "medicina",
            title: "Medicina Legal",
            specialty: "Tanatologia & Traumatologia",
            tags: ["Lesões Corporais", "Causa Mortis", "Necropsia"],
            icon: "activity",
            desc: "Perícias médico-legais no vivo e no cadáver, asfixiologia, traumatologia forense e elucidação da dinâmica do evento.",
            x: 68,
            y: 18
        }
    ]
};
