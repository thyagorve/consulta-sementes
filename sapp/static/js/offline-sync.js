(() => {
  'use strict';

  const root = document.body;
  const userId = Number(root?.dataset?.offlineUserId || 0);
  if (!userId) return;

  // A troca obrigatória de senha é uma etapa exclusivamente online.
  // Não inicializa o bloqueio offline nessa tela para evitar que um token
  // antigo cubra o formulário com o modal de "sessão offline expirada".
  if (/^\/mudar-senha\/?$/i.test(location.pathname)) return;

  const DB_NAME = `infinity-stock-offline-u${userId}`;
  const DB_VERSION = 1;
  const SYNC_INTERVAL = 45000;
  const REFERENCE_REFRESH_MS = 10 * 60 * 1000;
  const OFFLINE_CACHE_VERSION = '11.16';
  let softOffline = false;
  const WARN_QUEUE = 50;
  const CRITICAL_QUEUE = 200;
  let dbPromise = null;
  let syncing = false;
  let tokenCache = null;

  const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`);

  function openDB() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta', { keyPath: 'key' });
        if (!db.objectStoreNames.contains('queue')) {
          const store = db.createObjectStore('queue', { keyPath: 'id' });
          store.createIndex('status', 'status', { unique: false });
          store.createIndex('criado_local_em', 'criado_local_em', { unique: false });
        }
        if (!db.objectStoreNames.contains('reference')) db.createObjectStore('reference', { keyPath: 'key' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  async function tx(storeName, mode, fn) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction(storeName, mode);
      const store = transaction.objectStore(storeName);
      let result;
      try { result = fn(store); } catch (e) { reject(e); return; }
      transaction.oncomplete = () => resolve(result);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  }

  const requestValue = req => new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });

  async function metaGet(key) {
    const db = await openDB();
    const t = db.transaction('meta', 'readonly');
    return (await requestValue(t.objectStore('meta').get(key)))?.value;
  }
  async function metaSet(key, value) {
    const db = await openDB();
    const t = db.transaction('meta', 'readwrite');
    t.objectStore('meta').put({ key, value });
    return new Promise((resolve, reject) => { t.oncomplete = resolve; t.onerror = () => reject(t.error); });
  }
  async function queueAll() {
    const db = await openDB();
    const t = db.transaction('queue', 'readonly');
    return requestValue(t.objectStore('queue').getAll());
  }
  async function queuePut(item) {
    const db = await openDB();
    const t = db.transaction('queue', 'readwrite');
    t.objectStore('queue').put(item);
    return new Promise((resolve, reject) => { t.oncomplete = resolve; t.onerror = () => reject(t.error); });
  }
  async function referenceSet(data) {
    const db = await openDB();
    const t = db.transaction('reference', 'readwrite');
    t.objectStore('reference').put({ key: 'snapshot', value: data });
    return new Promise((resolve, reject) => { t.oncomplete = resolve; t.onerror = () => reject(t.error); });
  }
  async function referenceGet() {
    const db = await openDB();
    const t = db.transaction('reference', 'readonly');
    return (await requestValue(t.objectStore('reference').get('snapshot')))?.value || null;
  }

  async function snapshotGet(key) {
    const db = await openDB();
    const t = db.transaction('reference', 'readonly');
    return (await requestValue(t.objectStore('reference').get(`http:${key}`)))?.value || null;
  }

  async function snapshotPut(item) {
    const db = await openDB();
    const t = db.transaction('reference', 'readwrite');
    t.objectStore('reference').put({ key: `http:${item.key}`, value: item });
    return new Promise((resolve, reject) => {
      t.oncomplete = resolve;
      t.onerror = () => reject(t.error);
    });
  }

  function snapshotKey(url) {
    const u = new URL(url, location.origin);
    return `${u.pathname}${u.search}`;
  }

  function podeSalvarSnapshot(url, method = 'GET') {
    if (String(method || 'GET').toUpperCase() !== 'GET') return false;
    const u = new URL(url, location.origin);
    if (u.origin !== location.origin) return false;
    const p = u.pathname;
    // Salvar somente leituras realmente usadas no modo offline. Antes toda
    // chamada GET de /api/ era clonada e persistida, inclusive polling curto,
    // causando I/O desnecessário no celular e no PC.
    return (
      p === '/dashboard-data/'
      || p === '/api/solicitacoes/listar/'
      || p === '/api/kanban/dados/'
      || p === '/api/estoque-resumo/'
      || p === '/api/estoque/opcoes-filtro/'
    );
  }

  const nativeFetch = window.fetch.bind(window);

  async function fetchComSnapshot(input, init = {}) {
    const request = input instanceof Request ? input : null;
    const method = String(init.method || request?.method || 'GET').toUpperCase();
    const rawUrl = request?.url || String(input || '');

    if (!podeSalvarSnapshot(rawUrl, method)) {
      return nativeFetch(input, init);
    }

    const key = snapshotKey(rawUrl);

    if (!navigator.onLine) {
      const cached = await snapshotGet(key).catch(() => null);
      if (cached?.body != null) {
        window.dispatchEvent(new CustomEvent('infinity:offline-snapshot', { detail: { key, cached_at: cached.updated_at } }));
        return new Response(cached.body, {
          status: 200,
          headers: {
            'Content-Type': cached.content_type || 'application/json; charset=utf-8',
            'X-Infinity-Offline-Snapshot': '1',
          },
        });
      }
    }

    try {
      const response = await nativeFetch(input, init);
      softOffline = false;
      window.dispatchEvent(new CustomEvent('infinity:server-live', { detail: { key } }));
      if (response.ok) {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('json') || contentType.includes('text')) {
          // Não segure a renderização esperando IndexedDB. Clona a resposta e
          // grava o snapshot fora do caminho crítico da navegação.
          const copy = response.clone();
          setTimeout(async () => {
            try {
              const body = await copy.text();
              await snapshotPut({ key, body, content_type: contentType, updated_at: Date.now() });
            } catch (_) {}
          }, 0);
        }
      }
      return response;
    } catch (error) {
      const cached = await snapshotGet(key).catch(() => null);
      if (cached?.body != null) {
        softOffline = true;
        window.dispatchEvent(new CustomEvent('infinity:offline-snapshot', { detail: { key, cached_at: cached.updated_at, network_error: true } }));
        return new Response(cached.body, {
          status: 200,
          headers: {
            'Content-Type': cached.content_type || 'application/json; charset=utf-8',
            'X-Infinity-Offline-Snapshot': '1',
          },
        });
      }
      throw error;
    }
  }

  // Todas as leituras comuns continuam usando fetch normal quando online.
  // Quando a conexão cai, somente GETs previamente sincronizados usam o
  // snapshot IndexedDB deste usuário. POST/PUT/DELETE nunca passam por aqui.
  window.fetch = fetchComSnapshot;

  async function getDeviceId() {
    let id = await metaGet('device_id');
    if (!id) {
      id = uuid();
      await metaSet('device_id', id);
    }
    return id;
  }

  function injectUI() {
    if (document.getElementById('offlineSyncBubble')) return;
    const style = document.createElement('style');
    style.textContent = `
      #offlineSyncBubble{position:fixed;right:14px;bottom:14px;z-index:2147482000;border:0;border-radius:999px;min-width:48px;height:48px;padding:0 13px;display:flex;align-items:center;justify-content:center;gap:7px;color:#fff;font-weight:900;font-size:.76rem;box-shadow:0 10px 30px rgba(15,23,42,.25);cursor:pointer;transition:.18s ease}
      #offlineSyncBubble.sync-green{background:#16a34a} #offlineSyncBubble.sync-yellow{background:#d97706} #offlineSyncBubble.sync-red{background:#dc2626} #offlineSyncBubble.sync-black{background:#111827}
      #offlineSyncBubble .sync-spinner{display:none;width:14px;height:14px;border:2px solid rgba(255,255,255,.45);border-top-color:#fff;border-radius:50%;animation:infSpin .75s linear infinite} #offlineSyncBubble.is-syncing .sync-spinner{display:block}
      @keyframes infSpin{to{transform:rotate(360deg)}}
      #offlineStaleBanner{display:none;position:fixed;left:50%;transform:translateX(-50%);bottom:72px;z-index:2147481900;background:#fff7ed;color:#9a3412;border:1px solid #fed7aa;border-radius:10px;padding:7px 12px;font-size:.72rem;font-weight:800;box-shadow:0 7px 22px rgba(0,0,0,.12)}
      #offlineSessionBlock{display:none;position:fixed;inset:0;z-index:2147483000;background:rgba(15,23,42,.72);backdrop-filter:blur(4px);align-items:center;justify-content:center;padding:18px} #offlineSessionBlock.show{display:flex}.offline-session-card{width:min(460px,100%);background:#fff;border-radius:18px;padding:22px;text-align:center;box-shadow:0 26px 80px rgba(0,0,0,.35)}.offline-session-card i{font-size:2rem;color:#111827}.offline-session-card h5{font-weight:900;margin:12px 0 6px}.offline-session-card p{font-size:.78rem;color:#64748b;margin:0}.offline-session-card .offline-session-hint{margin-top:12px;padding:9px;border-radius:10px;background:#f8fafc;font-size:.7rem;font-weight:800;color:#475569}
      #offlineSyncModal{position:fixed;inset:0;z-index:2147482500;background:rgba(15,23,42,.52);display:none;align-items:center;justify-content:center;padding:14px} #offlineSyncModal.show{display:flex}
      .sync-center{width:min(920px,100%);max-height:min(86vh,780px);overflow:hidden;background:#fff;border-radius:18px;box-shadow:0 24px 70px rgba(0,0,0,.28);display:flex;flex-direction:column}
      .sync-center-head{padding:15px 17px;border-bottom:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center}.sync-center-head h5{margin:0;font-weight:900}.sync-close{border:0;background:#f3f4f6;border-radius:9px;width:34px;height:34px}
      .sync-tabs{display:flex;gap:5px;padding:10px 12px;border-bottom:1px solid #eef2f7;overflow:auto}.sync-tab{border:0;border-radius:999px;padding:7px 11px;background:#f3f4f6;font-size:.7rem;font-weight:900;white-space:nowrap}.sync-tab.active{background:#173f2a;color:#fff}
      .sync-body{overflow:auto;padding:12px}.sync-item{border:1px solid #e5e7eb;border-radius:12px;padding:10px;margin-bottom:8px}.sync-item-top{display:flex;justify-content:space-between;gap:10px}.sync-badge{font-size:.58rem;font-weight:900;border-radius:999px;padding:4px 7px;background:#eef2ff}.sync-meta{font-size:.66rem;color:#64748b;margin-top:5px}.sync-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}.sync-actions button{border:0;border-radius:8px;padding:6px 9px;font-size:.65rem;font-weight:900}.sync-apply{background:#dcfce7;color:#166534}.sync-cancel{background:#fee2e2;color:#991b1b}.sync-adjust{background:#fef3c7;color:#92400e}
      .sync-empty{text-align:center;color:#94a3b8;padding:35px 10px}.sync-warning{padding:8px 10px;margin-bottom:9px;border-radius:9px;background:#fff7ed;color:#9a3412;font-size:.68rem;font-weight:800}
      @media(max-width:600px){#offlineSyncBubble{right:10px;bottom:10px}.sync-center{max-height:92vh;border-radius:14px}.sync-item-top{flex-direction:column}}
    `;
    document.head.appendChild(style);
    document.body.insertAdjacentHTML('beforeend', `
      <div id="offlineStaleBanner">⚠️ saldo pode estar desatualizado</div>
      <div id="offlineSessionBlock"><div class="offline-session-card"><i class="fas fa-lock"></i><h5>Sessão offline expirada</h5><p>Conecte este dispositivo à internet e faça login novamente para continuar. As operações pendentes foram preservadas.</p><div class="offline-session-hint" id="offlineSessionPendingHint"></div><a href="/login/?next=/" class="btn btn-dark btn-sm mt-3">Fazer login online</a></div></div>
      <button id="offlineSyncBubble" class="sync-green" type="button" title="Central de Sincronização">
        <span id="offlineSyncDot">●</span><span class="sync-spinner"></span><span id="offlineSyncCount">0</span>
      </button>
      <div id="offlineSyncModal" role="dialog" aria-modal="true">
        <div class="sync-center">
          <div class="sync-center-head"><div><h5>Central de Sincronização</h5><div class="small text-muted" id="syncDeviceLabel"></div></div><button class="sync-close" type="button">✕</button></div>
          <div class="sync-tabs">
            <button class="sync-tab active" data-status="PENDENTE">Pendentes <span data-count="PENDENTE">0</span></button>
            <button class="sync-tab" data-status="CONFLITO">Conflitos <span data-count="CONFLITO">0</span></button>
            <button class="sync-tab" data-status="REJEITADA">Rejeitadas <span data-count="REJEITADA">0</span></button>
            <button class="sync-tab" data-status="ACEITA">Sincronizadas <span data-count="ACEITA">0</span></button>
          </div>
          <div class="sync-body" id="offlineSyncBody"></div>
        </div>
      </div>`);
    document.getElementById('offlineSyncBubble').addEventListener('click', openCentral);
    document.querySelector('#offlineSyncModal .sync-close').addEventListener('click', () => document.getElementById('offlineSyncModal').classList.remove('show'));
    document.getElementById('offlineSyncModal').addEventListener('click', e => { if (e.target.id === 'offlineSyncModal') e.currentTarget.classList.remove('show'); });
    document.querySelectorAll('.sync-tab').forEach(btn => btn.addEventListener('click', () => {
      document.querySelectorAll('.sync-tab').forEach(x => x.classList.toggle('active', x === btn));
      renderCentral(btn.dataset.status);
    }));
  }

  function sessionExpired(meta) {
    if (!meta?.expira_em) return true;
    return Date.now() >= new Date(meta.expira_em).getTime();
  }

  async function ensureSession(force = false) {
    const saved = await metaGet('session');
    if (!force && saved && !sessionExpired(saved)) {
      tokenCache = saved.access;
      return saved;
    }
    if (!navigator.onLine) return saved || null;
    try {
      const r = await fetch('/api/offline/session/', { credentials: 'same-origin', cache: 'no-store' });
      if (!r.ok) return saved || null;
      const data = await r.json();
      await metaSet('session', data);
      await metaSet('logged_out', false);
      tokenCache = data.access;
      return data;
    } catch (_) { return saved || null; }
  }

  async function authFetch(url, options = {}) {
    let session = await ensureSession(false);
    if (!session || sessionExpired(session)) session = await ensureSession(true);
    if (!session?.access) throw new Error('SESSION_EXPIRED');
    const headers = new Headers(options.headers || {});
    headers.set('Authorization', `Bearer ${session.access}`);
    if (!headers.has('Content-Type') && options.body) headers.set('Content-Type', 'application/json');
    let r = await fetch(url, { ...options, headers, cache: 'no-store' });
    if (r.status === 401 && navigator.onLine) {
      session = await ensureSession(true);
      if (session?.access) {
        headers.set('Authorization', `Bearer ${session.access}`);
        r = await fetch(url, { ...options, headers, cache: 'no-store' });
      }
    }
    return r;
  }

  async function refreshReference(force = false) {
    if (!navigator.onLine) return;
    try {
      const ultimo = Number(await metaGet('reference_refreshed_at') || 0);
      if (!force && ultimo && (Date.now() - ultimo) < REFERENCE_REFRESH_MS) return;
      const r = await authFetch('/api/referencia/');
      if (!r.ok) return;
      const data = await r.json();
      await referenceSet(data);
      await metaSet('reference_refreshed_at', Date.now());
      updateStatus();
    } catch (_) {}
  }

  async function getLotVersion(lote) {
    const ref = await referenceGet();
    const key = String(lote || '').trim().toUpperCase();
    const rows = ref?.estoques || [];
    const row = rows.find(x => String(x.lote || '').trim().toUpperCase() === key);
    return Number(row?.versao_lote || 0);
  }

  async function getLotVersions(lotes = []) {
    const ref = await referenceGet();
    const rows = ref?.estoques || [];
    const index = new Map(
      rows.map(row => [String(row.lote || '').trim().toUpperCase(), Number(row.versao_lote || 0)])
    );
    const result = {};
    for (const lote of lotes) {
      const key = String(lote || '').trim();
      if (!key) continue;
      result[key] = Number(index.get(key.toUpperCase()) || 0);
    }
    return result;
  }

  function emitQueueEvent(name, detail = {}) {
    try {
      window.dispatchEvent(new CustomEvent(name, { detail }));
    } catch (_) {}
  }

  async function enqueue(operation, optimisticFn) {
    const lote = String(operation.lote || operation.payload?.lote || '').trim();
    const baseVersao = operation.base_lote_versao !== undefined
      ? operation.base_lote_versao
      : await getLotVersion(lote);
    const item = {
      id: operation.id || uuid(),
      tipo: String(operation.tipo || '').toUpperCase(),
      lote,
      estoque_id: operation.estoque_id ?? operation.payload?.estoque_id ?? null,
      quantidade: operation.quantidade ?? operation.payload?.quantidade ?? null,
      base_lote_versao: baseVersao,
      criado_local_em: new Date().toISOString(),
      payload: operation.payload || {},
      status: 'PENDENTE',
      motivo: '',
      atualizado_em: new Date().toISOString(),
    };
    await queuePut(item);

    // A tela reage imediatamente. A leitura completa da fila e a sincronização
    // ficam em segundo plano para não segurar o clique do operador.
    if (typeof optimisticFn === 'function') optimisticFn(item);
    emitQueueEvent('infinity:queue-changed', { action: 'queued', item });
    updateStatus();
    if (navigator.onLine) setTimeout(syncNow, 0);
    return item;
  }

  async function syncNow() {
    if (syncing || !navigator.onLine) { updateStatus(); return; }
    const session = await ensureSession(false);
    if (!session || sessionExpired(session)) { updateStatus(); return; }
    const all = await queueAll();
    const pending = all.filter(x => x.status === 'PENDENTE');
    if (!pending.length) { updateStatus(); return; }
    syncing = true;
    updateStatus();
    try {
      const deviceId = await getDeviceId();
      // Compatibilidade com filas criadas por versões anteriores: operações
      // compostas (empenho/movimentação de card) não têm uma quantidade única
      // no nível raiz. Não envie campos opcionais nulos, pois versões antigas
      // do serializer podiam rejeitar o lote inteiro com HTTP 400.
      const operacoes = pending.map(({status, motivo, atualizado_em, ...x}) => {
        const clean = { ...x };
        if (clean.quantidade === null || clean.quantidade === undefined || clean.quantidade === '') delete clean.quantidade;
        if (clean.estoque_id === null || clean.estoque_id === undefined || clean.estoque_id === '') delete clean.estoque_id;
        return clean;
      });
      const body = { device_id: deviceId, operacoes };
      const r = await authFetch('/api/sync/', { method: 'POST', body: JSON.stringify(body) });
      if (r.status === 401) { await updateStatus(); return; }
      if (!r.ok) {
        let detalhe = '';
        try { detalhe = JSON.stringify(await r.json()); } catch (_) {}
        console.warn('[OfflineSync] servidor recusou a fila:', r.status, detalhe);
        throw new Error(`SYNC_${r.status}${detalhe ? `_${detalhe}` : ''}`);
      }
      const data = await r.json();
      const accepted = new Map((data.aceitos || []).map(x => [String(x.id), x]));
      const conflicts = new Map((data.conflitos || []).map(x => [String(x.id), x]));
      const rejected = new Map((data.rejeitados || []).map(x => [String(x.id), x]));
      const finalizados = [];
      for (const item of pending) {
        const id = String(item.id);
        if (accepted.has(id)) {
          item.status = 'ACEITA'; item.resultado = accepted.get(id).resultado || {}; item.motivo = '';
        } else if (conflicts.has(id)) {
          item.status = 'CONFLITO'; item.resultado = conflicts.get(id); item.motivo = 'Outro conferente movimentou este lote.';
        } else if (rejected.has(id)) {
          item.status = 'REJEITADA'; item.resultado = rejected.get(id).resultado || {}; item.motivo = rejected.get(id).motivo || 'Operação rejeitada.';
        } else {
          continue; // sem confirmação: permanece pendente
        }
        item.atualizado_em = new Date().toISOString();
        await queuePut(item);
        finalizados.push({ id: item.id, tipo: item.tipo, status: item.status, resultado: item.resultado || {}, motivo: item.motivo || '' });
      }
      emitQueueEvent('infinity:sync-finished', {
        accepted: finalizados.filter(x => x.status === 'ACEITA'),
        conflicts: finalizados.filter(x => x.status === 'CONFLITO'),
        rejected: finalizados.filter(x => x.status === 'REJEITADA'),
      });
      // Atualizar a referência completa pode ser mais pesado que confirmar a
      // operação. Fazemos isso depois, sem manter a bolinha presa no spinner.
      setTimeout(() => refreshReference(false), 2500);
    } catch (err) {
      console.warn('[OfflineSync] sync adiado:', err);
    } finally {
      syncing = false;
      await updateStatus();
      if (document.getElementById('offlineSyncModal')?.classList.contains('show')) renderCentral(document.querySelector('.sync-tab.active')?.dataset.status || 'PENDENTE');
    }
  }

  async function updateStatus() {
    const bubble = document.getElementById('offlineSyncBubble');
    if (!bubble) return;
    const all = await queueAll().catch(() => []);
    const actionable = all.filter(x => ['PENDENTE', 'CONFLITO', 'REJEITADA'].includes(x.status));
    let session = await metaGet('session');
    let loggedOut = Boolean(await metaGet('logged_out'));

    // Se a página está online e a sessão Django está válida, renova o token
    // offline antes de considerar a sessão expirada. Isso evita o modal preto
    // aparecer por causa de um token local antigo depois de um login normal.
    if (navigator.onLine && (loggedOut || sessionExpired(session))) {
      const renewed = await ensureSession(true).catch(() => null);
      if (renewed && !sessionExpired(renewed)) session = renewed;
      loggedOut = Boolean(await metaGet('logged_out'));
    }

    const expired = loggedOut || sessionExpired(session);
    bubble.classList.remove('sync-green','sync-yellow','sync-red','sync-black');
    if (expired) bubble.classList.add('sync-black');
    else if ((!navigator.onLine || softOffline) && actionable.length) bubble.classList.add('sync-red');
    else if (actionable.length) bubble.classList.add('sync-yellow');
    else if (!navigator.onLine || softOffline) bubble.classList.add('sync-red');
    else bubble.classList.add('sync-green');
    bubble.classList.toggle('is-syncing', syncing);
    document.getElementById('offlineSyncCount').textContent = actionable.length;
    bubble.title = expired ? 'Sessão expirada. Conecte-se e faça login novamente.' : ((!navigator.onLine || softOffline) ? `${actionable.length} pendência(s) offline` : `${actionable.length} item(ns) para tratar`);

    const sessionBlock = document.getElementById('offlineSessionBlock');
    // Sem internet, uma sessão de 5h expirada bloqueia novas ações. Online,
    // ensureSession() pode renovar silenciosamente pela sessão Django.
    const mustBlock = expired && !navigator.onLine;
    sessionBlock?.classList.toggle('show', mustBlock);
    const pendingHint = document.getElementById('offlineSessionPendingHint');
    if (pendingHint) pendingHint.textContent = actionable.length
      ? `${actionable.length} operação(ões) continuam guardadas neste dispositivo.`
      : 'Nenhuma operação pendente será perdida.';

    if (!actionable.length && navigator.onLine) {
      navigator.serviceWorker?.controller?.postMessage({ type:'PRUNE_OLD_CACHES' });
    }

    const ref = await referenceGet();
    const stale = !ref?.validade_ate || Date.now() > new Date(ref.validade_ate).getTime();
    const banner = document.getElementById('offlineStaleBanner');
    const operationalPath = /^\/(estoque|solicitacoes|kanban)(\/|$)/i.test(location.pathname);
    const pendingCount = all.filter(x => x.status === 'PENDENTE').length;
    if (pendingCount >= CRITICAL_QUEUE) {
      banner.textContent = '🔴 fila muito grande: conecte este dispositivo assim que possível';
      banner.style.display = 'block';
    } else if (pendingCount >= WARN_QUEUE) {
      banner.textContent = '⚠️ muitas operações aguardando sincronização';
      banner.style.display = 'block';
    } else if (!navigator.onLine || softOffline) {
      banner.textContent = '⚠️ DADOS LOCAIS: aguardando confirmação do servidor';
      banner.style.display = 'block';
    } else if (operationalPath && stale) {
      banner.textContent = '⏳ preparando referência offline em segundo plano';
      banner.style.display = 'block';
    } else {
      banner.style.display = 'none';
    }
  }

  function fmtDate(v) {
    if (!v) return '-';
    try { return new Intl.DateTimeFormat('pt-BR', {dateStyle:'short', timeStyle:'short'}).format(new Date(v)); } catch (_) { return v; }
  }

  function pendingAgeWarning(item) {
    if (item.status !== 'PENDENTE') return '';
    const raw = item.criado_local_em || item.recebido_em;
    if (!raw) return '';
    const minutos = Math.max(0, (Date.now() - new Date(raw).getTime()) / 60000);
    if (minutos >= 120) return '<div class="sync-warning" style="background:#fef2f2;color:#991b1b">🔴 Pendência crítica: aguardando sincronização há mais de 2 horas.</div>';
    if (minutos >= 30) return '<div class="sync-warning">⚠️ Pendência antiga: aguardando sincronização há mais de 30 minutos.</div>';
    return '';
  }

  async function fetchServerCentral() {
    if (!navigator.onLine) return { operacoes: [], contadores: {} };
    try {
      const deviceId = await getDeviceId();
      const r = await authFetch(`/api/sync/central/?device_id=${encodeURIComponent(deviceId)}`);
      return r.ok ? await r.json() : { operacoes: [], contadores: {} };
    } catch (_) { return { operacoes: [], contadores: {} }; }
  }

  async function renderCentral(status = 'PENDENTE') {
    const body = document.getElementById('offlineSyncBody');
    if (!body) return;
    body.innerHTML = '<div class="sync-empty">Carregando...</div>';
    const [local, server] = await Promise.all([queueAll(), fetchServerCentral()]);
    const byId = new Map(local.map(x => [String(x.id), x]));
    for (const x of (server.operacoes || [])) {
      const id = String(x.id);
      byId.set(id, { ...(byId.get(id) || {}), ...x });
    }
    const all = [...byId.values()].sort((a,b) => String(b.criado_local_em || b.recebido_em || '').localeCompare(String(a.criado_local_em || a.recebido_em || '')));
    const counts = {PENDENTE:0,CONFLITO:0,REJEITADA:0,ACEITA:0};
    all.forEach(x => { if (counts[x.status] !== undefined) counts[x.status]++; });
    Object.entries(counts).forEach(([k,v]) => { const el=document.querySelector(`[data-count="${k}"]`); if(el) el.textContent=v; });
    const device = await getDeviceId();
    document.getElementById('syncDeviceLabel').textContent = `Dispositivo ${device.slice(0,8)}…`;
    const rows = all.filter(x => x.status === status);
    if (!rows.length) { body.innerHTML = '<div class="sync-empty">Nenhum registro nesta área.</div>'; return; }
    body.innerHTML = rows.map(x => {
      const conflitoId = x.conflito_id || x.resultado?.conflito_id;
      const ctx = x.contexto_conflito || x.resultado?.contexto || {};
      const movimentos = Array.isArray(ctx.movimentos_de_outros) ? ctx.movimentos_de_outros : [];
      const conflitoDetalhes = movimentos.length ? `<div class="sync-meta" style="margin-top:7px"><strong>Alterações encontradas:</strong><br>${movimentos.map(m => `${escapeHtml(m.usuario || 'Outro usuário')} · ${escapeHtml(m.tipo || '')} · ${fmtDate(m.data)}`).join('<br>')}</div>` : '';
      const warning = x.status === 'CONFLITO' ? '<div class="sync-warning">Outro conferente alterou este lote. Mesmo com saldo disponível, a decisão precisa ser confirmada.</div>' : pendingAgeWarning(x);
      const podeAjustar = !['SOLICITACAO_MOVIMENTAR','SOLICITACAO_EMPENHAR','SOLICITACAO_CRIAR'].includes(String(x.tipo || '').toUpperCase());
      const actions = x.status === 'CONFLITO' && conflitoId ? `<div class="sync-actions"><button class="sync-apply" data-conflict="${conflitoId}" data-action="APLICAR">Aplicar mesmo assim</button>${podeAjustar ? `<button class="sync-adjust" data-conflict="${conflitoId}" data-action="AJUSTAR">Ajustar quantidade</button>` : ''}<button class="sync-cancel" data-conflict="${conflitoId}" data-action="CANCELAR">Cancelar pendência</button></div>` : '';
      return `<div class="sync-item">${warning}<div class="sync-item-top"><strong>${escapeHtml(x.tipo || 'OPERAÇÃO')} · ${escapeHtml(x.lote || '-')}</strong><span class="sync-badge">${escapeHtml(x.status)}</span></div><div class="sync-meta">Usuário: ${escapeHtml(x.usuario || '')}<br>Criada: ${fmtDate(x.criado_local_em || x.recebido_em)}${x.motivo ? `<br>${escapeHtml(x.motivo)}`:''}</div>${conflitoDetalhes}${actions}</div>`;
    }).join('');
    body.querySelectorAll('[data-conflict]').forEach(btn => btn.addEventListener('click', resolveConflict));
  }

  function escapeHtml(v) { const d=document.createElement('div'); d.textContent=String(v??''); return d.innerHTML; }

  async function resolveConflict(e) {
    const btn = e.currentTarget;
    const conflictId = btn.dataset.conflict;
    const action = btn.dataset.action;
    let quantidade = null;
    if (action === 'AJUSTAR') {
      quantidade = prompt('Informe a nova quantidade:');
      if (quantidade === null) return;
    } else if (!confirm(action === 'CANCELAR' ? 'Cancelar esta operação pendente?' : 'Aplicar esta operação usando o saldo atual do servidor?')) return;
    btn.disabled = true;
    try {
      const payload = { acao: action };
      if (quantidade !== null) payload.quantidade = quantidade;
      const r = await authFetch(`/api/sync/conflitos/${conflictId}/resolver/`, { method:'POST', body:JSON.stringify(payload) });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) { alert(data.detail || 'Não foi possível resolver o conflito.'); return; }
      const all = await queueAll();
      const local = all.find(x => String(x.resultado?.conflito_id) === String(conflictId));
      if (local) { local.status = action === 'CANCELAR' ? 'CANCELADA' : 'ACEITA'; local.atualizado_em = new Date().toISOString(); await queuePut(local); }
      await refreshReference();
      await updateStatus();
      renderCentral('CONFLITO');
    } finally { btn.disabled = false; }
  }

  async function openCentral() {
    document.getElementById('offlineSyncModal').classList.add('show');
    const current = document.querySelector('.sync-tab.active')?.dataset.status || 'PENDENTE';
    renderCentral(current);
  }

  function blockOfflineUnsupported(message = 'Esta operação exige conexão com a internet.') {
    if (navigator.onLine) return false;
    alert(`🌐 ${message}\n\nOs dados já sincronizados continuam disponíveis offline.`);
    return true;
  }

  async function registerSW() {
    if (!('serviceWorker' in navigator) || location.protocol !== 'https:' && location.hostname !== 'localhost') return;
    try {
      const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      const readyReg = await navigator.serviceWorker.ready;
      const worker = navigator.serviceWorker.controller || readyReg.active || reg.active || reg.waiting;

      // Offline progressivo: armazena a tela que o operador realmente abriu.
      // Não faz mais download de dashboard, estoque, kanban, cargas e várias
      // CDNs em toda navegação.
      const currentUrl = `${location.pathname}${location.search || ''}`;
      const pageCacheKey = `page_cached:${OFFLINE_CACHE_VERSION}:${location.pathname}`;
      const jaSolicitado = await metaGet(pageCacheKey).catch(() => false);
      if (!jaSolicitado && worker) {
        worker.postMessage({ type: 'CACHE_URLS', urls: [currentUrl] });
        await metaSet(pageCacheKey, Date.now()).catch(() => null);
      }
      return reg;
    } catch (e) { console.warn('[PWA] Service Worker:', e); }
  }

  function scheduleReferenceRefresh() {
    if (!navigator.onLine) return;
    const path = location.pathname.toLowerCase();
    if (!(path.startsWith('/estoque') || path.startsWith('/solicitacoes') || path.startsWith('/kanban'))) return;
    const run = () => refreshReference(false);
    if ('requestIdleCallback' in window) {
      requestIdleCallback(run, { timeout: 5000 });
    } else {
      setTimeout(run, 2500);
    }
  }

  function protectLogout() {
    document.querySelectorAll('form[action*="logout"]').forEach(form => {
      form.addEventListener('submit', async e => {
        e.preventDefault();
        const pending = (await queueAll()).filter(x => ['PENDENTE','CONFLITO','REJEITADA'].includes(x.status));
        if (pending.length && !confirm(`Existem ${pending.length} operação(ões) ainda não concluídas neste dispositivo. Elas serão preservadas para seu próximo login online. Deseja sair mesmo assim?`)) return;
        // Logout nunca apaga a fila, mas encerra o direito de continuar
        // trabalhando offline. Um novo login online reativa a sessão de 5h.
        await metaSet('logged_out', true);
        const sess = await metaGet('session');
        if (sess) { sess.expira_em = new Date(0).toISOString(); await metaSet('session', sess); }
        form.submit();
      });
    });
  }


  function protectUnsupportedOffline() {
    document.addEventListener('submit', e => {
      if (navigator.onLine) return;
      const form = e.target;
      if (!(form instanceof HTMLFormElement)) return;
      const hasFiles = [...form.querySelectorAll('input[type="file"]')].some(i => i.files && i.files.length);
      if (hasFiles) {
        e.preventDefault();
        e.stopImmediatePropagation();
        alert('📎 Fotos e anexos exigem conexão com a internet. A operação sem anexo pode continuar quando a tela oferecer modo offline.');
        return;
      }
      const path = location.pathname.toLowerCase();
      if (path.startsWith('/configuracoes') || path.startsWith('/admin')) {
        e.preventDefault();
        e.stopImmediatePropagation();
        alert('🌐 Cadastros e configurações estruturais exigem conexão com a internet. Os dados já sincronizados continuam disponíveis para consulta.');
      }
    }, true);
  }

  window.InfinityOffline = {
    enqueue,
    syncNow,
    refreshReference,
    getReference: referenceGet,
    getLotVersion,
    getLotVersions,
    openCentral,
    blockOfflineUnsupported,
    requireOnline: feature => !blockOfflineUnsupported(`${feature || 'Esta função'} não está disponível offline.`),
    status: updateStatus,
  };

  window.addEventListener('infinity:offline-snapshot', event => {
    const banner = document.getElementById('offlineStaleBanner');
    if (!banner) return;
    banner.textContent = '⚠️ DADOS LOCAIS: aguardando confirmação do servidor';
    banner.style.display = 'block';
    updateStatus();
  });

  window.addEventListener('infinity:server-live', () => {
    const banner = document.getElementById('offlineStaleBanner');
    if (banner) banner.style.display = 'none';
    softOffline = false;
    updateStatus();
  });

  document.addEventListener('DOMContentLoaded', async () => {
    injectUI();
    protectLogout();
    protectUnsupportedOffline();
    await getDeviceId();
    await registerSW();
    if (navigator.onLine) {
      await ensureSession(false);
      // Prioridade para a fila. Referência offline pesada só é atualizada em
      // telas operacionais e quando o navegador estiver ocioso.
      syncNow();
      scheduleReferenceRefresh();
    }
    updateStatus();
  });
  window.addEventListener('online', async () => {
    await ensureSession(true);
    syncNow();
    scheduleReferenceRefresh();
    updateStatus();
  });
  window.addEventListener('offline', updateStatus);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) syncNow(); });
  setInterval(syncNow, SYNC_INTERVAL);
})();
