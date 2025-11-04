// static/js/inicio.js

// ========= TU CÓDIGO EXISTENTE (MAPA, UBICARME, RUTA) =========
(function () {
  const rutaRadios = document.querySelectorAll('input[name="ruta"]');
  const selEstado = document.getElementById('estado');
  const selMunicipio = document.getElementById('municipio');

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
})();

(function () {
  const selEstado = document.getElementById('estado');
  const selMunicipio = document.getElementById('municipio');
  const btnUbicarme = document.getElementById('btn-ubicarme');
  const map = document.getElementById('mapFrame');

  const setMap = (lat, lng, zoom = 11) => {
    if (!map || !lat || !lng) return;
    // (Tu lógica de mapa original)
    // map.src = `https://www.google.com/maps?q=${encodeURIComponent(lat + ',' + lng)}&z=${zoom}&output=embed`;
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

  selEstado?.addEventListener('change', () => centerFromSelect(selEstado, 7));
  selMunicipio?.addEventListener('change', () => centerFromSelect(selMunicipio, 12));

  btnUbicarme?.addEventListener('click', () => {
    // (Tu lógica de ubicarme original)
  });

  window.addEventListener('load', () => {
    if (centerFromSelect(selMunicipio, 12)) return;
    if (centerFromSelect(selEstado, 7)) return;
    setMap(19.5333, -96.9167, 12); // Xalapa por defecto
  });
})();

// ========= TU CÓDIGO EXISTENTE (CARRUSEL) =========
document.addEventListener('DOMContentLoaded', () => {
    const sliderContainer = document.querySelector('.recom-container');
    if (!sliderContainer) return; 

    const wrapper = sliderContainer.querySelector('.recom-pages-wrapper');
    const pages = sliderContainer.querySelectorAll('.recom-page');
    const nextBtn = sliderContainer.querySelector('.recom-nav.next');
    const prevBtn = sliderContainer.querySelector('.recom-nav.prev');
    const dotsContainer = sliderContainer.querySelector('.recom-dots');

    if (!pages || pages.length <= 1) {
      if(nextBtn) nextBtn.style.display = 'none';
      if(prevBtn) prevBtn.style.display = 'none';
      return;
    }
    
    // (El resto de tu lógica del carrusel va aquí...)
});


// ========= NUEVO CÓDIGO (SIEMBRABOT) =========
document.addEventListener('DOMContentLoaded', () => {

  // --- 1. Seleccionar elementos del DOM ---
const siembraBotButton = document.querySelector('.ICON-SIEMBRABOT');
  if (!siembraBotButton) return; 
  
  const botText = siembraBotButton.querySelector('.text-wrapper-12'); 
  const botSubText = siembraBotButton.querySelector('.text-wrapper-13'); 
  
  const radioEstado = document.querySelector('input[name="ruta"][value="Estados"]');
  const radioMunicipio = document.querySelector('input[name="ruta"][value="Municipios"]');
  const selectEstado = document.getElementById('estado');
  const selectMunicipio = document.getElementById('municipio');
  const selectMes = document.getElementById('mes');

  // --- AÑADE ESTA LÍNEA ---
  const submitButton = document.querySelector('form[role="form"] button[type="submit"]');
  // -------------------------

  let mediaRecorder; 
  let audioChunks = [];

  // --- 2. Verificar si el navegador soporta la grabación ---
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    console.warn('API de MediaDevices no soportada. Ocultando SiembraBot.');
    siembraBotButton.style.display = 'none';
    return;
  }
  
  // --- 3. Lógica de "Hablar" (Reemplazo de gTTS en el cliente) ---
  const synth = window.speechSynthesis;
  function hablar(texto) {
    if (synth.speaking) {
      synth.cancel();
    }
    const utterThis = new SpeechSynthesisUtterance(texto);
    utterThis.lang = 'es-MX';
    synth.speak(utterThis);
  }

  // --- 4. Lógica del Botón ---
  siembraBotButton.addEventListener('click', async () => {
    // Si no está grabando, empieza a grabar
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' }); // Especificamos formato
        
        audioChunks = []; 
        mediaRecorder.start();
        
        botText.textContent = 'Grabando...';
        botSubText.textContent = 'Presiona de nuevo para detener.';
        
        mediaRecorder.ondataavailable = (event) => {
          audioChunks.push(event.data);
        };

 mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            stream.getTracks().forEach(track => track.stop()); 

            // --- INICIO DE LA DEPURACIÓN DE AUDIO ---
            console.log("Grabación detenida. Creando reproductor de prueba...");

            // 1. Crear una URL para el audio grabado
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // 2. Crear un elemento <audio> para reproducirlo
            const audioPlayer = new Audio(audioUrl);
            audioPlayer.controls = true; // Mostrar controles (play/pausa/volumen)
            
            // 3. Estilo para que sea visible
            audioPlayer.style.position = 'fixed';
            audioPlayer.style.top = '100px';
            audioPlayer.style.left = '10px';
            audioPlayer.style.zIndex = '10000';
            audioPlayer.style.border = '2px solid red';
            
            // 4. Añadirlo a la página
            document.body.appendChild(audioPlayer);
            
            // 5. Informar en la consola y en el bot
            console.log("Reproductor de audio de prueba añadido. Dale 'play' para escuchar lo que se grabó.");
            if(botSubText) botSubText.textContent = 'Prueba de audio lista. ¡Dale play!';

            // 6. Igual enviamos el audio al servidor para ver qué dice Vosk
            enviarAudioAlServidor(audioBlob);
            // --- FIN DE LA DEPURACIÓN DE AUDIO ---
        };

      } catch (err) {
        console.error('Error al acceder al micrófono:', err);
        botText.textContent = 'Error de Micrófono';
        botSubText.textContent = 'No diste permiso para el micrófono.';
        hablar('No diste permiso para usar el micrófono.');
      }
    } 
    // Si ya está grabando, detiene la grabación
    else if (mediaRecorder.state === 'recording') {
      mediaRecorder.stop();
      botText.textContent = 'Procesando...';
      botSubText.textContent = 'Enviando a Gemma y Vosk...';
    }
  });

  // --- 5. Función para enviar el audio a Flask ---
  async function enviarAudioAlServidor(audioBlob) {
    const formData = new FormData();
    // 'audio_data' debe coincidir con request.files['audio_data'] en Flask
    formData.append('audio_data', audioBlob, 'grabacion_usuario.webm');

    try {
      // Usamos la ruta del endpoint que definiste en app_inicio.py
      const response = await fetch('/procesar-voz', {
        method: 'POST',
        body: formData
      });

      // Restaurar botón
      botText.textContent = 'SiembraBot';
      botSubText.textContent = 'Presiona aquí para usar el asistente.';

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Error ${response.status}`);
      }

      const params = await response.json();
      console.log('Parámetros recibidos de Gemma:', params);

      // Rellenamos el formulario
      rellenarFormulario(params);
      
      hablar(`Parámetros listos. Lugar: ${params.lugar || 'no dicho'}. Mes: ${params.mes || 'no dicho'}.`);
      // Espera un segundo para que el usuario escuche la confirmación
        setTimeout(() => {
          submitButton.click();
        }, 1000);

    } catch (error) {
      console.error('Error al enviar audio:', error);
      botText.textContent = 'Error';
      botSubText.textContent = error.message;
      hablar('Hubo un error al procesar la solicitud.');
    }
  }
  
  // --- 6. Función para rellenar el formulario ---
  function rellenarFormulario(params) {
    if (params.ruta === "Estados") {
      radioEstado.checked = true;
    } else if (params.ruta === "Municipios") {
      radioMunicipio.checked = true;
    }
    
    // Disparamos el evento 'change' para que el JS del mapa reaccione
    radioEstado.dispatchEvent(new Event('change'));

    if (params.lugar) {
        if (params.ruta === "Estados") {
            setSelectByText(selectEstado, params.lugar);
        } else {
            // Buscamos en ambos por si Gemma no devuelve ruta pero sí lugar
            setSelectByText(selectEstado, params.lugar) || setSelectByText(selectMunicipio, params.lugar);
        }
    }
    
    if (params.mes) {
        setSelectByText(selectMes, params.mes);
    }
  }

  // Función de ayuda para seleccionar una <option> por su TEXTO
  function setSelectByText(selectElem, text) {
    if (!selectElem || !text) return false;
    const normText = text.toLowerCase();
    for (let i = 0; i < selectElem.options.length; i++) {
        if (selectElem.options[i].text.toLowerCase() === normText) {
            selectElem.selectedIndex = i;
            // Disparamos un evento 'change' para que el JS del mapa reaccione
            selectElem.dispatchEvent(new Event('change'));
            return true;
        }
    }
    console.warn(`No se encontró la opción "${text}" en el select #${selectElem.id}`);
    return false;
  }

});