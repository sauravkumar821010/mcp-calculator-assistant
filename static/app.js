/**
 * Frontend JavaScript for the MCP-Powered AI Calculator Assistant
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const sendBtn = document.getElementById('sendBtn');
  const messagesList = document.getElementById('messagesList');
  const welcomeHero = document.getElementById('welcomeHero');
  const toolsList = document.getElementById('toolsList');
  const toolCount = document.getElementById('toolCount');
  const historyList = document.getElementById('historyList');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const modeBadge = document.getElementById('modeBadge');
  const openSettingsBtn = document.getElementById('openSettingsBtn');
  const settingsModal = document.getElementById('settingsModal');
  const closeSettingsBtn = document.getElementById('closeSettingsBtn');
  const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
  const saveSettingsBtn = document.getElementById('saveSettingsBtn');
  const apiKeyInput = document.getElementById('apiKeyInput');

  // Load initial status, tools, and history
  fetchStatus();
  fetchTools();
  fetchHistory();

  // Handle Preset Chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      userInput.value = query;
      userInput.focus();
      submitQuery(query);
    });
  });

  // Handle Chat Form Submit
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;
    submitQuery(query);
  });

  // Submit Query to Assistant
  async function submitQuery(query) {
    // Hide welcome hero on first message
    if (welcomeHero) {
      welcomeHero.style.display = 'none';
    }

    // Append User Message
    appendMessage('user', query);
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Show Loading Assistant Placeholder
    const loadingId = 'loading-' + Date.now();
    appendLoadingMessage(loadingId);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query })
      });

      const data = await response.json();
      removeLoadingMessage(loadingId);

      if (data.status === 'success' || data.answer) {
        appendAssistantMessage(data.answer, data.tool_calls || []);
        // Refresh history to show newly executed calculation
        fetchHistory();
      } else {
        appendAssistantMessage('Error: ' + (data.error || 'Failed to process calculation.'), []);
      }
    } catch (err) {
      removeLoadingMessage(loadingId);
      appendAssistantMessage('Network or server error: ' + err.message, []);
    } finally {
      userInput.disabled = false;
      sendBtn.disabled = false;
      userInput.focus();
    }
  }

  // Append User Message
  function appendMessage(role, text) {
    const row = document.createElement('div');
    row.className = 'message-row user-row';
    row.innerHTML = `
      <div class="message-avatar">👤</div>
      <div class="message-body">
        <div class="message-sender">You</div>
        <div class="message-content">${escapeHtml(text)}</div>
      </div>
    `;
    messagesList.appendChild(row);
    scrollToBottom();
  }

  // Append Assistant Message with Tool Cards
  function appendAssistantMessage(markdownText, toolCalls) {
    const row = document.createElement('div');
    row.className = 'message-row assistant-row';

    let toolCardsHtml = '';
    if (toolCalls && toolCalls.length > 0) {
      toolCalls.forEach(tc => {
        const toolName = tc.tool || 'MCP Tool';
        const argsStr = JSON.stringify(tc.args || {}, null, 2);
        const resStr = JSON.stringify(tc.result || {}, null, 2);

        toolCardsHtml += `
          <div class="tool-execution-card">
            <div class="tool-card-header">
              <span>⚡ MCP Invocation: <strong class="tool-badge">${escapeHtml(toolName)}</strong></span>
              <span style="font-size: 0.7rem; color: #94a3b8;">stdio JSON-RPC</span>
            </div>
            <div class="tool-card-body">
              <strong>Inputs:</strong>
              <pre>${escapeHtml(argsStr)}</pre>
              <strong style="display:inline-block; margin-top: 0.4rem;">Result:</strong>
              <pre>${escapeHtml(resStr)}</pre>
            </div>
          </div>
        `;
      });
    }

    const parsedHtml = (window.marked && typeof marked.parse === 'function') 
      ? marked.parse(markdownText) 
      : `<p>${escapeHtml(markdownText)}</p>`;

    row.innerHTML = `
      <div class="message-avatar">🤖</div>
      <div class="message-body">
        <div class="message-sender">MCP Calculator Assistant</div>
        <div class="message-content">
          ${toolCardsHtml}
          <div class="markdown-body">${parsedHtml}</div>
        </div>
      </div>
    `;
    messagesList.appendChild(row);
    scrollToBottom();
  }

  // Loading Indicator Placeholder
  function appendLoadingMessage(id) {
    const row = document.createElement('div');
    row.className = 'message-row assistant-row';
    row.id = id;
    row.innerHTML = `
      <div class="message-avatar">🤖</div>
      <div class="message-body">
        <div class="message-sender">MCP Calculator Assistant</div>
        <div class="message-content" style="color: #94a3b8; font-style: italic;">
          ⚡ Invoking MCP tools & reasoning...
        </div>
      </div>
    `;
    messagesList.appendChild(row);
    scrollToBottom();
  }

  function removeLoadingMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollToBottom() {
    messagesList.scrollTop = messagesList.scrollHeight;
  }

  // Fetch MCP Tools
  async function fetchTools() {
    try {
      const res = await fetch('/api/tools');
      const data = await res.json();
      if (data.status === 'success' && Array.isArray(data.tools)) {
        toolCount.textContent = data.tools.length;
        toolsList.innerHTML = '';
        data.tools.forEach(t => {
          const item = document.createElement('div');
          item.className = 'tool-item';
          const shortDesc = t.description ? t.description.split('\n')[0] : 'MCP Tool';
          item.innerHTML = `
            <div class="tool-name">${escapeHtml(t.name)}</div>
            <div class="tool-desc">${escapeHtml(shortDesc)}</div>
          `;
          toolsList.appendChild(item);
        });
      }
    } catch (err) {
      toolsList.innerHTML = '<div class="empty-state">Failed to load tools</div>';
    }
  }

  // Fetch Calculation History
  async function fetchHistory() {
    try {
      const res = await fetch('/api/history?limit=15');
      const data = await res.json();
      if (data.status === 'success' && Array.isArray(data.history)) {
        historyList.innerHTML = '';
        if (data.history.length === 0) {
          historyList.innerHTML = '<div class="empty-state">No calculations yet</div>';
          return;
        }
        data.history.slice().reverse().forEach(h => {
          const item = document.createElement('div');
          item.className = 'history-item';
          const inputPreview = JSON.stringify(h.inputs || {});
          item.innerHTML = `
            <div class="history-op">${escapeHtml(h.operation)} (${escapeHtml(inputPreview)})</div>
            <div class="history-res">${escapeHtml(String(h.result))}</div>
          `;
          historyList.appendChild(item);
        });
      }
    } catch (err) {
      historyList.innerHTML = '<div class="empty-state">Failed to load history</div>';
    }
  }

  // Clear History
  clearHistoryBtn.addEventListener('click', async () => {
    try {
      await fetch('/api/clear', { method: 'POST' });
      fetchHistory();
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  });

  // Fetch Status
  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.mode) {
        modeBadge.textContent = data.mode === 'gemini-llm' ? 'Gemini LLM' : 'Smart Agent';
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }

  // Modal Dialog Logic
  openSettingsBtn.addEventListener('click', () => {
    settingsModal.classList.add('active');
  });

  const closeModal = () => settingsModal.classList.remove('active');
  closeSettingsBtn.addEventListener('click', closeModal);
  cancelSettingsBtn.addEventListener('click', closeModal);

  saveSettingsBtn.addEventListener('click', async () => {
    const key = apiKeyInput.value.trim();
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key })
      });
      const data = await res.json();
      if (data.status === 'success') {
        modeBadge.textContent = data.mode === 'gemini-llm' ? 'Gemini LLM' : 'Smart Agent';
        closeModal();
      }
    } catch (err) {
      alert('Error updating configuration: ' + err.message);
    }
  });

  // Helper
  function escapeHtml(str) {
    if (typeof str !== 'string') str = String(str);
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
