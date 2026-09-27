/* App JavaScript for Graph8 Cost Optimizer */

let APP_STATE = {
  currentTab: 'dashboard',
  isDemoMode: true,
  currentBatch: null,
  lastSimulation: null,
  providers: [],
  jobs: []
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  // Pre-fill default API Key in Settings if available
  const defaultApiKey = "g8_live_d5bdbe58d53f3dd6c3fe98df782d6fb9d1aab767dd9c3c37328d069b6d14cfb0fd4acd16385ed14255b547ac134ddbbd";
  const apiKeyInput = document.getElementById('settings-api-key');
  if (apiKeyInput) {
    apiKeyInput.value = defaultApiKey;
  }

  checkConnectionStatus();
  fetchDashboard();
  fetchProviders();
  fetchJobs();
});

// TAB SWITCHING ROUTER
function switchTab(tabName) {
  APP_STATE.currentTab = tabName;

  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  const activeBtn = document.getElementById(`tab-nav-${tabName}`);
  if (activeBtn) activeBtn.classList.add('active');

  document.querySelectorAll('main > section').forEach(sec => sec.classList.add('hidden'));

  const targetSec = document.getElementById(`tab-${tabName}`);
  if (targetSec) targetSec.classList.remove('hidden');

  if (tabName === 'dashboard') fetchDashboard();
  if (tabName === 'providers') fetchProviders();
  if (tabName === 'jobs') fetchJobs();
  if (tabName === 'savings') fetchSavings();

  if (window.lucide) lucide.createIcons();
}

// CHECK CONNECTION STATUS
async function checkConnectionStatus() {
  try {
    const res = await fetch('/api/v1/connection/status');
    const data = await res.json();
    
    const dot = document.getElementById('conn-dot');
    const text = document.getElementById('conn-status-text');
    const badge = document.getElementById('header-mode-badge');
    const setBadge = document.getElementById('settings-status-badge');

    if (data.is_connected) {
      dot.className = "w-2 h-2 rounded-full bg-[#047857]";
      text.innerText = "Connected (Live API)";
      badge.className = "px-2 py-0.5 text-[11px] font-semibold rounded-md badge-live";
      badge.innerHTML = '<i data-lucide="check" class="w-3 h-3 inline mr-1"></i>LIVE API';
      if (setBadge) {
        setBadge.className = "px-3 py-1 rounded-md text-xs font-bold badge-live";
        setBadge.innerText = "LIVE GRAPH8 API";
      }
    } else {
      dot.className = "w-2 h-2 rounded-full bg-amber-500";
      text.innerText = "Demo Mode";
      badge.className = "px-2 py-0.5 text-[11px] font-semibold rounded-md badge-demo";
      badge.innerHTML = '<i data-lucide="flask-conical" class="w-3 h-3 inline mr-1"></i>DEMO MODE';
      if (setBadge) {
        setBadge.className = "px-3 py-1 rounded-md text-xs font-bold badge-demo";
        setBadge.innerText = "DEMO MODE";
      }
    }
    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error("Connection check error:", e);
  }
}

