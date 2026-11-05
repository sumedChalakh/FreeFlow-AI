/**
 * FreeFlow AI — Dashboard Client Controller
 *
 * Lightweight, accessible, zero-dependency controller.
 * Handles in-memory Bearer token management, view routing (Overview vs Providers),
 * diagnostics fetching, provider listing, on-demand connection testing,
 * error resilience, and safe DOM manipulation.
 */

(function () {
  'use strict';

  // State held strictly in page execution memory
  let apiToken = null;
  let isFetching = false;
  let lastFetchTimestamp = null;
  let currentView = 'overview';
  let cachedProviders = [];

  // In-memory probe results: Map<provider_id, { status, latency_ms, error, timestamp }>
  const providerProbeResults = new Map();
  // Set of provider_ids currently being tested to prevent duplicate requests
  const activeProbes = new Set();

  // DOM Elements — Layout & Auth
  const authPanel = document.getElementById('auth-panel');
  const dashboardContent = document.getElementById('dashboard-content');
  const authForm = document.getElementById('auth-form');
  const apiTokenInput = document.getElementById('api-token-input');
  const connectBtn = document.getElementById('connect-btn');
  const authError = document.getElementById('auth-error');
  const authToggleBtn = document.getElementById('auth-toggle-btn');
  const authBtnLabel = document.getElementById('auth-btn-label');

  // Header Elements
  const pageTitle = document.getElementById('page-title');
  const refreshBtn = document.getElementById('refresh-btn');
  const refreshIcon = document.getElementById('refresh-icon');
  const lastUpdatedText = document.getElementById('last-updated-text');
  const statusPill = document.getElementById('gateway-status-pill');
  const statusLabel = document.getElementById('gateway-status-label');

  // Navigation Links
  const navLinkOverview = document.getElementById('nav-link-overview');
  const navLinkProviders = document.getElementById('nav-link-providers');
  const navLinkCatalog = document.getElementById('nav-link-catalog');
  const navLinkProfiles = document.getElementById('nav-link-profiles');
  const navLinkDiagnostics = document.getElementById('nav-link-diagnostics');

  // View Panels
  const overviewView = document.getElementById('overview-view');
  const providersView = document.getElementById('providers-view');
  const catalogView = document.getElementById('catalog-view');
  const profilesView = document.getElementById('profiles-view');
  const diagnosticsView = document.getElementById('diagnostics-view');

  // Catalog View Elements & State
  let cachedCatalog = [];
  let isRefreshingCatalog = false;
  let isFetchingCatalog = false;
  let selectedCatalogProvider = '';

  const refreshCatalogBtn = document.getElementById('refresh-catalog-btn');
  const refreshCatalogIcon = document.getElementById('refresh-catalog-icon');
  const refreshCatalogBtnText = document.getElementById('refresh-catalog-btn-text');
  const catalogProviderFilter = document.getElementById('catalog-provider-filter');
  const catalogCardsContainer = document.getElementById('catalog-cards-container');
  const catalogEmptyState = document.getElementById('catalog-empty-state');
  const catalogErrorAlert = document.getElementById('catalog-error-alert');
  const catalogRefreshAlert = document.getElementById('catalog-refresh-alert');

  // Routing Profiles View Elements & State
  let cachedProfiles = [];
  let isFetchingProfiles = false;
  const refreshProfilesBtn = document.getElementById('refresh-profiles-btn');
  const refreshProfilesIcon = document.getElementById('refresh-profiles-icon');
  const profilesCardsContainer = document.getElementById('profiles-cards-container');
  const profilesEmptyState = document.getElementById('profiles-empty-state');
  const profilesErrorAlert = document.getElementById('profiles-error-alert');

  // Diagnostics View Elements & State
  let cachedDiagnostics = null;
  let isFetchingDiagnostics = false;
  const refreshDiagnosticsBtn = document.getElementById('refresh-diagnostics-btn');
  const refreshDiagnosticsIcon = document.getElementById('refresh-diagnostics-icon');
  const diagnosticsContentContainer = document.getElementById('diagnostics-content-container');
  const diagnosticsErrorAlert = document.getElementById('diagnostics-error-alert');
  const diagnosticsDegradedAlert = document.getElementById('diagnostics-degraded-alert');

  // Overview View Elements
  const degradedBanner = document.getElementById('degraded-banner');
  const degradedReason = document.getElementById('degraded-reason');
  const cardGatewayVal = document.getElementById('card-gateway-value');
  const cardGatewayBadge = document.getElementById('card-gateway-badge');
  const cardGatewaySub = document.getElementById('card-gateway-sub');
  const cardDbVal = document.getElementById('card-db-value');
  const cardDbBadge = document.getElementById('card-db-badge');
  const cardDbSub = document.getElementById('card-db-sub');
  const cardProvVal = document.getElementById('card-providers-value');
  const cardProvBadge = document.getElementById('card-providers-badge');
  const cardProvSub = document.getElementById('card-providers-sub');
  const cardCatVal = document.getElementById('card-catalog-value');
  const cardCatBadge = document.getElementById('card-catalog-badge');
  const cardCatSub = document.getElementById('card-catalog-sub');
  const cardProfVal = document.getElementById('card-profiles-value');
  const cardProfSub = document.getElementById('card-profiles-sub');
  const providersTableBody = document.getElementById('providers-table-body');

  // Providers View Elements
  const refreshProvidersBtn = document.getElementById('refresh-providers-btn');
  const refreshProvidersIcon = document.getElementById('refresh-providers-icon');
  const providersCardsContainer = document.getElementById('providers-cards-container');
  const providersEmptyState = document.getElementById('providers-empty-state');
  const providersErrorAlert = document.getElementById('providers-error-alert');

  /**
   * Set Status Pill UI state
   */
  function setStatus(state, label) {
    statusPill.className = 'status-pill';
    if (state === 'healthy') {
      statusPill.classList.add('status-healthy');
    } else if (state === 'degraded') {
      statusPill.classList.add('status-degraded');
    } else if (state === 'unavailable') {
      statusPill.classList.add('status-unavailable');
    } else {
      statusPill.classList.add('status-unknown');
    }
    statusLabel.textContent = label;
  }

  /**
   * Switch between Views ('overview', 'providers', 'catalog', 'profiles', 'diagnostics')
   */
  function switchView(viewName) {
    let targetView = 'overview';
    if (viewName === 'providers') targetView = 'providers';
    else if (viewName === 'catalog') targetView = 'catalog';
    else if (viewName === 'profiles' || viewName === 'routing') targetView = 'profiles';
    else if (viewName === 'diagnostics') targetView = 'diagnostics';

    // Prevent redundant rendering when already on target view and hash is synchronized
    if (currentView === targetView && window.location.hash === '#' + targetView) {
      return;
    }
    currentView = targetView;

    // Reset all navigation link active states
    [navLinkOverview, navLinkProviders, navLinkCatalog, navLinkProfiles, navLinkDiagnostics].forEach(link => {
      if (link) {
        link.classList.remove('active');
        link.removeAttribute('aria-current');
      }
    });

    // Hide all view panels
    if (overviewView) overviewView.style.display = 'none';
    if (providersView) providersView.style.display = 'none';
    if (catalogView) catalogView.style.display = 'none';
    if (profilesView) profilesView.style.display = 'none';
    if (diagnosticsView) diagnosticsView.style.display = 'none';

    if (targetView === 'providers') {
      if (navLinkProviders) {
        navLinkProviders.classList.add('active');
        navLinkProviders.setAttribute('aria-current', 'page');
      }
      pageTitle.textContent = 'Providers';
      if (providersView) providersView.style.display = 'block';
      renderProvidersCards(cachedProviders);
    } else if (targetView === 'catalog') {
      if (navLinkCatalog) {
        navLinkCatalog.classList.add('active');
        navLinkCatalog.setAttribute('aria-current', 'page');
      }
      pageTitle.textContent = 'Model Catalog';
      if (catalogView) catalogView.style.display = 'block';

      // Load catalog models if not already cached and user is authenticated
      if (cachedCatalog.length === 0 && apiToken && !isFetchingCatalog) {
        fetchCatalogData();
      } else {
        renderCatalogCards();
      }
    } else if (targetView === 'profiles') {
      if (navLinkProfiles) {
        navLinkProfiles.classList.add('active');
        navLinkProfiles.setAttribute('aria-current', 'page');
      }
      pageTitle.textContent = 'Routing Profiles';
      if (profilesView) profilesView.style.display = 'block';

      if (cachedProfiles.length === 0 && apiToken && !isFetchingProfiles) {
        fetchProfilesData();
      } else {
        renderProfilesCards();
      }
    } else if (targetView === 'diagnostics') {
      if (navLinkDiagnostics) {
        navLinkDiagnostics.classList.add('active');
        navLinkDiagnostics.setAttribute('aria-current', 'page');
      }
      pageTitle.textContent = 'Diagnostics';
      if (diagnosticsView) diagnosticsView.style.display = 'block';

      if (apiToken && !isFetchingDiagnostics) {
        fetchDiagnosticsData();
      } else if (cachedDiagnostics) {
        renderDiagnostics();
      }
    } else {
      if (navLinkOverview) {
        navLinkOverview.classList.add('active');
        navLinkOverview.setAttribute('aria-current', 'page');
      }
      pageTitle.textContent = 'Overview';
      if (overviewView) overviewView.style.display = 'block';
    }

    if (window.location.hash !== '#' + targetView) {
      window.location.hash = targetView;
    }
  }

  /**
   * Set Disconnected / Connected view state
   */
  function updateAuthState(connected) {
    if (connected) {
      authPanel.style.display = 'none';
      dashboardContent.style.display = 'block';
      authBtnLabel.textContent = 'Disconnect';
      refreshBtn.disabled = false;
      if (refreshProvidersBtn) refreshProvidersBtn.disabled = false;
      if (refreshCatalogBtn) refreshCatalogBtn.disabled = false;
      if (refreshProfilesBtn) refreshProfilesBtn.disabled = false;
      if (refreshDiagnosticsBtn) refreshDiagnosticsBtn.disabled = false;
    } else {
      authPanel.style.display = 'flex';
      dashboardContent.style.display = 'none';
      authBtnLabel.textContent = 'Connect';
      refreshBtn.disabled = true;
      if (refreshProvidersBtn) refreshProvidersBtn.disabled = true;
      if (refreshCatalogBtn) refreshCatalogBtn.disabled = true;
      if (refreshProfilesBtn) refreshProfilesBtn.disabled = true;
      if (refreshDiagnosticsBtn) refreshDiagnosticsBtn.disabled = true;
      setStatus('unknown', 'Disconnected');
    }
  }

  /**
   * Disconnect and purge in-memory token
   */
  function disconnect() {
    apiToken = null;
    cachedProviders = [];
    cachedCatalog = [];
    cachedProfiles = [];
    cachedDiagnostics = null;
    selectedCatalogProvider = '';
    providerProbeResults.clear();
    activeProbes.clear();
    apiTokenInput.value = '';
    authError.style.display = 'none';
    authError.textContent = '';
    if (catalogRefreshAlert) {
      catalogRefreshAlert.style.display = 'none';
      catalogRefreshAlert.textContent = '';
    }
    if (catalogErrorAlert) {
      catalogErrorAlert.style.display = 'none';
      catalogErrorAlert.textContent = '';
    }
    if (profilesErrorAlert) {
      profilesErrorAlert.style.display = 'none';
      profilesErrorAlert.textContent = '';
    }
    if (diagnosticsErrorAlert) {
      diagnosticsErrorAlert.style.display = 'none';
      diagnosticsErrorAlert.textContent = '';
    }
    if (diagnosticsDegradedAlert) {
      diagnosticsDegradedAlert.style.display = 'none';
      diagnosticsDegradedAlert.textContent = '';
    }
    updateAuthState(false);
  }

  /**
   * Authenticate and load dashboard data
   */
  async function authenticate() {
    const enteredToken = apiTokenInput.value.trim();
    if (!enteredToken) {
      authError.textContent = 'Please enter a valid API token.';
      authError.style.display = 'flex';
      return;
    }

    connectBtn.disabled = true;
    connectBtn.textContent = 'Connecting...';
    authError.style.display = 'none';

    apiToken = enteredToken;
    const success = await fetchDashboardData();

    connectBtn.disabled = false;
    connectBtn.textContent = 'Connect Gateway';

    if (success) {
      updateAuthState(true);
      apiTokenInput.value = ''; // Clean input field from DOM
      // Check current hash for initial view
      const hash = window.location.hash.replace(/^#/, '');
      const validViews = ['providers', 'catalog', 'profiles', 'routing', 'diagnostics'];
      const targetHash = validViews.includes(hash)
        ? (hash === 'routing' ? 'profiles' : hash)
        : 'overview';
      switchView(targetHash);
    } else {
      apiToken = null;
      updateAuthState(false);
    }
  }

  /**
   * Fetch diagnostics and providers from existing management API
   */
  async function fetchDashboardData() {
    if (!apiToken || isFetching) return false;

    isFetching = true;
    refreshBtn.disabled = true;
    refreshIcon.classList.add('spin');
    if (refreshProvidersBtn) refreshProvidersBtn.disabled = true;

    try {
      const headers = {
        'Authorization': `Bearer ${apiToken}`,
        'Accept': 'application/json',
      };

      // Concurrent fetch of /api/diagnostics and /api/providers
      const [diagRes, provRes] = await Promise.all([
        fetch('/api/diagnostics', { headers }),
        fetch('/api/providers', { headers })
      ]);

      if (diagRes.status === 401 || provRes.status === 401) {
        disconnect();
        authError.textContent = 'Authentication failed: Invalid or expired API token.';
        authError.style.display = 'flex';
        setStatus('unavailable', 'Unauthorized');
        return false;
      }

      if (!diagRes.ok) {
        throw new Error(`Diagnostics request failed with HTTP ${diagRes.status}`);
      }
      if (!provRes.ok) {
        throw new Error(`Providers request failed with HTTP ${provRes.status}`);
      }

      const diagData = await diagRes.json();
      const provData = await provRes.json();

      cachedProviders = provData.data || [];
      populateCatalogProviderFilter();
      renderOverview(diagData, cachedProviders);
      renderProvidersCards(cachedProviders);

      if (currentView === 'catalog' && apiToken) {
        await fetchCatalogData();
      } else if (currentView === 'profiles' && apiToken) {
        await fetchProfilesData();
      } else if (currentView === 'diagnostics' && apiToken) {
        await fetchDiagnosticsData();
      }

      lastFetchTimestamp = new Date();
      lastUpdatedText.textContent = `Updated: ${lastFetchTimestamp.toLocaleTimeString()}`;
      return true;

    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setStatus('unavailable', 'Unavailable');
      authError.textContent = 'Could not reach gateway: Check that the local server is running.';
      authError.style.display = 'flex';
      return false;
    } finally {
      isFetching = false;
      refreshIcon.classList.remove('spin');
      if (apiToken) {
        refreshBtn.disabled = false;
        if (refreshProvidersBtn) refreshProvidersBtn.disabled = false;
      }
    }
  }

  /**
   * Render overview metrics and summary table
   */
  function renderOverview(diag, providersList) {
    const isDegraded = diag.database && diag.database.degraded;

    // 1. Header Status Pill
    if (isDegraded) {
      setStatus('degraded', 'Degraded');
    } else if (diag.status === 'ok') {
      setStatus('healthy', 'Healthy');
    } else {
      setStatus('unknown', 'Unknown');
    }

    // 2. Degraded Banner
    if (isDegraded) {
      degradedBanner.style.display = 'flex';
      const reason = (diag.database && diag.database.reason) ? diag.database.reason : 'Running with in-memory persistence fallback.';
      degradedReason.textContent = reason;
    } else {
      degradedBanner.style.display = 'none';
    }

    // 3. Card 1: Gateway Status
    if (isDegraded) {
      cardGatewayVal.textContent = 'Degraded';
      cardGatewayBadge.className = 'badge badge-warning';
      cardGatewayBadge.textContent = 'Degraded';
      cardGatewaySub.textContent = 'In-memory persistence active';
    } else if (diag.status === 'ok') {
      cardGatewayVal.textContent = 'Healthy';
      cardGatewayBadge.className = 'badge badge-success';
      cardGatewayBadge.textContent = 'Active';
      cardGatewaySub.textContent = 'Local loopback gateway operational';
    } else {
      cardGatewayVal.textContent = 'Unknown';
      cardGatewayBadge.className = 'badge badge-neutral';
      cardGatewayBadge.textContent = 'Status';
      cardGatewaySub.textContent = 'Operational status undetermined';
    }

    // 4. Card 2: Persistence Mode
    if (diag.database) {
      const mode = (diag.database.mode || 'none').toUpperCase();
      cardDbVal.textContent = mode;
      if (diag.database.degraded) {
        cardDbBadge.className = 'badge badge-warning';
        cardDbBadge.textContent = 'Fallback';
        cardDbSub.textContent = 'In-memory (unsaved)';
      } else {
        cardDbBadge.className = 'badge badge-success';
        cardDbBadge.textContent = 'WAL';
        cardDbSub.textContent = `SQLite • ${diag.database.journal_mode || 'wal'}`;
      }
    }

    // 5. Card 3: Providers Count
    cardProvVal.textContent = String(diag.registered_providers_count ?? providersList.length);
    const localCount = providersList.filter(p => p.local).length;
    const hostedCount = providersList.length - localCount;
    cardProvSub.textContent = `${localCount} local • ${hostedCount} hosted`;

    // 6. Card 4: Model Catalog
    cardCatVal.textContent = String(diag.catalog_entries_count ?? 0);
    const staleCount = diag.stale_models_count ?? 0;
    cardCatSub.textContent = `${staleCount} stale awaiting refresh`;
    if (staleCount > 0) {
      cardCatBadge.className = 'badge badge-warning';
      cardCatBadge.textContent = `${staleCount} Stale`;
    } else {
      cardCatBadge.className = 'badge badge-neutral';
      cardCatBadge.textContent = 'Synced';
    }

    // 7. Card 5: Routing Profiles
    cardProfVal.textContent = String(diag.routing_profiles_count ?? 0);
    cardProfSub.textContent = 'Active failover profiles';

    // 8. Render Providers Summary Table
    renderProvidersTable(providersList);
  }

  /**
   * Safely render registered providers list into Overview table
   */
  function renderProvidersTable(providers) {
    providersTableBody.innerHTML = '';

    if (!providers || providers.length === 0) {
      const emptyRow = document.createElement('tr');
      const emptyCell = document.createElement('td');
      emptyCell.colSpan = 6;
      emptyCell.className = 'text-center py-4';
      emptyCell.textContent = 'No providers currently registered in registry.';
      emptyRow.appendChild(emptyCell);
      providersTableBody.appendChild(emptyRow);
      return;
    }

    providers.forEach(p => {
      const row = document.createElement('tr');

      // Provider Name
      const nameCell = document.createElement('td');
      nameCell.style.fontWeight = '500';
      nameCell.textContent = p.display_name || p.id;
      row.appendChild(nameCell);

      // Identifier
      const idCell = document.createElement('td');
      const idCode = document.createElement('code');
      idCode.className = 'table-code';
      idCode.textContent = p.id;
      idCell.appendChild(idCode);
      row.appendChild(idCell);

      // Locality / Deployment
      const typeCell = document.createElement('td');
      const typeBadge = document.createElement('span');
      typeBadge.className = p.local ? 'badge badge-success' : 'badge badge-neutral';
      typeBadge.textContent = p.local ? 'Local' : 'Hosted';
      typeCell.appendChild(typeBadge);
      row.appendChild(typeCell);

      // Base URL
      const urlCell = document.createElement('td');
      const urlCode = document.createElement('code');
      urlCode.className = 'table-code';
      urlCode.textContent = p.base_url || '—';
      urlCell.appendChild(urlCode);
      row.appendChild(urlCell);

      // Credentials Presence
      const credCell = document.createElement('td');
      const credBadge = document.createElement('span');
      credBadge.className = 'badge badge-neutral';
      credBadge.textContent = p.has_credential ? 'Configured' : 'None';
      credCell.appendChild(credBadge);
      row.appendChild(credCell);

      // Connection Status (derives from probe results map if tested)
      const statusCell = document.createElement('td');
      const connBadge = document.createElement('span');
      const probeRes = providerProbeResults.get(p.id);

      if (activeProbes.has(p.id)) {
        connBadge.className = 'badge badge-neutral';
        connBadge.textContent = 'Testing...';
      } else if (probeRes) {
        if (probeRes.status === 'healthy') {
          connBadge.className = 'badge badge-success';
          connBadge.textContent = 'Healthy';
        } else if (probeRes.status === 'unhealthy') {
          connBadge.className = 'badge badge-warning';
          connBadge.textContent = 'Unhealthy';
        } else {
          connBadge.className = 'badge badge-error';
          connBadge.textContent = 'Error';
        }
      } else {
        connBadge.className = 'badge badge-neutral';
        connBadge.textContent = 'Unchecked';
        connBadge.title = 'Test connection available in Provider Management';
      }

      statusCell.appendChild(connBadge);
      row.appendChild(statusCell);

      providersTableBody.appendChild(row);
    });
  }

  /**
   * Safely render detailed provider management cards
   */
  function renderProvidersCards(providers) {
    providersCardsContainer.innerHTML = '';
    providersErrorAlert.style.display = 'none';

    if (!providers || providers.length === 0) {
      providersEmptyState.style.display = 'flex';
      return;
    }

    providersEmptyState.style.display = 'none';

    providers.forEach(p => {
      const card = document.createElement('div');
      card.className = 'provider-card';
      card.setAttribute('data-provider-card', p.id);

      // 1. Card Header
      const header = document.createElement('div');
      header.className = 'provider-card-header';

      const titleGroup = document.createElement('div');
      titleGroup.className = 'provider-title-group';

      const name = document.createElement('h3');
      name.className = 'provider-name';
      name.textContent = p.display_name || p.id;
      titleGroup.appendChild(name);

      const badges = document.createElement('div');
      badges.className = 'provider-badges';

      const idBadge = document.createElement('code');
      idBadge.className = 'table-code';
      idBadge.textContent = p.id;
      badges.appendChild(idBadge);

      const locBadge = document.createElement('span');
      locBadge.className = p.local ? 'badge badge-success' : 'badge badge-neutral';
      locBadge.textContent = p.local ? 'Local' : 'Hosted';
      badges.appendChild(locBadge);

      const enabledBadge = document.createElement('span');
      enabledBadge.className = p.enabled ? 'badge badge-neutral' : 'badge badge-error';
      enabledBadge.textContent = p.enabled ? 'Enabled' : 'Disabled';
      badges.appendChild(enabledBadge);

      titleGroup.appendChild(badges);
      header.appendChild(titleGroup);
      card.appendChild(header);

      // 2. Card Metadata Details
      const metaList = document.createElement('div');
      metaList.className = 'provider-meta-list';

      // Endpoint URL
      const urlRow = document.createElement('div');
      urlRow.className = 'provider-meta-row';
      const urlLabel = document.createElement('span');
      urlLabel.className = 'provider-meta-label';
      urlLabel.textContent = 'Endpoint';
      const urlVal = document.createElement('span');
      urlVal.className = 'provider-meta-value';
      urlVal.textContent = p.base_url || '—';
      urlRow.appendChild(urlLabel);
      urlRow.appendChild(urlVal);
      metaList.appendChild(urlRow);

      // Credentials status
      const credRow = document.createElement('div');
      credRow.className = 'provider-meta-row';
      const credLabel = document.createElement('span');
      credLabel.className = 'provider-meta-label';
      credLabel.textContent = 'Credentials';
      const credVal = document.createElement('span');
      credVal.className = 'provider-meta-value';
      credVal.textContent = p.has_credential ? 'Configured' : 'None';
      credRow.appendChild(credLabel);
      credRow.appendChild(credVal);
      metaList.appendChild(credRow);

      card.appendChild(metaList);

      // 3. Probe Status Box
      const probeBox = document.createElement('div');
      probeBox.className = 'probe-box';

      const probeHeader = document.createElement('div');
      probeHeader.className = 'probe-header';
      const probeTitle = document.createElement('span');
      probeTitle.className = 'probe-title';
      probeTitle.textContent = 'Connection Health';
      const probeBadge = document.createElement('span');
      probeHeader.appendChild(probeTitle);
      probeHeader.appendChild(probeBadge);
      probeBox.appendChild(probeHeader);

      const probeDetails = document.createElement('div');
      probeDetails.className = 'probe-details';

      const probeRes = providerProbeResults.get(p.id);
      const isProbing = activeProbes.has(p.id);

      if (isProbing) {
        probeBadge.className = 'badge badge-neutral';
        probeBadge.textContent = 'Testing...';
        const probingMsg = document.createElement('span');
        probingMsg.textContent = 'Executing reachability probe...';
        probeDetails.appendChild(probingMsg);
      } else if (probeRes) {
        if (probeRes.status === 'healthy') {
          probeBadge.className = 'badge badge-success';
          probeBadge.textContent = 'Healthy';

          const latencyText = document.createElement('span');
          const lat = (probeRes.latency_ms !== null && probeRes.latency_ms !== undefined)
            ? `${probeRes.latency_ms.toFixed(1)} ms`
            : 'latency unmeasured';
          latencyText.textContent = `Roundtrip: ${lat}`;
          probeDetails.appendChild(latencyText);

          const timeText = document.createElement('span');
          timeText.textContent = `Last tested: ${probeRes.timestamp.toLocaleTimeString()}`;
          probeDetails.appendChild(timeText);
        } else if (probeRes.status === 'unhealthy') {
          probeBadge.className = 'badge badge-warning';
          probeBadge.textContent = 'Unhealthy';

          if (probeRes.latency_ms !== null && probeRes.latency_ms !== undefined) {
            const latText = document.createElement('span');
            latText.textContent = `Roundtrip: ${probeRes.latency_ms.toFixed(1)} ms`;
            probeDetails.appendChild(latText);
          }

          if (probeRes.error) {
            const errDiv = document.createElement('div');
            errDiv.className = 'probe-error-msg';
            errDiv.textContent = probeRes.error;
            probeDetails.appendChild(errDiv);
          }

          const timeText = document.createElement('span');
          timeText.textContent = `Attempted: ${probeRes.timestamp.toLocaleTimeString()}`;
          probeDetails.appendChild(timeText);
        } else {
          probeBadge.className = 'badge badge-error';
          probeBadge.textContent = 'Error';

          if (probeRes.error) {
            const errDiv = document.createElement('div');
            errDiv.className = 'probe-error-msg';
            errDiv.textContent = probeRes.error;
            probeDetails.appendChild(errDiv);
          }

          const timeText = document.createElement('span');
          timeText.textContent = `Attempted: ${probeRes.timestamp.toLocaleTimeString()}`;
          probeDetails.appendChild(timeText);
        }
      } else {
        probeBadge.className = 'badge badge-neutral';
        probeBadge.textContent = 'Unchecked';
        const uncheckMsg = document.createElement('span');
        uncheckMsg.textContent = 'Not tested in this session.';
        probeDetails.appendChild(uncheckMsg);
      }

      probeBox.appendChild(probeDetails);
      card.appendChild(probeBox);

      // 4. Card Footer with Test Connection Button
      const footer = document.createElement('div');
      footer.className = 'provider-card-footer';

      const testBtn = document.createElement('button');
      testBtn.className = 'btn btn-secondary test-provider-btn';
      testBtn.setAttribute('data-provider-id', p.id);
      testBtn.disabled = isProbing;
      testBtn.textContent = isProbing ? 'Testing...' : 'Test Connection';

      testBtn.addEventListener('click', function () {
        testProviderConnection(p.id);
      });

      footer.appendChild(testBtn);
      card.appendChild(footer);

      providersCardsContainer.appendChild(card);
    });
  }

  /**
   * Explicitly execute on-demand connection test for a provider
   */
  async function testProviderConnection(providerId) {
    if (activeProbes.has(providerId) || !apiToken) return;

    activeProbes.add(providerId);
    renderProvidersCards(cachedProviders);
    renderProvidersTable(cachedProviders);

    try {
      const res = await fetch(`/api/providers/${encodeURIComponent(providerId)}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Accept': 'application/json',
        },
      });

      if (res.status === 401) {
        disconnect();
        authError.textContent = 'Session invalid or token expired: please reconnect.';
        authError.style.display = 'flex';
        return;
      }

      if (res.ok) {
        const data = await res.json();
        providerProbeResults.set(providerId, {
          status: data.status,
          latency_ms: data.latency_ms,
          error: data.error,
          timestamp: new Date()
        });
      } else {
        const errJson = await res.json().catch(() => null);
        const errDetail = (errJson && errJson.error && errJson.error.message)
          || (errJson && errJson.detail)
          || `HTTP ${res.status}`;
        providerProbeResults.set(providerId, {
          status: 'error',
          latency_ms: null,
          error: errDetail,
          timestamp: new Date()
        });
      }
    } catch (err) {
      providerProbeResults.set(providerId, {
        status: 'error',
        latency_ms: null,
        error: err.message || 'Connection test failed',
        timestamp: new Date()
      });
    } finally {
      activeProbes.delete(providerId);
      renderProvidersCards(cachedProviders);
      renderProvidersTable(cachedProviders);
    }
  }

  /**
   * Fetch model catalog entries from management API
   */
  async function fetchCatalogData() {
    if (!apiToken || isFetchingCatalog) return false;

    isFetchingCatalog = true;
    if (catalogErrorAlert) {
      catalogErrorAlert.style.display = 'none';
      catalogErrorAlert.textContent = '';
    }

    try {
      const res = await fetch('/api/catalog', {
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Accept': 'application/json',
        },
      });

      if (res.status === 401) {
        disconnect();
        authError.textContent = 'Session invalid or token expired: please reconnect.';
        authError.style.display = 'flex';
        return false;
      }

      if (!res.ok) {
        throw new Error(`Failed to load catalog (HTTP ${res.status})`);
      }

      const data = await res.json();
      cachedCatalog = data.data || [];
      populateCatalogProviderFilter();
      renderCatalogCards();
      return true;
    } catch (err) {
      console.error('Failed to load catalog data:', err);
      if (catalogErrorAlert) {
        catalogErrorAlert.textContent = 'Failed to load model catalog. Please check gateway connectivity.';
        catalogErrorAlert.style.display = 'block';
      }
      return false;
    } finally {
      isFetchingCatalog = false;
    }
  }

  /**
   * Populate Provider Filter dropdown with registered providers
   */
  function populateCatalogProviderFilter() {
    if (!catalogProviderFilter) return;

    const providerIds = new Set();
    cachedProviders.forEach(p => providerIds.add(p.id));
    cachedCatalog.forEach(m => providerIds.add(m.provider_id));

    const sortedProviders = Array.from(providerIds).sort();
    const currentVal = selectedCatalogProvider || catalogProviderFilter.value;

    catalogProviderFilter.textContent = '';
    const allOpt = document.createElement('option');
    allOpt.value = '';
    allOpt.textContent = 'All Providers';
    catalogProviderFilter.appendChild(allOpt);

    sortedProviders.forEach(pid => {
      const opt = document.createElement('option');
      opt.value = pid;
      opt.textContent = pid;
      if (pid === currentVal) {
        opt.selected = true;
      }
      catalogProviderFilter.appendChild(opt);
    });

    selectedCatalogProvider = catalogProviderFilter.value;
  }

  /**
   * Render Model Catalog cards safely
   */
  function renderCatalogCards() {
    if (!catalogCardsContainer) return;

    catalogCardsContainer.textContent = '';

    const filtered = selectedCatalogProvider
      ? cachedCatalog.filter(m => m.provider_id === selectedCatalogProvider)
      : cachedCatalog;

    if (filtered.length === 0) {
      if (catalogEmptyState) catalogEmptyState.style.display = 'flex';
      catalogCardsContainer.style.display = 'none';
      return;
    }

    if (catalogEmptyState) catalogEmptyState.style.display = 'none';
    catalogCardsContainer.style.display = 'grid';

    filtered.forEach(entry => {
      const card = document.createElement('div');
      card.className = entry.is_stale ? 'model-card is-stale' : 'model-card';

      // 1. Header
      const header = document.createElement('div');
      header.className = 'model-card-header';

      const titleWrap = document.createElement('div');
      titleWrap.className = 'model-title-wrap';

      const title = document.createElement('h3');
      title.className = 'model-display-name';
      title.textContent = entry.display_name || entry.model_id;
      titleWrap.appendChild(title);

      const compId = document.createElement('code');
      compId.className = 'model-composite-id';
      compId.textContent = entry.composite_id;
      titleWrap.appendChild(compId);

      header.appendChild(titleWrap);

      const badgeRow = document.createElement('div');
      badgeRow.className = 'model-badge-row';

      // Locality badge
      const localityBadge = document.createElement('span');
      localityBadge.className = 'badge badge-neutral';
      localityBadge.textContent = entry.is_local ? 'Local' : 'Hosted';
      badgeRow.appendChild(localityBadge);

      // Stale / Active status badge
      const statusBadge = document.createElement('span');
      if (entry.is_stale) {
        statusBadge.className = 'badge badge-warning stale-badge';
        statusBadge.textContent = 'Stale';
      } else {
        statusBadge.className = 'badge badge-success';
        statusBadge.textContent = 'Active';
      }
      badgeRow.appendChild(statusBadge);

      header.appendChild(badgeRow);
      card.appendChild(header);

      // 2. Metadata Grid
      const metaGrid = document.createElement('div');
      metaGrid.className = 'model-meta-grid';

      // Provider item
      const provItem = document.createElement('div');
      provItem.className = 'model-meta-item';
      const provLabel = document.createElement('span');
      provLabel.className = 'model-meta-label';
      provLabel.textContent = 'Provider';
      const provVal = document.createElement('span');
      provVal.className = 'model-meta-value';
      provVal.textContent = entry.provider_id;
      provItem.appendChild(provLabel);
      provItem.appendChild(provVal);
      metaGrid.appendChild(provItem);

      // Model ID item
      const idItem = document.createElement('div');
      idItem.className = 'model-meta-item';
      const idLabel = document.createElement('span');
      idLabel.className = 'model-meta-label';
      idLabel.textContent = 'Model ID';
      const idVal = document.createElement('span');
      idVal.className = 'model-meta-value';
      idVal.textContent = entry.model_id;
      idItem.appendChild(idLabel);
      idItem.appendChild(idVal);
      metaGrid.appendChild(idItem);

      // Context Window item
      const ctxItem = document.createElement('div');
      ctxItem.className = 'model-meta-item';
      const ctxLabel = document.createElement('span');
      ctxLabel.className = 'model-meta-label';
      ctxLabel.textContent = 'Context Window';
      const ctxVal = document.createElement('span');
      ctxVal.className = 'model-meta-value';
      if (entry.capabilities && entry.capabilities.context_window !== null && entry.capabilities.context_window !== undefined) {
        ctxVal.textContent = `${entry.capabilities.context_window.toLocaleString()} tokens`;
      } else {
        ctxVal.textContent = '—';
      }
      ctxItem.appendChild(ctxLabel);
      ctxItem.appendChild(ctxVal);
      metaGrid.appendChild(ctxItem);

      // Last Discovered item
      const seenItem = document.createElement('div');
      seenItem.className = 'model-meta-item';
      const seenLabel = document.createElement('span');
      seenLabel.className = 'model-meta-label';
      seenLabel.textContent = 'Last Discovered';
      const seenVal = document.createElement('span');
      seenVal.className = 'model-meta-value';
      if (entry.last_seen_at) {
        const d = new Date(entry.last_seen_at * 1000);
        seenVal.textContent = d.toLocaleTimeString();
      } else {
        seenVal.textContent = '—';
      }
      seenItem.appendChild(seenLabel);
      seenItem.appendChild(seenVal);
      metaGrid.appendChild(seenItem);

      card.appendChild(metaGrid);

      // 3. Capabilities Section
      const capSection = document.createElement('div');
      capSection.className = 'model-capabilities-section';

      const capTitle = document.createElement('span');
      capTitle.className = 'model-section-title';
      capTitle.textContent = 'Supported Capabilities';
      capSection.appendChild(capTitle);

      const capTags = document.createElement('div');
      capTags.className = 'capability-tags';

      const caps = entry.capabilities || {};
      const capDefs = [
        { key: 'supports_streaming', label: 'Streaming' },
        { key: 'supports_tools', label: 'Tools' },
        { key: 'supports_vision', label: 'Vision' },
      ];

      capDefs.forEach(c => {
        const tag = document.createElement('span');
        const isActive = Boolean(caps[c.key]);
        tag.className = isActive ? 'tag tag-active' : 'tag tag-inactive';
        tag.textContent = c.label;
        capTags.appendChild(tag);
      });

      capSection.appendChild(capTags);
      card.appendChild(capSection);

      // 4. Stale Callout (only when model is flagged stale)
      if (entry.is_stale) {
        const staleNotice = document.createElement('div');
        staleNotice.className = 'stale-callout';

        const warnIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        warnIcon.setAttribute('width', '16');
        warnIcon.setAttribute('height', '16');
        warnIcon.setAttribute('viewBox', '0 0 24 24');
        warnIcon.setAttribute('fill', 'none');
        warnIcon.setAttribute('stroke', 'currentColor');
        warnIcon.setAttribute('stroke-width', '2');
        warnIcon.setAttribute('stroke-linecap', 'round');
        warnIcon.setAttribute('stroke-linejoin', 'round');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z');
        const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line1.setAttribute('x1', '12'); line1.setAttribute('y1', '9'); line1.setAttribute('x2', '12'); line1.setAttribute('y2', '13');
        const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line2.setAttribute('x1', '12.01'); line2.setAttribute('y1', '17'); line2.setAttribute('x2', '12.01'); line2.setAttribute('y2', '17');
        warnIcon.appendChild(path);
        warnIcon.appendChild(line1);
        warnIcon.appendChild(line2);

        staleNotice.appendChild(warnIcon);

        const noticeText = document.createElement('span');
        noticeText.textContent = 'Restored from persistent storage; awaiting discovery confirmation. Not verified against live provider.';
        staleNotice.appendChild(noticeText);

        card.appendChild(staleNotice);
      }

      catalogCardsContainer.appendChild(card);
    });
  }

  /**
   * Explicitly execute on-demand discovery refresh across providers
   */
  async function refreshCatalogDiscovery() {
    if (isRefreshingCatalog || !apiToken) return;

    isRefreshingCatalog = true;
    refreshCatalogBtn.disabled = true;
    if (refreshCatalogIcon) refreshCatalogIcon.classList.add('spin');
    if (refreshCatalogBtnText) refreshCatalogBtnText.textContent = 'Refreshing...';

    if (catalogRefreshAlert) {
      catalogRefreshAlert.style.display = 'none';
      catalogRefreshAlert.textContent = '';
      catalogRefreshAlert.className = 'alert';
    }

    try {
      const payload = selectedCatalogProvider ? { provider_id: selectedCatalogProvider } : {};
      const res = await fetch('/api/catalog/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        disconnect();
        authError.textContent = 'Session invalid or token expired: please reconnect.';
        authError.style.display = 'flex';
        return;
      }

      if (res.ok) {
        const data = await res.json();
        const successful = data.successful_refreshes || 0;
        const failed = data.failed_refreshes || 0;
        const results = data.results || [];

        let totalModels = 0;
        results.forEach(r => {
          if (r.success) totalModels += (r.models_count || 0);
        });

        if (catalogRefreshAlert) {
          catalogRefreshAlert.textContent = '';
          const msgContainer = document.createElement('div');
          msgContainer.className = 'refresh-summary-box';

          const mainLine = document.createElement('div');
          if (failed === 0) {
            catalogRefreshAlert.className = 'alert alert-success';
            mainLine.textContent = `Discovery complete: Successfully refreshed ${successful} provider(s). Active models discovered: ${totalModels}.`;
          } else if (successful > 0) {
            catalogRefreshAlert.className = 'alert alert-warning';
            mainLine.textContent = `Partial discovery: ${successful} provider(s) succeeded (${totalModels} models), ${failed} failed.`;
          } else {
            catalogRefreshAlert.className = 'alert alert-error';
            mainLine.textContent = `Discovery failed across all ${failed} attempted provider(s).`;
          }
          msgContainer.appendChild(mainLine);

          // Add failure details if any
          const failedResults = results.filter(r => !r.success);
          if (failedResults.length > 0) {
            const list = document.createElement('div');
            list.className = 'refresh-summary-list';
            failedResults.forEach(f => {
              const item = document.createElement('div');
              item.className = 'refresh-summary-item';
              item.textContent = `• [${f.provider_id}] ${f.error || 'Discovery check failed'}`;
              list.appendChild(item);
            });
            msgContainer.appendChild(list);
          }

          catalogRefreshAlert.appendChild(msgContainer);
          catalogRefreshAlert.style.display = 'block';
        }

        // Re-fetch catalog entries so newly discovered/confirmed models update on screen
        await fetchCatalogData();
      } else {
        const errJson = await res.json().catch(() => null);
        const errDetail = (errJson && errJson.error && errJson.error.message)
          || (errJson && errJson.detail)
          || `HTTP ${res.status}`;
        if (catalogRefreshAlert) {
          catalogRefreshAlert.className = 'alert alert-error';
          catalogRefreshAlert.textContent = `Catalog refresh error: ${errDetail}`;
          catalogRefreshAlert.style.display = 'block';
        }
      }
    } catch (err) {
      if (catalogRefreshAlert) {
        catalogRefreshAlert.className = 'alert alert-error';
        catalogRefreshAlert.textContent = `Catalog refresh network error: ${err.message || 'Request failed'}`;
        catalogRefreshAlert.style.display = 'block';
      }
    } finally {
      isRefreshingCatalog = false;
      refreshCatalogBtn.disabled = false;
      if (refreshCatalogIcon) refreshCatalogIcon.classList.remove('spin');
      if (refreshCatalogBtnText) {
        refreshCatalogBtnText.textContent = selectedCatalogProvider
          ? `Refresh ${selectedCatalogProvider}`
          : 'Refresh Catalog';
      }
    }
  }

  /**
   * Fetch routing profiles from management API
   */
  async function fetchProfilesData() {
    if (!apiToken || isFetchingProfiles) return false;

    isFetchingProfiles = true;
    if (profilesErrorAlert) {
      profilesErrorAlert.style.display = 'none';
      profilesErrorAlert.textContent = '';
    }
    if (refreshProfilesBtn) refreshProfilesBtn.disabled = true;
    if (refreshProfilesIcon) refreshProfilesIcon.classList.add('spin');

    try {
      const res = await fetch('/api/profiles', {
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Accept': 'application/json',
        },
      });

      if (res.status === 401) {
        disconnect();
        authError.textContent = 'Session invalid or token expired: please reconnect.';
        authError.style.display = 'flex';
        return false;
      }

      if (!res.ok) {
        throw new Error(`Failed to load routing profiles (HTTP ${res.status})`);
      }

      const data = await res.json();
      cachedProfiles = data.data || [];
      renderProfilesCards();
      return true;
    } catch (err) {
      console.error('Failed to load routing profiles:', err);
      if (profilesErrorAlert) {
        profilesErrorAlert.textContent = 'Failed to load routing profiles. Please check gateway connectivity.';
        profilesErrorAlert.style.display = 'block';
      }
      return false;
    } finally {
      isFetchingProfiles = false;
      if (refreshProfilesBtn && apiToken) refreshProfilesBtn.disabled = false;
      if (refreshProfilesIcon) refreshProfilesIcon.classList.remove('spin');
    }
  }

  /**
   * Render Routing Profile cards safely
   */
  function renderProfilesCards() {
    if (!profilesCardsContainer) return;

    profilesCardsContainer.textContent = '';

    if (!cachedProfiles || cachedProfiles.length === 0) {
      if (profilesEmptyState) profilesEmptyState.style.display = 'flex';
      profilesCardsContainer.style.display = 'none';
      return;
    }

    if (profilesEmptyState) profilesEmptyState.style.display = 'none';
    profilesCardsContainer.style.display = 'grid';

    cachedProfiles.forEach(profile => {
      const card = document.createElement('div');
      card.className = 'profile-card';

      // 1. Header
      const header = document.createElement('div');
      header.className = 'profile-card-header';

      const titleWrap = document.createElement('div');
      titleWrap.className = 'profile-title-wrap';

      const title = document.createElement('h3');
      title.className = 'profile-name';
      title.textContent = profile.name;
      titleWrap.appendChild(title);

      header.appendChild(titleWrap);

      const badge = document.createElement('span');
      badge.className = 'badge badge-neutral';
      badge.textContent = 'Read-Only';
      header.appendChild(badge);

      card.appendChild(header);

      // 2. Description
      if (profile.description) {
        const desc = document.createElement('p');
        desc.className = 'profile-desc';
        desc.textContent = profile.description;
        card.appendChild(desc);
      }

      // 3. Candidate Sequence Box
      const candBox = document.createElement('div');
      candBox.className = 'candidate-sequence-box';

      const candTitle = document.createElement('span');
      candTitle.className = 'candidate-sequence-title';
      candTitle.textContent = 'Candidate Priority Sequence';
      candBox.appendChild(candTitle);

      const candList = document.createElement('div');
      candList.className = 'candidate-sequence-list';

      const candidates = profile.candidates || [];
      if (candidates.length === 0) {
        const emptyCand = document.createElement('span');
        emptyCand.className = 'candidate-disclaimer';
        emptyCand.textContent = 'No candidates configured for this profile.';
        candList.appendChild(emptyCand);
      } else {
        candidates.forEach((cand, idx) => {
          const item = document.createElement('div');
          item.className = 'candidate-item';

          const priBadge = document.createElement('span');
          priBadge.className = (idx === 0)
            ? 'candidate-priority-badge candidate-priority-primary'
            : 'candidate-priority-badge candidate-priority-failover';
          priBadge.textContent = (idx === 0) ? '#1 Primary' : `#${idx + 1} Failover`;
          item.appendChild(priBadge);

          const tag = document.createElement('code');
          tag.className = 'candidate-tag';
          tag.textContent = cand;
          item.appendChild(tag);

          candList.appendChild(item);
        });
      }

      candBox.appendChild(candList);

      const disclaimer = document.createElement('p');
      disclaimer.className = 'candidate-disclaimer';
      disclaimer.textContent = 'Sequence defines primary and fallback attempts. Candidate appearance does not guarantee live provider reachability.';
      candBox.appendChild(disclaimer);

      card.appendChild(candBox);

      // 4. Execution Parameters Grid
      const paramsGrid = document.createElement('div');
      paramsGrid.className = 'profile-params-grid';

      // Max Retries
      const retriesItem = document.createElement('div');
      retriesItem.className = 'profile-param-item';
      const retriesLabel = document.createElement('span');
      retriesLabel.className = 'profile-param-label';
      retriesLabel.textContent = 'Retry Budget';
      const retriesVal = document.createElement('span');
      retriesVal.className = 'profile-param-value';
      retriesVal.textContent = `${profile.max_retries} attempt${profile.max_retries === 1 ? '' : 's'}`;
      retriesItem.appendChild(retriesLabel);
      retriesItem.appendChild(retriesVal);
      paramsGrid.appendChild(retriesItem);

      // Timeout Ceiling
      const timeoutItem = document.createElement('div');
      timeoutItem.className = 'profile-param-item';
      const timeoutLabel = document.createElement('span');
      timeoutLabel.className = 'profile-param-label';
      timeoutLabel.textContent = 'Timeout Ceiling';
      const timeoutVal = document.createElement('span');
      timeoutVal.className = 'profile-param-value';
      if (profile.timeout_seconds !== null && profile.timeout_seconds !== undefined) {
        timeoutVal.textContent = `${profile.timeout_seconds}s`;
      } else {
        timeoutVal.textContent = '—';
      }
      timeoutItem.appendChild(timeoutLabel);
      timeoutItem.appendChild(timeoutVal);
      paramsGrid.appendChild(timeoutItem);

      card.appendChild(paramsGrid);

      // 5. Required Capabilities Section
      const capSection = document.createElement('div');
      capSection.className = 'model-capabilities-section';

      const capTitle = document.createElement('span');
      capTitle.className = 'model-section-title';
      capTitle.textContent = 'Required Candidate Capabilities';
      capSection.appendChild(capTitle);

      const capTags = document.createElement('div');
      capTags.className = 'capability-tags';

      const reqCaps = profile.required_capabilities || {};
      const capDefs = [
        { key: 'supports_streaming', label: 'Streaming' },
        { key: 'supports_tools', label: 'Tools' },
        { key: 'supports_vision', label: 'Vision' },
      ];

      capDefs.forEach(c => {
        const tag = document.createElement('span');
        const isActive = Boolean(reqCaps[c.key]);
        tag.className = isActive ? 'tag tag-active' : 'tag tag-inactive';
        tag.textContent = c.label;
        capTags.appendChild(tag);
      });

      if (reqCaps.context_window !== null && reqCaps.context_window !== undefined) {
        const ctxTag = document.createElement('span');
        ctxTag.className = 'tag tag-active';
        ctxTag.textContent = `≥ ${reqCaps.context_window.toLocaleString()} ctx`;
        capTags.appendChild(ctxTag);
      }

      capSection.appendChild(capTags);
      card.appendChild(capSection);

      profilesCardsContainer.appendChild(card);
    });
  }

  /**
   * Fetch diagnostics data from management API
   */
  async function fetchDiagnosticsData() {
    if (!apiToken || isFetchingDiagnostics) return false;

    isFetchingDiagnostics = true;
    if (diagnosticsErrorAlert) {
      diagnosticsErrorAlert.style.display = 'none';
      diagnosticsErrorAlert.textContent = '';
    }
    if (diagnosticsDegradedAlert) {
      diagnosticsDegradedAlert.style.display = 'none';
      diagnosticsDegradedAlert.textContent = '';
    }
    if (refreshDiagnosticsBtn) refreshDiagnosticsBtn.disabled = true;
    if (refreshDiagnosticsIcon) refreshDiagnosticsIcon.classList.add('spin');

    try {
      const res = await fetch('/api/diagnostics', {
        headers: {
          'Authorization': `Bearer ${apiToken}`,
          'Accept': 'application/json',
        },
      });

      if (res.status === 401) {
        disconnect();
        authError.textContent = 'Session invalid or token expired: please reconnect.';
        authError.style.display = 'flex';
        return false;
      }

      if (!res.ok) {
        throw new Error(`Failed to load diagnostics (HTTP ${res.status})`);
      }

      const data = await res.json();
      cachedDiagnostics = data;
      renderDiagnostics();
      return true;
    } catch (err) {
      console.error('Failed to load diagnostics:', err);
      if (diagnosticsErrorAlert) {
        diagnosticsErrorAlert.textContent = 'Failed to load diagnostics. Please check gateway connectivity.';
        diagnosticsErrorAlert.style.display = 'block';
      }
      return false;
    } finally {
      isFetchingDiagnostics = false;
      if (refreshDiagnosticsBtn && apiToken) refreshDiagnosticsBtn.disabled = false;
      if (refreshDiagnosticsIcon) refreshDiagnosticsIcon.classList.remove('spin');
    }
  }

  /**
   * Render Diagnostics Inspector details safely
   */
  function renderDiagnostics() {
    if (!diagnosticsContentContainer || !cachedDiagnostics) return;

    diagnosticsContentContainer.textContent = '';
    const diag = cachedDiagnostics;
    const isDegraded = Boolean(diag.database && diag.database.degraded);

    // 1. Degraded Alert Banner in Diagnostics
    if (isDegraded && diagnosticsDegradedAlert) {
      diagnosticsDegradedAlert.textContent = '';
      const strong = document.createElement('strong');
      strong.textContent = 'Persistence Degraded Notice: ';
      diagnosticsDegradedAlert.appendChild(strong);
      const span = document.createElement('span');
      span.textContent = (diag.database && diag.database.reason)
        ? diag.database.reason
        : 'SQLite database unavailable; gateway is running in degraded in-memory mode.';
      diagnosticsDegradedAlert.appendChild(span);
      diagnosticsDegradedAlert.style.display = 'block';
    } else if (diagnosticsDegradedAlert) {
      diagnosticsDegradedAlert.style.display = 'none';
    }

    // 2. Section 1: Gateway Runtime
    const secRuntime = document.createElement('div');
    secRuntime.className = 'diag-section';

    const runtimeHeader = document.createElement('div');
    runtimeHeader.className = 'diag-section-header';
    const runtimeTitle = document.createElement('h3');
    runtimeTitle.className = 'diag-section-title';
    runtimeTitle.textContent = 'Gateway Runtime Telemetry';
    runtimeHeader.appendChild(runtimeTitle);
    secRuntime.appendChild(runtimeHeader);

    const runtimeGrid = document.createElement('div');
    runtimeGrid.className = 'diag-grid';

    // Status
    const statusBox = document.createElement('div');
    statusBox.className = 'diag-item-box';
    const statusLbl = document.createElement('span');
    statusLbl.className = 'diag-item-label';
    statusLbl.textContent = 'Operational Status';
    const statusVal = document.createElement('span');
    statusVal.className = 'diag-item-value';
    statusVal.textContent = isDegraded ? 'Degraded' : (diag.status === 'ok' ? 'Healthy' : 'Unknown');
    const statusSub = document.createElement('span');
    statusSub.className = 'diag-item-sub';
    statusSub.textContent = isDegraded ? 'Running with memory fallback' : 'Loopback gateway operational';
    statusBox.appendChild(statusLbl);
    statusBox.appendChild(statusVal);
    statusBox.appendChild(statusSub);
    runtimeGrid.appendChild(statusBox);

    // Host / Binding
    const hostBox = document.createElement('div');
    hostBox.className = 'diag-item-box';
    const hostLbl = document.createElement('span');
    hostLbl.className = 'diag-item-label';
    hostLbl.textContent = 'Network Interface';
    const hostVal = document.createElement('span');
    hostVal.className = 'diag-item-value';
    hostVal.textContent = '127.0.0.1 (Loopback)';
    const hostSub = document.createElement('span');
    hostSub.className = 'diag-item-sub';
    hostSub.textContent = 'Isolated local process';
    hostBox.appendChild(hostLbl);
    hostBox.appendChild(hostVal);
    hostBox.appendChild(hostSub);
    runtimeGrid.appendChild(hostBox);

    // Authentication Mode
    const authBox = document.createElement('div');
    authBox.className = 'diag-item-box';
    const authLbl = document.createElement('span');
    authLbl.className = 'diag-item-label';
    authLbl.textContent = 'Session Security';
    const authVal = document.createElement('span');
    authVal.className = 'diag-item-value';
    authVal.textContent = 'Bearer Verified';
    const authSub = document.createElement('span');
    authSub.className = 'diag-item-sub';
    authSub.textContent = 'Volatile in-memory token';
    authBox.appendChild(authLbl);
    authBox.appendChild(authVal);
    authBox.appendChild(authSub);
    runtimeGrid.appendChild(authBox);

    secRuntime.appendChild(runtimeGrid);
    diagnosticsContentContainer.appendChild(secRuntime);

    // 3. Section 2: Persistence Subsystem
    const secDb = document.createElement('div');
    secDb.className = 'diag-section';

    const dbHeader = document.createElement('div');
    dbHeader.className = 'diag-section-header';
    const dbTitle = document.createElement('h3');
    dbTitle.className = 'diag-section-title';
    dbTitle.textContent = 'Persistence Subsystem Health';
    dbHeader.appendChild(dbTitle);
    secDb.appendChild(dbHeader);

    const dbGrid = document.createElement('div');
    dbGrid.className = 'diag-grid';

    const db = diag.database || {};

    // Available
    const dbAvailBox = document.createElement('div');
    dbAvailBox.className = 'diag-item-box';
    const dbAvailLbl = document.createElement('span');
    dbAvailLbl.className = 'diag-item-label';
    dbAvailLbl.textContent = 'Database Availability';
    const dbAvailVal = document.createElement('span');
    dbAvailVal.className = 'diag-item-value';
    dbAvailVal.textContent = db.available ? 'Available' : 'Unavailable';
    const dbAvailSub = document.createElement('span');
    dbAvailSub.className = 'diag-item-sub';
    dbAvailSub.textContent = db.available ? 'Active connection open' : 'No SQLite connection';
    dbAvailBox.appendChild(dbAvailLbl);
    dbAvailBox.appendChild(dbAvailVal);
    dbAvailBox.appendChild(dbAvailSub);
    dbGrid.appendChild(dbAvailBox);

    // Mode
    const dbModeBox = document.createElement('div');
    dbModeBox.className = 'diag-item-box';
    const dbModeLbl = document.createElement('span');
    dbModeLbl.className = 'diag-item-label';
    dbModeLbl.textContent = 'Persistence Mode';
    const dbModeVal = document.createElement('span');
    dbModeVal.className = 'diag-item-value';
    dbModeVal.textContent = (db.mode || 'none').toUpperCase();
    const dbModeSub = document.createElement('span');
    dbModeSub.className = 'diag-item-sub';
    dbModeSub.textContent = db.degraded ? 'Degraded fallback' : 'Persistent storage active';
    dbModeBox.appendChild(dbModeLbl);
    dbModeBox.appendChild(dbModeVal);
    dbModeBox.appendChild(dbModeSub);
    dbGrid.appendChild(dbModeBox);

    // Journal Mode
    const dbJournBox = document.createElement('div');
    dbJournBox.className = 'diag-item-box';
    const dbJournLbl = document.createElement('span');
    dbJournLbl.className = 'diag-item-label';
    dbJournLbl.textContent = 'SQLite Journal Mode';
    const dbJournVal = document.createElement('span');
    dbJournVal.className = 'diag-item-value';
    dbJournVal.textContent = db.journal_mode ? db.journal_mode.toUpperCase() : '—';
    const dbJournSub = document.createElement('span');
    dbJournSub.className = 'diag-item-sub';
    dbJournSub.textContent = db.journal_mode === 'wal' ? 'Write-Ahead Logging enabled' : 'Standard or unconfigured';
    dbJournBox.appendChild(dbJournLbl);
    dbJournBox.appendChild(dbJournVal);
    dbJournBox.appendChild(dbJournSub);
    dbGrid.appendChild(dbJournBox);

    secDb.appendChild(dbGrid);
    diagnosticsContentContainer.appendChild(secDb);

    // 4. Section 3: Subsystem Inventory & Counts
    const secInv = document.createElement('div');
    secInv.className = 'diag-section';

    const invHeader = document.createElement('div');
    invHeader.className = 'diag-section-header';
    const invTitle = document.createElement('h3');
    invTitle.className = 'diag-section-title';
    invTitle.textContent = 'Subsystem Inventory Metrics';
    invHeader.appendChild(invTitle);
    secInv.appendChild(invHeader);

    const invGrid = document.createElement('div');
    invGrid.className = 'diag-grid';

    // Providers
    const provBox = document.createElement('div');
    provBox.className = 'diag-item-box';
    const provLbl = document.createElement('span');
    provLbl.className = 'diag-item-label';
    provLbl.textContent = 'Registered Providers';
    const provVal = document.createElement('span');
    provVal.className = 'diag-item-value';
    provVal.textContent = String(diag.registered_providers_count ?? '—');
    provBox.appendChild(provLbl);
    provBox.appendChild(provVal);
    invGrid.appendChild(provBox);

    // Catalog entries
    const catBox = document.createElement('div');
    catBox.className = 'diag-item-box';
    const catLbl = document.createElement('span');
    catLbl.className = 'diag-item-label';
    catLbl.textContent = 'Catalog Models';
    const catVal = document.createElement('span');
    catVal.className = 'diag-item-value';
    catVal.textContent = String(diag.catalog_entries_count ?? '—');
    catBox.appendChild(catLbl);
    catBox.appendChild(catVal);
    invGrid.appendChild(catBox);

    // Stale models
    const staleBox = document.createElement('div');
    staleBox.className = 'diag-item-box';
    const staleLbl = document.createElement('span');
    staleLbl.className = 'diag-item-label';
    staleLbl.textContent = 'Stale Models';
    const staleVal = document.createElement('span');
    staleVal.className = 'diag-item-value';
    staleVal.textContent = String(diag.stale_models_count ?? '—');
    staleBox.appendChild(staleLbl);
    staleBox.appendChild(staleVal);
    invGrid.appendChild(staleBox);

    // Routing profiles
    const profBox = document.createElement('div');
    profBox.className = 'diag-item-box';
    const profLbl = document.createElement('span');
    profLbl.className = 'diag-item-label';
    profLbl.textContent = 'Routing Profiles';
    const profVal = document.createElement('span');
    profVal.className = 'diag-item-value';
    profVal.textContent = String(diag.routing_profiles_count ?? '—');
    profBox.appendChild(profLbl);
    profBox.appendChild(profVal);
    invGrid.appendChild(profBox);

    secInv.appendChild(invGrid);
    diagnosticsContentContainer.appendChild(secInv);

    // 5. Section 4: Operational Warnings & Degradation Feed
    const secWarn = document.createElement('div');
    secWarn.className = 'diag-section';

    const warnHeader = document.createElement('div');
    warnHeader.className = 'diag-section-header';
    const warnTitle = document.createElement('h3');
    warnTitle.className = 'diag-section-title';
    warnTitle.textContent = 'Operational Warnings & Diagnostics';
    warnHeader.appendChild(warnTitle);
    secWarn.appendChild(warnHeader);

    let hasWarnings = false;

    if (db.degraded && db.reason) {
      hasWarnings = true;
      const warnCard = document.createElement('div');
      warnCard.className = 'diag-warning-card';

      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('width', '16'); icon.setAttribute('height', '16');
      icon.setAttribute('viewBox', '0 0 24 24'); icon.setAttribute('fill', 'none');
      icon.setAttribute('stroke', 'currentColor'); icon.setAttribute('stroke-width', '2');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z');
      icon.appendChild(path);
      warnCard.appendChild(icon);

      const text = document.createElement('span');
      text.textContent = `Database Degradation: ${db.reason}`;
      warnCard.appendChild(text);

      secWarn.appendChild(warnCard);
    }

    if (diag.stale_models_count > 0) {
      hasWarnings = true;
      const staleWarn = document.createElement('div');
      staleWarn.className = 'diag-warning-card';

      const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      icon.setAttribute('width', '16'); icon.setAttribute('height', '16');
      icon.setAttribute('viewBox', '0 0 24 24'); icon.setAttribute('fill', 'none');
      icon.setAttribute('stroke', 'currentColor'); icon.setAttribute('stroke-width', '2');
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', 'm21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z');
      icon.appendChild(path);
      staleWarn.appendChild(icon);

      const text = document.createElement('span');
      text.textContent = `${diag.stale_models_count} model(s) are currently flagged as stale. Refresh catalog discovery to verify against live providers.`;
      staleWarn.appendChild(text);

      secWarn.appendChild(staleWarn);
    }

    if (!hasWarnings) {
      const cleanMsg = document.createElement('p');
      cleanMsg.className = 'diag-warning-empty';
      cleanMsg.textContent = 'No active operational warnings or persistence degradation detected.';
      secWarn.appendChild(cleanMsg);
    }

    diagnosticsContentContainer.appendChild(secWarn);
  }

  // Event Listeners — Auth
  authForm.addEventListener('submit', function (e) {
    e.preventDefault();
    authenticate();
  });

  authToggleBtn.addEventListener('click', function () {
    if (apiToken) {
      disconnect();
    } else {
      updateAuthState(false);
      apiTokenInput.focus();
    }
  });

  // Event Listeners — Refresh Controls
  refreshBtn.addEventListener('click', function () {
    fetchDashboardData();
  });

  if (refreshProvidersBtn) {
    refreshProvidersBtn.addEventListener('click', function () {
      if (!apiToken || isFetching) return;
      refreshProvidersBtn.disabled = true;
      if (refreshProvidersIcon) refreshProvidersIcon.classList.add('spin');
      fetchDashboardData().finally(() => {
        refreshProvidersBtn.disabled = false;
        if (refreshProvidersIcon) refreshProvidersIcon.classList.remove('spin');
      });
    });
  }

  if (refreshCatalogBtn) {
    refreshCatalogBtn.addEventListener('click', function () {
      refreshCatalogDiscovery();
    });
  }

  if (refreshProfilesBtn) {
    refreshProfilesBtn.addEventListener('click', function () {
      fetchProfilesData();
    });
  }

  if (refreshDiagnosticsBtn) {
    refreshDiagnosticsBtn.addEventListener('click', function () {
      fetchDiagnosticsData();
    });
  }

  if (catalogProviderFilter) {
    catalogProviderFilter.addEventListener('change', function () {
      selectedCatalogProvider = catalogProviderFilter.value;
      if (refreshCatalogBtnText) {
        refreshCatalogBtnText.textContent = selectedCatalogProvider
          ? `Refresh ${selectedCatalogProvider}`
          : 'Refresh Catalog';
      }
      renderCatalogCards();
    });
  }

  // Event Listeners — Navigation
  navLinkOverview.addEventListener('click', function (e) {
    e.preventDefault();
    switchView('overview');
  });

  navLinkProviders.addEventListener('click', function (e) {
    e.preventDefault();
    switchView('providers');
  });

  if (navLinkCatalog) {
    navLinkCatalog.addEventListener('click', function (e) {
      e.preventDefault();
      switchView('catalog');
    });
  }

  if (navLinkProfiles) {
    navLinkProfiles.addEventListener('click', function (e) {
      e.preventDefault();
      switchView('profiles');
    });
  }

  if (navLinkDiagnostics) {
    navLinkDiagnostics.addEventListener('click', function (e) {
      e.preventDefault();
      switchView('diagnostics');
    });
  }

  window.addEventListener('hashchange', function () {
    const hash = window.location.hash.replace(/^#/, '');
    const validViews = ['providers', 'catalog', 'profiles', 'routing', 'diagnostics'];
    const targetHash = validViews.includes(hash)
      ? (hash === 'routing' ? 'profiles' : hash)
      : 'overview';
    switchView(targetHash);
  });

  // Initial State on Page Load
  updateAuthState(false);
})();
