document.addEventListener("DOMContentLoaded", () => {
  const circleGraficas = document.getElementById("circle-graficas");

  if (circleGraficas) {
    circleGraficas.addEventListener("change", (e) => {
      if (e.target.checked) {
        console.log("🔘 Activado: gráficas de adecuación climática");
      } else {
        console.log("⚪ Desactivado");
      }
    });
  }
});