// TEST CONNECTION FROM SETTINGS
async function testConnectionFromSettings() {
  const apiKeyInput = document.getElementById('settings-api-key');
  const apiKey = apiKeyInput ? apiKeyInput.value.trim() : "";
  const resultMsg = document.getElementById('connection-result-msg');
  resultMsg.innerText = "Testing connection...";

  try {
    const res = await fetch('/api/v1/connection/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });
    const data = await res.json();

    if (data.success) {
      resultMsg.className = "text-xs text-[#047857] font-semibold";
      resultMsg.innerText = "Connected to Live Graph8 API!";
    } else {
      resultMsg.className = "text-xs text-[#C2410C] font-semibold";
      resultMsg.innerText = "Could not ping Live API. Reverted to Demo Mode with realistic data.";
    }
    checkConnectionStatus();
  } catch (e) {
    resultMsg.className = "text-xs text-[#B91C1C] font-semibold";
    resultMsg.innerText = "Connection test failed: " + e.message;
  }
}

// LOAD DEMO DATASET
async function loadDemoDataset(count) {
  try {
    const res = await fetch(`/api/v1/demo/generate?count=${count}`);
    const data = await res.json();

    APP_STATE.currentBatch = data.stats;
    renderBatchStats(data.stats);
    runOptimizationSimulation();
  } catch (e) {
    alert("Failed to load demo dataset: " + e.message);
  }
}

// HANDLE CSV FILE UPLOAD
async function handleCsvUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    const csvContent = e.target.result;
    try {
      const res = await fetch('/api/v1/contacts/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csv_content: csvContent })
      });
      const data = await res.json();

      if (data.error) {
        alert("Upload error: " + data.error);
        return;
      }

      APP_STATE.currentBatch = data.stats;
      renderBatchStats(data.stats);
      runOptimizationSimulation();
    } catch (err) {
      alert("Upload error: " + err.message);
    }
  };
  reader.readAsText(file);
}

// RENDER BATCH STATS CARDS
function renderBatchStats(stats) {
  const card = document.getElementById('batch-stats-card');
  if (!card) return;
  card.classList.remove('hidden');

  document.getElementById('stat-total').innerText = (stats.total_contacts || 0).toLocaleString();
  document.getElementById('stat-with-email').innerText = (stats.contacts_with_existing_email || 0).toLocaleString();
  document.getElementById('stat-missing-email').innerText = (stats.contacts_missing_email || 0).toLocaleString();
  document.getElementById('stat-with-domain').innerText = (stats.contacts_with_company_domain || 0).toLocaleString();
  document.getElementById('stat-already-enriched').innerText = (stats.contacts_already_enriched || 0).toLocaleString();
  document.getElementById('stat-eligible').innerText = (stats.contacts_eligible_for_enrichment || 0).toLocaleString();
}

