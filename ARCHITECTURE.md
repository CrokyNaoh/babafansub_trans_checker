# Web_py 工作逻辑详解

## 🎯 系统架构概览

```
用户浏览器
    ↓
Nginx (端口 8080)
    ↓
    ├─→ 静态文件服务 (/transtool-py/)
    │   - index.html
    │   - CSS, JavaScript
    │   
    └─→ API 代理 (/transtool-py/api/)
        ↓
    Flask 后端 (端口 5000)
        ↓
    openpyxl 处理
        ↓
    返回处理后的 Excel
```

---

## 📋 完整工作流程

### 第一阶段：用户访问页面

#### 1. 用户输入 URL
```
http://<服务器或域名>:<端口>/transtool-py/index.html?project=game1
        ↑                 ↑                ↑
     公网/内网        如 80/8080        项目参数
```

（对外访问时 `PUBLIC_ORIGIN` 写在本地 `deploy.env` 中，不进入版本库。）

#### 2. Nginx 处理请求
```nginx
# 由 nginx.conf.template + deploy.env 生成本地 nginx.conf
location /transtool-py/ {
    alias <FRONTEND_ROOT>/;
    # 返回 index.html
}
```

**Nginx 做了什么：**
- 监听 8080 端口
- 匹配 `/transtool-py/` 路径
- 将请求映射到 `web_py/frontend/` 目录
- 返回 `index.html`

#### 3. 浏览器加载页面
```html
<!-- index.html -->
<link rel="stylesheet" href="/transtool-py/css/style.css">
<script src="/transtool-py/js/main.js"></script>
```

**浏览器请求：**
1. `GET /transtool-py/index.html` → 返回 HTML
2. `GET /transtool-py/css/style.css` → 返回 CSS
3. `GET /transtool-py/js/main.js` → 返回 JavaScript

---

### 第二阶段：初始化项目信息

#### 4. JavaScript 读取 URL 参数
```javascript
// main.js - init()
function getProjectFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('project');  // 返回 'game1'
}
```

#### 5. 请求项目信息
```javascript
// main.js - loadProjectInfo()
const response = await fetch('/transtool-py/api/project/game1');
```

**请求路径：**
```
浏览器 → GET /transtool-py/api/project/game1
          ↓
       Nginx (代理)
          ↓
       POST http://127.0.0.1:5000/api/project/game1
          ↓
       Flask 后端
```

#### 6. 后端加载词库并返回
```python
# app.py - get_project_info()

# 1. 检查项目是否存在
if project_id not in PROJECTS:
    return 404

# 2. 根据项目标签过滤 errDict
project_tags = PROJECTS[project_id]['tags']  # ['game', 'rpg']
err_dict = filter_err_dict_by_tags(ERR_DICT_FULL, project_tags)

# 3. 加载项目专属 termDict
term_dict_file = 'termDict_game1.json'
term_dict = load(term_dict_file)

# 4. 返回 JSON
return {
    'project': {...},
    'errDictVersion': '2025-10-01 23:00',
    'termDictVersion': '2025-10-01 23:00'
}
```

#### 7. 前端更新页面
```javascript
// main.js
projectName.textContent = "游戏项目1";
projectInfo.textContent = "termDict: 2025-10-01 23:00 | errDict: 2025-10-01 23:00";
```

---

### 第三阶段：用户操作

#### 8. 用户选择文件和配置
```javascript
用户操作：
1. 选择功能：[检查易错字词]
2. 选择文件：example.xlsx
3. 输入列号：
   - 检查列：C
   - 提示列1：E
   - 提示列2：F
4. 工作表范围：[仅第一个]
5. 点击：[开始检查]
```

#### 9. 前端验证输入
```javascript
// main.js - validateInputs()
function validateInputs() {
    // 1. 检查是否选择了文件
    if (!selectedFile) return '請先選擇文件';
    
    // 2. 检查列号格式
    if (inputCol < 'A' || inputCol > 'Z') return '請輸入正確的列號';
    
    // 3. 检查文件大小
    if (file.size > 100MB) return '文件過大';
    
    return null;  // 验证通过
}
```

---

### 第四阶段：文件上传与处理

#### 10. 前端准备请求
```javascript
// main.js - checkBtn.click()

// 1. 创建 FormData（支持文件上传）
const formData = new FormData();

// 2. 添加文件
formData.append('file', selectedFile);  // 实际的 Excel 文件

// 3. 添加配置（JSON 字符串）
formData.append('config', JSON.stringify({
    project: 'game1',
    mode: 'common',
    inputCol: 'C',
    outputCol1: 'E',
    outputCol2: 'F',
    checkAllSheets: false
}));

// 4. 发送请求
const response = await fetch('/transtool-py/api/check', {
    method: 'POST',
    body: formData
});
```

