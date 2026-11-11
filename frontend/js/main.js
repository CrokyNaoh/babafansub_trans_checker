/**
 * 翻譯檢查工具 - 前端交互邏輯（後端處理版本）
 */

const API_BASE = '/transtool-py/api';

// DOM 元素
const fileInput = document.getElementById('fileInput');
const fileDrop = document.getElementById('fileDrop');
const fileName = document.getElementById('fileName');
const fileMeta = document.getElementById('fileMeta');
const inputCol = document.getElementById('inputCol');
const inputColLabel = document.getElementById('inputColLabel');
const outputCol1 = document.getElementById('outputCol1');
const outputCol2 = document.getElementById('outputCol2');
const outputCol2Group = document.getElementById('outputCol2Group');
const extraHintGroup = document.getElementById('extraHintGroup');
const extraHint = document.getElementById('extraHint');
const checkBtn = document.getElementById('checkBtn');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const message = document.getElementById('message');
const pageWrapper = document.getElementById('pageWrapper');
const errorContainer = document.getElementById('errorContainer');
const projectName = document.getElementById('projectName');
const projectDescription = document.getElementById('projectDescription');
const projectInfo = document.getElementById('projectInfo');
const bgLayer = document.getElementById('bgLayer');
const bannerProjectName = document.getElementById('bannerProjectName');
const bannerProjectDesc = document.getElementById('bannerProjectDesc');

// 上傳限制：以後端 /api/client-config 為準，取不到時用預設值
const limits = {
    maxFileSizeMb: 10,
    maxRowsPerSheet: 70000,
};

let selectedFile = null;
// 每次選文件遞增；異步解析結束時若已不是最新一次選擇，丟棄結果
let fileToken = 0;
let currentProject = null;

// ========== 工具函數 ==========

function getProjectFromURL() {
    return new URLSearchParams(window.location.search).get('project');
}

function getMode() {
    return document.querySelector('input[name="checkMode"]:checked').value;
}

