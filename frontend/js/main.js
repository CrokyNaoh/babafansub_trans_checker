/**
 * 翻译检查工具 - 前端交互逻辑（后端处理版本）
 */

// DOM 元素
const checkMode = document.getElementById('checkMode');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const inputCol = document.getElementById('inputCol');
const outputCol1 = document.getElementById('outputCol1');
const outputCol2 = document.getElementById('outputCol2');
const outputCol1Label = document.getElementById('outputCol1Label');
const outputCol2Group = document.getElementById('outputCol2Group');
const extraHintGroup = document.getElementById('extraHintGroup');
const extraHint = document.getElementById('extraHint');
const checkBtn = document.getElementById('checkBtn');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const message = document.getElementById('message');
const container = document.querySelector('.container');
const errorContainer = document.getElementById('errorContainer');
const projectName = document.getElementById('projectName');
const projectDescription = document.getElementById('projectDescription');
const projectInfo = document.getElementById('projectInfo');

// 全局变量
let selectedFile = null;
let currentProject = null;

// ========== 配置区域 ==========
// 最大行数限制配置 - 每个sheet的最大行数不能超过此值
const MAX_ROWS_PER_SHEET = 70000;
// ============================

// 检查Excel文件行数是否超过限制
function checkExcelRowCount(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, {type: 'array'});
                
                const sheetNames = workbook.SheetNames;
                const violations = [];
                
                sheetNames.forEach(sheetName => {
                    const worksheet = workbook.Sheets[sheetName];
                    const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1:A1');
                    const rowCount = range.e.r + 1; // +1 因为行号从0开始
                    
                    if (rowCount > MAX_ROWS_PER_SHEET) {
                        violations.push({
                            sheet: sheetName,
                            rows: rowCount,
                            maxRows: MAX_ROWS_PER_SHEET
                        });
                    }
                });
                
                resolve(violations);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = function() {
            reject(new Error('文件读取失败'));
        };
        reader.readAsArrayBuffer(file);
    });
}

// 从 URL 获取项目参数
function getProjectFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('project');
}

// 显示错误页面
function showProjectError() {
    container.style.display = 'none';
    errorContainer.style.display = 'flex';
}

// 加载项目信息
async function loadProjectInfo(projectId) {
    try {
        const response = await fetch(`/transtool-py/api/project/${projectId}`);
        
        if (!response.ok) {
            throw new Error('项目不存在');
        }
        
        const data = await response.json();
        currentProject = data.project;
        
        // 更新页面标题、描述和版本信息
        projectName.textContent = '霸霸組繁中工具：' + currentProject.name;
        projectDescription.textContent = currentProject.description || '';
        projectInfo.textContent = `詞庫更新時間: ${data.termDictVersion} | 易錯詞更新時間: ${data.errDictVersion}`;
        
        return true;
    } catch (error) {
        console.error('加载项目信息失败:', error);
        return false;
    }
}

// 模式切换
checkMode.addEventListener('change', () => {
    const mode = checkMode.value;
    
    if (mode === 'common') {
        // 检查易错字词模式
        inputColLabel.textContent = '待檢查翻譯列號 (A~Z)：';
        outputCol2Group.style.display = 'block';
        extraHintGroup.style.display = 'none';
    } else {
        // 标注统一词模式
        inputColLabel.textContent = '日文原文列號 (A~Z)：';
        outputCol2Group.style.display = 'none';
        extraHintGroup.style.display = 'block';
    }
});

