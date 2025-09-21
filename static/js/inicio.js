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

(function () {
  const selEstado = document.getElementById('estado');
  const selMunicipio = document.getElementById('municipio');
  const btnUbicarme = document.getElementById('btn-ubicarme');
  const map = document.getElementById('mapFrame');

  const setMap = (lat, lng, zoom = 11) => {
    if (!map || !lat || !lng) return;
    map.src = `https://www.google.com/maps?q=${encodeURIComponent(lat + ',' + lng)}&z=${zoom}&output=embed`;
  };

  const centerFromSelect = (selectEl, zoom) => {
    if (!selectEl) return false;
    const opt = selectEl.options[selectEl.selectedIndex];
    if (!opt) return false;
    const lat = opt.getAttribute('data-lat');
    const lng = opt.getAttribute('data-lng');
    if (lat && lng) { setMap(lat, lng, zoom); return true; }
    return false;
  };

  // Mueve el mapa al cambiar Estado / Municipio
  selEstado?.addEventListener('change', () => centerFromSelect(selEstado, 7));
  selMunicipio?.addEventListener('change', () => centerFromSelect(selMunicipio, 12));

  // Ubicarme → servidor devuelve { ruta, lugar }, setea el select y dispara el cambio
  btnUbicarme?.addEventListener('click', () => {
    if (!navigator.geolocation) { alert('Geolocalización no soportada'); return; }
    navigator.geolocation.getCurrentPosition(pos => {
      const { latitude, longitude } = pos.coords;
      fetch('/ubicarme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: latitude, lon: longitude })
      })
      .then(r => r.json())
      .then(data => {
        const { ruta, lugar } = data || {};
        if (ruta === 'Municipios' && selMunicipio) {
          // elige municipio y centra
          const opt = [...selMunicipio.options].find(o => o.value === lugar);
          if (opt) { opt.selected = true; selMunicipio.dispatchEvent(new Event('change')); return; }
        }
        if (ruta === 'Estados' && selEstado) {
          // elige estado y centra
          const opt = [...selEstado.options].find(o => o.value === lugar);
          if (opt) { opt.selected = true; selEstado.dispatchEvent(new Event('change')); return; }
        }
        // Fallback si no mapeó a nada
        setMap(latitude, longitude, 12);
      })
      .catch(() => {
        setMap(latitude, longitude, 12);
        alert('No se pudo ubicar automáticamente con el servidor.');
      });
    }, () => alert('Permiso de ubicación denegado.'));
  });

  // Estado inicial del mapa: municipio > estado > Xalapa
  window.addEventListener('load', () => {
    if (centerFromSelect(selMunicipio, 12)) return;
    if (centerFromSelect(selEstado, 7)) return;
    setMap(19.5333, -96.9167, 12); // Xalapa por defecto
  });
})();

document.addEventListener('DOMContentLoaded', () => {
    const sliderContainer = document.querySelector('.recom-container');
    if (!sliderContainer) return; // Si no hay recomendaciones, no hacer nada

    const wrapper = sliderContainer.querySelector('.recom-pages-wrapper');
    const pages = sliderContainer.querySelectorAll('.recom-page');
    const nextBtn = sliderContainer.querySelector('.recom-nav.next');
    const prevBtn = sliderContainer.querySelector('.recom-nav.prev');
    const dotsContainer = sliderContainer.querySelector('.recom-dots');

    if (pages.length <= 1) return; // Si solo hay una página, no se necesita JS

    let currentPage = 0;
    const totalPages = pages.length;

    // Crear los puntos de paginación
    for (let i = 0; i < totalPages; i++) {
        const dot = document.createElement('button');
        dot.classList.add('recom-dot');
        dot.dataset.page = i;
        dotsContainer.appendChild(dot);
    }
    const dots = dotsContainer.querySelectorAll('.recom-dot');

    function updateSlider() {
        // Mover el carrusel
        wrapper.style.transform = `translateX(-${currentPage * 100}%)`;

        // Actualizar los puntos
        dots.forEach(dot => {
            dot.classList.toggle('active', parseInt(dot.dataset.page) === currentPage);
        });

        // Ocultar/mostrar flechas
        prevBtn.classList.toggle('hidden', currentPage === 0);
        nextBtn.classList.toggle('hidden', currentPage === totalPages - 1);
    }

    nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages - 1) {
            currentPage++;
            updateSlider();
        }
    });

    prevBtn.addEventListener('click', () => {
        if (currentPage > 0) {
            currentPage--;
            updateSlider();
        }
    });

    dots.forEach(dot => {
        dot.addEventListener('click', () => {
            currentPage = parseInt(dot.dataset.page);
            updateSlider();
        });
    });

    // Inicializar el carrusel
    updateSlider();
});
