// Main application module
//app.js
const app = {
    // State
    isConnected: false,
    refreshInterval: null,  // 
    refreshCountdown: 30,
    currentProfile: '',
    currentRegion: '',
    instances: [],
    connections: [],
    awsAccountId: null,  // Add AWS account ID state 
    // Cached DOM elements
    elements: {},
    
    // Bootstrap components
    modals: {},
    toasts: {},

    preferences: {
        startPort: 60000,
        endPort: 60100,
        logLevel: 'INFO'
    },
    // Initialize application
    async init() {
        console.log('Initializing application...');
        try {
            this.cacheElements();
            this.initializeComponents();
            this.setupEventListeners();
            await this.loadProfilesAndRegions();
            this.startConnectionMonitoring(); 
            console.log('Application initialized successfully');
        } catch (error) {
            console.error('Error initializing application:', error);
        }

    },

    // Cache DOM elements for better performance
    cacheElements() {
        console.log('Caching DOM elements...');
        this.elements = {
            profileSelect: document.getElementById('profileSelect'),
            regionSelect: document.getElementById('regionSelect'),
            connectBtn: document.getElementById('connectBtn'),
            refreshBtn: document.getElementById('refreshBtn'),
            autoRefreshSwitch: document.getElementById('autoRefreshSwitch'),
            refreshTimer: document.getElementById('refreshTimer'),
            instancesList: document.getElementById('instancesList'),
            connectionsList: document.getElementById('connectionsList'),
            instanceCount: document.getElementById('instanceCount'),
            connectionCount: document.getElementById('connectionCount'),
            loadingOverlay: document.getElementById('loadingOverlay')  // 
        };
    },


    initializeComponents() {
        // Initialize modals
        console.log('Initializing Bootstrap components...');
        if (typeof bootstrap === 'undefined') {
            throw new Error('Bootstrap is not loaded. Please check your dependencies.');
        }
    
        // Check for required modal elements
        const instanceDetailsModal = document.getElementById('instanceDetailsModal');
        const customPortModal = document.getElementById('customPortModal');
        const preferencesModal = document.getElementById('preferencesModal');
    
        // Initialize instance details modal
        if (instanceDetailsModal) {
            this.modals.instanceDetails = new bootstrap.Modal(instanceDetailsModal);
        } else {
            console.warn('Instance details modal element not found');
        }
    
        // Initialize custom port modal
        if (customPortModal) {
            this.modals.customPort = new bootstrap.Modal(customPortModal);
        } else {
            console.warn('Custom port modal element not found');
        }
        // Add this in the initializeComponents function after the startPortForwardingBtn setup
        const modeSelect = document.getElementById('modeSelect');
        if (modeSelect) {
            modeSelect.onchange = () => this.handleModeChange();
        } else {
            console.warn('Mode select element not found');
        }
        
        // Initialize preferences modal
        if (preferencesModal) {
            this.modals.preferences = new bootstrap.Modal(preferencesModal);
        } else {
            console.warn('Preferences modal element not found');
        }
        
        // Setup preferences button
        const preferencesBtn = document.getElementById('preferencesBtn');
        if (preferencesBtn) {
            preferencesBtn.onclick = () => this.showPreferences();
        } else {
            console.warn('Preferences button not found');
        }

        const aboutModal = document.getElementById('aboutModal');
        if (aboutModal) {
            this.modals.about = new bootstrap.Modal(aboutModal);
        } else {
            console.warn('About modal element not found');
        }

        // Setup about button
        const aboutBtn = document.getElementById('aboutBtn');
        if (aboutBtn) {
            aboutBtn.onclick = () => this.showAbout();
        } else {
            console.warn('About button not found');
        }


        // Initialize tooltips
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            try {
                new bootstrap.Tooltip(tooltip);
            } catch (error) {
                console.warn('Failed to initialize tooltip:', error);
            }
        });
    
        // Setup port forwarding button
        const startPortForwardingBtn = document.getElementById('startPortForwardingBtn');
        if (startPortForwardingBtn) {
            startPortForwardingBtn.onclick = () => this.startCustomPortForwarding();
        }
    
        // Setup preferences menu items
        const preferencesMenuItem = document.getElementById('preferencesMenuItem');
        if (preferencesMenuItem) {
            preferencesMenuItem.onclick = () => this.showPreferences();
        } else {
            console.warn('Preferences menu item not found');
        }
    
        // Setup preferences save button
        const savePreferencesBtn = document.getElementById('savePreferencesBtn');
        if (savePreferencesBtn) {
            savePreferencesBtn.onclick = () => this.savePreferences();
        } else {
            console.warn('Save preferences button not found');
        }
    
        // Load saved preferences
        this.loadPreferences();
    },

    showCustomPortModal(instanceId) {
        console.log(`Showing custom port modal for instance ${instanceId}`);
        
        // Store the instance ID
        this.selectedInstanceId = instanceId;
        
        // Safely get and reset the form
        const remotePortInput = document.getElementById('remotePort');
        if (remotePortInput) {
            remotePortInput.value = '80';
        }
        
        // Check if modal exists before showing
        if (this.modals.customPort) {
            this.modals.customPort.show();
        } else {
            console.error('Custom port modal not initialized');
            this.showError('Failed to show modal. Please check the console for details.');
        }
    },

    // Setup event listeners
    setupEventListeners() {
        console.log('Setting up event listeners...');
        this.elements.connectBtn.onclick = () => this.toggleConnection();
        this.elements.refreshBtn.onclick = () => this.refreshData();
        this.elements.autoRefreshSwitch.onchange = (e) => this.toggleAutoRefresh(e);
    },

    // Load profiles and regions

    async loadProfilesAndRegions() {
        console.log('[Profile Loading] Starting to load profiles and regions...');
        try {
            // First attempt to load profiles
            const profilesRes = await fetch('/api/profiles');
            console.log('[Profile Loading] Profile response:', profilesRes);
            
            if (!profilesRes.ok) {
                throw new Error(`Failed to load profiles: ${profilesRes.status}`);
            }
            const profiles = await profilesRes.json();
            console.log('[Profile Loading] Loaded profiles:', profiles);

            // Then load regions
            const regionsRes = await fetch('/api/regions');
            console.log('[Profile Loading] Region response:', regionsRes);
            
            if (!regionsRes.ok) {
                throw new Error(`Failed to load regions: ${regionsRes.status}`);
            }
            const regions = await regionsRes.json();
            console.log('[Profile Loading] Loaded regions:', regions);

            // Update dropdowns only if we have valid data
            if (Array.isArray(profiles)) {
                this.updateSelect(this.elements.profileSelect, profiles);
            } else {
                console.error('[Profile Loading] Invalid profiles data:', profiles);
            }
            
            if (Array.isArray(regions)) {
                this.updateSelect(this.elements.regionSelect, regions);
            } else {
                console.error('[Profile Loading] Invalid regions data:', regions);
            }
        } catch (error) {
            console.error('[Profile Loading] Error loading profiles and regions:', error);
            // Show error to user
            this.showError('Failed to load profiles and regions: ' + error.message);
        }
    },

    // Update select element with options
    updateSelect(select, options) {
        if (!select || !options) return;
        console.log(`Updating select ${select.id} with options:`, options);
        
        select.innerHTML = `<option value="">Select ${select.id.replace('Select', '')}</option>`;
        options.forEach(option => {
            const opt = document.createElement('option');
            opt.value = option;
            opt.textContent = option;
            select.appendChild(opt);
        });
    },

    // Toggle connection state
    async toggleConnection() {
        if (this.isConnected) {
            if (!confirm('Are you sure you want to disconnect?')) return;
            this.disconnect();
            return;
        }

        const profile = this.elements.profileSelect.value;
        const region = this.elements.regionSelect.value;

        if (!profile || !region) {
            this.showError('Please select both profile and region');
            return;
        }

        try {
            this.showLoading();
            const response = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile, region })
            });

            if (!response.ok) throw new Error('Connection failed');
            
            // Get the response data
            const result = await response.json();  
            if (result.status === 'success') {
                this.isConnected = true;
                this.currentProfile = profile;
                this.currentRegion = region;
                this.awsAccountId = result.account_id;  // Store account ID
                // Update UI with account ID and console link
                this.updateAwsAccountDisplay();

                this.elements.connectBtn.innerHTML = '<i class="bi bi-plug fs-5"></i> Disconnect';
                this.elements.connectBtn.classList.replace('btn-success', 'btn-danger');
            
                // Save last used profile/region
                localStorage.setItem('lastProfile', profile);
                localStorage.setItem('lastRegion', region);
            
                await this.loadInstances();
                this.showSuccess('Connected successfully');
            } else {
                throw new Error(result.error || 'Connection failed');
            }
        } catch (error) {
            this.showError('Connection error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    // function to update AWS account display
    updateAwsAccountDisplay() {
        const accountContainer = document.getElementById('accountIdContainer');
        const accountId = document.getElementById('awsAccountId');
        
        if (this.isConnected && this.awsAccountId) {
            // Show account ID
            accountId.textContent = this.awsAccountId;
            // Show the container
            accountContainer.style.display = 'block';
        } else {
            // Hide when disconnected
            accountContainer.style.display = 'none';
            accountId.textContent = '';
        }
    },


    // Disconnect from AWS
    disconnect() {
        this.isConnected = false;
        this.currentProfile = '';
        this.currentRegion = '';
        this.awsAccountId = null; // Clear account ID
        this.instances = [];
        this.connections = [];
        
        this.updateAwsAccountDisplay();
        this.elements.connectBtn.innerHTML = '<i class="bi bi-plug"></i> Connect';
        this.elements.connectBtn.classList.replace('btn-danger', 'btn-success');
        this.elements.instancesList.innerHTML = '';
        this.elements.connectionsList.innerHTML = '';
        this.updateCounters();
        
        if (this.autoRefreshInterval) {
            this.toggleAutoRefresh({ target: { checked: false }});
        }
        
        this.showSuccess('Disconnected successfully');
    },



    
    
    // Load instances
    async loadInstances() {
        if (!this.isConnected) return;
        
        try {
            const response = await fetch('/api/instances');
            if (!response.ok) throw new Error('Failed to load instances');
            
            this.instances = await response.json();
            this.renderInstances();
            this.updateCounters();
        } catch (error) {
            this.showError('Failed to load instances: ' + error.message);
        }
    },

    // Render instances list
    renderInstances() {
        this.elements.instancesList.innerHTML = '';
        
        this.instances.forEach(instance => {
            const card = this.createInstanceCard(instance);
            this.elements.instancesList.appendChild(card);
        });
    },

    // Create instance card
    createInstanceCard(instance) {
        const card = document.createElement('div');
        card.className = `col-md-12 ${instance.has_ssm ? '' : 'non-ssm'}`;
        
        const statusClass = instance.state === 'running' ? 'success' : 'danger';
        
        card.innerHTML = `
                <div class="card instance-card h-100">
                    <div class="card-header d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="mt-2"> 
                                <ul class="list-unstyled">
                                    <li><b>${instance.name}</b></li>
                                    <li><small class="text-muted">${instance.id}</small></li>
                                    <li>
                                        <span class="badge bg-${statusClass} status-badge">${instance.state}</span>
                                        <span class="badge bg-warning status-badge">${instance.type}</span>
                                        <span class="badge bg-info status-badge">${instance.os}</span>
                                        ${instance.has_ssm ? 
                                            '<span class="badge badge-fucsia status-badge ms-1">SSM</span>' : 
                                            '<span class="badge bg-secondary status-badge ms-1">SSM not found</span>'}
                                    </li>
                                <ul>
                            </div>
                        </div>
                        <div>
                            ${this.createActionButtons(instance.id)}
                        </div>
                    </div>
                </div>
        `;
        
        return card;
    },

    // Create action buttons for instance
    createActionButtons(instanceId) {
        return `
            <div class="d-flex justify-content-between mt-3 gap-2">
                ${this.instances.find(i => i.id === instanceId).has_ssm ? `
                    <button class="btn btn-sm btn-dark" onclick="app.startSSH('${instanceId}')">
                        <i class="bi bi-terminal"></i> SSH
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="app.startRDP('${instanceId}')">
                        <i class="bi bi-display"></i> RDP
                    </button>
                    <button class="btn btn-sm btn-purple text-white" onclick="app.showCustomPortModal('${instanceId}')">
                        <i class="bi bi-arrow-left-right"></i> Port
                    </button>
                ` : ''}
                <button class="btn btn-sm btn-ottanio text-white" onclick="app.showInstanceDetails('${instanceId}')">
                    <i class="bi bi-info-circle"></i> Info
                </button>
            </div>
        `;
    },

    // Utility functions
    showLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.remove('d-none');
        }
    },

    hideLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.add('d-none');
        }
    },

    showError(message) {
        this.showToast(message, 'danger');
    },

    showSuccess(message) {
        this.showToast(message, 'success');
    },

    showToast(message, type = 'info') {
        const toastContainer = document.querySelector('.toast-container');
        const toast = document.createElement('div');
        toast.className = `toast align-items-center border-0 bg-${type} text-white`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        toastContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        toast.addEventListener('hidden.bs.toast', () => toast.remove());
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    updateCounters() {
        this.elements.instanceCount.textContent = `${this.instances.length} instances`;
        this.elements.connectionCount.textContent = `${this.connections.length} active`;
    },

    // Connection Management Methods
    async startSSH(instanceId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/ssh/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: this.currentProfile,
                    region: this.currentRegion
                })
            });
    
            if (!response.ok) throw new Error('Failed to start SSH session');
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.addConnection({
                    id: result.connection_id,  // Usa il connection_id dal backend
                    instanceId: instanceId,
                    type: 'SSH',
                    timestamp: new Date(),
                    status: 'active'
                });
                this.showSuccess('SSH session started successfully');
            } else {
                throw new Error(result.error || 'Failed to start SSH session');
            }
        } catch (error) {
            this.showError('SSH connection error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    async startRDP(instanceId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/rdp/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: this.currentProfile,
                    region: this.currentRegion
                })
            });
    
            if (!response.ok) throw new Error('Failed to start RDP session');
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.addConnection({
                    id: result.connection_id,  // Cambiato da this.generateConnectionId()
                    instanceId: instanceId,
                    type: 'RDP',
                    localPort: result.local_port,  // Rinominato da port a local_port
                    remotePort: "3389",  // Aggiunto il remote port esplicito per RDP
                    timestamp: new Date(),
                    status: 'active'
                });
                this.showSuccess(`RDP session started on port ${result.local_port}`);
            } else {
                throw new Error(result.error || 'Failed to start RDP session');
            }
        } catch (error) {
            this.showError('RDP connection error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    showCustomPortModal(instanceId) {
        console.log(`Showing custom port modal for instance ${instanceId}`);
        // Store the instance ID for use when starting the connection
        this.selectedInstanceId = instanceId;
        
        // Reset the form
        document.getElementById('remotePort').value = '80';
        
        // Show the modal
        this.modals.customPort.show();
    },


    async showInstanceDetails(instanceId) {
        console.log(`Showing instance details for ${instanceId}`);
        
        try {
            this.showLoading();
            
            // Fetch instance details from backend
            const response = await fetch(`/api/instance-details/${instanceId}`);
            if (!response.ok) throw new Error('Failed to fetch instance details');
            
            const details = await response.json();
            if (!details) throw new Error('No instance details found');
            
            // Update modal content
            const contentDiv = document.getElementById('instanceDetailsContent');
            contentDiv.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <tbody>
                            ${this.createDetailRow('Instance ID', details.id)}
                            ${this.createDetailRow('Name', details.name)}
                            ${this.createDetailRow('Platform', details.platform)}
                            ${this.createDetailRow('Public IPv4', details.public_ip)}
                            ${this.createDetailRow('Private IPv4', details.private_ip)}
                            ${this.createDetailRow('VPC ID', details.vpc_id)}
                            ${this.createDetailRow('Subnet ID', details.subnet_id)}
                            ${this.createDetailRow('IAM Role', details.iam_role)}
                            ${this.createDetailRow('AMI ID', details.ami_id)}
                            ${this.createDetailRow('SSH Key', details.key_name)}
                            ${this.createDetailRow('Security Groups', details.security_groups)}
                        </tbody>
                    </table>
                    <div class="text-muted small text-center mt-2">
                        Click on any value to copy to clipboard
                    </div>
                </div>
            `;
            
            // Add click handlers for copying
            contentDiv.querySelectorAll('.copy-value').forEach(element => {
                element.addEventListener('click', () => this.copyToClipboard(element.dataset.value));
            });
            
            // Show the modal
            this.modals.instanceDetails.show();
            
        } catch (error) {
            console.error('Error showing instance details:', error);
            this.showError('Failed to load instance details');
        } finally {
            this.hideLoading();
        }
    },
    
    // Helper method to create detail rows
    createDetailRow(label, value) {
        return `
            <tr>
                <td class="fw-bold" style="width: 35%">${label}:</td>
                <td>
                    <span class="copy-value" role="button" data-value="${value}" 
                          style="cursor: pointer" title="Click to copy">
                        ${value}
                    </span>
                </td>
            </tr>
        `;
    },
    
    // Helper method to copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showSuccess('Copied to clipboard');
        } catch (error) {
            console.error('Failed to copy:', error);
            this.showError('Failed to copy to clipboard');
        }
    },




    async startCustomPortForwarding() {
        const remotePort = document.getElementById('remotePort').value;
        const instanceId = this.selectedInstanceId;
    
        if (!remotePort || !instanceId) {
            this.showError('Please specify a remote port');
            return;
        }
    
        try {
            this.showLoading();
            const response = await fetch(`/api/custom-port/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: this.currentProfile,
                    region: this.currentRegion,
                    remote_port: remotePort
                })
            });
    
            if (!response.ok) throw new Error('Failed to start port forwarding');
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.addConnection({
                    id: result.connection_id,  // Usa l'ID generato dal backend
                    instanceId: instanceId,
                    type: 'Custom Port',
                    localPort: result.local_port,
                    remotePort: result.remote_port,
                    timestamp: new Date(),
                    status: 'active'
                });
                this.showSuccess(`Port forwarding started (Local: ${result.local_port}, Remote: ${result.remote_port})`);
                this.modals.customPort.hide();
            } else {
                throw new Error(result.error || 'Failed to start port forwarding');
            }
        } catch (error) {
            this.showError('Port forwarding error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    // Connection Management
    addConnection(connection) {
        this.connections.push(connection);
        this.renderConnections();
        this.updateCounters();
    },

    async terminateConnection(connectionId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/terminate-connection/${connectionId}`, {
                method: 'POST'
            });
    
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to terminate connection');
            }
            
            this.connections = this.connections.filter(c => c.id !== connectionId);
            this.renderConnections();
            this.updateCounters();
            this.showSuccess('Connection terminated successfully');
        } catch (error) {
            this.showError('Failed to terminate connection: ' + error.message);
        } finally {
            this.hideLoading();
        }
    },

    renderConnections() {
        const container = this.elements.connectionsList;
        container.innerHTML = '';

        if (this.connections.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="bi bi-diagram-2 fs-2"></i>
                    <p class="mt-2">No active connections</p>
                </div>
            `;
            return;
        }

        this.connections.forEach(conn => {
            const element = document.createElement('div');
            element.className = 'connection-item';
            
            // Format timestamp
            const timestamp = new Date(conn.timestamp).toLocaleTimeString();
            
            // Create connection info based on type
            let connectionInfo = '';
            if (conn.type === 'RDP' || conn.type === 'Custom Port') {
                connectionInfo = `
                    <div class="text-muted small">
                        Local Port: ${conn.localPort}
                        ${conn.remotePort ? `, Remote Port: ${conn.remotePort}` : ''}
                    </div>
                `;
            }

            element.innerHTML = `
                <!--
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="d-flex align-items-center gap-2">
                            
                            <span class="badge bg-${this.getConnectionTypeColor(conn.type)}">
                                ${conn.type}
                            </span>
                          
                            
                            <div class="text-muted small"><b>ID: ${this.getInstanceName(conn.instanceId)}</b</div>
                            ${connectionInfo}
                            <div class="text-muted small">Started at ${timestamp}</div>
                        </div>
                        
                    </div>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="app.terminateConnection('${conn.id}')">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                -->
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge 
                                ${this.getConnectionTypeColor(conn.type) === 'dark' ? 'bg-dark' : ''} 
                                ${this.getConnectionTypeColor(conn.type) === 'primary' ? 'bg-primary' : ''}" 
                                style="${this.getConnectionTypeColor(conn.type) === '#800080' ? `background-color: #800080;` : ''}">
                                ${conn.type}
                            </span>
                        </div>
                        <div class="text-muted small"><b>ID: ${this.getInstanceName(conn.instanceId)}</b></div>
                        ${connectionInfo}
                        <div class="text-muted small">Started at ${timestamp}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="app.terminateConnection('${conn.id}')">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>

            `;
            
            container.appendChild(element);
        });
    },

    // Utility methods for connections
    getConnectionTypeColor(type) {
        const colors = {
            'SSH': 'dark',
            'RDP': 'primary',
            'Custom Port': '#800080'
        };
        return colors[type] || 'secondary';
    },

    getInstanceName(instanceId) {
        const instance = this.instances.find(i => i.id === instanceId);
        return instance ? instance.name : instanceId;
    },

    generateConnectionId() {
        return 'conn_' + Math.random().toString(36).substr(2, 9);
    },

    // Connection monitoring
    startConnectionMonitoring() {
        setInterval(() => this.checkConnections(), 5000);
    },

    async checkConnections() {
        if (!this.isConnected || this.connections.length === 0) return;
    
        try {
            const response = await fetch('/api/active-connections');
            if (!response.ok) throw new Error('Failed to check connections');
            
            const activeConnections = await response.json();
            const activeIds = new Set(activeConnections.map(c => c.connection_id));
            
            // Rimuovi le connessioni che non sono più attive
            const previousCount = this.connections.length;
            this.connections = this.connections.filter(conn => {
                const isActive = activeIds.has(conn.id);
                if (!isActive) {
                    console.log(`Connection ${conn.id} is no longer active`);
                    this.showToast(`Connection to ${this.getInstanceName(conn.instanceId)} was terminated`, 'warning');
                }
                return isActive;
            });
    
            if (previousCount !== this.connections.length) {
                this.renderConnections();
                this.updateCounters();
            }
        } catch (error) {
            console.error('Error checking connections:', error);
        }
    }


    };

    



    app.refreshData = async function() {
        if (!this.isConnected) return;
    
        try {
            this.showLoading();
    
            // Reload profiles and regions first
            await this.loadProfilesAndRegions();
    
            // Reload instances
            const response = await fetch('/api/refresh', {
                method: 'POST'
            });
    
            if (!response.ok) throw new Error('Refresh failed');
    
            const result = await response.json();
            if (result.status === 'success') {
                this.instances = result.instances;
                this.renderInstances();
                this.updateCounters();
                this.showSuccess('Data refreshed successfully');
            }
        } catch (error) {
            this.showError('Failed to refresh data: ' + error.message);
            this.toggleAutoRefresh(false);  // Stop auto-refresh on error
        } finally {
            this.hideLoading();
        }
    };
    
    app.toggleAutoRefresh = function(enabled) {
        if (enabled && enabled.target) {
            enabled = enabled.target.checked;
        }
        
        console.log('Toggle auto-refresh:', enabled);
        
        if (enabled) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    };
    
    app.startAutoRefresh = function() {
        console.log('Starting auto-refresh');
        this.refreshCountdown = 30;
        this.updateRefreshTimer();
    
        // Clear any existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    
        // Set new interval for countdown and refresh
        this.refreshInterval = setInterval(() => {
            this.refreshCountdown--;
            this.updateRefreshTimer();
    
            if (this.refreshCountdown <= 0) {
                this.refreshData();
                this.refreshCountdown = 30;  // Reset countdown
            }
        }, 1000);
    };
    
    app.stopAutoRefresh = function() {
        console.log('Stopping auto-refresh');
        // Clear the interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    
        // Reset countdown and clear display
        this.refreshCountdown = 0;
        this.elements.refreshTimer.textContent = '';
        this.elements.autoRefreshSwitch.checked = false;
    };

    app.setupEventListeners = function() {
        console.log('Setting up event listeners...');
        this.elements.connectBtn.onclick = () => this.toggleConnection();
        this.elements.refreshBtn.onclick = () => this.refreshData();
        
        // Modifica la gestione dell'evento autoRefreshSwitch
        this.elements.autoRefreshSwitch.onchange = (e) => {
            this.toggleAutoRefresh(e.target.checked);
        };
    };
    
    app.updateRefreshTimer = function() {
        // Only show countdown if auto-refresh is active
        if (this.elements.autoRefreshSwitch.checked && this.refreshCountdown > 0) {
            this.elements.refreshTimer.textContent = `(${this.refreshCountdown}s)`;
        } else {
            this.elements.refreshTimer.textContent = '';
        }
    };
    // Update the showPreferences method in app.js

    /**
     * Applies or removes dark mode by toggling the data-bs-theme attribute on <html>.
     * @param {boolean} enabled - Whether dark mode should be active.
     */
    app.applyDarkMode = function(enabled) {
        document.documentElement.setAttribute('data-bs-theme', enabled ? 'dark' : 'light');
    };

    app.showPreferences = async function() {
        console.log('Showing preferences dialog');

        try {
            // Fetch latest preferences from server
            const response = await fetch('/api/preferences');
            if (!response.ok) throw new Error('Failed to load preferences');

            const prefs = await response.json();

            // Update the form fields with current values
            document.getElementById('startPort').value = prefs.port_range.start;
            document.getElementById('endPort').value = prefs.port_range.end;
            document.getElementById('logLevel').value = prefs.logging.level;
            document.getElementById('darkModeSwitch').checked = prefs.dark_mode === true;

            // Show the modal
            if (this.modals.preferences) {
                this.modals.preferences.show();
            } else {
                console.error('Preferences modal not initialized');
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
            this.showError('Failed to load current preferences');
        }
    };

    // Update the savePreferences method to ensure we're using the correct structure
    app.savePreferences = async function() {
        console.log('Saving preferences');
        try {
            const startPort = parseInt(document.getElementById('startPort').value);
            const endPort = parseInt(document.getElementById('endPort').value);
            const logLevel = document.getElementById('logLevel').value;
            const darkMode = document.getElementById('darkModeSwitch').checked;

            // Validate values
            if (startPort >= endPort) {
                this.showError('Start port must be less than end port');
                return;
            }

            if (startPort < 1024 || endPort > 65535) {
                this.showError('Ports must be between 1024 and 65535');
                return;
            }

            // Create new preferences object matching backend structure
            const newPreferences = {
                port_range: {
                    start: startPort,
                    end: endPort
                },
                logging: {
                    level: logLevel,
                    format: "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
                },
                dark_mode: darkMode
            };

            const response = await fetch('/api/preferences', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newPreferences)
            });

            if (!response.ok) throw new Error('Failed to save preferences');

            // Update local preferences and apply dark mode immediately
            this.preferences = newPreferences;
            this.applyDarkMode(darkMode);

            // Hide modal and show success message
            if (this.modals.preferences) {
                this.modals.preferences.hide();
            }
            this.showSuccess('Preferences saved successfully');

        } catch (error) {
            console.error('Error saving preferences:', error);
            this.showError('Failed to save preferences');
        }
    };

    // Update loadPreferences to match backend structure
    app.loadPreferences = async function() {
        console.log('Loading initial preferences');
        try {
            const response = await fetch('/api/preferences');
            if (!response.ok) throw new Error('Failed to load preferences');

            this.preferences = await response.json();
            console.log('Loaded preferences:', this.preferences);

            // Apply dark mode on startup based on saved preference
            this.applyDarkMode(this.preferences.dark_mode === true);

        } catch (error) {
            console.error('Error loading initial preferences:', error);
            // Use default values if loading fails
            this.preferences = {
                port_range: {
                    start: 60000,
                    end: 60100
                },
                logging: {
                    level: 'INFO',
                    format: "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
                },
                dark_mode: false
            };
        }
    };


    // Handle switching between port forwarding modes
    app.handleModeChange = function() {
        // Get the containers for different modes
        const remotePortContainer = document.getElementById('remotePortContainer');
        const otherHostContainer = document.getElementById('otherHostContainer');
        const modeSelect = document.getElementById('modeSelect');
        
        // Show/hide containers based on selected mode
        if (modeSelect.value === 'local') {
            remotePortContainer.style.display = 'block';
            otherHostContainer.style.display = 'none';
        } else {
            remotePortContainer.style.display = 'none';
            otherHostContainer.style.display = 'block';
        }
    };

    // Custom port forwarding with support for both local and remote host modes
    app.startCustomPortForwarding = async function() {
        // Get the selected mode from the dropdown
        const mode = document.getElementById('modeSelect').value;
        const instanceId = this.selectedInstanceId;
        
        // Add this validation before showing loading
        if (mode === 'local') {
            const remotePort = document.getElementById('remotePort').value;
            if (!remotePort || !instanceId) {
                this.showError('Please specify a remote port');
                return;
            }
        } else {
            const remoteHost = document.getElementById('remoteHost').value;
            const remotePort = document.getElementById('otherRemotePort').value;
            if (!remoteHost || !remotePort || !instanceId) {
                this.showError('Please specify both remote host and port');
                return;
            }
        }
    
        // Show loading BEFORE preparing request data
        this.showLoading();
        
        try {
            let requestData = {
                profile: this.currentProfile,
                region: this.currentRegion,
                mode: mode
            };
    
            // Add appropriate parameters based on mode
            if (mode === 'local') {
                requestData.remote_port = document.getElementById('remotePort').value;
            } else {
                requestData.remote_host = document.getElementById('remoteHost').value;
                requestData.remote_port = document.getElementById('otherRemotePort').value;
            }
    
            const response = await fetch(`/api/custom-port/${instanceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });
    
            if (!response.ok) throw new Error('Failed to start port forwarding');
            const result = await response.json();
            
            if (result.status === 'success') {
                // Create connection object based on mode
                const connectionData = {
                    id: result.connection_id,
                    instanceId: instanceId,
                    type: mode === 'local' ? 'Custom Port' : 'Remote Host Port',
                    localPort: result.local_port,
                    remotePort: result.remote_port,
                    remoteHost: result.remote_host,
                    timestamp: new Date(),
                    status: 'active'
                };
    
                this.addConnection(connectionData);
                
                // Show appropriate success message
                const successMessage = mode === 'local' 
                    ? `Port forwarding started (Local: ${result.local_port}, Remote: ${result.remote_port})`
                    : `Remote host port forwarding started (Local: ${result.local_port}, Remote: ${result.remote_host}:${result.remote_port})`;
                
                this.showSuccess(successMessage);
                this.modals.customPort.hide();
            }
        } catch (error) {
            this.showError('Port forwarding error: ' + error.message);
        } finally {
            this.hideLoading();
        }
    };
    
    // Modifica la funzione renderConnections per gestire meglio le informazioni di connessione
    app.renderConnections = function() {
        const container = this.elements.connectionsList;
        container.innerHTML = '';
    
        if (this.connections.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="bi bi-diagram-2 fs-2"></i>
                    <p class="mt-2">No active connections</p>
                </div>
            `;
            return;
        }
    
        this.connections.forEach(conn => {
            const element = document.createElement('div');
            element.className = 'connection-item';
            
            // Format timestamp
            const timestamp = new Date(conn.timestamp).toLocaleTimeString();
            
            // Create connection info based on type
            let connectionInfo = '';
            if (conn.type === 'RDP' || conn.type === 'Custom Port' || conn.type === 'Remote Host Port') {
                connectionInfo = `
                    <div class="text-muted small">
                        Local Port: ${conn.localPort}
                        ${conn.remotePort ? `, Remote Port: ${conn.remotePort}` : ''}
                        ${conn.remoteHost ? `, Host: ${conn.remoteHost}` : ''}
                    </div>
                `;
            }
    
            element.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge 
                                ${this.getConnectionTypeColor(conn.type) === 'dark' ? 'bg-dark' : ''} 
                                ${this.getConnectionTypeColor(conn.type) === 'primary' ? 'bg-primary' : ''}" 
                                style="${this.getConnectionTypeColor(conn.type) === '#800080' ? `background-color: #800080;` : ''}">
                                ${conn.type}
                            </span>
                        </div>
                        <div class="text-muted small"><b>ID: ${this.getInstanceName(conn.instanceId)}</b></div>
                        ${connectionInfo}
                        <div class="text-muted small">Started at ${timestamp}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="app.terminateConnection('${conn.id}')">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
            `;
            
            container.appendChild(element);
        });
    };
    
    // Aggiorna la funzione getConnectionTypeColor per gestire il nuovo tipo
    app.getConnectionTypeColor = function(type) {
        const colors = {
            'SSH': 'dark',
            'RDP': 'primary',
            'Custom Port': '#800080',
            'Remote Host Port': '#800080'  // Stesso colore del Custom Port
        };
        return colors[type] || 'secondary';
    };

    app.startConnectionMonitoring = function() {
        console.log('Starting connection monitoring');
        // Esegui il check ogni 2 secondi
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
        }
        this.monitoringInterval = setInterval(() => this.checkConnections(), 2000);
    },
    
    app.checkConnections = async function() {
        if (!this.isConnected || this.connections.length === 0) return;
    
        try {
            const response = await fetch('/api/active-connections');
            if (!response.ok) throw new Error('Failed to check connections');
            
            const activeConnections = await response.json();
            const activeIds = new Set(activeConnections.map(c => c.connection_id));
            
            // Rimuovi le connessioni che non sono più attive
            const previousCount = this.connections.length;
            this.connections = this.connections.filter(conn => {
                const isActive = activeIds.has(conn.id);
                if (!isActive) {
                    console.log(`Connection ${conn.id} is no longer active`);
                    this.showToast(`Connection to ${this.getInstanceName(conn.instanceId)} was terminated`, 'warning');
                }
                return isActive;
            });
    
            // Se il numero di connessioni è cambiato, aggiorna l'UI
            if (previousCount !== this.connections.length) {
                this.renderConnections();
                this.updateCounters();
            }
        } catch (error) {
            console.error('Error checking connections:', error);
        }
    },

    /**
     * Shows the About modal and fetches the current app version from the backend.
     * Version is loaded on every open to always reflect the running build.
     */
    app.showAbout = function() {
        if (this.modals.about) {
            // Fetch version from backend and update the version label before showing
            fetch('/api/version')
                .then(response => response.json())
                .then(data => {
                    const el = document.getElementById('aboutVersion');
                    if (el) {
                        el.textContent = `Version ${data.version}`;
                    }
                })
                .catch(() => {
                    const el = document.getElementById('aboutVersion');
                    if (el) el.textContent = 'Version unknown';
                });
            this.modals.about.show();
        } else {
            console.error('About modal not initialized');
        }
    };
    app.showLoading = function() {
        if (this.elements.loadingOverlay) {
            // Se c'è un modal aperto, aggiungi la classe modal-loading
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                modal.classList.add('modal-loading');
            });
            
            this.elements.loadingOverlay.classList.remove('d-none');
        }
    };
    
    app.hideLoading = function() {
        if (this.elements.loadingOverlay) {
            // Rimuovi la classe modal-loading da tutti i modal
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                modal.classList.remove('modal-loading');
            });
            
            this.elements.loadingOverlay.classList.add('d-none');
        }
    };
   
    

// Initialize app when document is ready
document.addEventListener('DOMContentLoaded', () => app.init());