// 文件选择
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        selectedFile = file;
        fileName.textContent = file.name;
        
        // 检查文件大小
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            showMessage(`文件過大（${(file.size / 1024 / 1024).toFixed(1)}MB），建議小於 10MB`, 'error');
            selectedFile = null;
            fileName.textContent = '未選擇文件';
            return;
        }
        
        // 检查Excel文件筛选功能
        try {
            // 检查Excel文件行数
            showMessage('正在檢查文件行数...', 'info');
            const violations = await checkExcelRowCount(file);
            
            if (violations.length > 0) {
                // 构建错误信息
                let errorMsg = `文件行數超限！每個工作表最多允許${MAX_ROWS_PER_SHEET}行<br>`;
                violations.forEach(violation => {
                    errorMsg += `• 工作表 "${violation.sheet}": ${violation.rows}行<br>`;
                });
                errorMsg += '請修正文件，只保留有效數據後重新上傳。';
                
                showMessage(errorMsg, 'error');
                selectedFile = null;
                fileName.textContent = '未選擇文件';
                fileInput.value = ''; // 清空文件输入
            } else {
                showMessage('文件可上傳', 'success');
                setTimeout(() => hideMessage(), 2000); // 2秒后隐藏成功消息
            }
        } catch (error) {
            console.error('文件異常:', error);
            showMessage('文件異常：' + error.message, 'error');
            selectedFile = null;
            fileName.textContent = '未選擇文件';
            fileInput.value = ''; // 清空文件输入
        }
    } else {
        selectedFile = null;
        fileName.textContent = '未選擇文件';
    }
});

// 自动转大写
inputCol.addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
});
outputCol1.addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
});
outputCol2.addEventListener('input', (e) => {
    e.target.value = e.target.value.toUpperCase();
});

// 验证输入
function validateInputs() {
    if (!selectedFile) {
        return '請先選擇文件';
    }
    
    const mode = checkMode.value;
    const input = inputCol.value.trim().toUpperCase();
    const output1 = outputCol1.value.trim().toUpperCase();
    
    if (!input || input.length !== 1 || input < 'A' || input > 'Z') {
        return '請輸入正確的檢查列號';
    }
    
    if (!output1 || output1.length !== 1 || output1 < 'A' || output1 > 'Z' || output1 === input) {
        return '請輸入正確的提示列號，不可與其他列號重複';
    }
    
    if (mode === 'common') {
        const output2 = outputCol2.value.trim().toUpperCase();
        if (!output2 || output2.length !== 1 || output2 < 'A' || output2 > 'Z' || output2 === input || output2 === output1) {
            return '請輸入正確的提示列號，不可與其他列號重複';
        }
    }
    
    return null;
}

// 显示消息
function showMessage(text, type = 'info') {
    message.innerHTML = text;
    message.className = 'message ' + type;
}

// 隐藏消息
function hideMessage() {
    message.className = 'message';
}

// 显示进度
function showProgress(percent, text) {
    progressBar.style.display = 'block';
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

// 隐藏进度
function hideProgress() {
    progressBar.style.display = 'none';
}

// 开始检查（上传到后端处理）
checkBtn.addEventListener('click', async () => {
    // 验证输入
    const error = validateInputs();
    if (error) {
        showMessage(error, 'error');
        return;
    }
    
    try {
        checkBtn.disabled = true;
        hideMessage();
        showProgress(20, '上傳文件中...');
        
        // 准备表单数据
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const config = {
            project: getProjectFromURL(),
            mode: checkMode.value,
            inputCol: inputCol.value.toUpperCase(),
            outputCol1: outputCol1.value.toUpperCase(),
            checkAllSheets: document.querySelector('input[name="sheetType"]:checked').value === '1'
        };
        
        if (config.mode === 'common') {
            config.outputCol2 = outputCol2.value.toUpperCase();
        } else {
            config.includeTransHint = extraHint.checked;
        }
        
        formData.append('config', JSON.stringify(config));
        
        showProgress(50, '檢查中...');
        
        // 调用后端 API
        const response = await fetch('/transtool-py/api/check', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '處理失敗');
        }
        
        showProgress(80, '下載中...');
        
        // 下载文件
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `checked_${selectedFile.name}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        hideProgress();
        showMessage(`檢查完成！文件已下載：${a.download}`, 'success');
        
    } catch (error) {
        console.error('處理錯誤:', error);
        hideProgress();
        showMessage('處理失敗：' + error.message, 'error');
    } finally {
        checkBtn.disabled = false;
    }
});

// 初始化
async function init() {
    const projectId = getProjectFromURL();
    
    if (!projectId) {
        showProjectError();
        return;
    }
    
    // 加载项目信息
    const success = await loadProjectInfo(projectId);
    
    if (!success) {
        showProjectError();
        return;
    }
    
    // 显示主界面
    container.style.display = 'block';
    errorContainer.style.display = 'none';
}

// 页面加载完成后初始化
init();


