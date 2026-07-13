document.addEventListener("DOMContentLoaded", () => {
    
    // --- 1. DROPDOWN MENU (Protegido contra errores) ---
    // Si estamos en la página de login, esto no explotará porque verifica que existan.
    const dropdown = document.querySelector(".dropdown");
    const menu = document.querySelector(".dropdown-menu");
    
    if (dropdown && menu) {
        document.addEventListener("click", (e) => {
            if (dropdown.contains(e.target)) {
                // El CSS ya tiene la animación, solo controlamos la visibilidad
                menu.style.display = (menu.style.display === "block") ? "none" : "block";
            } else {
                menu.style.display = "none";
            }
        });
    }

    // --- 2. MODAL DE CONFIRMACIÓN (Protegido) ---
    const confirmModal = document.getElementById("confirmModal");
    const openBtn = document.getElementById("openModal");
    const closeBtn = document.getElementById("closeModal");
    const cancelBtn = document.getElementById("cancelBtn");

    const cerrarConfirmacion = () => {
        if (confirmModal) confirmModal.style.display = "none";
    };

    if (openBtn && confirmModal) {
        openBtn.addEventListener("click", () => {
            confirmModal.style.display = "flex"; // Se usa flex para que quede centrado con el CSS moderno
        });
    }

    if (closeBtn) closeBtn.addEventListener("click", cerrarConfirmacion);
    if (cancelBtn) cancelBtn.addEventListener("click", cerrarConfirmacion);

    // Cerrar cualquier modal al hacer clic en el fondo oscuro
    window.addEventListener("click", (event) => {
        if (event.target === confirmModal) {
            cerrarConfirmacion();
        }
        
        const modalFiltros = document.getElementById("modalFiltros");
        if (event.target === modalFiltros) {
            cerrarModal(); // Llama a la función global de abajo
        }
    });
});


// ==========================================
// FUNCIONES GLOBALES (Llamadas desde el HTML)
// ==========================================

/* CONTROL DE CREACIÓN (Factores o Montos) con Animación Suave */
function mostrarModo() {
    const modoSelect = document.getElementById("modo");
    if (!modoSelect) return;

    const modo = modoSelect.value;
    const boxFactores = document.getElementById("crear_factores");
    const boxMontos = document.getElementById("crear_montos");

    if (!boxFactores || !boxMontos) return;

    // Efecto de desvanecimiento
    boxFactores.style.transition = "opacity 0.2s ease";
    boxMontos.style.transition = "opacity 0.2s ease";
    boxFactores.style.opacity = "0";
    boxMontos.style.opacity = "0";

    // Esperar a que se desvanezcan para cambiarlos de posición
    setTimeout(() => {
        if (modo === "factores") {
            boxFactores.style.display = "block";
            boxMontos.style.display = "none";
            setTimeout(() => boxFactores.style.opacity = "1", 50);
        } else if (modo === "montos") {
            boxFactores.style.display = "none";
            boxMontos.style.display = "block";
            setTimeout(() => boxMontos.style.opacity = "1", 50);
        } else {
            boxFactores.style.display = "none";
            boxMontos.style.display = "none";
        }
    }, 200);
}

/* MODAL DE FILTROS */
function abrirModal() {
    const modal = document.getElementById("modalFiltros");
    if (modal) {
        modal.style.display = "flex"; // Centra el modal
    }
}

function cerrarModal() {
    const modal = document.getElementById("modalFiltros");
    if (modal) {
        modal.style.display = "none";
    }
}