// RUN OPTIMIZATION SIMULATION
async function runOptimizationSimulation() {
  const maxDrop = parseFloat(document.getElementById('input-max-drop').value);
  const minSavings = parseFloat(document.getElementById('input-min-savings').value);
  const maxLatency = parseFloat(document.getElementById('input-max-latency').value);

  const payload = {
    constraints: {
      max_success_drop_percent: maxDrop,
      min_savings_percent: minSavings,
      max_latency_sec: maxLatency
    }
  };

  try {
    const res = await fetch('/api/v1/optimizer/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const sim = await res.json();

    if (sim.error) {
      alert("Simulation error: " + sim.error);
      return;
    }

    APP_STATE.lastSimulation = sim;
    renderSimulationResults(sim);
  } catch (e) {
    console.error("Simulation error:", e);
  }
}

// RENDER SIMULATION RESULTS
function renderSimulationResults(sim) {
  const container = document.getElementById('simulation-results-container');
  if (!container) return;
  container.classList.remove('hidden');

  const curr = sim.current_strategy;
  const opt = sim.optimized_strategy;
  const comp = sim.comparison;
  const guard = sim.guardrails;

  document.getElementById('sim-savings-highlight').innerText = `${comp.estimated_credits_saved.toLocaleString()} Credits (${comp.estimated_savings_percent}%)`;
  
  // Current Card
  document.getElementById('curr-chain-display').innerText = curr.chain.join(' → ');
  document.getElementById('curr-credits').innerText = curr.expected_credits.toLocaleString();
  document.getElementById('curr-successes').innerText = curr.expected_successful_emails.toLocaleString();
  document.getElementById('curr-cost-per-success').innerText = `${curr.expected_cost_per_success} Credits`;

  // Optimized Card
  document.getElementById('opt-chain-display').innerText = "Segment-Smart Waterfall (Prospeo / Hunter / Dropcontact)";
  document.getElementById('opt-credits').innerText = opt.expected_credits.toLocaleString();
  document.getElementById('opt-successes').innerText = opt.expected_successful_emails.toLocaleString();
  document.getElementById('opt-cost-per-success').innerText = `${opt.expected_cost_per_success} Credits`;

  // Render Segment Explanations
  const segGrid = document.getElementById('segment-explanation-grid');
  segGrid.innerHTML = '';

  const routing = opt.segment_routing || {};
  Object.keys(routing).forEach(segKey => {
    const r = routing[segKey];
    const card = document.createElement('div');
    card.className = 'bg-white p-3.5 rounded-lg border border-[#E2DDD5] space-y-1 text-xs';
    card.innerHTML = `
      <div class="font-bold text-[#7D2DF3]">${segKey} (${r.contact_count.toLocaleString()} contacts)</div>
      <div class="text-[#251B3A] font-semibold">${r.recommended_chain.join(' → ')}</div>
      <div class="text-[11px] text-[#737373]">
        Cost / Success: <span class="text-[#047857] font-bold">${r.expected_cost_per_success} credits</span> (${r.success_rate}% success)
      </div>
    `;
    segGrid.appendChild(card);
  });

  // Guardrail Banner
  const banner = document.getElementById('guardrail-status-banner');
  if (guard.passed) {
    banner.className = "flex items-center space-x-2 text-xs font-semibold text-[#047857]";
    banner.innerHTML = '<i data-lucide="check-circle-2" class="w-4 h-4"></i><span>All Safety Guardrails Passed</span>';
  } else {
    banner.className = "flex items-center space-x-2 text-xs font-semibold text-[#B91C1C]";
    banner.innerHTML = `<i data-lucide="alert-triangle" class="w-4 h-4"></i><span>REJECTED: ${guard.rejection_reasons[0]}</span>`;
  }

  container.scrollIntoView({ behavior: 'smooth' });
  if (window.lucide) lucide.createIcons();
}

// MODAL CONTROLS
function openReviewModal() {
  const sim = APP_STATE.lastSimulation;
  if (!sim) return;

  const modal = document.getElementById('review-modal');
  const body = document.getElementById('review-modal-body');

  body.innerHTML = `
    <div class="p-4 bg-[#F8F6F1] rounded-lg border border-[#E2DDD5] space-y-1">
      <div class="font-bold text-[#251B3A]">Current Strategy Baseline</div>
      <div>Waterfall: ${sim.current_strategy.chain.join(' → ')}</div>
      <div>Expected Credits: ${sim.current_strategy.expected_credits.toLocaleString()}</div>
      <div>Expected Cost / Success: ${sim.current_strategy.expected_cost_per_success} credits</div>
    </div>

    <div class="p-4 bg-[#ECFDF5] rounded-lg border border-[#A7F3D0] space-y-1">
      <div class="font-bold text-[#047857]">Proposed Optimization Plan</div>
      <div>Expected Credits: ${sim.optimized_strategy.expected_credits.toLocaleString()}</div>
      <div>Net Savings: ${sim.comparison.estimated_credits_saved.toLocaleString()} Credits (${sim.comparison.estimated_savings_percent}%)</div>
      <div>Expected Cost / Success: ${sim.optimized_strategy.expected_cost_per_success} credits</div>
    </div>

    <div class="space-y-1 pt-2">
      <div class="font-semibold text-[#251B3A]">System Assumptions:</div>
      <ul class="list-disc list-inside text-[11px] text-[#737373]">
        ${sim.assumptions.map(a => `<li>${a}</li>`).join('')}
      </ul>
    </div>
  `;

  modal.classList.remove('hidden');
}

function closeReviewModal() {
  document.getElementById('review-modal').classList.add('hidden');
}

function openApplyConfirmModal() {
  const sim = APP_STATE.lastSimulation;
  if (!sim) return;

  document.getElementById('modal-confirm-credits').innerText = sim.optimized_strategy.expected_credits.toLocaleString();
  document.getElementById('modal-confirm-savings').innerText = `${sim.comparison.estimated_credits_saved.toLocaleString()} Credits (${sim.comparison.estimated_savings_percent}%)`;
  document.getElementById('modal-confirm-success').innerText = `${sim.optimized_strategy.expected_success_rate}%`;

  document.getElementById('apply-modal').classList.remove('hidden');
}

function closeApplyModal() {
  document.getElementById('apply-modal').classList.add('hidden');
}

// CONFIRM AND EXECUTE OPTIMIZATION
async function confirmAndExecuteOptimization() {
  closeApplyModal();

  const tracker = document.getElementById('execution-tracker-container');
  tracker.classList.remove('hidden');
  tracker.scrollIntoView({ behavior: 'smooth' });

  document.getElementById('exec-progress-pct').innerText = '0%';
  document.getElementById('exec-progress-fill').style.width = '0%';
  document.getElementById('exec-title').innerText = "Executing Optimized Enrichment Job";
  document.getElementById('exec-spent-credits').innerText = "0";
  document.getElementById('exec-success-count').innerText = "0";
  document.getElementById('exec-cost-per-success').innerText = "0.00";
  document.getElementById('exec-saved-credits').innerText = "0";

  let p = 0;
  const interval = setInterval(() => {
    p += 15;
    if (p > 90) p = 90;
    document.getElementById('exec-progress-pct').innerText = `${p}%`;
    document.getElementById('exec-progress-fill').style.width = `${p}%`;
  }, 300);

  try {
    const res = await fetch('/api/v1/optimizer/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulation_plan: APP_STATE.lastSimulation })
    });
    const exec = await res.json();

    clearInterval(interval);

    document.getElementById('exec-progress-pct').innerText = '100%';
    document.getElementById('exec-progress-fill').style.width = '100%';
    document.getElementById('exec-title').innerText = "Optimization Execution Completed";
    document.getElementById('exec-subtitle').innerText = `Batch of ${exec.total_contacts.toLocaleString()} contacts processed in ${exec.elapsed_seconds}s.`;

    document.getElementById('exec-spent-credits').innerText = exec.actual_credits_spent.toLocaleString();
    document.getElementById('exec-success-count').innerText = exec.actual_successful_emails.toLocaleString();
    document.getElementById('exec-cost-per-success').innerText = exec.actual_cost_per_success;
    document.getElementById('exec-saved-credits').innerText = exec.actual_savings_credits.toLocaleString();

    const learnBox = document.getElementById('learning-update-summary');
    const learnList = document.getElementById('learning-updates-list');
    learnBox.classList.remove('hidden');
    learnList.innerHTML = '';

    const updates = exec.learning_updates.updated_providers || [];
    updates.forEach(u => {
      const item = document.createElement('div');
      item.className = 'bg-white p-3 rounded border border-[#E2DDD5] flex justify-between items-center';
      item.innerHTML = `
        <span><strong class="text-[#251B3A]">${u.provider_name}</strong> historical success rate updated</span>
        <span class="text-[#047857] font-mono font-bold">${u.previous_success_rate}% → ${u.new_success_rate}% (${u.new_sample_size.toLocaleString()} samples)</span>
      `;
      learnList.appendChild(item);
    });

    fetchDashboard();
    fetchJobs();
  } catch (e) {
    clearInterval(interval);
    alert("Execution error: " + e.message);
  }
}

