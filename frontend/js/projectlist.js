/**
 * 項目管理界面 JavaScript
 * 用於載入和顯示所有項目信息，並提供項目鏈接功能
 */

// API 基礎 URL
const API_BASE_URL = '/transtool-py/api';
const PROJECT_BASE_URL = 'http://139.224.225.128/transtool-py/index.html';

// DOM 元素
let projectsContainer;
let loadingContainer;
let errorContainer;
let errorMessage;
let statsContainer;
let statsText;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 獲取 DOM 元素
    projectsContainer = document.getElementById('projectsContainer');
    loadingContainer = document.getElementById('loadingContainer');
    errorContainer = document.getElementById('errorContainer');
    errorMessage = document.getElementById('errorMessage');
    statsContainer = document.getElementById('statsContainer');
    statsText = document.getElementById('statsText');

    // 載入項目列表
    loadProjects();
});

/**
 * 載入項目列表
 */
async function loadProjects() {
    try {
        // 顯示載入狀態
        showLoading();
        hideError();

        // 發送 API 請求
        const response = await fetch(`${API_BASE_URL}/projects`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        if (!data.projects) {
            throw new Error('API 返回數據格式錯誤');
        }

        // 渲染項目列表
        renderProjects(data.projects);
        
        // 更新統計信息
        updateStats(data.projects);

    } catch (error) {
        console.error('載入項目失敗:', error);
        showError(`載入項目列表失敗: ${error.message}`);
    }
}

/**
 * 渲染項目列表
 * @param {Object} projects - 項目數據對象
 */
function renderProjects(projects) {
    const projectIds = Object.keys(projects);
    
    if (projectIds.length === 0) {
        projectsContainer.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #666;">
                <h3>📭 暫無項目</h3>
                <p>目前沒有配置任何項目</p>
            </div>
        `;
    } else {
        projectsContainer.innerHTML = projectIds.map(projectId => {
            const project = projects[projectId];
            return createProjectCard(projectId, project);
        }).join('');
    }

    hideLoading();
    showProjects();
}

/**
 * 創建項目卡片 HTML
 * @param {string} projectId - 項目 ID
 * @param {Object} project - 項目信息
 * @returns {string} 項目卡片 HTML
 */
function createProjectCard(projectId, project) {
    const projectUrl = `${PROJECT_BASE_URL}?project=${encodeURIComponent(projectId)}`;
    
    // 處理標籤
    const tags = project.tags || [];
    const tagsHtml = tags.length > 0 
        ? `<div class="project-tags">${tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>`
        : '';

    // 處理描述
    const description = project.description || '暫無描述';
    
    // 處理術語詞典文件名
    const termDict = project.termDict || `termDict_${projectId}.json`;
    // 項目名
    const name = project.name || projectId;

    return `
        <div class="project-card" onclick="openProject('${escapeHtml(projectId)}')">
            <h3>${escapeHtml(name)}</h3>
            <div class="project-info">
                <p><strong>描述：</strong>${escapeHtml(description)}</p>
                <p><strong>術語詞典：</strong>${escapeHtml(termDict)}</p>
                <p><strong>項目 ID：</strong><code>${escapeHtml(projectId)}</code></p>
            </div>
            ${tagsHtml}
            <a href="${projectUrl}" class="project-link" target="_blank" onclick="event.stopPropagation()">
                🔗 打開項目
            </a>
        </div>
    `;
}

/**
 * 更新統計信息
 * @param {Object} projects - 項目數據對象
 */
function updateStats(projects) {
    const projectIds = Object.keys(projects);
    const totalProjects = projectIds.length;
    
    // 統計有標籤的項目
    const projectsWithTags = projectIds.filter(id => {
        const project = projects[id];
        return project.tags && project.tags.length > 0;
    }).length;

    statsText.innerHTML = `
        總共 <strong>${totalProjects}</strong> 個項目，
        其中 <strong>${projectsWithTags}</strong> 個項目配置了標籤
    `;
}

/**
 * 打開項目（在新標籤頁中）
 * @param {string} projectId - 項目 ID
 */
function openProject(projectId) {
    const projectUrl = `${PROJECT_BASE_URL}?project=${encodeURIComponent(projectId)}`;
    window.open(projectUrl, '_blank');
}

/**
 * 顯示載入狀態
 */
function showLoading() {
    loadingContainer.style.display = 'block';
    projectsContainer.style.display = 'none';
    errorContainer.style.display = 'none';
}

/**
 * 隱藏載入狀態
 */
function hideLoading() {
    loadingContainer.style.display = 'none';
}

/**
 * 顯示項目列表
 */
function showProjects() {
    projectsContainer.style.display = 'grid';
}

/**
 * 顯示錯誤信息
 * @param {string} message - 錯誤信息
 */
function showError(message) {
    errorMessage.textContent = message;
    errorContainer.style.display = 'block';
    loadingContainer.style.display = 'none';
    projectsContainer.style.display = 'none';
}

/**
 * 隱藏錯誤信息
 */
function hideError() {
    errorContainer.style.display = 'none';
}

/**
 * HTML 轉義函數
 * @param {string} text - 需要轉義的文本
 * @returns {string} 轉義後的文本
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 重新加载配置文件
 */
async function reloadConfig() {
    const reloadBtn = document.querySelector('.reload-config-btn');
    
    try {
        // 禁用按钮并显示加载状态
        reloadBtn.disabled = true;
        reloadBtn.textContent = '⏳ 重新加載中...';
        
        showLoading();
        hideError();
        hideSuccess();

        // 发送重新加载请求
        const response = await fetch(`${API_BASE_URL}/reload-config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 重新加载成功后刷新项目列表
            await loadProjects();
            showSuccess(`✅ 配置重新加载成功！加载了 ${data.projects_count} 个项目`);
        } else {
            showError(`重新加载失败: ${data.error}`);
        }
    } catch (error) {
        console.error('重新加载配置失败:', error);
        showError(`重新加载失败: ${error.message}`);
    } finally {
        // 恢复按钮状态
        reloadBtn.disabled = false;
        reloadBtn.textContent = '⚙️ 重新加載配置';
    }
}

/**
 * 显示成功消息
 * @param {string} message - 成功信息
 */
function showSuccess(message) {
    // 创建或更新成功消息容器
    let successContainer = document.getElementById('successContainer');
    if (!successContainer) {
        successContainer = document.createElement('div');
        successContainer.id = 'successContainer';
        successContainer.className = 'success';
        successContainer.style.display = 'none';
        
        // 插入到错误容器之前
        const errorContainer = document.getElementById('errorContainer');
        errorContainer.parentNode.insertBefore(successContainer, errorContainer);
    }
    
    successContainer.innerHTML = `<strong>✅ 操作成功：</strong><span>${message}</span>`;
    successContainer.style.display = 'block';
    
    // 3秒后自动隐藏
    setTimeout(() => {
        hideSuccess();
    }, 3000);
}

/**
 * 隐藏成功消息
 */
function hideSuccess() {
    const successContainer = document.getElementById('successContainer');
    if (successContainer) {
        successContainer.style.display = 'none';
    }
}

/**
 * 定期刷新項目列表（可選功能）
 */
function startAutoRefresh(intervalMinutes = 5) {
    setInterval(() => {
        console.log('自動刷新項目列表...');
        loadProjects();
    }, intervalMinutes * 60 * 1000);
}

// 可選：啟用自動刷新（每5分鐘）
// startAutoRefresh(5);
