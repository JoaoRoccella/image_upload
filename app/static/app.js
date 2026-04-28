/* ══════════════════════════════════════════════════════════════════
   WebCam Capture — Lógica de aplicação
   Usa POST /images com auto-criação de sessão e cookie wc_session_id
══════════════════════════════════════════════════════════════════ */

'use strict';

/* ── Constantes ────────────────────────────────────────────────── */
const API         = '';               // mesmo origin que o servidor
const COOKIE_NAME = 'wc_session_id';
const COOKIE_DAYS = 30;

/* ── Cookie helpers ────────────────────────────────────────────── */

/**
 * Lê o valor de um cookie pelo nome.
 * @param {string} name
 * @returns {string|null}
 */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

/**
 * Define ou remove um cookie.
 * @param {string} name
 * @param {string} value
 * @param {number} days  — use número negativo para remover
 */
function setCookie(name, value, days) {
  const maxAge = days * 24 * 3600;
  document.cookie = `${name}=${value}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

/* ── Referências DOM ───────────────────────────────────────────── */
const video          = document.getElementById('video');
const canvas         = document.getElementById('canvas');
const flash          = document.getElementById('flash');
const overlay        = document.getElementById('video-overlay');
const camDot         = document.getElementById('cam-dot');
const camStatusText  = document.getElementById('cam-status-text');
const startBtn       = document.getElementById('start-btn');
const captureBtn     = document.getElementById('capture-btn');
const stopBtn        = document.getElementById('stop-btn');
const captureSpinner = document.getElementById('capture-spinner');
const captureLabel   = document.getElementById('capture-label');
const sessionDisplay = document.getElementById('session-display');
const copyBtn        = document.getElementById('copy-btn');
const restoreInput   = document.getElementById('restore-input');
const restoreBtn     = document.getElementById('restore-btn');
const gallery        = document.getElementById('gallery');
const countBadge     = document.getElementById('count-badge');
const toast          = document.getElementById('toast');

/* ── Estado da aplicação ───────────────────────────────────────── */
let stream    = null;
let sessionId = getCookie(COOKIE_NAME);   // persiste entre reloads via cookie

/* ══════════════════════════════════════════════════════════════════
   Toast
══════════════════════════════════════════════════════════════════ */
let toastTimer = null;

/**
 * Exibe uma mensagem temporária no canto da tela.
 * @param {string} msg
 * @param {'info'|'success'|'error'} type
 */
function showToast(msg, type = 'info') {
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
}

/* ══════════════════════════════════════════════════════════════════
   Sessão
══════════════════════════════════════════════════════════════════ */

/** Atualiza o badge do header com o session_id abreviado. */
function updateSessionDisplay() {
  sessionDisplay.textContent = sessionId
    ? `${sessionId.slice(0, 8)}…${sessionId.slice(-4)}`
    : '—';
  sessionDisplay.title = sessionId || 'Nenhuma sessão ativa';
}

/**
 * Aplica o session_id recebido da API:
 * - salva no cookie (renova prazo)
 * - atualiza o badge no header
 *
 * Chamado após cada resposta de upload — a API sempre retorna
 * session_id no body, seja sessão nova ou existente.
 *
 * @param {string} id
 */
function applySessionId(id) {
  sessionId = id;
  setCookie(COOKIE_NAME, id, COOKIE_DAYS);
  updateSessionDisplay();
}

/**
 * Carrega uma sessão existente por ID (restauração manual).
 * @param {string} id
 * @returns {Promise<boolean>}
 */
async function loadSession(id) {
  const r = await fetch(`${API}/sessions/${id}`);
  if (!r.ok) {
    showToast('❌ Sessão não encontrada.', 'error');
    return false;
  }
  applySessionId(id);
  await loadGallery();
  showToast('✅ Sessão restaurada!', 'success');
  return true;
}

/* ══════════════════════════════════════════════════════════════════
   Câmera
══════════════════════════════════════════════════════════════════ */

startBtn.addEventListener('click', async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user' },
      audio: false,
    });
    video.srcObject = stream;
    overlay.classList.add('hidden');
    camDot.classList.add('active');
    camStatusText.textContent = 'Ativa';
    startBtn.disabled  = true;
    captureBtn.disabled = false;
    stopBtn.disabled   = false;
  } catch (err) {
    showToast(`❌ Câmera indisponível: ${err.message}`, 'error');
  }
});

stopBtn.addEventListener('click', () => {
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }
  video.srcObject = null;
  overlay.classList.remove('hidden');
  camDot.classList.remove('active');
  camStatusText.textContent = 'Inativa';
  startBtn.disabled  = false;
  captureBtn.disabled = true;
  stopBtn.disabled   = true;
});

/* ══════════════════════════════════════════════════════════════════
   Captura e upload
══════════════════════════════════════════════════════════════════ */

captureBtn.addEventListener('click', async () => {
  if (!stream) return;

  // Efeito flash
  flash.classList.add('active');
  setTimeout(() => flash.classList.remove('active'), 200);

  // Captura frame do vídeo no canvas oculto
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const base64 = canvas.toDataURL('image/jpeg', 0.92).split(',')[1];

  // UI de loading
  captureBtn.disabled = true;
  captureSpinner.classList.add('show');
  captureLabel.textContent = 'Enviando…';

  try {
    /*
     * POST /images
     * - O cookie wc_session_id é enviado automaticamente pelo browser
     *   se já existir (mesmo origin).
     * - Se o cookie estiver ausente ou inválido, a API cria uma nova
     *   sessão e retorna o session_id no body + Set-Cookie header.
     * - O frontend lê data.session_id e renova o cookie via applySessionId().
     */
    const response = await fetch(`${API}/images`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ image: base64, mime_type: 'image/jpeg' }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Erro ao enviar imagem.');

    applySessionId(data.session_id);  // registra/renova sessão no cookie
    addToGallery(data.image);
    showToast('✅ Imagem salva!', 'success');

  } catch (err) {
    showToast(`❌ ${err.message}`, 'error');
  } finally {
    captureBtn.disabled = false;
    captureSpinner.classList.remove('show');
    captureLabel.textContent = '📸 Capturar imagem';
  }
});

/* ══════════════════════════════════════════════════════════════════
   Galeria
══════════════════════════════════════════════════════════════════ */

/** Busca todas as imagens da sessão atual e renderiza na galeria. */
async function loadGallery() {
  if (!sessionId) return;
  try {
    const r = await fetch(`${API}/sessions/${sessionId}/images`);
    if (!r.ok) return;
    const data = await r.json();
    gallery.innerHTML = '';
    if (data.images.length === 0) {
      showEmptyGallery();
    } else {
      data.images.forEach(addToGallery);
    }
  } catch (_) { /* rede indisponível — ignora silenciosamente */ }
}

/**
 * Insere um item de imagem no topo da galeria.
 * @param {{ url: string, created_at: string }} image
 */
function addToGallery(image) {
  const empty = gallery.querySelector('.gallery-empty');
  if (empty) empty.remove();

  const item = document.createElement('div');
  item.className = 'gallery-item';

  const time = new Date(image.created_at).toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  item.innerHTML = `
    <img src="${image.url}" alt="Captura das ${time}" loading="lazy" />
    <div class="gallery-item-meta">
      <span>${time}</span>
      <a href="${image.url}" target="_blank" rel="noopener" title="Abrir em nova aba">↗</a>
    </div>`;

  gallery.prepend(item);
  updateCount();
}

/** Exibe o estado vazio da galeria. */
function showEmptyGallery() {
  gallery.innerHTML = `
    <div class="gallery-empty">
      <div class="empty-icon">🌑</div>
      <p>Nenhuma imagem capturada ainda.<br>Inicie a câmera e pressione Capturar.</p>
    </div>`;
  updateCount();
}

/** Atualiza o badge de contagem. */
function updateCount() {
  countBadge.textContent = gallery.querySelectorAll('.gallery-item').length;
}

/* ══════════════════════════════════════════════════════════════════
   Copiar session ID
══════════════════════════════════════════════════════════════════ */

[copyBtn, sessionDisplay].forEach(el => {
  el.addEventListener('click', () => {
    if (!sessionId) return;
    navigator.clipboard
      .writeText(sessionId)
      .then(() => showToast('📋 Session ID copiado!', 'success'))
      .catch(() => showToast('❌ Falha ao copiar.', 'error'));
  });
});

/* ══════════════════════════════════════════════════════════════════
   Restaurar sessão manualmente
══════════════════════════════════════════════════════════════════ */

restoreBtn.addEventListener('click', async () => {
  const id = restoreInput.value.trim();
  if (!id) {
    showToast('⚠️ Cole um session ID válido.', 'error');
    return;
  }
  const ok = await loadSession(id);
  if (ok) restoreInput.value = '';
});

restoreInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') restoreBtn.click();
});

/* ══════════════════════════════════════════════════════════════════
   Inicialização
   Verifica se há sessão salva no cookie e carrega a galeria.
══════════════════════════════════════════════════════════════════ */

(async () => {
  updateSessionDisplay();

  if (!sessionId) return;

  try {
    const r = await fetch(`${API}/sessions/${sessionId}`);
    if (r.ok) {
      await loadGallery();
    } else {
      // Sessão não existe mais no banco — limpa o cookie
      setCookie(COOKIE_NAME, '', -1);
      sessionId = null;
      updateSessionDisplay();
    }
  } catch (_) { /* sem conexão — aguarda ação do usuário */ }
})();
