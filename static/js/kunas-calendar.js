/**
 * CALENDARIO KUNAS ROBUSTO - JavaScript
 * =====================================
 * Sistema inteligente para gestionar el calendario de precios
 */

class KunasCalendar {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.currentDate = new Date();
        this.selectedDate = null;
        this.priceData = new Map();
        this.historyData = new Map();
        this.isExpanded = false;
        
        // Configuración
        this.options = {
            showHistory: true,
            autoRefresh: false,
            refreshInterval: 30000, // 30 segundos
            propertyId: 9355,
            roomTypeId: 29119,
            ...options
        };
        
        this.init();
        this.loadData();
        
        if (this.options.autoRefresh) {
            this.startAutoRefresh();
        }
    }
    
    init() {
        this.render();
        this.attachEvents();
        console.log('📅 Calendario Kunas inicializado correctamente');
    }
    
    render() {
        const currentMonth = this.currentDate.getMonth();
        const currentYear = this.currentDate.getFullYear();
        const today = new Date();
        
        // Obtener días del mes
        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        
        // Nombres de meses y días
        const monthNames = [
            'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
        ];
        const dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
        
        this.container.innerHTML = `
            <div class="kunas-calendar">
                <div class="kunas-calendar-header">
                    <h3 class="kunas-calendar-title">
                        ${monthNames[currentMonth]} ${currentYear}
                    </h3>
                    <div class="kunas-calendar-nav">
                        <button class="kunas-nav-btn" data-action="prev">‹</button>
                        <button class="kunas-nav-btn" data-action="next">›</button>
                    </div>
                </div>
                
                <div class="kunas-calendar-grid">
                    ${dayNames.map(day => `<div class="kunas-day-header">${day}</div>`).join('')}
                    ${this.renderDays(daysInMonth, startingDayOfWeek, today, currentMonth, currentYear)}
                </div>
                
                <div class="kunas-calendar-stats">
                    <div class="kunas-stat">
                        <span class="kunas-stat-value" id="kunas-total-days">0</span>
                        <span class="kunas-stat-label">Días con precio</span>
                    </div>
                    <div class="kunas-stat">
                        <span class="kunas-stat-value" id="kunas-updated-today">0</span>
                        <span class="kunas-stat-label">Actualizados hoy</span>
                    </div>
                    <div class="kunas-stat">
                        <span class="kunas-stat-value" id="kunas-avg-price">$0</span>
                        <span class="kunas-stat-label">Precio promedio</span>
                    </div>
                </div>
                
                <div class="kunas-calendar-legend">
                    <div class="kunas-legend-item">
                        <div class="kunas-legend-color has-price"></div>
                        <span>Con precio</span>
                    </div>
                    <div class="kunas-legend-item">
                        <div class="kunas-legend-color updated"></div>
                        <span>Actualizado hoy</span>
                    </div>
                    <div class="kunas-legend-item">
                        <div class="kunas-legend-color today"></div>
                        <span>Hoy</span>
                    </div>
                </div>
                
                ${this.options.showHistory ? this.renderHistory() : ''}
            </div>
        `;
        
        this.updateStats();
    }
    
    renderDays(daysInMonth, startingDay, today, currentMonth, currentYear) {
        let daysHTML = '';
        
        // Días vacíos del mes anterior
        for (let i = 0; i < startingDay; i++) {
            daysHTML += '<div class="kunas-day-cell empty"></div>';
        }
        
        // Días del mes actual
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateStr = this.formatDate(date);
            const isToday = date.toDateString() === today.toDateString();
            const priceInfo = this.priceData.get(dateStr);
            const isUpdatedToday = this.isUpdatedToday(dateStr);
            
            let cssClasses = ['kunas-day-cell'];
            if (isToday) cssClasses.push('today');
            if (priceInfo) cssClasses.push('has-price');
            if (isUpdatedToday) cssClasses.push('updated-today');
            
            daysHTML += `
                <div class="${cssClasses.join(' ')}" data-date="${dateStr}">
                    <span class="kunas-day-number">${day}</span>
                    ${priceInfo ? `<span class="kunas-day-price">$${priceInfo.price}</span>` : ''}
                    ${isUpdatedToday ? '<div class="kunas-day-updated"></div>' : ''}
                </div>
            `;
        }
        
        return daysHTML;
    }
    
    renderHistory() {
        return `
            <div class="kunas-history ${this.isExpanded ? 'expanded' : ''}">
                <div class="kunas-history-header" data-action="toggle-history">
                    <span class="kunas-history-title">Historial de actualizaciones</span>
                    <span class="kunas-history-arrow">▼</span>
                </div>
                <div class="kunas-history-content">
                    <div class="kunas-history-list" id="kunas-history-list">
                        ${this.renderHistoryItems()}
                    </div>
                </div>
            </div>
        `;
    }
    
    renderHistoryItems() {
        const sortedHistory = Array.from(this.historyData.entries())
            .sort(([,a], [,b]) => new Date(b.timestamp) - new Date(a.timestamp))
            .slice(0, 10); // Últimas 10 actualizaciones
        
        if (sortedHistory.length === 0) {
            return '<div class="kunas-history-item">No hay historial disponible</div>';
        }
        
        return sortedHistory.map(([date, data]) => `
            <div class="kunas-history-item">
                <span class="kunas-history-date">${this.formatDisplayDate(date)}</span>
                <span class="kunas-history-price">$${data.price}</span>
                <span class="kunas-history-time">${this.formatTime(data.timestamp)}</span>
            </div>
        `).join('');
    }
    
    attachEvents() {
        this.container.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            const date = e.target.closest('.kunas-day-cell')?.dataset.date;
            
            if (action === 'prev') {
                this.previousMonth();
            } else if (action === 'next') {
                this.nextMonth();
            } else if (action === 'toggle-history') {
                this.toggleHistory();
            } else if (date) {
                this.selectDate(date);
            }
        });
    }
    
    previousMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        this.render();
        this.loadData();
    }
    
    nextMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        this.render();
        this.loadData();
    }
    
    toggleHistory() {
        this.isExpanded = !this.isExpanded;
        const historyElement = this.container.querySelector('.kunas-history');
        if (historyElement) {
            historyElement.classList.toggle('expanded', this.isExpanded);
        }
    }
    
    selectDate(dateStr) {
        this.selectedDate = dateStr;
        const priceInfo = this.priceData.get(dateStr);
        
        if (priceInfo) {
            console.log(`📅 Fecha seleccionada: ${dateStr} - Precio: $${priceInfo.price}`);
            // Aquí puedes emitir un evento personalizado o llamar un callback
            this.onDateSelect && this.onDateSelect(dateStr, priceInfo);
        }
    }
    
    async loadData() {
        try {
            console.log('🔄 Cargando datos del calendario...');
            
            // Simular carga de datos desde la API
            const response = await this.fetchPriceData();
            this.updatePriceData(response);
            this.updateStats();
            
            console.log('✅ Datos del calendario cargados correctamente');
        } catch (error) {
            console.error('❌ Error cargando datos del calendario:', error);
        }
    }
    
    async fetchPriceData() {
        try {
            const currentDate = new Date(this.currentDate);
            const year = currentDate.getFullYear();
            const month = currentDate.getMonth() + 1;
            
            console.log(`🌐 Obteniendo datos reales del servidor para ${year}-${String(month).padStart(2, '0')}`);
            
            const response = await fetch(`/api/calendario/?year=${year}&month=${month}&property_id=${this.options.propertyId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log(`✅ Datos recibidos: ${Object.keys(data.prices || {}).length} precios`);
                return this.formatServerData(data);
            } else {
                throw new Error(data.error || 'Error desconocido del servidor');
            }
            
        } catch (error) {
            console.warn(`⚠️ Error obteniendo datos del servidor: ${error.message}`);
            console.log('🔄 Usando datos de demostración...');
            return this.generateMockData();
        }
    }
    
    generateMockData() {
        const data = new Map();
        const historyData = new Map();
        const today = new Date();
        
        // Generar datos de prueba para el mes actual
        for (let i = 1; i <= 30; i++) {
            const date = new Date(this.currentDate.getFullYear(), this.currentDate.getMonth(), i);
            if (date <= today) continue; // Solo fechas futuras
            
            const dateStr = this.formatDate(date);
            const basePrice = 1200 + Math.floor(Math.random() * 800);
            const timestamp = new Date(today.getTime() - Math.random() * 7 * 24 * 60 * 60 * 1000);
            
            data.set(dateStr, {
                price: basePrice.toFixed(2),
                timestamp: timestamp.toISOString(),
                propertyId: this.options.propertyId,
                roomTypeId: this.options.roomTypeId
            });
            
            historyData.set(dateStr, {
                price: basePrice.toFixed(2),
                timestamp: timestamp.toISOString(),
                changeType: 'update'
            });
        }
        
        return { prices: data, history: historyData };
    }
    
    formatServerData(serverResponse) {
        // Convertir respuesta del servidor al formato esperado
        const data = new Map();
        const historyData = new Map();
        
        // Procesar precios
        if (serverResponse.prices) {
            for (const [dateStr, priceInfo] of Object.entries(serverResponse.prices)) {
                data.set(dateStr, {
                    price: priceInfo.price,
                    timestamp: priceInfo.timestamp,
                    propertyId: priceInfo.property_id,
                    roomTypeId: priceInfo.room_type_id,
                    hotelName: priceInfo.hotel_name || 'PatricioRamos'
                });
            }
        }
        
        // Procesar historial
        if (serverResponse.history) {
            for (const [key, historyInfo] of Object.entries(serverResponse.history)) {
                historyData.set(key, {
                    date: historyInfo.date,
                    price: historyInfo.price,
                    timestamp: historyInfo.timestamp,
                    changeType: historyInfo.change_type || 'update',
                    hotelName: historyInfo.hotel_name || 'PatricioRamos'
                });
            }
        }
        
        console.log(`📊 Datos formateados: ${data.size} precios, ${historyData.size} historial`);
        return { prices: data, history: historyData };
    }
    
    updatePriceData(response) {
        this.priceData = response.prices;
        this.historyData = response.history;
        
        // Actualizar el historial en el DOM
        const historyList = document.getElementById('kunas-history-list');
        if (historyList) {
            historyList.innerHTML = this.renderHistoryItems();
        }
    }
    
    updateStats() {
        const totalDaysEl = document.getElementById('kunas-total-days');
        const updatedTodayEl = document.getElementById('kunas-updated-today');
        const avgPriceEl = document.getElementById('kunas-avg-price');
        
        if (!totalDaysEl) return;
        
        const totalDays = this.priceData.size;
        const updatedToday = Array.from(this.priceData.values())
            .filter(data => this.isUpdatedToday(data.timestamp)).length;
        
        const avgPrice = totalDays > 0 ? 
            Array.from(this.priceData.values())
                .reduce((sum, data) => sum + parseFloat(data.price), 0) / totalDays : 0;
        
        totalDaysEl.textContent = totalDays;
        updatedTodayEl.textContent = updatedToday;
        avgPriceEl.textContent = `$${avgPrice.toFixed(0)}`;
    }
    
    startAutoRefresh() {
        setInterval(() => {
            this.loadData();
        }, this.options.refreshInterval);
        console.log(`🔄 Auto-refresh activado cada ${this.options.refreshInterval/1000}s`);
    }
    
    // Utilidades
    formatDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    formatDisplayDate(dateStr) {
        const date = new Date(dateStr);
        return `${date.getDate()}/${date.getMonth() + 1}`;
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }
    
    isUpdatedToday(timestamp) {
        const today = new Date().toDateString();
        const updateDate = new Date(timestamp).toDateString();
        return today === updateDate;
    }
    
    // Métodos públicos para integración
    addPriceData(dateStr, priceData) {
        this.priceData.set(dateStr, priceData);
        this.addToHistory(dateStr, priceData, 'add');
        this.render();
    }
    
    updatePriceData(dateStr, priceData) {
        this.priceData.set(dateStr, priceData);
        this.addToHistory(dateStr, priceData, 'update');
        this.render();
    }
    
    addToHistory(dateStr, priceData, changeType) {
        this.historyData.set(dateStr, {
            ...priceData,
            changeType,
            timestamp: new Date().toISOString()
        });
    }
    
    // Eventos personalizados
    onDateSelect(callback) {
        this.onDateSelect = callback;
    }
    
    onPriceUpdate(callback) {
        this.onPriceUpdate = callback;
    }
}

// Inicialización automática cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Verificar si existe el contenedor del calendario
    const calendarContainer = document.getElementById('kunas-calendar-container');
    if (calendarContainer) {
        window.kunasCalendar = new KunasCalendar('kunas-calendar-container', {
            showHistory: true,
            autoRefresh: true,
            refreshInterval: 30000
        });
        
        console.log('🎉 Calendario Kunas inicializado automáticamente');
    }
});

// Exportar para uso global
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KunasCalendar;
}
window.KunasCalendar = KunasCalendar;
