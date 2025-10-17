const grid = document.getElementById('grid');
const statusEl = document.getElementById('status');
let devices = new Map();

// Fetch and display server info
async function loadServerInfo() {
  try {
    const response = await fetch('/api/server/info');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const info = await response.json();
    
    console.log('Server info loaded:', info);
    
    // MAC address
    const macEl = document.querySelector('#mac-address .value');
    if (macEl) {
      macEl.textContent = info.mac_address;
      macEl.parentElement.title = `Bluetooth MAC: ${info.mac_address}`;
    }
    
    // Service UUID
    const serviceEl = document.querySelector('#service-uuid .value');
    if (serviceEl) {
      const shortUuid = info.service_uuid.substring(0, 13) + '...';
      serviceEl.textContent = shortUuid;
      serviceEl.parentElement.title = `Service UUID: ${info.service_uuid}\nDevice: ${info.device_name}`;
    }
    
    // Characteristics
    const charsEl = document.querySelector('#characteristics .value');
    if (charsEl) {
      charsEl.textContent = 'RX + TX';
      const rxUuid = info.characteristics.rx.uuid;
      const txUuid = info.characteristics.tx.uuid;
      charsEl.parentElement.title = 
        `RX (${info.characteristics.rx.direction}):\n${rxUuid}\n${info.characteristics.rx.description}\n\n` +
        `TX (${info.characteristics.tx.direction}):\n${txUuid}\n${info.characteristics.tx.description}`;
    }
    
  } catch (e) {
    console.error('Could not load server info:', e);
    // Zet fallback waarden
    const macEl = document.querySelector('#mac-address .value');
    const serviceEl = document.querySelector('#service-uuid .value');
    const charsEl = document.querySelector('#characteristics .value');
    if (macEl) macEl.textContent = 'Fout';
    if (serviceEl) serviceEl.textContent = 'Fout';
    if (charsEl) charsEl.textContent = 'Fout';
  }
}

function render() {
  // Remove tiles not present
  for (const [id, tile] of [...devices.entries()]) {
    if (!tile.data) continue;
  }
}

function upsertTile(dev) {
  let tile = document.querySelector(`.tile[data-id="${dev.id}"]`);
  if (!tile) {
    tile = document.createElement('div');
    tile.className = 'tile enter';
    tile.dataset.id = dev.id;
    grid.appendChild(tile);
    setTimeout(() => tile.classList.remove('enter'), 50);
  }
  tile.style.setProperty('--tile-color', dev.color || '#444');
  tile.innerHTML = `
    <div class="top">
      <span class="device" title="${dev.id}">${escapeHtml(dev.name)}</span>
      <span class="game">${escapeHtml(dev.game_name)}</span>
    </div>
    <div class="score" data-score="${dev.score}">${dev.score}</div>
  `;
}

function removeTile(id) {
  const tile = document.querySelector(`.tile[data-id="${id}"]`);
  if (tile) {
    tile.classList.add('exit');
    setTimeout(() => tile.remove(), 300);
  }
}

function escapeHtml(str) {
  return (str || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\'':'&#39;','"':'&quot;'}[c]));
}

function connectWs() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    statusEl.textContent = 'Verbonden';
    statusEl.classList.remove('error');
  };
  ws.onclose = () => {
    statusEl.textContent = 'Verbinding verbroken - opnieuw proberen...';
    statusEl.classList.add('error');
    setTimeout(connectWs, 3000);
  };
  ws.onerror = () => {
    statusEl.textContent = 'WebSocket fout';
    statusEl.classList.add('error');
  };
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      handleMessage(msg);
    } catch (e) {
      console.warn('Bad message', e);
    }
  };
}

function handleMessage(msg) {
  switch (msg.type) {
    case 'init':
      grid.innerHTML = '';
      (msg.devices || []).forEach(upsertTile);
      break;
    case 'device_added':
      upsertTile(msg.device);
      break;
    case 'device_updated':
      upsertTile(msg.device);
      animateScoreChange(msg.device.id, msg.device.score);
      break;
    case 'device_removed':
      removeTile(msg.id);
      break;
  }
}

function animateScoreChange(id, newScore) {
  const tile = document.querySelector(`.tile[data-id="${id}"] .score`);
  if (!tile) return;
  const prev = tile.getAttribute('data-score');
  if (prev != newScore) {
    tile.setAttribute('data-score', newScore);
    tile.textContent = newScore;
    tile.classList.add('pulse');
    setTimeout(() => tile.classList.remove('pulse'), 600);
  }
}

// Load server info on page load
loadServerInfo();
connectWs();