#### 11. Nginx 代理到后端
```nginx
# 本地生成的 nginx.conf（自 template）
location ^~ /transtool-py/api/ {
    proxy_pass http://127.0.0.1:5000/api/;
    client_max_body_size 100M;  # 允许大文件
}
```

**流程：**
```
浏览器上传 → Nginx (8080) → Flask (5000)
  [文件]        [代理]         [接收]
```

#### 12. 后端接收并验证
```python
# app.py - check_excel()

# 1. 接收文件
file = request.files['file']  # Excel 文件对象

# 2. 接收配置
config = json.loads(request.form.get('config'))

# 3. 验证文件
if not file.filename.endswith('.xlsx'):
    return 400, '僅支持 .xlsx 文件'

if file.size > 100MB:
    return 400, '文件過大'

# 4. 验证项目和列号
if project_id not in PROJECTS:
    return 400, '無效的項目ID'

if not valid_column(inputCol):
    return 400, '無效的列號'
```

---

### 第五阶段：Excel 处理（核心）

#### 13. 保存临时文件
```python
# app.py

# 1. 生成唯一文件名
timestamp = int(time.time())
input_filename = f"{timestamp}_example.xlsx"
input_path = "/tmp/transtool_uploads/1696204800_example.xlsx"

# 2. 保存上传的文件
file.save(input_path)
```

#### 14. 加载项目词库
```python
# app.py - load_project_dicts()

# 1. 获取项目标签
project_tags = ['game', 'rpg']

# 2. 过滤 errDict（只保留匹配标签的错误词）
err_dict = filter_err_dict_by_tags(ERR_DICT_FULL, project_tags)
# 结果：只包含 tags 中有 'game' 或 'rpg' 的错误词

# 3. 加载项目 termDict
term_dict = load('termDict_game1.json')
```

**词库过滤示例：**
```json
// 原始 errDict
{
  "err": {
    "錯誤1": {"correct": "正確1", "tags": ["game"]},      ← 保留
    "錯誤2": {"correct": "正確2", "tags": ["novel"]},     ← 过滤掉
    "錯誤3": {"correct": "正確3", "tags": ["game", "novel"]} ← 保留（有交集）
  }
}

// 过滤后（game1 项目）
{
  "err": {
    "錯誤1": {"correct": "正確1", "tags": ["game"]},
    "錯誤3": {"correct": "正確3", "tags": ["game", "novel"]}
  }
}
```

#### 15. 创建检查器并处理
```python
# app.py

# 1. 创建检查器实例
checker = ExcelChecker(err_dict, term_dict)

# 2. 调用处理方法
output_path = checker.process_file(
    input_path,   # 输入文件
    output_path,  # 输出文件
    config        # 配置
)
```

#### 16. 核心处理逻辑（保留格式）
```python
# checker_core.py - process_file()

# 1. 加载工作簿（关键：保留所有格式）
wb = load_workbook(input_path, 
                   data_only=False,  # 保留公式
                   keep_vba=True)    # 保留宏

# 2. 确定要处理的工作表
if config['checkAllSheets']:
    sheetnames = wb.sheetnames  # 所有工作表
else:
    sheetnames = [wb.sheetnames[0]]  # 仅第一个

# 3. 根据模式执行检查
if config['mode'] == 'common':
    do_common_check(...)  # 检查易错字词
else:
    do_spec_check(...)     # 标注统一词

# 4. 保存（所有原始格式保留）
wb.save(output_path)
```

---

### 第六阶段：具体检查逻辑

#### 17a. 检查易错字词模式（common）
```python
# checker_core.py - do_common_check()

for row in sheet.iter_rows():
    # 跳过首行（表头）
    if first:
        first = False
        continue
    
    # 获取待检查的单元格内容
    content = str(row[input_col_index].value)  # C列
    
    # === 1. 检查错误词 ===
    err_hints = []
    for err_word, correct in err_dict['err'].items():
        if err_word in content:
            err_hints.append(f"{err_word}→{correct}")
    
    # === 2. 检查易混淆字（标红功能）===
    warn_hints = []
    mark_chars = []  # 需要标红的字符
    
    for warn_word, desc in err_dict['warn'].items():
        for char in warn_word:
            if char in content:
                mark_chars.append(char)  # 记录需要标红
                warn_hints.append(f"{warn_word}：{desc}")
                break
    
    # === 3. 检查叠字 ===
    for i in range(1, len(content)):
        if content[i-1] == content[i]:  # 连续重复
            if content[i] not in repeat_chars:  # 不在白名单
                warn_hints.append(f"出現疊字 {content[i]}")
    
    # === 4. 写入检查结果 ===
    sheet.cell(row_num, err_col).value = '\n'.join(err_hints)
    sheet.cell(row_num, warn_col).value = '\n'.join(warn_hints)
    
    # === 5. 设置自动换行 ===
    sheet.cell(row_num, err_col).alignment = Alignment(wrapText=True)
    
    # === 6. 调整列宽和行高 ===
    sheet.column_dimensions[err_col].width = estimate_width(err_hints)
    sheet.row_dimensions[row_num].height = estimate_height(err_hints)
    
    # === 7. 颜色标注（Rich Text）===
    if mark_chars:
        red_font = InlineFont(color='FF0000')
        rich_text = CellRichText([
            TextBlock(red_font, char) if char in mark_chars else char
            for char in content
        ])
        sheet[f'C{row_num}'] = rich_text  # 在原单元格标红
```