// FETCH DASHBOARD METRICS
async function fetchDashboard() {
  try {
    const res = await fetch('/api/v1/dashboard');
    const data = await res.json();

    const m = data.metrics;
    document.getElementById('dash-total-saved-credits').innerText = m.actual_credits_saved.toLocaleString();
    document.getElementById('dash-savings-pct').innerText = `${m.actual_savings_percent}% reduction vs baseline`;
    document.getElementById('dash-avg-cost-success').innerText = `${m.avg_cost_per_successful_enrichment} Credits`;
    document.getElementById('dash-total-contacts').innerText = m.total_contacts_enriched.toLocaleString();

    const segList = document.getElementById('dash-top-segments-list');
    if (segList) {
      segList.innerHTML = '';
      (data.top_expensive_segments || []).forEach(s => {
        const row = document.createElement('div');
        row.className = 'bg-[#F8F6F1] p-3.5 rounded-lg border border-[#E2DDD5] flex items-center justify-between text-xs';
        row.innerHTML = `
          <div>
            <div class="font-bold text-[#251B3A]">${s.segment}</div>
            <div class="text-[11px] text-[#737373]">${s.recommendation}</div>
          </div>
          <div class="text-right font-mono font-bold text-[#C2410C]">${s.avg_cost_per_success}</div>
        `;
        segList.appendChild(row);
      });
    }

    const jobsList = document.getElementById('dash-recent-jobs-list');
    if (jobsList) {
      jobsList.innerHTML = '';
      (data.recent_jobs || []).slice(0, 3).forEach(j => {
        const row = document.createElement('div');
        row.className = 'bg-[#F8F6F1] p-3.5 rounded-lg border border-[#E2DDD5] flex items-center justify-between text-xs';
        row.innerHTML = `
          <div>
            <div class="font-bold text-[#251B3A]">${j.batch_name}</div>
            <div class="text-[11px] text-[#737373]">${j.contacts_count.toLocaleString()} contacts • ${j.status}</div>
          </div>
          <div class="text-right">
            <div class="text-[#047857] font-bold">+${j.actual_savings.toLocaleString()} Credits Saved</div>
            <div class="text-[11px] text-[#737373]">${j.success_rate}% success</div>
          </div>
        `;
        jobsList.appendChild(row);
      });
    }

  } catch (e) {
    console.error("Dashboard fetch error:", e);
  }
}

