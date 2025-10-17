const grid = document.getElementById('grid');
const statusEl = document.getElementById('status');
let devices = new Map();

// Fetch and display server info
async function loadServerInfo() {
  console.log('loadServerInfo() called');
  try {
    console.log('Fetching /api/server/info...');
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
      console.log('MAC address set to:', info.mac_address);
    }
    
    // Service UUID (volledige UUID)
    const serviceEl = document.querySelector('#service-uuid .value');
    if (serviceEl) {
      serviceEl.textContent = info.service_uuid;
      serviceEl.parentElement.title = `Service UUID\nDevice: ${info.device_name}`;
      console.log('Service UUID set to:', info.service_uuid);
    }
    
    // RX Characteristic UUID
    const rxEl = document.querySelector('#rx-char .value');
    if (rxEl) {
      rxEl.textContent = info.characteristics.rx.uuid;
      rxEl.parentElement.title = `RX Characteristic (${info.characteristics.rx.direction})\n${info.characteristics.rx.description}`;
      console.log('RX UUID set to:', info.characteristics.rx.uuid);
    }
    
    // TX Characteristic UUID
    const txEl = document.querySelector('#tx-char .value');
    if (txEl) {
      txEl.textContent = info.characteristics.tx.uuid;
      txEl.parentElement.title = `TX Characteristic (${info.characteristics.tx.direction})\n${info.characteristics.tx.description}`;
      console.log('TX UUID set to:', info.characteristics.tx.uuid);
    }
    
    console.log('Server info display complete!');
    
  } catch (e) {
    console.error('Could not load server info:', e);
    // Zet fallback waarden
    const macEl = document.querySelector('#mac-address .value');
    const serviceEl = document.querySelector('#service-uuid .value');
    const rxEl = document.querySelector('#rx-char .value');
    const txEl = document.querySelector('#tx-char .value');
    if (macEl) macEl.textContent = 'Fout';
    if (serviceEl) serviceEl.textContent = 'Fout';
    if (rxEl) rxEl.textContent = 'Fout';
    if (txEl) txEl.textContent = 'Fout';
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
console.log('App.js loaded, starting initialization...');

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

function init() {
  console.log('Initializing app...');
  loadServerInfo();
  connectWs();
}