**颜色标注示例：**
```
原文：这是一个測試的文本
易混淆字：的
结果：这是一个測試的文本
               ↑ 标红
```

#### 17b. 标注统一词模式（spec）
```python
# checker_core.py - do_spec_check()

for row in sheet.iter_rows():
    content = str(row[input_col].value)
    content_clean = fix_content(content)  # 去除换行、全角空格
    
    hints = []
    
    # === 1. 检查统一词 ===
    for term in term_dict['word']:
        term_text = term['']
        term_clean = fix_content(term_text)
        
        if term_clean in content_clean:
            comment = f"({term['comment']})" if term.get('comment') else ''
            hints.append(f"{term_text}{comment}：{term['suggestion']}")
    
    # === 2. 检查易塞翻词（可选）===
    if include_transhint:
        for trans_word, desc in err_dict['transhint'].items():
            if trans_word not in term_set and trans_word in content_clean:
                hints.append(f"{trans_word}：{desc}")
    
    # === 3. 写入结果 ===
    sheet.cell(row_num, warn_col).value = '\n'.join(hints)
```

---

### 第七阶段：返回文件

#### 18. 后端返回处理后的文件
```python
# app.py

# 1. 发送文件
response = send_file(
    output_path,
    as_attachment=True,
    download_name=f"checked_example.xlsx",
    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)

# 2. 清理临时文件（在发送完成后）
@response.call_on_close
def cleanup():
    os.remove(input_path)   # 删除上传的原文件
    # 延迟删除输出文件（确保已发送）
    threading.Thread(target=lambda: time.sleep(5) and os.remove(output_path)).start()

return response
```

#### 19. 前端接收并下载
```javascript
// main.js

// 1. 接收文件（Blob）
const blob = await response.blob();

// 2. 创建下载链接
const url = URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = 'checked_example.xlsx';

// 3. 触发下载
document.body.appendChild(a);
a.click();
document.body.removeChild(a);

// 4. 释放资源
URL.revokeObjectURL(url);

// 5. 显示成功消息
showMessage('檢查完成！文件已下載', 'success');
```

---

## 🎨 关键技术细节

### 1. 格式保留的原理

**为什么能保留格式？**
```python
# ❌ 错误做法（会丢失格式）
data = sheet.values  # 只获取数据
new_sheet = create_sheet()
new_sheet.append(data)  # 重建工作表

# ✅ 正确做法（保留格式）
wb = load_workbook(file, data_only=False)  # 加载完整信息
sheet.cell(2, 5).value = '新内容'  # 只修改值
wb.save(output)  # 保存时保留所有格式
```

**openpyxl 保留的内容：**
- ✅ 单元格样式（字体、颜色、边框、填充）
- ✅ 合并单元格
- ✅ 公式（`data_only=False`）
- ✅ 条件格式
- ✅ 数据验证
- ✅ 图片和图表（位置不变时）
- ✅ VBA 宏（`keep_vba=True`）

### 2. Rich Text 颜色标注

**原理：**
```python
# 普通文本（单一格式）
cell.value = "这是文本"

# Rich Text（多种格式混合）
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont

red_font = InlineFont(color='FF0000')

# 对每个字符单独设置格式
cell.value = CellRichText([
    '这',
    '是',
    TextBlock(red_font, '一'),  # 这个字是红色
    '个',
    '文',
    '本'
])
```

**效果：**
```
这是一个文本
  ↑ 只有这个字是红色
```

### 3. 多项目词库过滤

**过滤逻辑：**
```python
def filter_err_dict_by_tags(err_dict, project_tags):
    filtered = {'err': {}}
    
    for word, data in err_dict['err'].items():
        word_tags = data['tags']
        
        # 只要有任一标签匹配就保留
        if any(tag in project_tags for tag in word_tags):
            filtered['err'][word] = data
    
    # warn、repeat、transhint 全局生效
    filtered['warn'] = err_dict['warn']
    filtered['repeat'] = err_dict['repeat']
    filtered['transhint'] = err_dict['transhint']
    
    return filtered
```

**示例：**
```python
项目标签: ['game', 'rpg']

错误词1: tags=['game']         → 保留 ✅
错误词2: tags=['novel']        → 过滤 ❌
错误词3: tags=['game', 'novel'] → 保留 ✅（有交集）
```