// FETCH PROVIDERS INVENTORY
async function fetchProviders() {
  try {
    const res = await fetch('/api/v1/providers');
    const data = await res.json();
    APP_STATE.providers = data.providers;

    const tbody = document.getElementById('providers-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.providers.forEach(p => {
      const tr = document.createElement('tr');
      tr.className = "hover:bg-[#F8F6F1] transition-colors";
      
      const isWarn = p.sample_size < 30;
      const warnBadge = isWarn ? `<span class="ml-2 px-1.5 py-0.5 text-[10px] badge-warning rounded">Low Sample</span>` : '';

      tr.innerHTML = `
        <td class="p-3.5 font-bold text-[#251B3A] flex items-center">
          ${p.name} ${warnBadge}
        </td>
        <td class="p-3.5 text-xs text-[#737373]">${p.action}</td>
        <td class="p-3.5 font-mono text-[#251B3A]">${p.credit_cost} credits</td>
        <td class="p-3.5 font-mono text-[#047857] font-bold">${(p.success_rate * 100).toFixed(1)}%</td>
        <td class="p-3.5 font-mono text-[#7D2DF3] font-bold">${p.expected_cost_per_success} credits</td>
        <td class="p-3.5 text-xs text-[#251B3A]">${p.avg_response_time}s</td>
        <td class="p-3.5 text-xs text-[#737373] font-mono">${p.sample_size.toLocaleString()}</td>
        <td class="p-3.5">
          <span class="px-2 py-0.5 text-[11px] rounded ${p.is_byok ? 'badge-byok' : 'bg-[#E2DDD5] text-[#251B3A]'}">
            ${p.is_byok ? 'BYOK' : 'System'}
          </span>
        </td>
        <td class="p-3.5 text-center">
          <button onclick="editProviderCost('${p.id}')" class="btn-secondary text-xs py-1 px-2.5">Edit</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

  } catch (e) {
    console.error("Providers fetch error:", e);
  }
}

// EDIT PROVIDER COST MANUAL OVERRIDE
async function editProviderCost(providerId) {
  const newCost = prompt("Enter new credit cost per attempt for provider:", "1.5");
  if (!newCost) return;

  try {
    const res = await fetch(`/api/v1/providers/${providerId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credit_cost: parseFloat(newCost) })
    });
    const data = await res.json();
    if (data.success) {
      fetchProviders();
    }
  } catch (e) {
    alert("Update failed: " + e.message);
  }
}

