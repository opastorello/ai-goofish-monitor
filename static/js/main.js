document.addEventListener('DOMContentLoaded', function() {
    const mainContent = document.getElementById('main-content');
    const navLinks = document.querySelectorAll('.nav-link');
    let logRefreshInterval = null;
    let taskRefreshInterval = null;

    // --- Templates for each section ---
    const templates = {
        tasks: () => `
            <section id="tasks-section" class="content-section">
                <div class="section-header">
                    <h2>Gerenciamento de tarefas</h2>
                    <button id="add-task-btn" class="control-button primary-btn">➕ Criar nova tarefa</button>
                </div>
                <div id="tasks-table-container">
                    <p>Carregando lista de tarefas...</p>
                </div>
            </section>`,
        results: () => `
            <section id="results-section" class="content-section">
                <div class="section-header">
                    <h2>Visualizar resultados</h2>
                </div>
                <div class="results-filter-bar">
                    <select id="result-file-selector"><option>Carregando...</option></select>
                    <label>
                        <input type="checkbox" id="recommended-only-checkbox">
                        Mostrar apenas recomendações da IA
                    </label>
                    <select id="sort-by-selector">
                        <option value="crawl_time">Por hora de coleta</option>
                        <option value="publish_time">Por hora de publicação</option>
                        <option value="price">Por preço</option>
                    </select>
                    <select id="sort-order-selector">
                        <option value="desc">Descendente</option>
                        <option value="asc">Ascendente</option>
                    </select>
                    <button id="refresh-results-btn" class="control-button">🔄 Atualizar</button>
                    <button id="delete-results-btn" class="control-button danger-btn" disabled>🗑️ Excluir resultados</button>
                </div>
                <div id="results-grid-container">
                    <p>Selecione um arquivo de resultados primeiro.</p>
                </div>
            </section>`,
        logs: () => `
            <section id="logs-section" class="content-section">
                <div class="section-header">
                    <h2>Logs de execução</h2>
                    <div class="log-controls">
                        <label>
                            <input type="checkbox" id="auto-refresh-logs-checkbox">
                            Atualizar automaticamente
                        </label>
                        <button id="refresh-logs-btn" class="control-button">🔄 Atualizar</button>
                        <button id="clear-logs-btn" class="control-button danger-btn">🗑️ Limpar logs</button>
                    </div>
                </div>
                <pre id="log-content-container">Carregando logs...</pre>
            </section>`,
        settings: () => `
            <section id="settings-section" class="content-section">
                <h2>Configurações do sistema</h2>
                <div class="settings-card">
                    <h3>Verificação de status do sistema</h3>
                    <div id="system-status-container"><p>Carregando status...</p></div>
                </div>
                <div class="settings-card">
                    <h3>Configuração de notificações</h3>
                    <div id="notification-settings-container">
                        <p>Carregando configuração de notificações...</p>
                    </div>
                </div>
                <div class="settings-card">
                    <h3>Gerenciamento de Prompts</h3>
                    <div class="prompt-manager">
                        <div class="prompt-list-container">
                            <label for="prompt-selector">Selecione o Prompt para editar:</label>
                            <select id="prompt-selector"><option>Carregando...</option></select>
                        </div>
                        <div class="prompt-editor-container">
                            <textarea id="prompt-editor" spellcheck="false" disabled placeholder="Selecione um arquivo de Prompt acima para editar..."></textarea>
                            <button id="save-prompt-btn" class="control-button primary-btn" disabled>Salvar alterações</button>
                        </div>
                    </div>
                </div>
            </section>`
    };

    // --- API Functions ---
    async function fetchNotificationSettings() {
        try {
            const response = await fetch('/api/settings/notifications');
            if (!response.ok) throw new Error('Não foi possível obter as configurações de notificação');
            return await response.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    async function fetchAISettings() {
        try {
            const response = await fetch('/api/settings/ai');
            if (!response.ok) throw new Error('Não foi possível obter as configurações de IA');
            return await response.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    async function updateAISettings(settings) {
        try {
            const response = await fetch('/api/settings/ai', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao atualizar as configurações de IA');
            }
            return await response.json();
        } catch (error) {
            console.error('Não foi possível atualizar as configurações de IA:', error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function testAISettings(settings) {
        try {
            const response = await fetch('/api/settings/ai/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao testar as configurações de IA');
            }
            return await response.json();
        } catch (error) {
            console.error('Não foi possível testar as configurações de IA:', error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function updateNotificationSettings(settings) {
        try {
            const response = await fetch('/api/settings/notifications', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(settings),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao atualizar as configurações de notificações');
            }
            return await response.json();
        } catch (error) {
            console.error('Não foi possível atualizar as configurações de notificações:', error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function fetchPrompts() {
        try {
            const response = await fetch('/api/prompts');
            if (!response.ok) throw new Error('Não foi possível obter a lista de Prompts');
            return await response.json();
        } catch (error) {
            console.error(error);
            return [];
        }
    }

    async function fetchPromptContent(filename) {
        try {
            const response = await fetch(`/api/prompts/${filename}`);
            if (!response.ok) throw new Error(`Não foi possível obter o conteúdo do arquivo de Prompt ${filename}`);
            return await response.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    async function updatePrompt(filename, content) {
        try {
            const response = await fetch(`/api/prompts/${filename}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: content}),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao atualizar o Prompt');
            }
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível atualizar o Prompt ${filename}:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function createTaskWithAI(data) {
        try {
            const response = await fetch(`/api/tasks/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao criar tarefa com IA');
            }
            console.log(`Tarefa criada pela IA com sucesso!`);
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível criar a tarefa com IA:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function startSingleTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/start/${taskId}`, {
                method: 'POST',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao iniciar a tarefa');
            }
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível iniciar a tarefa ${taskId}:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function stopSingleTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/stop/${taskId}`, {
                method: 'POST',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao parar a tarefa');
            }
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível parar a tarefa ${taskId}:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function deleteTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao excluir a tarefa');
            }
            console.log(`Tarefa ${taskId} excluída com sucesso!`);
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível excluir a tarefa ${taskId}:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function updateTask(taskId, data) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao atualizar a tarefa');
            }
            console.log(`Tarefa ${taskId} atualizada com sucesso!`);
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível atualizar a tarefa ${taskId}:`, error);
            // TODO: Use a more elegant notification system
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function fetchTasks() {
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("Não foi possível obter a lista de tarefas:", error);
            return null;
        }
    }

    async function fetchResultFiles() {
        try {
            const response = await fetch('/api/results/files');
            if (!response.ok) throw new Error('Não foi possível obter a lista de arquivos de resultados');
            return await response.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    async function deleteResultFile(filename) {
        try {
            const response = await fetch(`/api/results/files/${filename}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Falha ao excluir o arquivo de resultados');
            }
            return await response.json();
        } catch (error) {
            console.error(`Não foi possível excluir o arquivo de resultados ${filename}:`, error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function fetchResultContent(filename, recommendedOnly, sortBy, sortOrder) {
        try {
            const params = new URLSearchParams({
                page: 1,
                limit: 100, // Fetch a decent number of items
                recommended_only: recommendedOnly,
                sort_by: sortBy,
                sort_order: sortOrder
            });
            const response = await fetch(`/api/results/${filename}?${params}`);
            if (!response.ok) throw new Error(`Não foi possível obter o conteúdo do arquivo ${filename}`);
            return await response.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    async function fetchSystemStatus() {
        try {
            const response = await fetch('/api/settings/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("Não foi possível obter o status do sistema:", error);
            return null;
        }
    }

    async function clearLogs() {
        try {
            const response = await fetch('/api/logs', {method: 'DELETE'});
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Falha ao limpar os logs');
            }
            return await response.json();
        } catch (error) {
            console.error("Não foi possível limpar os logs:", error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function deleteLoginState() {
        try {
            const response = await fetch('/api/login-state', {method: 'DELETE'});
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Falha ao excluir as credenciais de login');
            }
            return await response.json();
        } catch (error) {
            console.error("Não foi possível excluir as credenciais de login:", error);
            alert(`Erro: ${error.message}`);
            return null;
        }
    }

    async function fetchLogs(fromPos = 0) {
        try {
            const response = await fetch(`/api/logs?from_pos=${fromPos}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error("Não foi possível obter os logs:", error);
            return {new_content: `\nFalha ao carregar logs: ${error.message}`, new_pos: fromPos};
        }
    }

    // --- Render Functions ---
    function renderLoginStatusWidget(status) {
        const container = document.getElementById('login-status-widget-container');
        if (!container) return;

        const loginState = status.login_state_file;
        let content = '';

        if (loginState && loginState.exists) {
            content = `
                <div class="login-status-widget">
                    <span class="status-text status-ok">✓ Conectado</span>
                    <div class="dropdown-menu">
                        <a href="#" class="dropdown-item" id="update-login-state-btn-widget">Atualizar manualmente</a>
                        <a href="#" class="dropdown-item delete" id="delete-login-state-btn-widget">Remover credenciais</a>
                    </div>
                </div>
            `;
        } else {
            content = `
                <div class="login-status-widget">
                    <span class="status-text status-error" id="update-login-state-btn-widget">! Goofish desconectado (clique para configurar)</span>
                </div>
            `;
        }
        container.innerHTML = content;
    }

    function renderNotificationSettings(settings) {
        if (!settings) return '<p>Não foi possível carregar as configurações de notificação.</p>';

        return `
            <form id="notification-settings-form">
                <div class="form-group">
                    <label for="ntfy-topic-url">Ntfy Topic URL</label>
                    <input type="text" id="ntfy-topic-url" name="NTFY_TOPIC_URL" value="${settings.NTFY_TOPIC_URL || ''}" placeholder="Ex.: https://ntfy.sh/your_topic">
                    <p class="form-hint">Usado para enviar notificações para o serviço ntfy.sh</p>
                </div>
                
                <div class="form-group">
                    <label for="gotify-url">Gotify URL</label>
                    <input type="text" id="gotify-url" name="GOTIFY_URL" value="${settings.GOTIFY_URL || ''}" placeholder="Ex.: https://push.example.de">
                    <p class="form-hint">Endereço do serviço Gotify</p>
                </div>
                
                <div class="form-group">
                    <label for="gotify-token">Gotify Token</label>
                    <input type="text" id="gotify-token" name="GOTIFY_TOKEN" value="${settings.GOTIFY_TOKEN || ''}" placeholder="Ex.: your_gotify_token">
                    <p class="form-hint">Token do aplicativo Gotify</p>
                </div>
                
                <div class="form-group">
                    <label for="bark-url">Bark URL</label>
                    <input type="text" id="bark-url" name="BARK_URL" value="${settings.BARK_URL || ''}" placeholder="Ex.: https://api.day.app/your_key">
                    <p class="form-hint">URL de envio do Bark</p>
                </div>
                
                <div class="form-group">
                    <label for="wx-bot-url">URL do robô do WeCom</label>
                    <input type="text" id="wx-bot-url" name="WX_BOT_URL" value="${settings.WX_BOT_URL || ''}" placeholder="Ex.: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your_key">
                    <p class="form-hint">Webhook do robô do WeCom</p>
                </div>
                
                <div class="form-group">
                    <label for="telegram-bot-token">Telegram Bot Token</label>
                    <input type="text" id="telegram-bot-token" name="TELEGRAM_BOT_TOKEN" value="${settings.TELEGRAM_BOT_TOKEN || ''}" placeholder="Ex.: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789">
                    <p class="form-hint">Token do bot do Telegram obtido com o @BotFather</p>
                </div>
                
                <div class="form-group">
                    <label for="telegram-chat-id">Telegram Chat ID</label>
                    <input type="text" id="telegram-chat-id" name="TELEGRAM_CHAT_ID" value="${settings.TELEGRAM_CHAT_ID || ''}" placeholder="Ex.: 123456789">
                    <p class="form-hint">ID de chat do Telegram obtido com @userinfobot</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-url">URL de Webhook genérico</label>
                    <input type="text" id="webhook-url" name="WEBHOOK_URL" value="${settings.WEBHOOK_URL || ''}" placeholder="Ex.: https://your-webhook-url.com/endpoint">
                    <p class="form-hint">Endereço do Webhook genérico</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-method">Método do Webhook</label>
                    <select id="webhook-method" name="WEBHOOK_METHOD">
                        <option value="POST" ${settings.WEBHOOK_METHOD === 'POST' ? 'selected' : ''}>POST</option>
                        <option value="GET" ${settings.WEBHOOK_METHOD === 'GET' ? 'selected' : ''}>GET</option>
                    </select>
                    <p class="form-hint">Método da requisição do Webhook</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-headers">Cabeçalhos do Webhook (JSON)</label>
                    <textarea id="webhook-headers" name="WEBHOOK_HEADERS" rows="3" placeholder='Ex.: {"Authorization": "Bearer token"}'>${settings.WEBHOOK_HEADERS || ''}</textarea>
                    <p class="form-hint">Deve ser uma string JSON válida</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-content-type">Tipo de conteúdo do Webhook</label>
                    <select id="webhook-content-type" name="WEBHOOK_CONTENT_TYPE">
                        <option value="JSON" ${settings.WEBHOOK_CONTENT_TYPE === 'JSON' ? 'selected' : ''}>JSON</option>
                        <option value="FORM" ${settings.WEBHOOK_CONTENT_TYPE === 'FORM' ? 'selected' : ''}>FORM</option>
                    </select>
                    <p class="form-hint">Tipo de conteúdo para requisições POST</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-query-parameters">Parâmetros de consulta do Webhook (JSON)</label>
                    <textarea id="webhook-query-parameters" name="WEBHOOK_QUERY_PARAMETERS" rows="3" placeholder='Ex.: {"param1": "value1"}'>${settings.WEBHOOK_QUERY_PARAMETERS || ''}</textarea>
                    <p class="form-hint">Parâmetros de consulta para GET; suporta os placeholders \${title} e \${content}</p>
                </div>
                
                <div class="form-group">
                    <label for="webhook-body">Corpo do Webhook (JSON)</label>
                    <textarea id="webhook-body" name="WEBHOOK_BODY" rows="3" placeholder='Ex.: {"message": "\${content}"}'>${settings.WEBHOOK_BODY || ''}</textarea>
                    <p class="form-hint">Corpo da requisição POST; suporta os placeholders \${title} e \${content}</p>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="pcurl-to-mobile" name="PCURL_TO_MOBILE" ${settings.PCURL_TO_MOBILE ? 'checked' : ''}>
                        Converter links da versão desktop para a versão mobile
                    </label>
                    <p class="form-hint">Converte links de produtos da versão desktop para a versão mobile nas notificações</p>
                </div>
                
                <button type="submit" class="control-button primary-btn">Salvar configurações de notificações</button>
            </form>
        `;
    }

    function renderAISettings(settings) {
        if (!settings) return '<p>Não foi possível carregar as configurações de IA.</p>';

        return `
            <form id="ai-settings-form">
                <div class="form-group">
                    <label for="openai-api-key">API Key *</label>
                    <input type="password" id="openai-api-key" name="OPENAI_API_KEY" value="${settings.OPENAI_API_KEY || ''}" placeholder="Ex.: sk-..." required>
                    <p class="form-hint">API Key fornecida pelo serviço de IA</p>
                </div>
                
                <div class="form-group">
                    <label for="openai-base-url">API Base URL *</label>
                    <input type="text" id="openai-base-url" name="OPENAI_BASE_URL" value="${settings.OPENAI_BASE_URL || ''}" placeholder="Ex.: https://api.openai.com/v1/" required>
                    <p class="form-hint">Endpoint da API do modelo de IA; deve ser compatível com o formato da OpenAI</p>
                </div>
                
                <div class="form-group">
                    <label for="openai-model-name">Nome do modelo *</label>
                    <input type="text" id="openai-model-name" name="OPENAI_MODEL_NAME" value="${settings.OPENAI_MODEL_NAME || ''}" placeholder="Ex.: gemini-2.5-pro" required>
                    <p class="form-hint">Nome do modelo a ser usado; deve suportar análise de imagens</p>
                </div>
                
                <div class="form-group">
                    <label for="proxy-url">Endereço de proxy (opcional)</label>
                    <input type="text" id="proxy-url" name="PROXY_URL" value="${settings.PROXY_URL || ''}" placeholder="Ex.: http://127.0.0.1:7890">
                    <p class="form-hint">Endereço de proxy HTTP/S; suporta http e socks5</p>
                </div>
                
                <div class="form-group">
                    <button type="button" id="test-ai-settings-btn" class="control-button">Testar conexão (navegador)</button>
                    <button type="button" id="test-ai-settings-backend-btn" class="control-button">Testar conexão (contêiner backend)</button>
                    <button type="submit" class="control-button primary-btn">Salvar configurações de IA</button>
                </div>
            </form>
        `;
    }

    async function refreshLoginStatusWidget() {
        const status = await fetchSystemStatus();
        if (status) {
            renderLoginStatusWidget(status);
        }
    }

    function renderSystemStatus(status) {
        if (!status) return '<p>Não foi possível carregar o status do sistema.</p>';

        const renderStatusTag = (isOk) => isOk
            ? `<span class="tag status-ok">OK</span>`
            : `<span class="tag status-error">Problema</span>`;

        const env = status.env_file || {};

        return `
            <ul class="status-list">
                <li class="status-item">
                    <span class="label">Arquivo de variáveis de ambiente (.env)</span>
                    <span class="value">${renderStatusTag(env.exists)}</span>
                </li>
                <li class="status-item">
                    <span class="label">OpenAI API Key</span>
                    <span class="value">${renderStatusTag(env.openai_api_key_set)}</span>
                </li>
                <li class="status-item">
                    <span class="label">OpenAI Base URL</span>
                    <span class="value">${renderStatusTag(env.openai_base_url_set)}</span>
                </li>
                <li class="status-item">
                    <span class="label">OpenAI Model Name</span>
                    <span class="value">${renderStatusTag(env.openai_model_name_set)}</span>
                </li>
                <li class="status-item">
                    <span class="label">Ntfy Topic URL</span>
                    <span class="value">${renderStatusTag(env.ntfy_topic_url_set)}</span>
                </li>
            </ul>
        `;
    }

    function renderResultsGrid(data) {
        if (!data || !data.items || data.items.length === 0) {
            return '<p>Nenhum item correspondente encontrado.</p>';
        }

        const cards = data.items.map(item => {
            const info = item.商品信息 || {};
            const seller = item.卖家信息 || {};
            const ai = item.ai_analysis || {};

            const isRecommended = ai.is_recommended === true;
            const recommendationClass = isRecommended ? 'recommended' : 'not-recommended';
            const recommendationText = isRecommended ? 'Recomendado' : (ai.is_recommended === false ? 'Não recomendado' : 'Indefinido');

            const imageUrl = (info.商品图片列表 && info.商品图片列表[0]) ? info.商品图片列表[0] : 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
            const crawlTime = item.爬取时间 ? new Date(item.爬取时间).toLocaleString('sv-SE').slice(0, 16) : 'Desconhecido';
            const publishTime = info.发布时间 || 'Desconhecido';

            // Escape HTML to prevent XSS
            const escapeHtml = (unsafe) => {
                if (typeof unsafe !== 'string') return unsafe;
                return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            };

            return `
            <div class="result-card" data-item='${escapeHtml(JSON.stringify(item))}'>
                <div class="card-image">
                    <a href="${escapeHtml(info.商品链接) || '#'}" target="_blank"><img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(info.商品标题) || 'Imagem do produto'}" loading="lazy" onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuWbvueJhzwvdGV4dD48L3N2Zz4=';"></a>
                </div>
                <div class="card-content">
                    <h3 class="card-title"><a href="${escapeHtml(info.商品链接) || '#'}" target="_blank" title="${escapeHtml(info.商品标题) || ''}">${escapeHtml(info.商品标题) || 'Sem título'}</a></h3>
                    <p class="card-price">${escapeHtml(info.当前售价) || 'Preço desconhecido'}</p>
                    <div class="card-ai-summary ${recommendationClass}">
                        <strong>Sugestão da IA: ${escapeHtml(recommendationText)}</strong>
                        <p title="${escapeHtml(ai.reason) || ''}">Motivo: ${escapeHtml(ai.reason) || 'Sem análise'}</p>
                    </div>
                    <div class="card-footer">
                        <div>
                            <span class="seller-info" title="${escapeHtml(info.卖家昵称) || escapeHtml(seller.卖家昵称) || 'Desconhecido'}">Vendedor: ${escapeHtml(info.卖家昵称) || escapeHtml(seller.卖家昵称) || 'Desconhecido'}</span>
                            <div class="time-info">
                                <p>Publicado em: ${escapeHtml(publishTime)}</p>
                                <p>Coletado em: ${escapeHtml(crawlTime)}</p>
                            </div>
                        </div>
                        <a href="${escapeHtml(info.商品链接) || '#'}" target="_blank" class="action-btn">Ver detalhes</a>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        return `<div id="results-grid">${cards}</div>`;
    }

    function renderTasksTable(tasks) {
        if (!tasks || tasks.length === 0) {
            return '<p>Nenhuma tarefa encontrada. Clique em "Criar nova tarefa" no canto superior direito para adicionar uma.</p>';
        }

        const refreshBtn = '<svg class="icon" viewBox="0 0 1025 1024" version="1.1" xmlns="http://www.w3.org/2000/svg"  width="16" height="16"><path d="M914.17946 324.34283C854.308387 324.325508 750.895846 324.317788 750.895846 324.317788 732.045471 324.317788 716.764213 339.599801 716.764213 358.451121 716.764213 377.30244 732.045471 392.584453 750.895846 392.584453L955.787864 392.584453C993.448095 392.584453 1024 362.040424 1024 324.368908L1024 119.466667C1024 100.615347 1008.718742 85.333333 989.868367 85.333333 971.017993 85.333333 955.736735 100.615347 955.736735 119.466667L955.736735 256.497996C933.314348 217.628194 905.827487 181.795372 873.995034 149.961328 778.623011 54.584531 649.577119 0 511.974435 0 229.218763 0 0 229.230209 0 512 0 794.769791 229.218763 1024 511.974435 1024 794.730125 1024 1023.948888 794.769791 1023.948888 512 1023.948888 493.148681 1008.66763 477.866667 989.817256 477.866667 970.966881 477.866667 955.685623 493.148681 955.685623 512 955.685623 757.067153 757.029358 955.733333 511.974435 955.733333 266.91953 955.733333 68.263265 757.067153 68.263265 512 68.263265 266.932847 266.91953 68.266667 511.974435 68.266667 631.286484 68.266667 743.028524 115.531923 825.725634 198.233152 862.329644 234.839003 892.298522 277.528256 914.17946 324.34283L914.17946 324.34283Z" fill="#389BFF"></path></svg>'

        const tableHeader = `
            <thead>
                <tr>
                    <th>Ativar</th>
                    <th>Nome da tarefa</th>
                    <th>Status de execução</th>
                    <th>Palavra-chave</th>
                    <th>Faixa de preço</th>
                    <th>Filtros</th>
                    <th>Máx. páginas</th>
                    <th>Critérios da IA</th>
                    <th>Regra de agendamento</th>
                    <th>Ações</th>
                </tr>
            </thead>`;

        const tableBody = tasks.map(task => {
            const isRunning = task.is_running === true;
            const statusBadge = isRunning
                ? `<span class="status-badge status-running">Em execução</span>`
                : `<span class="status-badge status-stopped">Parado</span>`;

            const actionButton = isRunning
                ? `<button class="action-btn stop-task-btn" data-task-id="${task.id}">Parar</button>`
                : `<button class="action-btn run-task-btn" data-task-id="${task.id}" ${!task.enabled ? 'disabled title="Tarefa desativada"' : ''}>Executar</button>`;

            return `
            <tr data-task-id="${task.id}" data-task='${JSON.stringify(task)}'>
                <td>
                    <label class="switch">
                        <input type="checkbox" ${task.enabled ? 'checked' : ''}>
                        <span class="slider round"></span>
                    </label>
                </td>
                <td>${task.task_name}</td>
                <td>${statusBadge}</td>
                <td><span class="tag">${task.keyword}</span></td>
                <td>${task.min_price || 'Sem limite'} - ${task.max_price || 'Sem limite'}</td>
                <td>${task.personal_only ? '<span class="tag personal">Vendedor particular</span>' : ''}</td>
                <td>${task.max_pages || 3}</td>
                <td><div class="criteria"><button class="refresh-criteria" title="Gerar critérios da IA novamente" data-task-id="${task.id}">${refreshBtn}</button>${(task.ai_prompt_criteria_file || 'N/A').replace('prompts/', '')}</div></td>
                <td>${task.cron || 'Não definido'}</td>
                <td>
                    ${actionButton}
                    <button class="action-btn edit-btn">Editar</button>
                    <button class="action-btn delete-btn">Excluir</button>
                </td>
            </tr>`
        }).join('');

        return `<table class="tasks-table">${tableHeader}<tbody>${tableBody}</tbody></table>`;
    }


    async function navigateTo(hash) {
        if (logRefreshInterval) {
            clearInterval(logRefreshInterval);
            logRefreshInterval = null;
        }
        if (taskRefreshInterval) {
            clearInterval(taskRefreshInterval);
            taskRefreshInterval = null;
        }
        const sectionId = hash.substring(1) || 'tasks';

        // Update nav links active state
        navLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === `#${sectionId}`);
        });

        // Update main content
        if (templates[sectionId]) {
            mainContent.innerHTML = templates[sectionId]();
            // Make the new content visible
            const newSection = mainContent.querySelector('.content-section');
            if (newSection) {
                requestAnimationFrame(() => {
                    newSection.classList.add('active');
                });
            }

            // --- Load data for the current section ---
            if (sectionId === 'tasks') {
                const container = document.getElementById('tasks-table-container');
                const refreshTasks = async () => {
                    const tasks = await fetchTasks();
                    // Avoid re-rendering if in edit mode to not lose user input
                    if (container && !container.querySelector('tr.editing')) {
                        container.innerHTML = renderTasksTable(tasks);
                    }
                };
                await refreshTasks();
                taskRefreshInterval = setInterval(refreshTasks, 5000);
            } else if (sectionId === 'results') {
                await initializeResultsView();
            } else if (sectionId === 'logs') {
                await initializeLogsView();
            } else if (sectionId === 'settings') {
                await initializeSettingsView();
            }

        } else {
            mainContent.innerHTML = '<section class="content-section active"><h2>Página não encontrada</h2></section>';
        }
    }

    async function initializeLogsView() {
        const logContainer = document.getElementById('log-content-container');
        const refreshBtn = document.getElementById('refresh-logs-btn');
        const autoRefreshCheckbox = document.getElementById('auto-refresh-logs-checkbox');
        const clearBtn = document.getElementById('clear-logs-btn');
        let currentLogSize = 0;

        const updateLogs = async (isFullRefresh = false) => {
            // For incremental updates, check if user is at the bottom BEFORE adding new content.
            const shouldAutoScroll = isFullRefresh || (logContainer.scrollHeight - logContainer.clientHeight <= logContainer.scrollTop + 5);

            if (isFullRefresh) {
                currentLogSize = 0;
                logContainer.textContent = 'Carregando...';
            }

            const logData = await fetchLogs(currentLogSize);

            if (isFullRefresh) {
                // If the log is empty, show a message instead of a blank screen.
                logContainer.textContent = logData.new_content || 'Logs vazios, aguardando conteúdo...';
            } else if (logData.new_content) {
                // If it was showing the empty message, replace it.
                if (logContainer.textContent === 'Logs vazios, aguardando conteúdo...') {
                    logContainer.textContent = logData.new_content;
                } else {
                    logContainer.textContent += logData.new_content;
                }
            }
            currentLogSize = logData.new_pos;

            // Scroll to bottom if it was a full refresh or if the user was already at the bottom.
            if (shouldAutoScroll) {
                logContainer.scrollTop = logContainer.scrollHeight;
            }
        };

        refreshBtn.addEventListener('click', () => updateLogs(true));

        clearBtn.addEventListener('click', async () => {
            if (confirm('Tem certeza de que deseja limpar todos os logs de execução? Esta ação não pode ser desfeita.')) {
                const result = await clearLogs();
                if (result) {
                    await updateLogs(true);
                    alert('Logs limpos.');
                }
            }
        });

        autoRefreshCheckbox.addEventListener('change', () => {
            if (autoRefreshCheckbox.checked) {
                if (logRefreshInterval) clearInterval(logRefreshInterval);
                logRefreshInterval = setInterval(() => updateLogs(false), 1000);
            } else {
                if (logRefreshInterval) {
                    clearInterval(logRefreshInterval);
                    logRefreshInterval = null;
                }
            }
        });

        await updateLogs(true);
        autoRefreshCheckbox.click(); // Enable auto-refresh by default
    }

    async function fetchAndRenderResults() {
        const selector = document.getElementById('result-file-selector');
        const checkbox = document.getElementById('recommended-only-checkbox');
        const sortBySelector = document.getElementById('sort-by-selector');
        const sortOrderSelector = document.getElementById('sort-order-selector');
        const container = document.getElementById('results-grid-container');

        if (!selector || !checkbox || !container || !sortBySelector || !sortOrderSelector) return;

        const selectedFile = selector.value;
        const recommendedOnly = checkbox.checked;
        const sortBy = sortBySelector.value;
        const sortOrder = sortOrderSelector.value;

        if (!selectedFile) {
            container.innerHTML = '<p>Selecione um arquivo de resultados primeiro.</p>';
            return;
        }

        localStorage.setItem('lastSelectedResultFile', selectedFile);

        container.innerHTML = '<p>Carregando resultados...</p>';
        const data = await fetchResultContent(selectedFile, recommendedOnly, sortBy, sortOrder);
        container.innerHTML = renderResultsGrid(data);
    }

    async function initializeResultsView() {
        const selector = document.getElementById('result-file-selector');
        const checkbox = document.getElementById('recommended-only-checkbox');
        const refreshBtn = document.getElementById('refresh-results-btn');
        const deleteBtn = document.getElementById('delete-results-btn');
        const sortBySelector = document.getElementById('sort-by-selector');
        const sortOrderSelector = document.getElementById('sort-order-selector');

        const fileData = await fetchResultFiles();
        if (fileData && fileData.files && fileData.files.length > 0) {
            const lastSelectedFile = localStorage.getItem('lastSelectedResultFile');
            // Determine the file to select. Default to the first file if nothing is stored or if the stored file no longer exists.
            let fileToSelect = fileData.files[0];
            if (lastSelectedFile && fileData.files.includes(lastSelectedFile)) {
                fileToSelect = lastSelectedFile;
            }

            selector.innerHTML = fileData.files.map(f =>
                `<option value="${f}" ${f === fileToSelect ? 'selected' : ''}>${f}</option>`
            ).join('');

            // The selector's value is now correctly set by the 'selected' attribute.
            // We can proceed with adding listeners and the initial fetch.

            selector.addEventListener('change', fetchAndRenderResults);
            checkbox.addEventListener('change', fetchAndRenderResults);
            sortBySelector.addEventListener('change', fetchAndRenderResults);
            sortOrderSelector.addEventListener('change', fetchAndRenderResults);
            refreshBtn.addEventListener('click', fetchAndRenderResults);

            // Enable delete button when a file is selected
            const updateDeleteButtonState = () => {
                deleteBtn.disabled = !selector.value;
            };
            selector.addEventListener('change', updateDeleteButtonState);
            // Atualize o estado do botão de exclusão na inicialização
            updateDeleteButtonState();

            // Delete button functionality
            deleteBtn.addEventListener('click', async () => {
                const selectedFile = selector.value;
                if (!selectedFile) {
                    alert('Selecione um arquivo de resultados primeiro.');
                    return;
                }

                if (confirm(`Tem certeza de que deseja excluir o arquivo de resultados "${selectedFile}"? Esta ação não pode ser desfeita.`)) {
                    const result = await deleteResultFile(selectedFile);
                    if (result) {
                        alert(result.message);
                        // Refresh the file list
                        await initializeResultsView();
                    }
                }
            });

            // Initial load
            await fetchAndRenderResults();
        } else {
            selector.innerHTML = '<option value="">Nenhum arquivo de resultado disponível</option>';
            document.getElementById('results-grid-container').innerHTML = '<p>Nenhum arquivo de resultados encontrado. Execute uma tarefa de monitoramento primeiro.</p>';
        }
    }

    async function initializeSettingsView() {
        // 1. Render System Status
        const statusContainer = document.getElementById('system-status-container');
        const status = await fetchSystemStatus();
        statusContainer.innerHTML = renderSystemStatus(status);

        // 2. Render Notification Settings
        const notificationContainer = document.getElementById('notification-settings-container');
        const notificationSettings = await fetchNotificationSettings();
        if (notificationSettings !== null) {
            notificationContainer.innerHTML = renderNotificationSettings(notificationSettings);
        } else {
            notificationContainer.innerHTML = '<p>Falha ao carregar a configuração de notificações. Verifique se o servidor está em execução.</p>';
        }

        // 3. Render AI Settings
        const aiContainer = document.createElement('div');
        aiContainer.className = 'settings-card';
        aiContainer.innerHTML = `
            <h3>Configuração do modelo de IA</h3>
            <div id="ai-settings-container">
                <p>Carregando configuração de IA...</p>
            </div>
        `;

        // Insert AI settings card before Prompt Management
        const promptCard = document.querySelector('.settings-card h3').closest('.settings-card');
        promptCard.parentNode.insertBefore(aiContainer, promptCard);

        const aiSettingsContainer = document.getElementById('ai-settings-container');
        const aiSettings = await fetchAISettings();
        if (aiSettings !== null) {
            aiSettingsContainer.innerHTML = renderAISettings(aiSettings);
        } else {
            aiSettingsContainer.innerHTML = '<p>Falha ao carregar configuração de IA. Verifique se o servidor está em execução.</p>';
        }

        // 4. Setup Prompt Editor
        const promptSelector = document.getElementById('prompt-selector');
        const promptEditor = document.getElementById('prompt-editor');
        const savePromptBtn = document.getElementById('save-prompt-btn');

        const prompts = await fetchPrompts();
        if (prompts && prompts.length > 0) {
            promptSelector.innerHTML = '<option value="">-- Selecione --</option>' + prompts.map(p => `<option value="${p}">${p}</option>`).join('');
        } else if (prompts && prompts.length === 0) {
            promptSelector.innerHTML = '<option value="">Nenhum arquivo de Prompt encontrado</option>';
        } else {
            // prompts is null or undefined, which means fetch failed
            promptSelector.innerHTML = '<option value="">Falha ao carregar a lista de arquivos de Prompt</option>';
        }

        promptSelector.addEventListener('change', async () => {
            const selectedFile = promptSelector.value;
            if (selectedFile) {
                promptEditor.value = "Carregando...";
                promptEditor.disabled = true;
                savePromptBtn.disabled = true;
                const data = await fetchPromptContent(selectedFile);
                if (data) {
                    promptEditor.value = data.content;
                    promptEditor.disabled = false;
                    savePromptBtn.disabled = false;
                } else {
                    promptEditor.value = `Falha ao carregar o arquivo ${selectedFile}.`;
                }
            } else {
                promptEditor.value = "Selecione um arquivo de Prompt acima para editar...";
                promptEditor.disabled = true;
                savePromptBtn.disabled = true;
            }
        });

        savePromptBtn.addEventListener('click', async () => {
            const selectedFile = promptSelector.value;
            const content = promptEditor.value;
            if (!selectedFile) {
                alert("Selecione um arquivo de Prompt para salvar.");
                return;
            }

            savePromptBtn.disabled = true;
            savePromptBtn.textContent = 'Salvando...';

            const result = await updatePrompt(selectedFile, content);
            if (result) {
                alert(result.message || "Salvo com sucesso!");
            }
            // No need to show alert on failure, as updatePrompt already does.

            savePromptBtn.disabled = false;
            savePromptBtn.textContent = 'Salvar alterações';
        });

        // 5. Add event listener for notification settings form
        const notificationForm = document.getElementById('notification-settings-form');
        if (notificationForm) {
            notificationForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                // Collect form data
                const formData = new FormData(notificationForm);
                const settings = {};

                // Handle regular inputs
                for (let [key, value] of formData.entries()) {
                    if (key === 'PCURL_TO_MOBILE') {
                        settings[key] = value === 'on';
                    } else {
                        settings[key] = value || '';
                    }
                }

                // Handle unchecked checkboxes (they don't appear in FormData)
                const pcurlCheckbox = document.getElementById('pcurl-to-mobile');
                if (pcurlCheckbox && !pcurlCheckbox.checked) {
                    settings.PCURL_TO_MOBILE = false;
                }

                // Save settings
                const saveBtn = notificationForm.querySelector('button[type="submit"]');
                const originalText = saveBtn.textContent;
                saveBtn.disabled = true;
                saveBtn.textContent = 'Salvando...';

                const result = await updateNotificationSettings(settings);
                if (result) {
                    alert(result.message || "Configurações de notificações salvas!");
                }

                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            });
        }

        // 6. Add event listener for AI settings form
        const aiForm = document.getElementById('ai-settings-form');
        if (aiForm) {
            aiForm.addEventListener('submit', async (e) => {
                e.preventDefault();

                // Collect form data
                const formData = new FormData(aiForm);
                const settings = {};

                // Handle regular inputs
                for (let [key, value] of formData.entries()) {
                    settings[key] = value || '';
                }

                // Save settings
                const saveBtn = aiForm.querySelector('button[type="submit"]');
                const originalText = saveBtn.textContent;
                saveBtn.disabled = true;
                saveBtn.textContent = 'Salvando...';

                const result = await updateAISettings(settings);
                if (result) {
                    alert(result.message || "Configurações de IA salvas!");
                }

                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            });

            // Add event listener for AI settings test button (browser)
            const testBtn = document.getElementById('test-ai-settings-btn');
            if (testBtn) {
                testBtn.addEventListener('click', async () => {
                    // Collect form data
                    const formData = new FormData(aiForm);
                    const settings = {};

                    // Handle regular inputs
                    for (let [key, value] of formData.entries()) {
                        settings[key] = value || '';
                    }

                    // Test settings
                    const originalText = testBtn.textContent;
                    testBtn.disabled = true;
                    testBtn.textContent = 'Testando...';

                    const result = await testAISettings(settings);
                    if (result) {
                        if (result.success) {
                            alert(result.message || "Teste de conexão do modelo de IA bem-sucedido!");
                        } else {
                            alert("Teste no navegador falhou: " + result.message);
                        }
                    }

                    testBtn.disabled = false;
                    testBtn.textContent = originalText;
                });
            }

            // Add event listener for AI settings test button (backend)
            const testBackendBtn = document.getElementById('test-ai-settings-backend-btn');
            if (testBackendBtn) {
                testBackendBtn.addEventListener('click', async () => {
                    // Test backend settings without form data (uses env config)
                    const originalText = testBackendBtn.textContent;
                    testBackendBtn.disabled = true;
                    testBackendBtn.textContent = 'Testando...';

                    try {
                        const response = await fetch('/api/settings/ai/test/backend', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                        });

                        if (!response.ok) {
                            throw new Error('Falha ao solicitar teste no backend');
                        }

                        const result = await response.json();
                    if (result.success) {
                        alert(result.message || "Teste do modelo de IA no backend concluído com sucesso!");
                    } else {
                        alert("Teste do contêiner backend falhou: " + result.message);
                    }
                } catch (error) {
                    alert("Erro no teste do contêiner backend: " + error.message);
                }

                    testBackendBtn.disabled = false;
                    testBackendBtn.textContent = originalText;
                });
            }
        }
    }

    // Handle navigation clicks
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const hash = this.getAttribute('href');
            if (window.location.hash !== hash) {
                window.location.hash = hash;
            }
        });
    });

    // Handle hash changes (e.g., back/forward buttons, direct URL)
    window.addEventListener('hashchange', () => {
        navigateTo(window.location.hash);
    });

    // --- Event Delegation for dynamic content ---
    mainContent.addEventListener('click', async (event) => {
        const target = event.target;
        const button = target.closest('button'); // Find the closest button element
        if (!button) return;

        const row = button.closest('tr');
        const taskId = row ? row.dataset.taskId : null;

        if (button.matches('.view-json-btn')) {
            const card = button.closest('.result-card');
            const itemData = JSON.parse(card.dataset.item);
            const jsonContent = document.getElementById('json-viewer-content');
            jsonContent.textContent = JSON.stringify(itemData, null, 2);

            const modal = document.getElementById('json-viewer-modal');
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('visible'), 10);
        } else if (button.matches('.run-task-btn')) {
            const taskId = button.dataset.taskId;
            button.disabled = true;
            button.textContent = 'Iniciando...';
            await startSingleTask(taskId);
            // The auto-refresh will update the UI. For immediate feedback:
            const tasks = await fetchTasks();
            document.getElementById('tasks-table-container').innerHTML = renderTasksTable(tasks);
        } else if (button.matches('.stop-task-btn')) {
            const taskId = button.dataset.taskId;
            button.disabled = true;
            button.textContent = 'Parando...';
            await stopSingleTask(taskId);
            // The auto-refresh will update the UI. For immediate feedback:
            const tasks = await fetchTasks();
            document.getElementById('tasks-table-container').innerHTML = renderTasksTable(tasks);
        } else if (button.matches('.edit-btn')) {
            const taskData = JSON.parse(row.dataset.task);
            const isRunning = taskData.is_running === true;
            const statusBadge = isRunning
                ? `<span class="status-badge status-running">Em execução</span>`
                : `<span class="status-badge status-stopped">Parado</span>`;

            row.classList.add('editing');
            row.innerHTML = `
                <td>
                    <label class="switch">
                        <input type="checkbox" ${taskData.enabled ? 'checked' : ''} data-field="enabled">
                        <span class="slider round"></span>
                    </label>
                </td>
                <td><input type="text" value="${taskData.task_name}" data-field="task_name"></td>
                <td>${statusBadge}</td>
                <td><input type="text" value="${taskData.keyword}" data-field="keyword"></td>
                <td>
                    <input type="text" value="${taskData.min_price || ''}" placeholder="Sem limite" data-field="min_price" style="width: 60px;"> -
                    <input type="text" value="${taskData.max_price || ''}" placeholder="Sem limite" data-field="max_price" style="width: 60px;">
                </td>
                <td>
                    <label>
                        <input type="checkbox" ${taskData.personal_only ? 'checked' : ''} data-field="personal_only"> Vendedor particular
                    </label>
                </td>
                <td><input type="number" value="${taskData.max_pages || 3}" data-field="max_pages" style="width: 60px;" min="1"></td>
                <td>${(taskData.ai_prompt_criteria_file || 'N/A').replace('prompts/', '')}</td>
                <td><input type="text" value="${taskData.cron || ''}" placeholder="* * * * *" data-field="cron"></td>
                <td>
                    <button class="action-btn save-btn">Salvar</button>
                    <button class="action-btn cancel-btn">Cancelar</button>
                </td>
            `;

        } else if (button.matches('.delete-btn')) {
            const taskName = row.querySelector('td:nth-child(2)').textContent;
            if (confirm(`Tem certeza de que deseja excluir a tarefa "${taskName}"?`)) {
                const result = await deleteTask(taskId);
                if (result) {
                    row.remove();
                }
            }
        } else if (button.matches('#add-task-btn')) {
            const modal = document.getElementById('add-task-modal');
            modal.style.display = 'flex';
            // Use a short timeout to allow the display property to apply before adding the transition class
            setTimeout(() => modal.classList.add('visible'), 10);
        } else if (button.matches('.save-btn')) {
            const taskNameInput = row.querySelector('input[data-field="task_name"]');
            const keywordInput = row.querySelector('input[data-field="keyword"]');
            if (!taskNameInput.value.trim() || !keywordInput.value.trim()) {
                alert('Nome da tarefa e palavra-chave são obrigatórios.');
                return;
            }

            const inputs = row.querySelectorAll('input[data-field]');
            const updatedData = {};
            inputs.forEach(input => {
                const field = input.dataset.field;
                if (input.type === 'checkbox') {
                    updatedData[field] = input.checked;
                } else {
                    const value = input.value.trim();
                    if (field === 'max_pages') {
                        // Garantir que max_pages seja enviado como número; se vazio, padrão é 3
                        updatedData[field] = value ? parseInt(value, 10) : 3;
                    } else {
                        updatedData[field] = value === '' ? null : value;
                    }
                }
            });

            const result = await updateTask(taskId, updatedData);
            if (result && result.task) {
                const container = document.getElementById('tasks-table-container');
                const tasks = await fetchTasks();
                container.innerHTML = renderTasksTable(tasks);
            }
        } else if (button.matches('.cancel-btn')) {
            const container = document.getElementById('tasks-table-container');
            const tasks = await fetchTasks();
            container.innerHTML = renderTasksTable(tasks);
        } else if (button.matches('.refresh-criteria')) {
            const task = JSON.parse(row.dataset.task);
            const modal = document.getElementById('refresh-criteria-modal');
            const textarea = document.getElementById('refresh-criteria-description');
            textarea.value = task['description'] || '';
            modal.dataset.taskId = taskId;
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('visible'), 10);
        }
    });

    mainContent.addEventListener('change', async (event) => {
        const target = event.target;
        // Check if the changed element is a toggle switch in the main table (not in an editing row)
        if (target.matches('.tasks-table input[type="checkbox"]') && !target.closest('tr.editing')) {
            const row = target.closest('tr');
            const taskId = row.dataset.taskId;
            const isEnabled = target.checked;

            if (taskId) {
                await updateTask(taskId, {enabled: isEnabled});
                // The visual state is already updated by the checkbox itself.
            }
        }
    });

    // --- Modal Logic ---
    const modal = document.getElementById('add-task-modal');
    if (modal) {
        const closeModalBtn = document.getElementById('close-modal-btn');
        const cancelBtn = document.getElementById('cancel-add-task-btn');
        const saveBtn = document.getElementById('save-new-task-btn');
        const form = document.getElementById('add-task-form');

        const closeModal = () => {
            modal.classList.remove('visible');
            setTimeout(() => {
                modal.style.display = 'none';
                form.reset(); // Reset form on close
            }, 300);
        };

        closeModalBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);

        let canClose = false;
        modal.addEventListener('mousedown', event => {
            canClose = event.target === modal;
        });
        modal.addEventListener('mouseup', (event) => {
            // Close if clicked on the overlay background
            if (canClose && event.target === modal) {
                closeModal();
            }
        });

        saveBtn.addEventListener('click', async () => {
            if (form.checkValidity() === false) {
                form.reportValidity();
                return;
            }

            const formData = new FormData(form);
            const data = {
                task_name: formData.get('task_name'),
                keyword: formData.get('keyword'),
                description: formData.get('description'),
                min_price: formData.get('min_price') || null,
                max_price: formData.get('max_price') || null,
                personal_only: formData.get('personal_only') === 'on',
                max_pages: parseInt(formData.get('max_pages'), 10) || 3,
                cron: formData.get('cron') || null,
            };

            // Show loading state
            const btnText = saveBtn.querySelector('.btn-text');
            const spinner = saveBtn.querySelector('.spinner');
            btnText.style.display = 'none';
            spinner.style.display = 'inline-block';
            saveBtn.disabled = true;

            const result = await createTaskWithAI(data);

            // Hide loading state
            btnText.style.display = 'inline-block';
            spinner.style.display = 'none';
            saveBtn.disabled = false;

            if (result && result.task) {
                closeModal();
                // Refresh task list
                const container = document.getElementById('tasks-table-container');
                if (container) {
                    const tasks = await fetchTasks();
                    container.innerHTML = renderTasksTable(tasks);
                }
            }
        });
    }

    // --- refresh criteria Modal Logic ---
    const refreshCriteriaModal = document.getElementById('refresh-criteria-modal');
    if (refreshCriteriaModal) {
        const form = document.getElementById('refresh-criteria-form');
        const closeModalBtn = document.getElementById('close-refresh-criteria-btn');
        const cancelBtn = document.getElementById('cancel-refresh-criteria-btn');
        const refreshBtn = document.getElementById('refresh-criteria-btn');

        const closeModal = () => {
            refreshCriteriaModal.classList.remove('visible');
            setTimeout(() => {
                refreshCriteriaModal.style.display = 'none';
                form.reset(); // Reset form on close
            }, 300);
        };

        closeModalBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);

        let canClose = false;
        refreshCriteriaModal.addEventListener('mousedown', event => {
            canClose = event.target === refreshCriteriaModal;
        });
        refreshCriteriaModal.addEventListener('mouseup', (event) => {
            // Close if clicked on the overlay background
            if (canClose && event.target === refreshCriteriaModal) {
                closeModal();
            }
        });

        refreshBtn.addEventListener('click', async () => {
            if (form.checkValidity() === false) {
                form.reportValidity();
                return;
            }
            const btnText = refreshBtn.querySelector('.btn-text');
            const spinner = refreshBtn.querySelector('.spinner');

            // Show loading state
            btnText.style.display = 'none';
            spinner.style.display = 'inline-block';
            refreshBtn.disabled = true;

            const taskId = refreshCriteriaModal.dataset.taskId
            const formData = new FormData(form);
            const result = await updateTask(taskId, {description: formData.get('description')});

            // Hide loading state
            btnText.style.display = 'inline-block';
            spinner.style.display = 'none';
            refreshBtn.disabled = false;

            if (result && result.task) {
                closeModal();
            }
        })

    }


    // Initial load
    refreshLoginStatusWidget();
    navigateTo(window.location.hash || '#tasks');

    // --- Global Event Listener for header/modals ---
    document.body.addEventListener('click', async (event) => {
        const target = event.target;
        const widgetUpdateBtn = target.closest('#update-login-state-btn-widget');
        const widgetDeleteBtn = target.closest('#delete-login-state-btn-widget');
        const copyCodeBtn = target.closest('#copy-login-script-btn');

        if (copyCodeBtn) {
            event.preventDefault();
            const codeToCopy = document.getElementById('login-script-code').textContent.trim();

            // Use a API moderna de área de transferência em contexto seguro; caso contrário, use o método alternativo
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(codeToCopy).then(() => {
                    copyCodeBtn.textContent = 'Copiado!';
                    setTimeout(() => {
                        copyCodeBtn.textContent = 'Copiar script';
                    }, 2000);
                }).catch(err => {
                    console.error('Não foi possível usar a API da área de transferência: ', err);
                    alert('Falha ao copiar, copie manualmente.');
                });
            } else {
                // Alternativa para contextos inseguros (HTTP) ou navegadores antigos
                const textArea = document.createElement("textarea");
                textArea.value = codeToCopy;
                // Tornar a área de texto invisível
                textArea.style.position = "fixed";
                textArea.style.top = "-9999px";
                textArea.style.left = "-9999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                    copyCodeBtn.textContent = 'Copiado!';
                    setTimeout(() => {
                        copyCodeBtn.textContent = 'Copiar script';
                    }, 2000);
                } catch (err) {
                    console.error('Alternativa: não foi possível copiar o texto', err);
                    alert('Falha ao copiar, copie manualmente.');
                }
                document.body.removeChild(textArea);
            }
        } else if (widgetUpdateBtn) {
            event.preventDefault();
            const modal = document.getElementById('login-state-modal');
            modal.style.display = 'flex';
            setTimeout(() => modal.classList.add('visible'), 10);
        } else if (widgetDeleteBtn) {
            event.preventDefault();
            if (confirm('Tem certeza de que deseja excluir as credenciais de login (xianyu_state.json)? Será necessário configurá-las novamente para executar tarefas.')) {
                const result = await deleteLoginState();
                if (result) {
                    alert(result.message);
                    await refreshLoginStatusWidget(); // Refresh the widget UI
                    // Also refresh settings view if it's currently active
                    if (window.location.hash === '#settings' || window.location.hash === '') {
                        const statusContainer = document.getElementById('system-status-container');
                        if (statusContainer) {
                            const status = await fetchSystemStatus();
                            statusContainer.innerHTML = renderSystemStatus(status);
                        }
                    }
                }
            }
        }
    });

    // --- JSON Viewer Modal Logic ---
    const jsonViewerModal = document.getElementById('json-viewer-modal');
    if (jsonViewerModal) {
        const closeBtn = document.getElementById('close-json-viewer-btn');

        const closeModal = () => {
            jsonViewerModal.classList.remove('visible');
            setTimeout(() => {
                jsonViewerModal.style.display = 'none';
            }, 300);
        };

        closeBtn.addEventListener('click', closeModal);
        jsonViewerModal.addEventListener('click', (event) => {
            if (event.target === jsonViewerModal) {
                closeModal();
            }
        });
    }

    // --- Login State Modal Logic ---
    const loginStateModal = document.getElementById('login-state-modal');
    if (loginStateModal) {
        const closeBtn = document.getElementById('close-login-state-modal-btn');
        const cancelBtn = document.getElementById('cancel-login-state-btn');
        const saveBtn = document.getElementById('save-login-state-btn');
        const form = document.getElementById('login-state-form');
        const contentTextarea = document.getElementById('login-state-content');

        const closeModal = () => {
            loginStateModal.classList.remove('visible');
            setTimeout(() => {
                loginStateModal.style.display = 'none';
                form.reset();
            }, 300);
        };

        async function updateLoginState(content) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Salvando...';
            try {
                const response = await fetch('/api/login-state', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content: content}),
                });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Falha ao atualizar o status de login');
                }
                alert('Status de login atualizado com sucesso!');
                closeModal();
                await refreshLoginStatusWidget(); // Refresh the widget UI
                // Also refresh settings view if it's currently active
                if (window.location.hash === '#settings') {
                    await initializeSettingsView();
                }
            } catch (error) {
                console.error('Erro ao atualizar o status de login:', error);
                alert(`Falha na atualização: ${error.message}`);
            } finally {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Salvar';
            }
        }

        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        loginStateModal.addEventListener('click', (event) => {
            if (event.target === loginStateModal) {
                closeModal();
            }
        });

        saveBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const content = contentTextarea.value.trim();
            if (!content) {
                alert('Cole o JSON obtido no navegador.');
                return;
            }
            await updateLoginState(content);
        });

    }
});
