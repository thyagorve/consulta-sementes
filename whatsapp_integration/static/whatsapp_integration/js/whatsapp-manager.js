// whatsapp_integration/static/whatsapp_integration/js/whatsapp-manager.js
class WhatsAppManager {
    constructor() {
        this.baseUrl = '/whatsapp/api/';
        this.instances = [];
        this.currentInstanceId = null;
        this.qrTimer = null;
        this.checkIntervals = new Map();
        this.init();
    }
    
    init() {
        this.cacheElements();
        this.bindEvents();
        this.loadInstances();
        this.startGlobalUpdates();
        
        // Inicializar status global
        this.updateGlobalStatus();
    }
    
    cacheElements() {
        // Alertas
        this.alertContainer = document.getElementById('alertContainer');
        
        // Formulário
        this.instanceNameInput = document.getElementById('instanceName');
        this.createInstanceBtn = document.getElementById('createInstanceBtn');
        
        // Lista
        this.instanceList = document.getElementById('instanceList');
        this.emptyState = document.getElementById('emptyState');
        
        // Estatísticas
        this.totalInstancesEl = document.getElementById('totalInstances');
        this.connectedInstancesEl = document.getElementById('connectedInstances');
        this.scanningInstancesEl = document.getElementById('scanningInstances');
        this.instancesCountEl = document.getElementById('instancesCount');
        this.lastRefreshEl = document.getElementById('lastRefresh');
        
        // Status global
        this.globalStatusIndicator = document.getElementById('globalStatusIndicator');
        this.globalStatusText = document.getElementById('globalStatusText');
        this.lastUpdateEl = document.getElementById('lastUpdate');
        
        // Botões de ação
        this.refreshBtn = document.getElementById('refreshBtn');
        this.checkAllStatusBtn = document.getElementById('checkAllStatusBtn');
        this.reconnectAllBtn = document.getElementById('reconnectAllBtn');
        
        // Modais
        this.qrModal = new bootstrap.Modal(document.getElementById('qrModal'));
        this.instanceModal = new bootstrap.Modal(document.getElementById('instanceModal'));
        
        // Elementos do modal QR
        this.qrImage = document.getElementById('qrImage');
        this.qrLoading = document.getElementById('qrLoading');
        this.qrPlaceholder = document.getElementById('qrPlaceholder');
        this.qrInstanceName = document.getElementById('qrInstanceName');
        this.qrInstructions = document.getElementById('qrInstructions');
        this.qrTimerBar = document.getElementById('qrTimer');
        this.qrTimeLeft = document.getElementById('qrTimeLeft');
        this.confirmScanBtn = document.getElementById('confirmScanBtn');
        this.newQRBtn = document.getElementById('newQRBtn');
        this.downloadQRBtn = document.getElementById('downloadQRBtn');
        
        // Elementos do modal de detalhes
        this.modalInstanceName = document.getElementById('modalInstanceName');
        this.modalInstanceStatus = document.getElementById('modalInstanceStatus');
        this.modalProfileName = document.getElementById('modalProfileName');
        this.modalCreatedAt = document.getElementById('modalCreatedAt');
        this.modalLastCheck = document.getElementById('modalLastCheck');
        this.modalConnectBtn = document.getElementById('modalConnectBtn');
        this.modalDisconnectBtn = document.getElementById('modalDisconnectBtn');
        this.modalDeleteBtn = document.getElementById('modalDeleteBtn');
        this.modalDeleteWarning = document.getElementById('modalDeleteWarning');
    }
    
