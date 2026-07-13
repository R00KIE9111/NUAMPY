/*LOGIN */
function mostrarModo() {
    const modo = document.getElementById("modo").value;

    const boxFactores = document.getElementById("crear_factores");
    const boxMontos = document.getElementById("crear_montos");

    if (modo === "factores") {
        boxFactores.style.display = "block";
        boxMontos.style.display = "none";
    } else if (modo === "montos") {
        boxFactores.style.display = "none";
        boxMontos.style.display = "block";
    } else {
        boxFactores.style.display = "none";
        boxMontos.style.display = "none";
    }
}
/*DASHBOARD */
document.addEventListener("click", function(e) {
    const dropdown = document.querySelector(".dropdown");
    const menu = document.querySelector(".dropdown-menu");

    if (dropdown.contains(e.target)) {
        menu.style.display = (menu.style.display === "block") ? "none" : "block";
    } else {
        menu.style.display = "none"; // clic afuera = cerrar
    }
});

/* MODAL DE FILTROS */
function abrirModal() {
  document.getElementById("modalFiltros").style.display = "block";
}

function cerrarModal() {
  document.getElementById("modalFiltros").style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("confirmModal");
    const openBtn = document.getElementById("openModal");
    const closeBtn = document.getElementById("closeModal");
    const cancelBtn = document.getElementById("cancelBtn");

    openBtn.addEventListener("click", () => {
        modal.style.display = "block";
    });

    closeBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    cancelBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });

    window.addEventListener("click", (event) => {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });
});