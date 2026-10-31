/**
 * AquaGuard AI — Sensor Health Monitoring Dashboard Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const kpiTotal = document.getElementById('kpi-total');
    const kpiHealthy = document.getElementById('kpi-healthy');
    const kpiOffline = document.getElementById('kpi-offline');
    const kpiFaulty = document.getElementById('kpi-faulty');
    const kpiMaintenance = document.getElementById('kpi-maintenance');
    const sensorTableBody = document.getElementById('sensor-table-body');
    const alertListContainer = document.getElementById('alert-list-container');
    const badgeCritCount = document.getElementById('badge-crit-count');
    const badgeWarnCount = document.getElementById('badge-warn-count');
    const filterZone = document.getElementById('filter-zone');
    const filterHealth = document.getElementById('filter-health');
    const btnRefresh = document.getElementById('btn-refresh');

    // Modals
    const sensorModalBackdrop = document.getElementById('sensor-modal-backdrop');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalSensorTitle = document.getElementById('modal-sensor-title');
    const modalSensorBadge = document.getElementById('modal-sensor-badge');
    const modalSensorContent = document.getElementById('modal-sensor-content');

    const simModalBackdrop = document.getElementById('sim-modal-backdrop');
    const simModalCloseBtn = document.getElementById('sim-modal-close-btn');
    const btnOpenSimModal = document.getElementById('btn-open-sim-modal');
    const simForm = document.getElementById('sim-form');
    const simResultBox = document.getElementById('sim-result-box');

    let allSensors = [];
    let allAlerts = [];

    // Real-time clock
    function updateClock() {
        const now = new Date();
        document.getElementById('clock-display').textContent = now.toISOString().replace('T', ' ').slice(0, 19);
    }
    setInterval(updateClock, 1000);
    updateClock();

    // Fetch and render dashboard state
    async function loadDashboard() {
        try {
            // 1. Fetch Health Summary
            const healthRes = await fetch('/api/v1/sensors/health');
            if (healthRes.ok) {
                const healthData = await healthRes.json();
                kpiTotal.textContent = healthData.total_sensors;
                kpiHealthy.textContent = healthData.healthy_sensors;
                kpiOffline.textContent = healthData.offline_sensors;
                kpiFaulty.textContent = healthData.faulty_sensors;
                kpiMaintenance.textContent = healthData.maintenance_sensors;
            }

            // 2. Fetch Sensor Fleet
            const sensorsRes = await fetch('/api/v1/sensors');
            if (sensorsRes.ok) {
                allSensors = await sensorsRes.json();
                renderSensorTable();
            }

            // 3. Fetch Alerts
            const alertsRes = await fetch('/api/v1/sensors/alerts');
            if (alertsRes.ok) {
                allAlerts = await alertsRes.json();
                renderAlerts();
            }
        } catch (err) {
            console.error('Error fetching sensor telemetry:', err);
        }
    }

    // Render sensor fleet table
    function renderSensorTable() {
        const zoneVal = filterZone.value;
        const healthVal = filterHealth.value;

        const filtered = allSensors.filter(s => {
            const matchZone = !zoneVal || s.zone_id === zoneVal;
            const matchHealth = !healthVal || s.health_status === healthVal;
            return matchZone && matchHealth;
        });

        if (filtered.length === 0) {
            sensorTableBody.innerHTML = `<tr><td colspan="9" class="loading-cell">No sensors matching selected filter criteria.</td></tr>`;
            return;
        }

        sensorTableBody.innerHTML = filtered.map(s => {
            const hClass = `status-${s.health_status.toLowerCase()}`;
            const powerClass = s.power_status === 'ON' ? 'power-on' : 'power-off';
            const connClass = s.connectivity_status === 'CONNECTED' ? 'conn-connected' : 'conn-disconnected';
            const missingBadge = s.consecutive_missing > 0 ? `<span class="badge-status status-warning">${s.consecutive_missing} missed</span>` : `<span style="color:#64748b">0</span>`;
            const lastTime = s.last_reading_timestamp ? s.last_reading_timestamp.slice(11, 16) : '--:--';

            return `
                <tr>
                    <td><span class="sensor-code">${s.sensor_id}</span></td>
                    <td><strong>${s.zone_id}</strong></td>
                    <td><span class="${powerClass}">● ${s.power_status}</span></td>
                    <td><span class="${connClass}">${s.connectivity_status}</span></td>
                    <td><span class="badge-status ${hClass}">${s.health_status}</span></td>
                    <td>
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span>${s.battery_percentage}%</span>
                        </div>
                    </td>
                    <td>${missingBadge}</td>
                    <td><span style="font-family:var(--font-mono); font-size:0.8rem;">${lastTime}</span></td>
                    <td>
                        <button class="btn-detail" onclick="viewSensorDetail('${s.meter_id}')">Inspect</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Render Alert Incident Cards
    function renderAlerts() {
        const criticalActive = allAlerts.filter(a => a.severity === 'Critical' && a.alert_status !== 'RESOLVED').length;
        const warningActive = allAlerts.filter(a => a.severity === 'Warning' && a.alert_status !== 'RESOLVED').length;

        badgeCritCount.textContent = `${criticalActive} Critical`;
        badgeWarnCount.textContent = `${warningActive} Warning`;

        if (allAlerts.length === 0) {
            alertListContainer.innerHTML = `<div class="empty-alerts">No alerts recorded. All sensors operating within normal parameters.</div>`;
            return;
        }

        alertListContainer.innerHTML = allAlerts.map(a => {
            const sevClass = a.severity.toLowerCase();
            const isResolved = a.alert_status === 'RESOLVED';
            const cardClass = isResolved ? 'alert-card resolved' : `alert-card ${sevClass}`;

            const ackButton = (a.alert_status === 'OPEN') 
                ? `<button class="btn-ack" onclick="acknowledgeAlert('${a.alert_id}')">Acknowledge</button>` 
                : `<span style="font-size:0.75rem; color:#f59e0b;">✓ Ack by ${a.acknowledged_by || 'Operator'}</span>`;

            const resButton = !isResolved 
                ? `<button class="btn-res" onclick="resolveAlert('${a.alert_id}')">Resolve Incident</button>` 
                : `<span style="font-size:0.75rem; color:#10b981;">✓ Resolved</span>`;

            return `
                <div class="${cardClass}">
                    <div class="alert-top">
                        <span class="alert-cat-tag">${a.alert_type} (${a.severity})</span>
                        <span class="alert-time">${a.last_detected_timestamp ? a.last_detected_timestamp.slice(11, 19) : ''}</span>
                    </div>
                    <div class="alert-msg">
                        <strong>[${a.meter_id} - ${a.zone_id}]</strong> ${a.alert_message}
                    </div>
                    <div class="alert-rec">
                        💡 <strong>Action:</strong> ${a.recommended_action}
                    </div>
                    <div class="alert-actions">
                        ${ackButton}
                        ${resButton}
                    </div>
                </div>
            `;
        }).join('');
    }

    // View sensor detail modal
    window.viewSensorDetail = async function(meterId) {
        modalSensorTitle.textContent = `Sensor Profile — ${meterId}`;
        modalSensorContent.innerHTML = `<p style="color:var(--text-muted)">Querying sensor history...</p>`;
        sensorModalBackdrop.style.display = 'flex';

        try {
            const res = await fetch(`/api/v1/sensors/${meterId}`);
            if (res.ok) {
                const data = await res.json();
                modalSensorBadge.textContent = data.health_status;
                modalSensorBadge.className = `badge-status status-${data.health_status.toLowerCase()}`;

                modalSensorContent.innerHTML = `
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:16px;">
                        <div style="background:var(--bg-surface); padding:10px; border-radius:8px;">
                            <span style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">Sensor Identity</span>
                            <p style="font-weight:700; font-size:1.1rem; color:#3b82f6;">${data.sensor_id}</p>
                            <span style="font-size:0.8rem; color:var(--text-secondary)">Meter ID: ${data.meter_id} | Zone: ${data.zone_id}</span>
                        </div>
                        <div style="background:var(--bg-surface); padding:10px; border-radius:8px;">
                            <span style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase;">Telemetry Link</span>
                            <p style="font-weight:600; font-size:0.95rem;">Power: ${data.power_status} | Link: ${data.connectivity_status}</p>
                            <span style="font-size:0.8rem; color:var(--text-secondary)">Battery: ${data.battery_percentage}%</span>
                        </div>
                    </div>

                    <div style="background:var(--bg-surface); padding:12px; border-radius:8px; margin-bottom:16px;">
                        <h4 style="font-size:0.85rem; margin-bottom:6px;">Current Operational Status</h4>
                        <p style="font-size:0.85rem; color:var(--text-secondary);">Consecutive Missing Readings: <strong>${data.consecutive_missing}</strong> (${data.consecutive_missing * 5} minutes)</p>
                        <p style="font-size:0.85rem; color:var(--text-secondary);">Consecutive Valid Readings: <strong>${data.consecutive_valid}</strong></p>
                        <p style="font-size:0.85rem; color:var(--text-secondary);">Active Malfunction: <strong>${data.active_fault}</strong></p>
                        <p style="font-size:0.85rem; color:var(--text-secondary);">Last Valid Timestamp: <strong>${data.last_reading_timestamp || 'N/A'}</strong></p>
                    </div>

                    <h4 style="font-size:0.85rem; margin-bottom:8px;">Recent Incident History (${data.alert_history.length})</h4>
                    <div style="display:flex; flex-direction:column; gap:8px;">
                        ${data.alert_history.length === 0 ? '<p style="font-size:0.8rem; color:var(--text-muted)">No recorded incidents for this sensor.</p>' :
                            data.alert_history.map(a => `
                                <div style="background:rgba(0,0,0,0.25); padding:8px 12px; border-radius:6px; font-size:0.8rem; border-left:3px solid #3b82f6;">
                                    <strong>${a.alert_category} (${a.severity})</strong> — ${a.alert_status}<br>
                                    <span style="color:var(--text-muted); font-size:0.75rem;">${a.first_detected_timestamp}</span>
                                </div>
                            `).join('')
                        }
                    </div>
                `;
            }
        } catch (e) {
            modalSensorContent.innerHTML = `<p style="color:#ef4444">Failed to load sensor detail: ${e.message}</p>`;
        }
    };

    // Acknowledge alert
    window.acknowledgeAlert = async function(alertId) {
        try {
            const res = await fetch(`/api/v1/sensors/alerts/${alertId}/acknowledge`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: 'facility_operator' })
            });
            if (res.ok) {
                loadDashboard();
            }
        } catch (err) {
            console.error('Error acknowledging alert:', err);
        }
    };

    // Resolve alert
    window.resolveAlert = async function(alertId) {
        try {
            const res = await fetch(`/api/v1/sensors/alerts/${alertId}/resolve`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resolution_note: 'Resolved via dashboard operator action.' })
            });
            if (res.ok) {
                loadDashboard();
            }
        } catch (err) {
            console.error('Error resolving alert:', err);
        }
    };

    // Scenario Injection Form
    simForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const meterId = document.getElementById('sim-meter-id').value;
        const scenario = document.getElementById('sim-scenario-type').value;
        const intervals = parseInt(document.getElementById('sim-intervals').value);

        simResultBox.style.display = 'block';
        simResultBox.innerHTML = `Injecting ${intervals} interval(s) of scenario '${scenario}' on meter ${meterId}...`;

        let powerStat = 'ON';
        let connStat = 'CONNECTED';
        let recReceived = 1;
        let faultType = 'NONE';
        let maintMode = false;
        let flowVal = 25.0;
        let pressVal = 2.4;

        if (scenario === 'POWER_OFF') {
            powerStat = 'OFF';
            connStat = 'DISCONNECTED';
            recReceived = 0;
            flowVal = null;
            pressVal = null;
        } else if (scenario === 'DISCONNECTED') {
            powerStat = 'ON';
            connStat = 'DISCONNECTED';
            recReceived = 0;
            flowVal = null;
            pressVal = null;
        } else if (scenario === 'MALFUNCTION_STUCK') {
            faultType = 'SENSOR_STUCK';
            flowVal = 18.0;
            pressVal = 2.1;
        } else if (scenario === 'MALFUNCTION_DRIFT') {
            faultType = 'SENSOR_DRIFT';
            flowVal = 85.0;
            pressVal = 0.5;
        } else if (scenario === 'MALFUNCTION_SPIKE') {
            faultType = 'SENSOR_SPIKE';
            flowVal = 190.0;
            pressVal = 5.8;
        } else if (scenario === 'MAINTENANCE') {
            powerStat = 'OFF';
            connStat = 'DISCONNECTED';
            recReceived = 0;
            maintMode = true;
            flowVal = null;
            pressVal = null;
        } else if (scenario === 'RECOVER_HEALTHY') {
            powerStat = 'ON';
            connStat = 'CONNECTED';
            recReceived = 1;
            flowVal = 22.0;
            pressVal = 2.5;
        }

        // Simulate incoming sequential 5-min intervals
        let lastResp = null;
        for (let i = 0; i < intervals; i++) {
            const payload = {
                meter_id: meterId,
                sensor_power_status: powerStat,
                sensor_connectivity_status: connStat,
                reading_received: recReceived,
                sensor_fault_type: faultType,
                maintenance_mode: maintMode,
                inlet_flow_lpm: flowVal,
                pressure_bar: pressVal,
                hour: 14,
                occupancy: 20
            };

            const res = await fetch('/api/v1/telemetry/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                lastResp = await res.json();
            }
        }

        if (lastResp) {
            simResultBox.innerHTML = `
                <span style="color:#10b981; font-weight:700;">Scenario Injected Successfully!</span><br>
                <strong>Layer 1 Sensor Health:</strong> ${lastResp.layer_1_sensor_health.health_status} (Missing: ${lastResp.layer_1_sensor_health.consecutive_missing})<br>
                <strong>Layer 2 Water Intelligence:</strong> ${lastResp.layer_2_water_intelligence.layer_2_water_assessment}<br>
                <strong>Decoupled Rationale:</strong> ${lastResp.layer_2_water_intelligence.rationale}<br>
                <strong>Alerts Generated:</strong> ${lastResp.layer_1_sensor_health.alerts_triggered.length}
            `;
            loadDashboard();
        }
    });

    // Event listeners
    filterZone.addEventListener('change', renderSensorTable);
    filterHealth.addEventListener('change', renderSensorTable);
    btnRefresh.addEventListener('click', loadDashboard);

    btnOpenSimModal.addEventListener('click', () => {
        simModalBackdrop.style.display = 'flex';
        simResultBox.style.display = 'none';
    });
    simModalCloseBtn.addEventListener('click', () => { simModalBackdrop.style.display = 'none'; });
    modalCloseBtn.addEventListener('click', () => { sensorModalBackdrop.style.display = 'none'; });

    window.addEventListener('click', (e) => {
        if (e.target === sensorModalBackdrop) sensorModalBackdrop.style.display = 'none';
        if (e.target === simModalBackdrop) simModalBackdrop.style.display = 'none';
    });

    // Initial load
    loadDashboard();
    // Auto-poll every 10 seconds
    setInterval(loadDashboard, 10000);
});