function formatSize(bytes) {
    if (bytes >= 1024 * 1024) {
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** 顯示提示；默認按純文字顯示，只有自己拼好、已轉義的 HTML 才傳 isHtml=true */
function showMessage(text, type = 'info', isHtml = false) {
    if (isHtml) {
        message.innerHTML = text;
    } else {
        message.textContent = text;
    }
    message.className = 'message ' + type;
}

function hideMessage() {
    message.className = 'message';
}

function showProgress(percent, text) {
    progressBar.style.display = 'block';
    progressBar.classList.remove('indeterminate');
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

function showIndeterminate(text) {
    progressBar.style.display = 'block';
    progressBar.classList.add('indeterminate');
    progressText.textContent = text;
}

function hideProgress() {
    progressBar.style.display = 'none';
    progressBar.classList.remove('indeterminate');
}

/** 項目可在 projects.json 設定 accentColor（如 "#c0567a"），作為頁面主色 */
function applyAccentColor(color) {
    if (typeof color === 'string' && /^#[0-9a-fA-F]{6}$/.test(color)) {
        document.documentElement.style.setProperty('--accent', color);
    }
}

// ========== 文件檢查 ==========

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * 上傳前檢查各工作表行數（讀取邏輯見 xlsx-rows.js）。
 * 讀不出行數時不攔截，由伺服器檢查；只有文件明顯不是 xlsx 時報錯。
 * 返回 { sheetCount, violations }，讀不出時 sheetCount 為 null。
 */
async function readSheetInfo(file) {
    let sheets = null;
    try {
        sheets = await readXlsxSheetRows(file);
    } catch (error) {
        if (error instanceof NotXlsxError) {
            throw error;
        }
        console.warn('預先讀取行數失敗，交給伺服器檢查:', error);
    }
    if (!sheets) {
        return { sheetCount: null, violations: [] };
    }
    const violations = sheets
        .filter(sheet => sheet.rows > limits.maxRowsPerSheet)
        .map(sheet => ({ sheet: sheet.name, rows: sheet.rows }));
    return { sheetCount: sheets.length, violations };
}

function clearSelectedFile() {
    selectedFile = null;
    fileInput.value = '';
    fileName.textContent = '未選擇文件';
    fileMeta.textContent = '';
    fileDrop.classList.remove('has-file');
}

async function handleFile(file) {
    const token = ++fileToken;
    // 新文件解析完成前不允許用舊文件提交
    selectedFile = null;
    if (!file) {
        clearSelectedFile();
        return;
    }
    if (!/\.xlsx$/i.test(file.name)) {
        clearSelectedFile();
        showMessage('僅支持 .xlsx 文件', 'error');
        return;
    }
    if (file.size > limits.maxFileSizeMb * 1024 * 1024) {
        clearSelectedFile();
        showMessage(`文件過大（${formatSize(file.size)}），建議小於 ${limits.maxFileSizeMb}MB`, 'error');
        return;
    }

    fileName.textContent = file.name;
    fileMeta.textContent = formatSize(file.size);
    fileDrop.classList.add('has-file');

    try {
        showMessage('正在檢查文件行數...', 'info');
        const { sheetCount, violations } = await readSheetInfo(file);
        if (token !== fileToken) {
            return;
        }

        if (violations.length > 0) {
            let errorMsg = `文件行數超限！每個工作表最多允許 ${limits.maxRowsPerSheet} 行<br>`;
            violations.forEach(v => {
                errorMsg += `• 工作表 "${escapeHtml(v.sheet)}"：${v.rows} 行<br>`;
            });
            errorMsg += '請修正文件，只保留有效數據後重新上傳。';
            clearSelectedFile();
            showMessage(errorMsg, 'error', true);
            return;
        }

        selectedFile = file;
        fileMeta.textContent = sheetCount === null
            ? formatSize(file.size)
            : `${formatSize(file.size)} · ${sheetCount} 個工作表`;
        showMessage('文件可上傳', 'success');
        setTimeout(hideMessage, 2000);
    } catch (error) {
        if (token !== fileToken) {
            return;
        }
        console.error('文件異常:', error);
        clearSelectedFile();
        showMessage('文件異常：' + error.message, 'error');
    }
}

// ========== 輸入校驗 ==========

function validateInputs() {
    if (!selectedFile) {
        return '請先選擇文件';
    }

    const isCol = c => c.length === 1 && c >= 'A' && c <= 'Z';
    const input = inputCol.value.trim().toUpperCase();
    const output1 = outputCol1.value.trim().toUpperCase();

    if (!isCol(input)) {
        return '請輸入正確的檢查列號';
    }
    if (!isCol(output1) || output1 === input) {
        return '請輸入正確的提示列號，不可與其他列號重複';
    }
    if (getMode() === 'common') {
        const output2 = outputCol2.value.trim().toUpperCase();
        if (!isCol(output2) || output2 === input || output2 === output1) {
            return '請輸入正確的提示列號，不可與其他列號重複';
        }
    }
    return null;
}

function buildCheckConfig() {
    const config = {
        project: getProjectFromURL(),
        mode: getMode(),
        inputCol: inputCol.value.trim().toUpperCase(),
        outputCol1: outputCol1.value.trim().toUpperCase(),
        checkAllSheets: document.querySelector('input[name="sheetType"]:checked').value === '1',
    };
    if (config.mode === 'common') {
        config.outputCol2 = outputCol2.value.trim().toUpperCase();
    } else {
        config.includeTransHint = extraHint.checked;
    }
    return config;
}

// ========== 上傳與檢查 ==========

/** 從失敗回應中取出錯誤信息；nginx 等返回的非 JSON 頁面也能給出可讀提示 */
function parseErrorResponse(xhr) {
    try {
        const data = JSON.parse(xhr.responseText || '{}');
        if (data.error) {
            return data.error;
        }
    } catch (e) {
        // 非 JSON 回應，按狀態碼提示
    }
    if (xhr.status === 413) {
        return `文件過大，建議小於 ${limits.maxFileSizeMb}MB`;
    }
    if (xhr.status === 502 || xhr.status === 503 || xhr.status === 504) {
        return `伺服器暫時無法處理（HTTP ${xhr.status}），請稍後重試`;
    }
    return `處理失敗（HTTP ${xhr.status || '連線中斷'}）`;
}

/**
 * 上傳並等待檢查結果。
 * 上傳階段顯示真實進度；伺服器處理階段無法得知進度，顯示已用時間。
 */
function uploadAndCheck(formData) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        let timer = null;
        const stopTimer = () => timer && clearInterval(timer);

        xhr.open('POST', `${API_BASE}/check`);

        xhr.upload.onprogress = e => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                showProgress(percent, `上傳中... ${percent}%`);
            }
        };
        xhr.upload.onload = () => {
            const start = Date.now();
            showIndeterminate('伺服器檢查中... 0 秒');
            timer = setInterval(() => {
                const sec = Math.floor((Date.now() - start) / 1000);
                showIndeterminate(`伺服器檢查中... ${sec} 秒`);
            }, 1000);
        };
        xhr.onreadystatechange = () => {
            // 收到回應頭後再決定格式：成功時是 xlsx 二進位，失敗時是 JSON 文字
            if (xhr.readyState === XMLHttpRequest.HEADERS_RECEIVED) {
                xhr.responseType = xhr.status === 200 ? 'blob' : 'text';
            }
        };
        xhr.onload = () => {
            stopTimer();
            if (xhr.status === 200) {
                resolve(xhr.response);
            } else {
                reject(new Error(parseErrorResponse(xhr)));
            }
        };
        xhr.onerror = () => {
            stopTimer();
            reject(new Error('網絡連線失敗，請檢查網絡後重試'));
        };
        xhr.send(formData);
    });
}

function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/** 檢查進行中鎖住選文件區，避免中途換文件 */
function setBusy(busy) {
    checkBtn.disabled = busy;
    fileInput.disabled = busy;
    fileDrop.classList.toggle('busy', busy);
    fileDrop.setAttribute('aria-disabled', String(busy));
}