    bindEvents() {
        // Criar instância
        if (this.createInstanceBtn) {
            this.createInstanceBtn.addEventListener('click', () => this.createInstance());
        }
        
        if (this.instanceNameInput) {
            this.instanceNameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.createInstance();
            });
        }
        
        // Botões de ação
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => this.loadInstances(true));
        }
        
        if (this.checkAllStatusBtn) {
            this.checkAllStatusBtn.addEventListener('click', () => this.checkAllStatus());
        }
        
        if (this.reconnectAllBtn) {
            this.reconnectAllBtn.addEventListener('click', () => this.reconnectAll());
        }
        
        // Modal QR
        if (this.confirmScanBtn) {
            this.confirmScanBtn.addEventListener('click', () => this.confirmQRScan());
        }
        
        if (this.newQRBtn) {
            this.newQRBtn.addEventListener('click', () => this.generateNewQR());
        }
        
        if (this.downloadQRBtn) {
            this.downloadQRBtn.addEventListener('click', () => this.downloadQRCode());
        }
        
        // Modal detalhes
        if (this.modalConnectBtn) {
            this.modalConnectBtn.addEventListener('click', () => this.connectInstance(this.currentInstanceId));
        }
        
        if (this.modalDisconnectBtn) {
            this.modalDisconnectBtn.addEventListener('click', () => this.disconnectInstance(this.currentInstanceId));
        }
        
        if (this.modalDeleteBtn) {
            this.modalDeleteBtn.addEventListener('click', () => this.deleteInstance(this.currentInstanceId));
        }
        
        // Fechar modais
        document.getElementById('qrModal').addEventListener('hidden.bs.modal', () => {
            this.clearQRTimer();
            this.stopCheckingInstance();
        });
        
        document.getElementById('instanceModal').addEventListener('hidden.bs.modal', () => {
            this.currentInstanceId = null;
        });
    }
    
    async loadInstances(showAlert = false) {
        try {
            if (showAlert) {
                this.showAlert('Atualizando lista...', 'info');
            }
            
            const response = await this.apiRequest('GET', 'instances/');
            
            if (response.success) {
                this.instances = response.instances || [];
                this.renderInstances();
                this.updateStatistics();
                this.updateLastRefresh();
                
                if (showAlert) {
                    this.showAlert('Lista atualizada com sucesso', 'success');
                }
            } else {
                throw new Error(response.error || 'Erro ao carregar instâncias');
            }
        } catch (error) {
            console.error('Erro ao carregar instâncias:', error);
            this.showAlert(error.message || 'Erro ao carregar instâncias', 'error');
            
            // Mostrar estado vazio em caso de erro
            this.showEmptyState();
        }
    }
    
    renderInstances() {
        if (!this.instanceList) return;
        
        if (this.instances.length === 0) {
            this.showEmptyState();
            return;
        }
        
        this.hideEmptyState();
        
        this.instanceList.innerHTML = this.instances.map(instance => `
            <div class="instance-card ${instance.status}" data-instance-id="${instance.id}">
                <div class="instance-header">
                    <div class="instance-info">
                        <h4>
                            <i class="fab fa-whatsapp me-2 text-success"></i>
                            ${instance.instance_name}
                        </h4>
                        <span class="instance-status status-${instance.status}">
                            <span class="status-dot ${instance.status}"></span>
                            ${instance.display_status}
                            ${instance.qr_expired ? ' (Expirado)' : ''}
                        </span>
                    </div>
                    <div class="instance-actions">
                        <button class="btn btn-sm btn-outline-primary view-details-btn" 
                                data-instance-id="${instance.id}"
                                title="Ver detalhes">
                            <i class="fas fa-info-circle"></i>
                        </button>
                        
                        ${instance.can_connect ? `
                            <button class="btn btn-sm btn-success connect-btn" 
                                    data-instance-id="${instance.id}"
                                    ${instance.status === 'scanning_qr' ? 'disabled' : ''}>
                                <i class="fas fa-plug me-1"></i>
                                ${instance.status === 'connected' ? 'Reconectar' : 'Conectar'}
                            </button>
                        ` : ''}
                        
                        ${instance.status === 'connected' ? `
                            <button class="btn btn-sm btn-warning disconnect-btn" 
                                    data-instance-id="${instance.id}">
                                <i class="fas fa-power-off me-1"></i>
                                Desconectar
                            </button>
                        ` : ''}
                    </div>
                </div>
                
                ${instance.profile_name ? `
                    <div class="instance-profile">
                        <i class="fas fa-user-circle"></i>
                        <span>${instance.profile_name}</span>
                    </div>
                ` : ''}
                
                <div class="instance-footer">
                    <small class="text-muted">
                        <i class="far fa-clock me-1"></i>
                        Última verificação: ${this.formatDateTime(instance.last_check)}
                    </small>
                    <small class="text-muted">
                        <i class="far fa-calendar me-1"></i>
                        Criada em: ${this.formatDate(instance.created_at)}
                    </small>
                </div>
            </div>
        `).join('');
        
        // Adicionar event listeners
        this.addInstanceEventListeners();
    }
    
    addInstanceEventListeners() {
        // Botão ver detalhes
        document.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = parseInt(e.target.closest('.view-details-btn').dataset.instanceId);
                this.showInstanceDetails(instanceId);
            });
        });
        
        // Botão conectar
        document.querySelectorAll('.connect-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = parseInt(e.target.closest('.connect-btn').dataset.instanceId);
                this.connectInstance(instanceId);
            });
        });
        
        // Botão desconectar
        document.querySelectorAll('.disconnect-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const instanceId = parseInt(e.target.closest('.disconnect-btn').dataset.instanceId);
                this.disconnectInstance(instanceId);
            });
        });
        
        // Clique no card (exceto nos botões)
        document.querySelectorAll('.instance-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('button')) {
                    const instanceId = parseInt(card.dataset.instanceId);
                    this.showInstanceDetails(instanceId);
                }
            });
        });
    }
    
    showEmptyState() {
        if (this.instanceList) this.instanceList.style.display = 'none';
        if (this.emptyState) this.emptyState.style.display = 'block';
    }
    
    hideEmptyState() {
        if (this.instanceList) this.instanceList.style.display = 'block';
        if (this.emptyState) this.emptyState.style.display = 'none';
    }
    
    updateStatistics() {
        const total = this.instances.length;
        const connected = this.instances.filter(i => i.status === 'connected').length;
        const scanning = this.instances.filter(i => i.status === 'scanning_qr').length;
        
        if (this.totalInstancesEl) this.totalInstancesEl.textContent = total;
        if (this.connectedInstancesEl) this.connectedInstancesEl.textContent = connected;
        if (this.scanningInstancesEl) this.scanningInstancesEl.textContent = scanning;
        if (this.instancesCountEl) this.instancesCountEl.textContent = `${total} instância${total !== 1 ? 's' : ''}`;
    }
    
    updateLastRefresh() {
        if (this.lastRefreshEl) {
            const now = new Date();
            this.lastRefreshEl.textContent = `Última atualização: ${now.toLocaleTimeString()}`;
        }
    }
    
    updateGlobalStatus() {
        if (!this.globalStatusIndicator || !this.globalStatusText) return;
        
        const connected = this.instances.filter(i => i.status === 'connected').length;
        const scanning = this.instances.filter(i => i.status === 'scanning_qr').length;
        
        if (connected > 0) {
            this.globalStatusIndicator.className = 'status-indicator connected';
            this.globalStatusText.textContent = `${connected} conectada(s)`;
        } else if (scanning > 0) {
            this.globalStatusIndicator.className = 'status-indicator scanning';
            this.globalStatusText.textContent = `${scanning} aguardando QR`;
        } else {
            this.globalStatusIndicator.className = 'status-indicator disconnected';
            this.globalStatusText.textContent = 'Desconectado';
        }
        
        if (this.lastUpdateEl) {
            this.lastUpdateEl.innerHTML = `<i class="far fa-clock me-1"></i> ${new Date().toLocaleTimeString()}`;
        }
    }
    
    async createInstance() {
        const instanceName = this.instanceNameInput?.value.trim();
        
        if (!instanceName) {
            this.showAlert('Digite um nome para a instância', 'error');
            return;
        }
        
        if (!/^[a-zA-Z0-9_]+$/.test(instanceName)) {
            this.showAlert('Use apenas letras, números e underscore (_)', 'error');
            return;
        }
        
        const originalText = this.createInstanceBtn.innerHTML;
        this.createInstanceBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Criando...';
        this.createInstanceBtn.disabled = true;
        
        try {
            const response = await this.apiRequest('POST', 'instances/', {
                instance_name: instanceName
            });
            
            if (response.success) {
                this.showAlert(response.message || 'Instância criada com sucesso!', 'success');
                this.instanceNameInput.value = '';
                await this.loadInstances();
                
                // Mostrar QR Code automaticamente
                if (response.instance) {
                    setTimeout(() => {
                        this.connectInstance(response.instance.id);
                    }, 1000);
                }
            } else {
                throw new Error(response.error || 'Erro ao criar instância');
            }
        } catch (error) {
            console.error('Erro ao criar instância:', error);
            this.showAlert(error.message || 'Erro ao criar instância', 'error');
        } finally {
            this.createInstanceBtn.innerHTML = originalText;
            this.createInstanceBtn.disabled = false;
        }
    }
    
    async connectInstance(instanceId) {
        try {
            // Mostrar modal de QR
            this.showQRModal(instanceId);
            
            const response = await this.apiRequest('POST', `instances/${instanceId}/connect/`);
            
            if (response.success) {
                if (response.status === 'connected') {
                    this.showAlert(`Conectado como: ${response.profile_name}`, 'success');
                    this.qrModal.hide();
                    await this.loadInstances();
                } else if (response.status === 'scanning') {
                    this.showQRCode(response.qr_data, response.instance_name);
                    this.startQRTimer(response.qr_expires_at);
                    this.startCheckingInstance(instanceId);
                }
            } else {
                throw new Error(response.error || 'Erro ao conectar');
            }
        } catch (error) {
            console.error('Erro ao conectar:', error);
            this.showAlert(error.message || 'Erro ao conectar', 'error');
            this.hideQRLoading();
        }
    }
    
    async disconnectInstance(instanceId) {
        if (!(await window.AppUI.confirm('Tem certeza que deseja desconectar esta instância?', {title:'Desconectar WhatsApp'}))) {
            return;
        }
        
        try {
            const response = await this.apiRequest('DELETE', `instances/${instanceId}/disconnect/`);
            
            if (response.success) {
                this.showAlert(response.message || 'Instância desconectada', 'success');
                await this.loadInstances();
                this.instanceModal.hide();
            } else {
                throw new Error(response.error || 'Erro ao desconectar');
            }
        } catch (error) {
            console.error('Erro ao desconectar:', error);
            this.showAlert(error.message || 'Erro ao desconectar', 'error');
        }
    }
    
    async deleteInstance(instanceId) {
        if (!(await window.AppUI.confirm('ATENÇÃO: Esta ação irá deletar permanentemente a instância e todas as configurações associadas. Tem certeza?', {title:'Excluir instância', danger:true, confirmText:'Excluir'}))) {
            return;
        }
        
        try {
            const response = await this.apiRequest('DELETE', `instances/${instanceId}/`);
            
            if (response.success) {
                this.showAlert(response.message || 'Instância deletada com sucesso', 'success');
                await this.loadInstances();
                this.instanceModal.hide();
            } else {
                throw new Error(response.error || 'Erro ao deletar instância');
            }
        } catch (error) {
            console.error('Erro ao deletar:', error);
            this.showAlert(error.message || 'Erro ao deletar instância', 'error');
        }
    }
    
    async showInstanceDetails(instanceId) {
        const instance = this.instances.find(i => i.id === instanceId);
        if (!instance) return;
        
        this.currentInstanceId = instanceId;
        
        // Preencher modal
        this.modalInstanceName.textContent = instance.instance_name;
        this.modalInstanceStatus.textContent = instance.display_status;
        this.modalInstanceStatus.className = `badge bg-${this.getStatusColor(instance.status)}`;
        this.modalProfileName.textContent = instance.profile_name || 'Não conectado';
        this.modalCreatedAt.textContent = this.formatDateTime(instance.created_at);
        this.modalLastCheck.textContent = this.formatDateTime(instance.last_check);
        
        // Configurar botões
        this.modalConnectBtn.disabled = !instance.can_connect;
        this.modalConnectBtn.innerHTML = instance.status === 'connected' 
            ? '<i class="fas fa-redo me-1"></i> Reconectar' 
            : '<i class="fas fa-plug me-1"></i> Conectar';
        
        this.modalDisconnectBtn.disabled = instance.status !== 'connected';
        
        // Mostrar/ocultar aviso de deleção
        this.modalDeleteWarning.style.display = 'none';
        this.modalDeleteBtn.addEventListener('mouseenter', () => {
            this.modalDeleteWarning.style.display = 'block';
        });
        this.modalDeleteBtn.addEventListener('mouseleave', () => {
            this.modalDeleteWarning.style.display = 'none';
        });
        
        // Mostrar modal
        this.instanceModal.show();
    }
    
    showQRModal(instanceId) {
        const instance = this.instances.find(i => i.id === instanceId);
        if (!instance) return;
        
        this.currentInstanceId = instanceId;
        
        // Resetar modal
        this.qrImage.style.display = 'none';
        this.qrPlaceholder.style.display = 'block';
        this.qrLoading.style.display = 'block';
        this.qrInstanceName.textContent = `Instância: ${instance.instance_name}`;
        this.qrInstructions.textContent = 'Gerando QR Code...';
        
        // Mostrar modal
        this.qrModal.show();
    }
    
    showQRCode(qrData, instanceName) {
        this.hideQRLoading();
        
        if (qrData.includes('base64')) {
            this.qrImage.src = qrData;
        } else if (qrData.includes('data:image')) {
            this.qrImage.src = qrData;
        } else {
            this.qrImage.src = `data:image/png;base64,${qrData}`;
        }
        
        this.qrImage.style.display = 'block';
        this.qrInstructions.textContent = 'Escaneie este código com seu WhatsApp';
    }
    
    hideQRLoading() {
        this.qrLoading.style.display = 'none';
        this.qrPlaceholder.style.display = 'none';
    }
    
    startQRTimer(expiresAt) {
        this.clearQRTimer();
        
        const expires = new Date(expiresAt);
        const updateTimer = () => {
            const now = new Date();
            const diff = expires - now;
            
            if (diff <= 0) {
                this.qrTimerBar.style.width = '0%';
                this.qrTimeLeft.textContent = 'Expirado!';
                this.clearQRTimer();
                return;
            }
            
            const minutes = Math.floor(diff / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            const percent = (diff / (5 * 60 * 1000)) * 100;
            
            this.qrTimerBar.style.width = `${percent}%`;
            this.qrTimeLeft.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            // Mudar cor conforme expira
            if (percent < 30) {
                this.qrTimerBar.className = 'progress-bar bg-danger';
            } else if (percent < 60) {
                this.qrTimerBar.className = 'progress-bar bg-warning';
            }
        };
        
        updateTimer();
        this.qrTimer = setInterval(updateTimer, 1000);
    }
    
    clearQRTimer() {
        if (this.qrTimer) {
            clearInterval(this.qrTimer);
            this.qrTimer = null;
        }
    }
    
    async confirmQRScan() {
        if (!this.currentInstanceId) return;
        
        try {
            const response = await this.apiRequest('GET', `instances/${this.currentInstanceId}/status/`);
            
            if (response.success && response.connected) {
                this.showAlert('WhatsApp conectado com sucesso!', 'success');
                this.qrModal.hide();
                await this.loadInstances();
            } else {
                this.showAlert('Ainda não conectado. Continue aguardando ou gere um novo QR.', 'warning');
            }
        } catch (error) {
            console.error('Erro ao verificar conexão:', error);
        }
    }
    
    async generateNewQR() {
        if (!this.currentInstanceId) return;
        
        if (!(await window.AppUI.confirm('Gerar um novo QR Code? O anterior será invalidado.', {title:'Novo QR Code'}))) {
            return;
        }
        
        await this.connectInstance(this.currentInstanceId);
    }
    
    downloadQRCode() {
        if (!this.qrImage.src) {
            this.showAlert('Nenhum QR Code para baixar', 'warning');
            return;
        }
        
        const link = document.createElement('a');
        link.href = this.qrImage.src;
        link.download = `whatsapp-qr-${this.currentInstanceId}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showAlert('QR Code baixado com sucesso', 'success');
    }
    
    startCheckingInstance(instanceId) {
        this.stopCheckingInstance(instanceId);
        
        const checkInterval = setInterval(async () => {
            try {
                const response = await this.apiRequest('GET', `instances/${instanceId}/status/`);
                
                if (response.success && response.connected) {
                    this.showAlert('WhatsApp conectado com sucesso!', 'success');
                    this.qrModal.hide();
                    this.stopCheckingInstance(instanceId);
                    await this.loadInstances();
                }
            } catch (error) {
                // Ignorar erros temporários
            }
        }, 3000);
        
        this.checkIntervals.set(instanceId, checkInterval);
        
        // Parar após 5 minutos
        setTimeout(() => {
            this.stopCheckingInstance(instanceId);
        }, 300000);
    }
    
    stopCheckingInstance(instanceId = null) {
        if (instanceId) {
            const interval = this.checkIntervals.get(instanceId);
            if (interval) {
                clearInterval(interval);
                this.checkIntervals.delete(instanceId);
            }
        } else {
            this.checkIntervals.forEach((interval, id) => {
                clearInterval(interval);
            });
            this.checkIntervals.clear();
        }
    }
    
    async checkAllStatus() {
        this.showAlert('Verificando status de todas as instâncias...', 'info');
        
        try {
            await this.loadInstances();
            this.showAlert('Status verificado com sucesso', 'success');
        } catch (error) {
            this.showAlert('Erro ao verificar status', 'error');
        }
    }
    
    async reconnectAll() {
        const disconnected = this.instances.filter(i => i.status === 'disconnected' && i.can_connect);
        
        if (disconnected.length === 0) {
            this.showAlert('Nenhuma instância desconectada para reconectar', 'info');
            return;
        }
        
        if (!(await window.AppUI.confirm(`Reconectar ${disconnected.length} instância(s) desconectada(s)?`, {title:'Reconectar instâncias'}))) {
            return;
        }
        
        this.showAlert(`Reconectando ${disconnected.length} instância(s)...`, 'info');
        
        for (const instance of disconnected) {
            try {
                await this.connectInstance(instance.id);
                await new Promise(resolve => setTimeout(resolve, 1000)); // Delay entre conexões
            } catch (error) {
                console.error(`Erro ao reconectar instância ${instance.instance_name}:`, error);
            }
        }
        
        await this.loadInstances();
        this.showAlert('Reconexão concluída', 'success');
    }
    
    startGlobalUpdates() {
        // Atualizar a cada 30 segundos
        setInterval(() => {
            this.updateGlobalStatus();
        }, 30000);
        
        // Verificar instâncias scanning a cada 10 segundos
        setInterval(() => {
            const scanningInstances = this.instances.filter(i => i.status === 'scanning_qr');
            scanningInstances.forEach(instance => {
                this.apiRequest('GET', `instances/${instance.id}/status/`).then(response => {
                    if (response.success && response.connected) {
                        this.showAlert(`Instância ${instance.instance_name} conectada!`, 'success');
                        this.loadInstances();
                    }
                }).catch(() => {});
            });
        }, 10000);
    }
    
    async apiRequest(method, endpoint, data = null) {
        const url = this.baseUrl + endpoint;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            credentials: 'same-origin'
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                window.location.reload(); // Redirecionar para login
                throw new Error('Sessão expirada');
            }
            
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Erro ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        return cookieValue;
    }
    
    showAlert(message, type = 'info') {
        if (!this.alertContainer) {
            return;
        }
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="fas fa-${this.getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Limitar a 3 alertas
        if (this.alertContainer.children.length >= 3) {
            this.alertContainer.removeChild(this.alertContainer.firstChild);
        }
        
        this.alertContainer.appendChild(alert);
        
        // Auto-remover após 5 segundos
        setTimeout(() => {
            if (alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 150);
            }
        }, 5000);
    }
    
    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    getStatusColor(status) {
        const colors = {
            'connected': 'success',
            'scanning_qr': 'warning',
            'disconnected': 'danger',
            'created': 'info',
            'error': 'dark'
        };
        return colors[status] || 'secondary';
    }
    
    formatDateTime(dateString) {
        if (!dateString) return '--';
        const date = new Date(dateString);
        return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR');
    }
    
    formatDate(dateString) {
        if (!dateString) return '--';
        return new Date(dateString).toLocaleDateString('pt-BR');
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.whatsappManager = new WhatsAppManager();
});