---

## 📊 数据流图

```
┌─────────────┐
│ 用户浏览器   │
└──────┬──────┘
       │ 1. GET /transtool-py/index.html?project=game1
       ↓
┌──────────────┐
│ Nginx (8080) │ ← 静态文件服务
└──────┬───────┘
       │ 2. 返回 HTML/CSS/JS
       ↓
┌─────────────┐
│ JavaScript  │
└──────┬──────┘
       │ 3. GET /transtool-py/api/project/game1
       ↓
┌──────────────┐
│ Nginx (代理) │
└──────┬───────┘
       │ 4. 代理到 127.0.0.1:5000
       ↓
┌──────────────┐
│ Flask 后端   │ ← 加载词库
└──────┬───────┘
       │ 5. 返回项目信息 + 版本号
       ↓
┌─────────────┐
│ JavaScript  │ ← 更新页面
└──────┬──────┘
       │ 用户操作：选择文件、配置
       │ 6. POST /transtool-py/api/check
       │    FormData: file + config
       ↓
┌──────────────┐
│ Nginx (代理) │
└──────┬───────┘
       │ 7. 代理到 Flask
       ↓
┌──────────────┐
│ Flask 后端   │
└──────┬───────┘
       │ 8. 保存文件到 /tmp
       │ 9. 加载项目词库（按标签过滤）
       ↓
┌──────────────┐
│ ExcelChecker │
└──────┬───────┘
       │ 10. load_workbook (保留格式)
       │ 11. 遍历行
       │ 12. 检查内容
       │ 13. 写入提示
       │ 14. 标红字符 (Rich Text)
       │ 15. 调整列宽行高
       │ 16. save (保留格式)
       ↓
┌──────────────┐
│ Flask 后端   │
└──────┬───────┘
       │ 17. 返回文件 (Blob)
       │ 18. 清理临时文件
       ↓
┌─────────────┐
│ JavaScript  │
└──────┬──────┘
       │ 19. 创建下载链接
       │ 20. 触发下载
       ↓
┌─────────────┐
│ 用户浏览器   │ ← 保存文件
└─────────────┘
```

---

## 🔑 关键组件说明

### 1. Nginx 角色
- **静态文件服务器**：提供 HTML/CSS/JS
- **反向代理**：转发 API 请求到 Flask
- **负载均衡**：可配置多个 Flask 实例

### 2. Flask 角色
- **API 服务器**：提供 RESTful API
- **词库管理**：加载和过滤词库
- **文件管理**：接收上传、保存临时文件、清理

### 3. ExcelChecker 角色
- **核心处理引擎**：执行检查逻辑
- **格式保留**：使用 openpyxl 保留所有格式
- **颜色标注**：使用 Rich Text 标红字符

### 4. JavaScript 角色
- **用户界面**：表单交互、进度显示
- **项目管理**：读取 URL 参数、加载项目信息
- **文件处理**：上传文件、下载结果

---

## ⚡ 性能优化

### 1. 文件处理
- 大文件限制：100MB
- 临时文件自动清理
- 使用时间戳避免文件名冲突

### 2. 并发处理
```python
# 当前：单进程 Flask
app.run(threaded=True)

# 生产环境：Gunicorn 多进程
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### 3. 缓存策略
```nginx
# 静态资源缓存 5 分钟
add_header Cache-Control "public, max-age=300";
```

---

## 🛡️ 安全措施

### 1. 文件验证
- 扩展名检查（仅 .xlsx）
- 文件大小限制（100MB）
- MIME 类型验证

### 2. 输入验证
- 项目 ID 验证
- 列号格式验证（A-Z）
- 配置参数验证

### 3. 临时文件管理
- 唯一文件名（时间戳）
- 自动清理机制
- 权限控制（777）

---

## 📝 总结

**web_py 的核心优势：**

1. **完整保留 Excel 格式** ✅
   - 使用 openpyxl 的正确姿势
   - 只修改值，不重建结构

2. **字符级颜色标注** 🎨
   - Rich Text 技术
   - 精准标红易混淆字

3. **多项目智能过滤** 🎯
   - 基于标签的词库过滤
   - 项目独立术语词典

4. **前后端分离架构** 🏗️
   - 前端：用户界面
   - 后端：核心处理
   - Nginx：静态服务 + 代理

5. **健壮的错误处理** 🛡️
   - 文件验证
   - 输入验证
   - 自动清理

**适用场景：**
- ✅ 需要保留完整 Excel 格式
- ✅ 需要颜色标注功能
- ✅ 团队协作，共享词库
- ✅ 处理大型复杂文件

---

**开发者备注：**
这个架构基于 `CHTchecker_v3.0.py` 改造，保留了原始脚本的所有核心功能（包括颜色标注），并增加了 Web 化和多项目支持。

