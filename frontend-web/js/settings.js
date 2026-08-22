import { getSettings, updateModelConfig, updateAdvisorMapping, getAdvisorModels } from './api.js';

let settingsModal = null;
let currentConfig = {};
let currentAdvisorMapping = {};

export function initSettings() {
    const settingsBtn = document.getElementById('settingsBtn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            openSettingsModal();
        });
    }
}

function openSettingsModal() {
    if (settingsModal) return;
    
    Promise.all([getSettings(), getAdvisorModels()])
        .then(([settingsData, advisorModels]) => {
            currentConfig = settingsData.providers || {};
            currentAdvisorMapping = settingsData.advisor_mapping || {};
            renderSettingsModal();
        })
        .catch(err => {
            console.error('获取设置失败', err);
            alert('获取设置失败，请刷新重试');
        });
}

// 判断是否为脱敏后的 API Key（包含 ****）
function isMaskedKey(key) {
    if (!key) return false;
    // 如果包含连续4个以上 *，认为是脱敏后的
    return key.includes('****') && key.length < 20;
}

function renderSettingsModal() {
    settingsModal = document.createElement('div');
    settingsModal.className = 'modal-overlay';
    settingsModal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2>模型配置</h2>
                <button class="close-btn">&times;</button>
            </div>
            <div class="modal-body">
                ${renderAdvisorCard('zhuge_liang', '诸葛亮', currentConfig, currentAdvisorMapping)}
                ${renderAdvisorCard('si_ma_yi', '司马懿', currentConfig, currentAdvisorMapping)}
                ${renderAdvisorCard('zhou_yu', '周瑜', currentConfig, currentAdvisorMapping)}
                ${renderAdvisorCard('xun_yu', '荀彧', currentConfig, currentAdvisorMapping)}
            </div>
            <div class="modal-footer">
                <button id="saveSettingsBtn" class="btn btn-primary">保存</button>
                <button id="cancelSettingsBtn" class="btn btn-secondary">取消</button>
            </div>
        </div>
    `;

    document.body.appendChild(settingsModal);

    settingsModal.querySelector('.close-btn').addEventListener('click', closeSettingsModal);
    settingsModal.querySelector('#cancelSettingsBtn').addEventListener('click', closeSettingsModal);
    settingsModal.querySelector('#saveSettingsBtn').addEventListener('click', saveSettings);
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) closeSettingsModal();
    });
}

function renderAdvisorCard(advisorId, advisorName, config, mapping) {
    const provider = mapping[advisorId] || 'ollama';
    const providerConfig = config[provider] || {};
    const model = providerConfig.model || '';

    const providerOptions = [
        { value: 'zhipu', label: '智谱' },
        { value: 'siliconflow', label: '硅基' },
        { value: 'ollama', label: '本地' },
        { value: 'deepseek', label: 'deepseek' },
        { value: 'kimi', label: 'kimi' },
        { value: 'volcano', label: '火山' },
        { value: 'qwen', label: '千问' }
    ];

    return `
        <div class="advisor-card">
            <h3>${advisorName}</h3>
            <div class="form-group">
                <label>服务商名称</label>
                <select class="provider-select" data-advisor="${advisorId}">
                    ${providerOptions.map(opt => 
                        `<option value="${opt.value}" ${opt.value === provider ? 'selected' : ''}>${opt.label}</option>`
                    ).join('')}
                </select>
            </div>
            <div class="form-group">
                <label>API 密钥</label>
                <input type="password" class="api-key-input" data-advisor="${advisorId}" 
                       value="${providerConfig.api_key || ''}" placeholder="留空表示使用默认">
            </div>
            <div class="form-group">
                <label>模型名称</label>
                <input type="text" class="model-name-input" data-advisor="${advisorId}" 
                       value="${model}" placeholder="例如：glm-4-flash">
            </div>
        </div>
    `;
}

function saveSettings() {
    const newConfig = {};
    const newMapping = {};
    // 保存原来的配置（用于保留未修改的 API Key）
    const originalConfig = currentConfig;

    document.querySelectorAll('.advisor-card').forEach(card => {
        const advisorId = card.querySelector('.provider-select').dataset.advisor;
        const provider = card.querySelector('.provider-select').value;
        const apiKey = card.querySelector('.api-key-input').value;
        const modelName = card.querySelector('.model-name-input').value;

        newMapping[advisorId] = provider;

        if (!newConfig[provider]) {
            newConfig[provider] = {};
        }

        // ===== 关键修复：如果 API Key 是脱敏后的 **** 格式，则不更新 =====
        if (apiKey && isMaskedKey(apiKey)) {
            // 保留原配置中的 API Key（从 originalConfig 读取）
            const originalProviderConfig = originalConfig[provider] || {};
            newConfig[provider].api_key = originalProviderConfig.api_key || '';
            console.log(`[Settings] ${advisorId} 的 API Key 是脱敏格式，保留原值`);
        } else {
            // 用户修改了 Key，使用新值
            newConfig[provider].api_key = apiKey;
        }
        
        newConfig[provider].model = modelName;
        // base_url 在服务端硬编码，不从前端传入
    });

    Promise.all([
        updateModelConfig(newConfig),
        updateAdvisorMapping({ mapping: newMapping })
    ])
    .then(() => {
        alert('设置已保存');
        closeSettingsModal();
        import('./chat.js').then(chat => {
            chat.refreshAdvisorModels();
        });
    })
    .catch(err => {
        console.error('保存设置失败', err);
        alert('保存失败，请重试');
    });
}

function closeSettingsModal() {
    if (settingsModal) {
        settingsModal.remove();
        settingsModal = null;
    }
}