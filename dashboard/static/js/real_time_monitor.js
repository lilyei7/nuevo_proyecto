/**
 * 📡 MONITOR EN TIEMPO REAL - JAVASCRIPT PURO
 * ===========================================
 * 
 * Sistema de monitoreo que usa polling inteligente
 * para mostrar logs en tiempo real sin WebSockets.
 * Se integra directamente con el servidor Django existente.
 */

class RealTimeMonitor {
    constructor(options = {}) {
        this.options = {
            pollInterval: 2000,  // 2 segundos
            maxLogs: 100,
            autoStart: true,
            logContainer: '#log-container',
            statsContainer: '#stats-container',
            ...options
        };
        
        this.isActive = false;
        this.lastTimestamp = null;
        this.logs = [];
        this.stats = {};
        
        if (this.options.autoStart) {
            this.start();
        }
        
        this.setupUI();
    }
    
    setupUI() {
        // Agregar contenedor de logs si no existe
        if (!document.querySelector(this.options.logContainer)) {
            const container = document.createElement('div');
            container.id = 'log-container';
            container.className = 'log-container';
            document.body.appendChild(container);
        }
        
        // Agregar estilos
        this.addStyles();
        
        // Configurar controles
        this.setupControls();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .log-container {
                background: #1e1e1e;
                color: #ffffff;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                height: 400px;
                overflow-y: auto;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 10px;
                margin: 10px 0;
            }
            
            .log-entry {
                margin: 2px 0;
                padding: 2px 5px;
                border-left: 3px solid #333;
                white-space: pre-wrap;
            }
            
            .log-entry.info { border-color: #17a2b8; color: #17a2b8; }
            .log-entry.success { border-color: #28a745; color: #28a745; }
            .log-entry.warning { border-color: #ffc107; color: #ffc107; }
            .log-entry.error { border-color: #dc3545; color: #dc3545; }
            .log-entry.debug { border-color: #6c757d; color: #6c757d; }
            
            .monitor-controls {
                margin: 10px 0;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            }
            
            .monitor-btn {
                margin: 0 5px;
                padding: 5px 15px;
                border: none;
                border-radius: 3px;
                cursor: pointer;
            }
            
            .monitor-btn.start { background: #28a745; color: white; }
            .monitor-btn.stop { background: #dc3545; color: white; }
            .monitor-btn.clear { background: #6c757d; color: white; }
            .monitor-btn.export { background: #17a2b8; color: white; }
            
            .stats-display {
                display: flex;
                gap: 20px;
                margin: 10px 0;
                padding: 10px;
                background: #e9ecef;
                border-radius: 4px;
            }
            
            .stat-item {
                text-align: center;
            }
            
            .stat-value {
                font-size: 24px;
                font-weight: bold;
                color: #495057;
            }
            
            .stat-label {
                font-size: 12px;
                color: #6c757d;
                text-transform: uppercase;
            }
        `;
        document.head.appendChild(style);
    }
    
    setupControls() {
        const controlsHtml = `
            <div class="monitor-controls">
                <button class="monitor-btn start" onclick="monitor.start()">▶️ Iniciar</button>
                <button class="monitor-btn stop" onclick="monitor.stop()">⏹️ Parar</button>
                <button class="monitor-btn clear" onclick="monitor.clearLogs()">🗑️ Limpiar</button>
                <button class="monitor-btn export" onclick="monitor.exportLogs()">📥 Exportar</button>
                
                <select id="log-level-filter" onchange="monitor.setLogFilter(this.value)">
                    <option value="">Todos los niveles</option>
                    <option value="DEBUG">Debug</option>
                    <option value="INFO">Info</option>
                    <option value="WARNING">Warning</option>
                    <option value="ERROR">Error</option>
                </select>
                
                <label>
                    <input type="checkbox" id="auto-scroll" checked> Auto-scroll
                </label>
            </div>
            
            <div class="stats-display" id="stats-container">
                <div class="stat-item">
                    <div class="stat-value" id="total-logs">0</div>
                    <div class="stat-label">Total Logs</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="error-count">0</div>
                    <div class="stat-label">Errores</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="last-update">--:--</div>
                    <div class="stat-label">Última Actualización</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="connection-status">🔴</div>
                    <div class="stat-label">Estado</div>
                </div>
            </div>
        `;
        
        const container = document.querySelector(this.options.logContainer);
        container.insertAdjacentHTML('beforebegin', controlsHtml);
    }
    
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.updateConnectionStatus('🟢');
        this.poll();
        
        this.addLog('Sistema de monitoreo iniciado', 'info');
    }
    
    stop() {
        this.isActive = false;
        this.updateConnectionStatus('🔴');
        
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
        }
        
        this.addLog('Sistema de monitoreo detenido', 'info');
    }
    
    async poll() {
        if (!this.isActive) return;
        
        try {
            const url = '/dashboard/api/logs/?' + new URLSearchParams({
                limit: this.options.maxLogs,
                since: this.lastTimestamp || ''
            });
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success && data.logs.length > 0) {
                data.logs.forEach(log => this.processLog(log));
                this.lastTimestamp = data.timestamp;
            }
            
            this.updateStats();
            this.updateConnectionStatus('🟢');
            
        } catch (error) {
            console.error('Error polling logs:', error);
            this.updateConnectionStatus('🔴');
            this.addLog(`Error de conexión: ${error.message}`, 'error');
        }
        
        if (this.isActive) {
            this.pollTimer = setTimeout(() => this.poll(), this.options.pollInterval);
        }
    }
    
    processLog(logData) {
        // Filtrar por nivel si está configurado
        const levelFilter = document.getElementById('log-level-filter')?.value;
        if (levelFilter && logData.level !== levelFilter) {
            return;
        }
        
        this.logs.push(logData);
        
        // Mantener límite de logs
        if (this.logs.length > this.options.maxLogs) {
            this.logs.shift();
        }
        
        this.displayLog(logData);
    }
    
    displayLog(logData) {
        const container = document.querySelector(this.options.logContainer);
        
        const logElement = document.createElement('div');
        logElement.className = `log-entry ${logData.level.toLowerCase()}`;
        
        const timestamp = new Date(logData.timestamp).toLocaleTimeString();
        const message = logData.message;
        const module = logData.module || 'system';
        
        logElement.textContent = `[${timestamp}] [${module}] ${message}`;
        
        if (logData.data) {
            const dataElement = document.createElement('pre');
            dataElement.style.marginLeft = '20px';
            dataElement.style.fontSize = '10px';
            dataElement.style.opacity = '0.7';
            dataElement.textContent = JSON.stringify(logData.data, null, 2);
            logElement.appendChild(dataElement);
        }
        
        container.appendChild(logElement);
        
        // Auto-scroll si está habilitado
        if (document.getElementById('auto-scroll')?.checked) {
            container.scrollTop = container.scrollHeight;
        }
        
        // Mantener límite de elementos DOM
        while (container.children.length > this.options.maxLogs) {
            container.removeChild(container.firstChild);
        }
    }
    
    addLog(message, level = 'info', module = 'monitor') {
        const logData = {
            timestamp: new Date().toISOString(),
            level: level.toUpperCase(),
            message: message,
            module: module
        };
        this.processLog(logData);
    }
    
    updateStats() {
        const totalLogs = this.logs.length;
        const errorCount = this.logs.filter(log => log.level === 'ERROR').length;
        const lastUpdate = new Date().toLocaleTimeString();
        
        document.getElementById('total-logs').textContent = totalLogs;
        document.getElementById('error-count').textContent = errorCount;
        document.getElementById('last-update').textContent = lastUpdate;
    }
    
    updateConnectionStatus(status) {
        const element = document.getElementById('connection-status');
        if (element) {
            element.textContent = status;
        }
    }
    
    clearLogs() {
        this.logs = [];
        const container = document.querySelector(this.options.logContainer);
        container.innerHTML = '';
        
        this.addLog('Logs limpiados', 'info');
        this.updateStats();
        
        // Llamar al endpoint para limpiar logs del servidor
        fetch('/dashboard/api/logs/clear/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json'
            }
        });
    }
    
    setLogFilter(level) {
        // Re-renderizar logs con filtro
        const container = document.querySelector(this.options.logContainer);
        container.innerHTML = '';
        
        const filteredLogs = level ? 
            this.logs.filter(log => log.level === level) : 
            this.logs;
            
        filteredLogs.forEach(log => this.displayLog(log));
    }
    
    exportLogs() {
        const data = {
            timestamp: new Date().toISOString(),
            logs: this.logs,
            stats: {
                total: this.logs.length,
                errors: this.logs.filter(log => log.level === 'ERROR').length
            }
        };
        
        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `monitor-logs-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.addLog('Logs exportados', 'info');
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
}

// Inicializar monitor global
window.monitor = new RealTimeMonitor();

// Funciones helper para integración
window.logToMonitor = function(message, level = 'info', module = 'system', data = null) {
    monitor.addLog(message, level, module);
    if (data) {
        monitor.logs[monitor.logs.length - 1].data = data;
    }
};

// Auto-inicializar cuando se carga el DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('📡 Monitor en tiempo real iniciado');
    });
} else {
    console.log('📡 Monitor en tiempo real iniciado');
}
