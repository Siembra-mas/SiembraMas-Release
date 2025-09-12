// static/js/inicio.js

(function () {
  const rutaRadios = document.querySelectorAll('input[name="ruta"]');
  const selEstado = document.getElementById('estado');
  const selMunicipio = document.getElementById('municipio');
  const btnUbicarme = document.getElementById('btn-ubicarme');
  const recomSection = document.getElementById('recom-section');

  function syncRuta() {
    const ruta = [...rutaRadios].find(r => r.checked)?.value || 'Estados';
    if (ruta === 'Estados') {
      if (selEstado) selEstado.disabled = false;
      if (selMunicipio) selMunicipio.disabled = true;
    } else {
      if (selEstado) selEstado.disabled = true;
      if (selMunicipio) selMunicipio.disabled = false;
    }
  }

  rutaRadios.forEach(r => r.addEventListener('change', syncRuta));
  syncRuta();

  // Botón "Ubicarme"
  if (btnUbicarme) {
    btnUbicarme.addEventListener('click', () => {
      if (!navigator.geolocation) {
        alert("Geolocalización no soportada.");
        return;
      }
      navigator.geolocation.getCurrentPosition(pos => {
        const { latitude, longitude } = pos.coords;
        fetch("/ubicarme", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lat: latitude, lon: longitude })
        })
          .then(r => r.json())
          .then(data => {
            const ruta = data.ruta;
            const lugar = data.lugar;
            const radio = document.querySelector(`input[name="ruta"][value="${ruta}"]`);
            if (radio) radio.checked = true;
            syncRuta();
            if (ruta === "Municipios" && selMunicipio) {
              const opt = [...selMunicipio.options].find(o => o.value === lugar);
              if (opt) opt.selected = true;
            }
            if (ruta === "Estados" && selEstado) {
              const opt = [...selEstado.options].find(o => o.value === lugar);
              if (opt) opt.selected = true;
            }
          })
          .catch(() => alert("No se pudo ubicar automáticamente."));
      }, () => alert("Permiso de ubicación denegado."));
    });
  }

  // Scroll automático si hay recomendaciones renderizadas
  window.addEventListener('load', () => {
    if (!recomSection) return;
    // Detecta si hay al menos una tarjeta dinámica
    const hasDynamicCards = recomSection.querySelectorAll('.RECOM .div-6').length > 0;
    // Heurística: si el servidor ha enviado recomendaciones (tras submit), hacemos scroll
    const urlParams = new URLSearchParams(window.location.search);
    const triggered = document.referrer && document.referrer === window.location.origin + '/'; // o detectar POST→redirect

    if (hasDynamicCards) {
      recomSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
})();