// FETCH JOBS HISTORY
async function fetchJobs() {
  try {
    const res = await fetch('/api/v1/jobs');
    const data = await res.json();
    APP_STATE.jobs = data.jobs;

    const tbody = document.getElementById('jobs-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    data.jobs.forEach(j => {
      const tr = document.createElement('tr');
      tr.className = "hover:bg-[#F8F6F1] transition-colors";
      const dateStr = new Date(j.created_at * 1000).toLocaleDateString();

      tr.innerHTML = `
        <td class="p-3.5 text-xs font-mono text-[#737373]">${dateStr}<br><span class="text-[#737373]">${j.id}</span></td>
        <td class="p-3.5 font-bold text-[#251B3A]">${j.batch_name}</td>
        <td class="p-3.5 text-xs text-[#251B3A] font-mono">${j.contacts_count.toLocaleString()}</td>
        <td class="p-3.5 text-xs text-[#737373]">${j.original_strategy.chain ? j.original_strategy.chain.join(' → ') : 'Default'}</td>
        <td class="p-3.5 text-xs text-[#047857] font-semibold">${j.optimized_strategy.chain ? j.optimized_strategy.chain.join(' → ') : 'Smart Waterfall'}</td>
        <td class="p-3.5 text-xs font-mono text-[#251B3A]">${j.actual_cost.toLocaleString()} credits</td>
        <td class="p-3.5 text-xs font-mono font-bold text-[#047857]">+${j.actual_savings.toLocaleString()} credits</td>
        <td class="p-3.5 text-xs font-mono text-[#7D2DF3]">${j.success_rate}%</td>
        <td class="p-3.5 text-center">
          <button onclick="inspectJobCalculation('${j.id}')" class="btn-secondary text-xs py-1 px-2.5">Inspect</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

  } catch (e) {
    console.error("Jobs fetch error:", e);
  }
}

// INSPECT JOB CALCULATION MODAL
function inspectJobCalculation(jobId) {
  const job = APP_STATE.jobs.find(j => j.id === jobId);
  if (!job) return;

  alert(`Job Calculation Details (${job.id}):\n\nBatch Name: ${job.batch_name}\nContacts: ${job.contacts_count.toLocaleString()}\nBaseline Cost: ${job.baseline_cost.toLocaleString()} credits\nActual Spent: ${job.actual_cost.toLocaleString()} credits\nActual Savings: ${job.actual_savings.toLocaleString()} credits\nSuccess Rate: ${job.success_rate}%\n\nOptimization Rationale: Segment-smart waterfall routing calculated expected cost per success across historical provider rates.`);
}

// FETCH SAVINGS ANALYTICS
async function fetchSavings() {
  try {
    const res = await fetch('/api/v1/savings');
    const data = await res.json();

    document.getElementById('sav-baseline').innerText = `${data.baseline_credits_without_optimizer.toLocaleString()} Credits`;
    document.getElementById('sav-actual').innerText = `${data.actual_credits_saved.toLocaleString()} Credits (${data.actual_savings_percent}%)`;
    document.getElementById('sav-projected').innerText = `${data.projected_monthly_savings.toLocaleString()} Credits`;

    const list = document.getElementById('savings-assumptions-list');
    if (list) {
      list.innerHTML = '';
      (data.assumptions || []).forEach(a => {
        const li = document.createElement('li');
        li.innerText = a;
        list.appendChild(li);
      });
    }

  } catch (e) {
    console.error("Savings fetch error:", e);
  }
}
