// Dashboard scoped JS - Version 2025-09-08 20:30
// CORS-free version - no Flask endpoints
(function(){
    console.log('[dashboard] Dashboard JS v2.0 loaded - Flask endpoints disabled');

    function initDashboard() {
        const root = document.querySelector('.dashboard-page');
        console.log('[dashboard] initDashboard() start');
        if(!root) { console.log('[dashboard] no .dashboard-page root found, aborting'); return; }
        // Provide a small function only for dashboard
        window.refreshDashboard = function(){
            // Try to find the container scoped to root, fall back to document-wide search
            let el = root.querySelector('#system-status-container') || document.querySelector('#system-status-container');
            if(el) {
                console.log('[dashboard] initial system-status-container found, innerHTML length', el.innerHTML.length);
                el.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary me-2"></div>Cargando estado del sistema...</div>';
            } else {
                console.log('[dashboard] #system-status-container not found in DOM at start of refresh (root and document)');
            }

            // Fetch stats from the API and update UI
            const apiUrl = '/dashboard/stats/api/';
            console.log('[dashboard] refreshDashboard: fetching', apiUrl);
            fetch(apiUrl, { credentials: 'same-origin' })
                .then(resp => {
                    console.log('[dashboard] fetch response status', resp.status);
                    if(!resp.ok) throw new Error('Network response was not ok: ' + resp.status);
                    return resp.json();
                })
                .then(data => {
                    console.log('[dashboard] api data received', data);

                    // Update quick stat counts if present
                    try {
                        const activeEl = root.querySelector('.status-list .status-item:nth-child(1) .status-count');
                        const inactiveEl = root.querySelector('.status-list .status-item:nth-child(2) .status-count');
                        const pendingEl = root.querySelector('.status-list .status-item:nth-child(3) .status-count');

                        if(data.hotel_status) {
                            if(activeEl) { activeEl.textContent = data.hotel_status.active; console.log('[dashboard] active count updated', data.hotel_status.active); }
                            else console.log('[dashboard] activeEl not found');
                            if(inactiveEl) { inactiveEl.textContent = data.hotel_status.inactive; console.log('[dashboard] inactive count updated', data.hotel_status.inactive); }
                            else console.log('[dashboard] inactiveEl not found');
                            if(pendingEl) { pendingEl.textContent = data.hotel_status.pending; console.log('[dashboard] pending count updated', data.hotel_status.pending); }
                            else console.log('[dashboard] pendingEl not found');
                        } else {
                            console.log('[dashboard] data.hotel_status missing');
                        }
                    } catch (e) {
                        console.warn('[dashboard] Could not update quick stats:', e);
                    }

                    // Build summary HTML
                    const top = data.top_hotels || [];
                    let html = '<div class="small">';
                    html += `<div class="mb-2"><strong>Resumen (últimos ${data.daily_stats ? data.daily_stats.length : ''} días)</strong></div>`;
                    if(top.length) {
                        html += '<ul class="list-unstyled mb-0">';
                        top.forEach(h => {
                            html += `<li><strong>${h.name}</strong> — ${h.success_rate}% éxitos (${h.total_scrapes})</li>`;
                        });
                        html += '</ul>';
                    } else {
                        html += '<div class="text-muted">No hay datos de hoteles destacados.</div>';
                    }
                    html += '</div>';

                    // Try to update existing container or the card body; fall back to quick-actions
                    el = root.querySelector('#system-status-container') || document.querySelector('#system-status-container');
                    if(el) {
                        console.log('[dashboard] updating system-status-container');
                        // aggressive cleanup: remove any spinner elements or leftover loading text
                        const spinners = el.querySelectorAll('.spinner-border');
                        spinners.forEach(s=> s.remove());
                        // remove any lines that contain 'Cargando' to avoid duplicates
                        Array.from(el.querySelectorAll('div,span')).forEach(n=>{
                            if(n.textContent && n.textContent.trim().toLowerCase().includes('cargando')) n.remove();
                        });
                        el.innerHTML = html;
                        console.log('[dashboard] system-status-container updated; new innerHTML length', el.innerHTML.length);
                    } else {
                        console.log('[dashboard] system-status-container missing — searching for system card');
                        // Find card by header text
                        const cards = root.querySelectorAll('.card');
                        let systemCardBody = null;
                        cards.forEach(card => {
                            const header = card.querySelector('.card-header h5') || card.querySelector('.card-header');
                            if(header && header.textContent && header.textContent.trim().includes('Estado del Sistema')) {
                                systemCardBody = card.querySelector('.card-body');
                            }
                        });

                        if(systemCardBody) {
                            console.log('[dashboard] found system card body, replacing its content');
                            // remove any spinner nodes within the card to avoid visual leftovers
                            const spinners = systemCardBody.querySelectorAll('.spinner-border');
                            spinners.forEach(s=> s.remove());
                            // also remove small loading messages
                            Array.from(systemCardBody.querySelectorAll('div,span')).forEach(n=>{
                                if(n.textContent && n.textContent.trim().toLowerCase().includes('cargando')) n.remove();
                            });
                            systemCardBody.innerHTML = html;
                            console.log('[dashboard] system card body updated');
                        } else {
                            console.log('[dashboard] system card not found — inserting fallback summary under .quick-actions');
                            const quick = root.querySelector('.quick-actions');
                            if(quick) {
                                let fallback = quick.parentElement.querySelector('.dashboard-summary-fallback');
                                if(!fallback) {
                                    fallback = document.createElement('div');
                                    fallback.className = 'dashboard-summary-fallback mt-3';
                                    quick.parentElement.appendChild(fallback);
                                }
                                // clear any spinners in the nearby area
                                const nearbySpinners = quick.parentElement.querySelectorAll('.spinner-border');
                                nearbySpinners.forEach(s=> s.remove());
                                fallback.innerHTML = '<div class="fallback-summary">' + html + '</div>';
                                console.log('[dashboard] fallback summary inserted');
                            } else {
                                console.log('[dashboard] .quick-actions not found; cannot insert fallback summary');
                            }
                        }

                        // Hide global loading overlay if present
                        const overlay = document.getElementById('loading-overlay');
                        if(overlay) {
                            overlay.classList.add('d-none');
                            overlay.style.display = 'none';
                            console.log('[dashboard] loading-overlay hidden');
                        }
                    }
                })
                .catch(err => {
                    console.error('[dashboard] Failed to fetch dashboard stats:', err);
                    if(el) el.innerHTML = '<div class="text-center text-muted py-3">No se pudo cargar el estado del sistema.</div>';
                });
        }
        
        // Delay initial refresh until all assets (CSS/images) are loaded to avoid FOUC
        function startRefreshes() {
            try {
                console.log('[dashboard] starting initial refresh after window.load');
                window.refreshDashboard();
            } catch (e) {
                console.warn('[dashboard] refreshDashboard failed on start', e);
            }

            // Periodic refresh every 60 seconds
            setInterval(() => {
                console.log('[dashboard] periodic refresh triggered');
                try { window.refreshDashboard(); } catch(e){ console.warn('[dashboard] periodic refresh error', e); }
            }, 60000);
        }

        if (document.readyState === 'complete') {
            // Already loaded
            startRefreshes();
        } else {
            window.addEventListener('load', startRefreshes);
        }

        // Bulk scrape action (scoped) - invoke central Flask auto-start API
        window.bulkScrape = function(){
            if(!confirm('Iniciar scraping masivo?')) return;
            const btn = root.querySelector('.btn-outline-primary[onclick]');
            if(btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Iniciando...';
            }

            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

            // POST to Django view for bulk scraping
            fetch('/hotels/bulk/scrape/', { 
                method: 'POST', 
                credentials: 'same-origin', 
                headers: { 
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: '' // Empty body for bulk scrape of all hotels
            })
            .then(response => {
                // Don't follow redirects automatically for AJAX requests
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    alert(`✅ ${data.message}\n\nHoteles en proceso: ${data.hotels_count}\n\nRevisa el Monitor en Vivo para ver el progreso.`);
                } else if (data.error) {
                    alert(`❌ Error: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Django bulk-scrape error:', error);
                alert('❌ No se pudo iniciar scraping masivo. Revisa la consola para más detalles.');
            })
            .finally(() => {
                if (btn) { 
                    btn.disabled = false; 
                    btn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Scraping Masivo'; 
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }
})();
