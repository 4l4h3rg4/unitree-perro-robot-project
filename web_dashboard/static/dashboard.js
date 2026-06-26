let ws = null;
let reconnectTimer = null;

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}/ws`;

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log('WebSocket conectado');
    updateConnection('connected', 'Conectado');
    startCamera();
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'history') {
      for (const evt of (msg.events || [])) {
        updateDashboard(evt.topic, evt.data);
      }
    } else if (msg.type === 'event') {
      updateDashboard(msg.topic, msg.data);
    } else if (msg.type === 'prompt_result') {
      handlePromptResult(msg.result);
    }
  };

  ws.onclose = () => {
    console.log('WebSocket desconectado');
    updateConnection('disconnected', 'Desconectado');
    scheduleReconnect();
  };

  ws.onerror = () => {
    updateConnection('error', 'Error');
  };
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 3000);
}

function updateConnection(state, label) {
  const dot = document.getElementById('conn-indicator');
  const lbl = document.getElementById('conn-label');
  dot.className = `dot ${state}`;
  lbl.textContent = label;
}

function updateDashboard(topic, data) {
  switch (topic) {
    case 'connection.state':
      handleConnectionState(data);
      break;
    case 'sensor.camera':
      updateCamera(data);
      break;
    case 'agent.action':
      updateAgentAction(data);
      break;
    case 'agent.reasoning':
      updateReasoning(data);
      break;
    case 'agent.alert':
      addAlert(data);
      break;
  }
}

function handleConnectionState(state) {
  const statusMap = {
    connected: ['connected', 'Conectado'],
    disconnected: ['disconnected', 'Desconectado'],
    connecting: ['connecting', 'Conectando...'],
    reconnecting: ['connecting', 'Reconectando...'],
    error: ['error', 'Error de conexion'],
  };
  const [css, label] = statusMap[state] || ['disconnected', state];
  updateConnection(css, label);
  if (state === 'connected') {
    startCamera();
  } else if (state === 'disconnected' || state === 'error') {
    stopCamera();
  }
}

let cameraRetryTimer = null;
let cameraActive = false;

function startCamera() {
  const img = document.getElementById('camera-img');
  const ph = document.getElementById('camera-placeholder');
  cameraActive = true;

  img.onload = () => {
    img.style.display = 'block';
    ph.style.display = 'none';
  };
  img.onerror = () => {
    img.style.display = 'none';
    ph.style.display = '';
    ph.textContent = 'Reintentando camara...';
    scheduleCameraRetry();
  };

  // cache-busting para evitar imagenes/streams cacheados
  img.src = '/video?t=' + Date.now();
}

function scheduleCameraRetry() {
  if (cameraRetryTimer || !cameraActive) return;
  cameraRetryTimer = setTimeout(() => {
    cameraRetryTimer = null;
    if (cameraActive) startCamera();
  }, 2500);
}

function updateCamera(data) {
  if (!data || !data.frame_available) return;
  const img = document.getElementById('camera-img');
  if (!img.src) startCamera();
}

function stopCamera() {
  cameraActive = false;
  if (cameraRetryTimer) { clearTimeout(cameraRetryTimer); cameraRetryTimer = null; }
  const img = document.getElementById('camera-img');
  const ph = document.getElementById('camera-placeholder');
  img.src = '';
  img.style.display = 'none';
  ph.style.display = '';
  ph.textContent = 'Esperando stream...';
}

function updateAgentAction(data) {
  const el = document.getElementById('reasoning-text');
  const tool = data.tool || 'accion';
  const result = data.result || '';
  el.textContent = result || `Ejecutado: ${tool}`;
}

function updateReasoning(data) {
  const el = document.getElementById('reasoning-text');
  if (data.thought) {
    el.textContent = data.thought;
  }
}

function addAlert(data) {
  const container = document.getElementById('alerts-container');
  const alertEl = document.createElement('div');
  alertEl.className = `alert-item alert-${data.level || 'info'}`;
  const icon = data.level === 'critical' ? '🔴' : data.level === 'warning' ? '🟡' : '🔵';
  const label = data.level === 'critical' ? 'CRITICO' : data.level === 'warning' ? 'Atencion' : 'Info';
  alertEl.innerHTML = `<span>${icon}</span><span><strong>${label}:</strong> ${data.message || ''}</span>`;
  container.prepend(alertEl);

  while (container.children.length > 4) {
    container.removeChild(container.lastChild);
  }

  setTimeout(() => {
    if (alertEl.parentNode) alertEl.remove();
  }, 8000);
}

function sendPrompt() {
  const input = document.getElementById('prompt-input');
  const text = (input.value || '').trim();
  if (!text) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    addAlert({ level: 'warning', message: 'Sin conexion con el servidor.' });
    return;
  }
  ws.send(JSON.stringify({ type: 'prompt', prompt: text }));
  document.getElementById('reasoning-text').textContent = `▶ ${text}`;
  input.value = '';
}

function quickPrompt(text) {
  const input = document.getElementById('prompt-input');
  input.value = text;
  sendPrompt();
}

function handlePromptResult(result) {
  if (!result) return;
  document.getElementById('reasoning-text').textContent = result.message || '';
  if (!result.matched) {
    addAlert({ level: 'warning', message: result.message || 'Comando no reconocido' });
  }
}

/* ── Voz → Whisper ── */
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

async function toggleRecording() {
  if (isRecording) {
    stopRecording();
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    addAlert({ level: 'warning', message: 'Tu navegador no soporta grabacion de audio.' });
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      transcribeAudio(blob);
    };
    mediaRecorder.start();
    isRecording = true;
    setMicState('recording', 'Grabando... toca para terminar');
  } catch (e) {
    addAlert({ level: 'warning', message: 'No se pudo acceder al microfono.' });
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  isRecording = false;
  setMicState('processing', 'Transcribiendo...');
}

async function transcribeAudio(blob) {
  try {
    const ext = (blob.type.includes('ogg')) ? 'ogg' : 'webm';
    const form = new FormData();
    form.append('audio', blob, `audio.${ext}`);
    const resp = await fetch('/transcribe', { method: 'POST', body: form });
    const data = await resp.json();
    if (!resp.ok || data.error) {
      addAlert({ level: 'warning', message: data.error || 'Error transcribiendo audio' });
      setMicState('idle');
      return;
    }
    const text = (data.text || '').trim();
    setMicState('idle');
    if (!text) {
      addAlert({ level: 'info', message: 'No se detecto voz.' });
      return;
    }
    const input = document.getElementById('prompt-input');
    input.value = text;
    sendPrompt();
  } catch (e) {
    addAlert({ level: 'warning', message: 'Fallo la transcripcion.' });
    setMicState('idle');
  }
}

function setMicState(state, label) {
  const btn = document.getElementById('prompt-mic');
  btn.classList.remove('rec', 'busy');
  if (state === 'recording') { btn.classList.add('rec'); btn.textContent = '⏹'; }
  else if (state === 'processing') { btn.classList.add('busy'); btn.textContent = '…'; }
  else { btn.textContent = '🎤'; }
  if (label) document.getElementById('reasoning-text').textContent = label;
}

function emergencyStop() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'emergency_stop' }));
    addAlert({ level: 'critical', message: '🛑 STOP DE EMERGENCIA ACTIVADO' });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  connectWebSocket();
});
