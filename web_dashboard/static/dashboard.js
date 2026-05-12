let ws = null;
let reconnectTimer = null;
let speedChart = null;
let lidarCtx = null;

const DATA_HISTORY = { speed_vx: [], speed_vyaw: [], labels: [], battery_pct: [] };
const MAX_HISTORY = 60;
const THROTTLE_MS = 100;

let _lastSpeedUpdate = 0;
let _lastLidarUpdate = 0;
let _lastImuUpdate = 0;
let _pendingSpeed = null;
let _pendingLidar = null;
let _pendingImu = null;

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}/ws`;

  ws = new WebSocket(url);

  ws.onopen = () => {
    console.log('WebSocket conectado');
    updateConnection('connected', 'Conectado');
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'history') {
      for (const evt of (msg.events || [])) {
        updateDashboard(evt.topic, evt.data);
      }
    } else if (msg.type === 'event') {
      addLog(msg.topic, msg.data);
      updateDashboard(msg.topic, msg.data);
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

function addLog(topic, data) {
  const container = document.getElementById('log-container');
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  const now = new Date();
  const time = now.toLocaleTimeString('es-CL', { hour12: false });

  let dataStr = '';
  try {
    dataStr = typeof data === 'object' ? JSON.stringify(data).substring(0, 120) : String(data).substring(0, 120);
  } catch (e) {
    dataStr = '[object]';
  }

  entry.innerHTML = `<span class="time">${time}</span><span class="topic">${topic}</span><span class="data">${dataStr}</span>`;
  container.appendChild(entry);

  while (container.children.length > 200) {
    container.removeChild(container.firstChild);
  }
  container.scrollTop = container.scrollHeight;
}

function updateDashboard(topic, data) {
  switch (topic) {
    case 'connection.state':
      handleConnectionState(data);
      break;
    case 'sensor.battery':
      updateBattery(data);
      break;
    case 'sensor.speed':
      _pendingSpeed = data;
      _throttleUpdate('speed');
      break;
    case 'sensor.imu':
      _pendingImu = data;
      _throttleUpdate('imu');
      break;
    case 'sensor.lidar':
      _pendingLidar = data;
      _throttleUpdate('lidar');
      break;
    case 'sensor.camera':
      updateCamera(data);
      break;
    case 'robot.posture':
      updatePosture(data);
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

function _throttleUpdate(type) {
  const now = Date.now();
  if (type === 'speed' && now - _lastSpeedUpdate < THROTTLE_MS) return;
  if (type === 'imu' && now - _lastImuUpdate < THROTTLE_MS) return;
  if (type === 'lidar' && now - _lastLidarUpdate < THROTTLE_MS) return;

  if (type === 'speed') {
    _lastSpeedUpdate = now;
    updateSpeed(_pendingSpeed);
  } else if (type === 'imu') {
    _lastImuUpdate = now;
    updateIMU(_pendingImu);
  } else if (type === 'lidar') {
    _lastLidarUpdate = now;
    updateLidar(_pendingLidar);
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
}

function updateBattery(data) {
  const pct = data.percentage || 0;
  document.getElementById('battery-pct').textContent = `${pct}%`;
  document.getElementById('battery-volt').textContent = `${(data.voltage || 0).toFixed(1)} V`;
  document.getElementById('battery-temp').textContent = `${data.temperature || 0}°C`;

  const arc = document.getElementById('battery-arc');
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (pct / 100) * circumference;
  arc.style.strokeDasharray = circumference;
  arc.style.strokeDashoffset = offset;

  if (pct > 50) arc.style.stroke = '#3fb950';
  else if (pct > 20) arc.style.stroke = '#d29922';
  else arc.style.stroke = '#f85149';

  DATA_HISTORY.battery_pct.push(pct);
  if (DATA_HISTORY.battery_pct.length > MAX_HISTORY) DATA_HISTORY.battery_pct.shift();
}

function updateSpeed(data) {
  const vx = data.vx || 0;
  const vyaw = data.vyaw || 0;
  document.getElementById('speed-vx').textContent = `vx: ${vx.toFixed(2)}`;
  document.getElementById('speed-vyaw').textContent = `vyaw: ${vyaw.toFixed(2)}`;

  const arrow = document.getElementById('compass-arrow');
  const angle = (vyaw * 40);
  arrow.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
  arrow.style.height = `${Math.min(40, Math.abs(vx) * 60 + 8)}px`;

  const now = new Date().toLocaleTimeString('es-CL', { hour12: false });
  DATA_HISTORY.speed_vx.push(vx);
  DATA_HISTORY.speed_vyaw.push(vyaw);
  DATA_HISTORY.labels.push(now);
  if (DATA_HISTORY.labels.length > MAX_HISTORY) {
    DATA_HISTORY.speed_vx.shift();
    DATA_HISTORY.speed_vyaw.shift();
    DATA_HISTORY.labels.shift();
  }

  if (speedChart) {
    speedChart.data.labels = DATA_HISTORY.labels;
    speedChart.data.datasets[0].data = DATA_HISTORY.speed_vx;
    speedChart.data.datasets[1].data = DATA_HISTORY.speed_vyaw;
    speedChart.update('none');
  }
}

function updateIMU(data) {
  document.getElementById('imu-roll').textContent = `${(data.roll || 0).toFixed(1)}°`;
  document.getElementById('imu-pitch').textContent = `${(data.pitch || 0).toFixed(1)}°`;
  document.getElementById('imu-yaw').textContent = `${(data.yaw || 0).toFixed(1)}°`;

  const roll = Math.abs(data.roll || 0);
  const pitch = Math.abs(data.pitch || 0);
  const stabilityEl = document.getElementById('stability-icon');
  const stabilityLabel = document.getElementById('stability-label');

  if (roll > 45 || pitch > 45) {
    stabilityEl.textContent = '🔴'; stabilityLabel.textContent = 'Inestable / Caido';
  } else if (roll > 20 || pitch > 20) {
    stabilityEl.textContent = '🟡'; stabilityLabel.textContent = 'Inclinado';
  } else {
    stabilityEl.textContent = '🟢'; stabilityLabel.textContent = 'Estable';
  }
}

function updateLidar(data) {
  const minDist = data.min_distance;
  const points = data.points || [];
  const pointCount = data.point_count || points.length;

  document.getElementById('lidar-min-dist').textContent =
    `Dist min: ${minDist === Infinity || minDist === null ? '--' : minDist.toFixed(2) + ' m'}`;
  document.getElementById('lidar-points').textContent = `Puntos: ${pointCount}`;

  const obstacleIcon = document.getElementById('obstacle-icon');
  const obstacleLabel = document.getElementById('obstacle-label');
  if (minDist < 0.5) {
    obstacleIcon.textContent = '🔴'; obstacleLabel.textContent = `Obstaculo cercano (${minDist.toFixed(2)}m)`;
  } else if (minDist < 1.5) {
    obstacleIcon.textContent = '🟡'; obstacleLabel.textContent = `Obstaculo medio (${minDist.toFixed(2)}m)`;
  } else if (minDist < Infinity) {
    obstacleIcon.textContent = '🟢'; obstacleLabel.textContent = `Libre (${minDist.toFixed(2)}m)`;
  } else {
    obstacleIcon.textContent = '⚪'; obstacleLabel.textContent = 'Sin datos';
  }

  drawLidarPoints(points);
}

function drawLidarPoints(points) {
  const canvas = document.getElementById('canvas-lidar');
  if (!canvas) return;
  lidarCtx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2, cy = h / 2;
  const scale = 100;

  lidarCtx.fillStyle = '#0a0a0f';
  lidarCtx.fillRect(0, 0, w, h);

  lidarCtx.strokeStyle = '#1a1a2e';
  lidarCtx.lineWidth = 1;
  for (let r = 30; r < 130; r += 30) {
    lidarCtx.beginPath();
    lidarCtx.arc(cx, cy, r, 0, Math.PI * 2);
    lidarCtx.stroke();
  }

  if (!points || points.length === 0) return;

  const maxPoints = 2000;
  const step = Math.max(1, Math.floor(points.length / maxPoints));

  lidarCtx.fillStyle = '#3fb950';
  for (let i = 0; i < points.length; i += step) {
    const pt = points[i];
    let x, y;
    if (typeof pt === 'object' && pt !== null) {
      x = pt.x || pt[0] || 0;
      y = pt.y || pt[1] || 0;
    } else if (Array.isArray(pt)) {
      x = pt[0] || 0;
      y = pt[1] || 0;
    } else {
      continue;
    }

    const sx = cx + x * scale;
    const sy = cy - y * scale;

    const dist = Math.sqrt(x * x + y * y);
    const alpha = Math.max(0.3, 1 - dist / 5);
    lidarCtx.globalAlpha = alpha;
    lidarCtx.fillRect(sx, sy, 2, 2);
  }
  lidarCtx.globalAlpha = 1;

  lidarCtx.fillStyle = '#58a6ff';
  lidarCtx.beginPath();
  lidarCtx.arc(cx, cy, 4, 0, Math.PI * 2);
  lidarCtx.fill();
}

function updateCamera(data) {
  document.getElementById('camera-placeholder').textContent = 'Camara activa';
}

function updatePosture(posture) {
  const iconMap = {
    standing: ['🧍', 'De pie'],
    sitting: ['🪑', 'Sentado'],
    damping: ['😴', 'Damp (relajado)'],
    lying: ['🛌', 'En el suelo'],
    recovery: ['🔄', 'Recuperando...'],
    walking: ['🚶', 'Caminando'],
  };
  const [icon, label] = iconMap[posture] || ['❓', posture || 'Desconocida'];
  document.getElementById('posture-icon').textContent = icon;
  document.getElementById('posture-label').textContent = label;
}

function updateAgentAction(data) {
  const el = document.getElementById('reasoning-text');
  const tool = data.tool || 'accion';
  const result = data.result || '';
  el.textContent = `Ejecutado: ${tool} → ${result}`;
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

  while (container.children.length > 8) {
    container.removeChild(container.lastChild);
  }

  setTimeout(() => {
    if (alertEl.parentNode) alertEl.remove();
  }, 15000);
}

function emergencyStop() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'emergency_stop' }));
    addAlert({ level: 'critical', message: '🛑 STOP DE EMERGENCIA ACTIVADO' });
  }
}

function initSpeedChart() {
  const ctx = document.getElementById('chart-speed').getContext('2d');
  speedChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: DATA_HISTORY.labels,
      datasets: [
        {
          label: 'vx (m/s)',
          data: DATA_HISTORY.speed_vx,
          borderColor: '#58a6ff',
          backgroundColor: 'rgba(88,166,255,0.1)',
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
        {
          label: 'vyaw (rad/s)',
          data: DATA_HISTORY.speed_vyaw,
          borderColor: '#3fb950',
          backgroundColor: 'rgba(63,185,80,0.1)',
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: { display: false },
        y: { min: -1.5, max: 1.5, ticks: { color: '#8b949e', font: { size: 10 } }, grid: { color: '#21262d' } },
      },
      plugins: { legend: { labels: { color: '#8b949e', font: { size: 10 }, boxWidth: 12 } } },
    },
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initSpeedChart();
  connectWebSocket();
});