async function startCheck() {
    if (checkBtn.disabled) {
        return;
    }
    const error = validateInputs();
    if (error) {
        showMessage(error, 'error');
        return;
    }

    const file = selectedFile;
    const downloadName = `checked_${file.name}`;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('config', JSON.stringify(buildCheckConfig()));

    try {
        setBusy(true);
        hideMessage();
        showProgress(0, '上傳中... 0%');

        const blob = await uploadAndCheck(formData);
        downloadBlob(blob, downloadName);

        hideProgress();
        showMessage(`檢查完成！文件已下載：${downloadName}`, 'success');
    } catch (error) {
        console.error('處理錯誤:', error);
        hideProgress();
        showMessage(error.message, 'error');
    } finally {
        setBusy(false);
    }
}

// ========== 事件綁定 ==========

function updateModeUI() {
    if (getMode() === 'common') {
        inputColLabel.textContent = '待檢查翻譯列號 (A~Z)：';
        outputCol2Group.style.display = 'block';
        extraHintGroup.style.display = 'none';
    } else {
        inputColLabel.textContent = '日文原文列號 (A~Z)：';
        outputCol2Group.style.display = 'none';
        extraHintGroup.style.display = 'block';
    }
}

document.querySelectorAll('input[name="checkMode"]').forEach(radio => {
    radio.addEventListener('change', updateModeUI);
});

fileInput.addEventListener('change', e => handleFile(e.target.files[0]));

// 拖放上傳
['dragenter', 'dragover'].forEach(type => {
    fileDrop.addEventListener(type, e => {
        e.preventDefault();
        fileDrop.classList.add('dragover');
    });
});
['dragleave', 'drop'].forEach(type => {
    fileDrop.addEventListener(type, e => {
        e.preventDefault();
        fileDrop.classList.remove('dragover');
    });
});
fileDrop.addEventListener('drop', e => {
    if (fileInput.disabled) {
        return;
    }
    // 拖放不經過 input，清掉 input 裡的舊值，之後重新選同一個文件也能觸發 change
    fileInput.value = '';
    handleFile(e.dataTransfer.files[0]);
});

// 鍵盤：在選文件區按 Enter / 空格打開選擇框
fileDrop.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!fileInput.disabled) {
            fileInput.click();
        }
    }
});

// 拖到頁面其他地方時，不讓瀏覽器直接打開文件
['dragover', 'drop'].forEach(type => {
    window.addEventListener(type, e => e.preventDefault());
});

[inputCol, outputCol1, outputCol2].forEach(input => {
    input.addEventListener('input', e => {
        e.target.value = e.target.value.toUpperCase();
    });
});

checkBtn.addEventListener('click', startCheck);

// Ctrl + Enter 開始檢查
document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        startCheck();
    }
});

// ========== 初始化 ==========

function showProjectError() {
    pageWrapper.style.display = 'none';
    document.getElementById('topBanner').style.display = 'none';
    errorContainer.style.display = 'flex';
}

async function loadClientConfig() {
    try {
        const response = await fetch(`${API_BASE}/client-config`);
        if (!response.ok) {
            return;
        }
        const data = await response.json();
        if (Number.isFinite(data.maxFileSizeMb)) {
            limits.maxFileSizeMb = data.maxFileSizeMb;
        }
        if (Number.isFinite(data.maxRowsPerSheet)) {
            limits.maxRowsPerSheet = data.maxRowsPerSheet;
        }
    } catch (error) {
        console.warn('讀取上傳限制失敗，使用預設值:', error);
    }
}

async function loadProjectInfo(projectId) {
    try {
        const response = await fetch(`${API_BASE}/project/${encodeURIComponent(projectId)}`);
        if (!response.ok) {
            throw new Error('項目不存在');
        }

        const data = await response.json();
        currentProject = data.project;

        const nameText = currentProject.name;
        const descText = currentProject.description || '';
        projectName.textContent = nameText;
        projectDescription.textContent = descText;
        projectInfo.textContent = `詞庫更新時間: ${data.termDictVersion} | 易錯詞更新時間: ${data.errDictVersion}`;
        bannerProjectName.textContent = nameText;
        bannerProjectDesc.textContent = descText;

        applyAccentColor(currentProject.accentColor);

        if (currentProject.bgImage) {
            const imgUrl = '/transtool-py/img/' + currentProject.bgImage;
            const img = new Image();
            img.onload = function () {
                bgLayer.style.backgroundImage = 'url(' + imgUrl + ')';
                bgLayer.classList.add('loaded');
            };
            img.src = imgUrl;
        }
        return true;
    } catch (error) {
        console.error('載入項目信息失敗:', error);
        return false;
    }
}

async function init() {
    const projectId = getProjectFromURL();
    if (!projectId) {
        showProjectError();
        return;
    }

    const [success] = await Promise.all([loadProjectInfo(projectId), loadClientConfig()]);
    if (!success) {
        showProjectError();
        return;
    }

    updateModeUI();
    pageWrapper.style.display = 'flex';
    errorContainer.style.display = 'none';
}

init();
