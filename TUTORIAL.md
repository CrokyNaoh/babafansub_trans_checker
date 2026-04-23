# 翻译检查工具 - 后端版本

## 📋 概述

这是翻译检查工具的**后端处理版本**，使用 Python + openpyxl 处理 Excel 文件，完美保留所有格式并支持字符级颜色标注。

### ✨ 核心特性

1. **完整保留 Excel 格式** ✅
   - 单元格样式（颜色、字体、边框、填充）
   - 合并单元格
   - 公式（不会转为值）
   - 条件格式
   - 数据验证
   - 图片和图表
   - Rich Text 格式
   - VBA 宏

2. **颜色标注功能** 🎨
   - 易混淆字在原文中标红
   - 使用 Rich Text 技术精准标注

3. **多项目支持** 🎯
   - 基于 URL 参数选择项目
   - 每个项目独立术语词典
   - 错误词典按标签过滤

4. **两种检查模式**
   - **检查易错字词**：错误词、警告词、叠字检查
   - **标注统一词**：术语词、易塞翻词提示

---

## 🏗️ 架构说明

### 技术栈

**后端：**
- Python 3.x
- Flask (Web 框架)
- openpyxl (Excel 处理，保留格式)
- Flask-CORS (跨域支持)

**前端：**
- HTML5 + CSS3 + JavaScript
- 文件上传 + 进度显示

**服务：**
- Nginx (反向代理 + 静态文件服务)

### 目录结构

```
web_py/
├── backend/                # 后端代码
│   ├── app.py             # Flask API
│   ├── checker_core.py    # 核心检查逻辑
│   └── requirements.txt   # Python 依赖
├── frontend/              # 前端代码
│   ├── index.html        # 主页面
│   ├── css/
│   │   └── style.css     # 样式
│   └── js/
│       └── main.js       # 交互逻辑
├── data/                  # 词库数据
│   ├── projects.json     # 项目配置
│   ├── errDict.json      # 错误词典
│   ├── termDict_game1.json
│   ├── termDict_game2.json
│   └── termDict_novel.json
├── logs/                  # 日志目录
├── deploy.env.template   # 部署地址等（复制为 deploy.env，勿提交真实值）
├── nginx.conf.template   # Nginx 模板
├── render_nginx.sh      # 由 template + deploy.env 生成本地 nginx.conf
├── start.sh              # 启动脚本
├── stop.sh               # 停止脚本
├── restart.sh            # 重启脚本
├── status.sh             # 状态检查
└── README.md             # 本文档
```

---

## 🚀 快速开始

### 0. 部署配置（首次 / 新机器）

仓库内**不**包含真实公网地址。请从模板生成本地 `deploy.env`（已加入 `.gitignore`）：

```bash
cd <项目根目录>
cp deploy.env.template deploy.env
# 编辑 deploy.env：至少设置 PUBLIC_ORIGIN、NGINX_SERVER_NAME、FRONTEND_ROOT
chmod +x render_nginx.sh
./render_nginx.sh
```

- `PUBLIC_ORIGIN`：对外访问根地址（无尾斜杠），如 `http://你的服务器` 或 `https://子域名.域名`，供项目列表「打开项目」与脚本提示使用。
- `FRONTEND_ROOT`：本机 `frontend` 目录的**绝对路径**。
- 生成本地 `nginx.conf` 后，再按下面「配置 Nginx」复制到 `sites-available`。

若暂不配置 `deploy.env`，后端仍可启动；项目列表会退化为使用**当前页所在 origin** 拼链接。

### 1. 安装依赖

```bash
cd <项目根目录>

# 安装 Python 依赖
pip3 install -r backend/requirements.txt
```

### 2. 启动后端服务

```bash
# 启动
./start.sh

# 查看状态
./status.sh

# 停止
./stop.sh

# 重启
./restart.sh
```

### 3. 配置 Nginx

先完成上一节中的 `./render_nginx.sh`，生成本地 `nginx.conf`（该文件不提交到 Git）。

```bash
# 复制配置文件
sudo cp nginx.conf /etc/nginx/sites-available/transtool-py
sudo ln -sf /etc/nginx/sites-available/transtool-py /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 4. 访问应用

将 `<PUBLIC_ORIGIN>` 换为 `deploy.env` 中的 `PUBLIC_ORIGIN`（无尾斜杠），例如 `http://你的服务器`：

```
<PUBLIC_ORIGIN>/transtool-py/index.html?project=game1
<PUBLIC_ORIGIN>/transtool-py/index.html?project=game2
<PUBLIC_ORIGIN>/transtool-py/index.html?project=novel
```

本机调试可访问（若 Nginx 监听本机 80 端口）：

```
http://127.0.0.1/transtool-py/index.html?project=game1
```

---

## 📝 项目配置

### projects.json 格式

```json
{
  "projects": {
    "game1": {
      "name": "游戏项目1",
      "description": "第一个游戏翻译项目",
      "tags": ["game", "rpg"],
      "termDict": "termDict_game1.json"
    },
    "game2": {
      "name": "游戏项目2",
      "description": "第二个游戏翻译项目",
      "tags": ["game", "action"],
      "termDict": "termDict_game2.json"
    }
  }
}
```

**字段说明：**
- `name`: 项目显示名称
- `description`: 项目描述
- `tags`: 项目标签数组（用于过滤 errDict）
- `termDict`: 术语词典文件名

### errDict.json 格式

```json
{
  "version": "2025-10-01 23:00",
  "err": {
    "錯誤詞1": {
      "correct": "正確詞1",
      "tags": ["game", "novel"]
    },
    "錯誤詞2": {
      "correct": "正確詞2",
      "tags": []
    }
  },
  "warn": {
    "易混淆字組1": "說明文字"
  },
  "repeat": ["的", "了", "是"],
  "transhint": {
    "スキル": "技能/技巧"
  }
}
```

**说明：**
- `version`: 错误词典版本号（更新词典时修改）
- `err` 中的词条通过 `tags` 筛选：
  - 如果 `tags` 为空数组 `[]`，则对所有项目生效
  - 如果 `tags` 不为空，则只对包含相应标签的项目生效
- `warn`、`repeat`、`transhint` 对所有项目全局生效

### termDict_xxx.json 格式

```json
{
  "version": "2025-10-01 23:00",
  "word": [
    {
      "ja": "スキル",
      "zh": "技能",
      "note": "游戏术语"
    }
  ]
}
```

**说明：**
- `version`: 术语词典版本号（更新词典时修改）
- `word`: 术语词数组

---

## 🎨 颜色标注功能

### 原理

使用 openpyxl 的 `CellRichText` 功能，对单元格内的特定字符设置红色：

```python
from openpyxl.cell.text import InlineFont
from openpyxl.cell.rich_text import TextBlock, CellRichText

red_font = InlineFont(color='FF0000')
rich_text = CellRichText([
    TextBlock(red_font, char) if char in mark_chars else char
    for char in content
])
sheet['C2'] = rich_text
```

### 应用场景

在**检查易错字词**模式下：
- 检测到易混淆字（如"的地得"）
- 在原文单元格中将这些字标红
- 方便译者快速定位问题

### 效果示例

原文：`这是一个測試的文本`
- "的" 是易混淆字
- 输出：这是一个測試<span style="color:red;">的</span>文本（红色）

---

## 🔍 API 文档

### 1. 健康检查

```
GET /transtool-py/api/health
```

**响应：**
```json
{
  "status": "ok",
  "timestamp": "2025-10-01T23:00:00",
  "projects": ["game1", "game2", "novel"]
}
```

### 2. 获取项目信息

```
GET /transtool-py/api/project/{project_id}
```

**响应：**
```json
{
  "project": {
    "name": "游戏项目1",
    "description": "...",
    "tags": ["game", "rpg"],
    "termDict": "termDict_game1.json"
  },
  "errDictVersion": "2025-10-01 23:00",
  "termDictVersion": "2025-10-01 23:00"
}
```

### 3. 检查 Excel 文件

```
POST /transtool-py/api/check
Content-Type: multipart/form-data
```

**参数：**
- `file`: Excel 文件 (.xlsx)
- `config`: JSON 配置字符串

**config 格式：**
```json
{
  "project": "game1",
  "mode": "common",           // 或 "spec"
  "inputCol": "C",
  "outputCol1": "E",
  "outputCol2": "F",          // 仅 common 模式
  "checkAllSheets": true,
  "includeTransHint": false   // 仅 spec 模式
}
```

**响应：**
- 返回处理后的 Excel 文件（二进制流）

---

## 🛠️ 运维管理

### 启动服务

```bash
./start.sh
```

**检查内容：**
1. Python 环境
2. 依赖包
3. 词库文件
4. 启动后端
5. 测试 API

### 查看状态

```bash
./status.sh
```

**显示信息：**
- 后端进程状态
- API 健康检查
- Nginx 配置状态
- 访问地址
- 日志文件

### 停止服务

```bash
./stop.sh
```

### 重启服务

```bash
./restart.sh
```

### 查看日志

```bash
# 实时查看后端日志
tail -f logs/backend.log

# 查看 Nginx 日志
tail -f /var/log/nginx/transtool_py_access.log
tail -f /var/log/nginx/transtool_py_error.log
```

---

## 📊 性能说明

### 文件大小限制

| 文件大小 | 处理速度 | 说明 |
|---------|---------|------|
| < 10MB  | < 5秒   | 推荐 |
| 10-50MB | 5-30秒  | 可接受 |
| 50-100MB| 30-120秒| 慢但可用 |
| > 100MB | 拒绝    | 超出限制 |

#### 修改文件大小限制

如需调整文件大小限制，需要同步修改以下文件：

1. **config.py** （主配置文件）
   - 路径：`<项目根目录>/config.py`
   - 修改：`MAX_FILE_SIZE_MB = 100`

2. **frontend/js/main.js** （前端验证）
   - 路径：`<项目根目录>/frontend/js/main.js`
   - 第 90 行：`const maxSize = 10 * 1024 * 1024; // 10MB`
   - 第 92 行：错误提示文本

3. **由 nginx.conf.template 生成的 nginx.conf** （Nginx 上传限制）
   - 修改模板或生成后的 `nginx.conf` 中：`client_max_body_size 10M;`
   - 修改后需执行 `./render_nginx.sh`（若改动了依赖 deploy.env 的项），再重载 Nginx：`sudo systemctl reload nginx`

**注意：** 三处配置必须保持一致，否则会导致上传失败。当前配置为：
- 后端支持：100MB（config.py）
- 前端限制：10MB（main.js）
- Nginx 限制：10M（本地生成的 nginx.conf）
- **实际生效：10MB**（取最小值）

### 并发能力

- 单进程：1-2 个并发请求
- 建议使用 Gunicorn 多进程：
  ```bash
  gunicorn -w 4 -b 127.0.0.1:5000 app:app
  ```

---

## 🆚 与前端版本对比

| 特性 | 前端版本 (web/) | 后端版本 (web_py/) |
|-----|----------------|-------------------|
| 格式保留 | ❌ 丢失所有格式 | ✅ 完整保留 |
| 公式 | ❌ 转为值 | ✅ 保留公式 |
| 合并单元格 | ❌ 丢失 | ✅ 保留 |
| 颜色标注 | ❌ 不支持 | ✅ 支持 |
| 图片图表 | ❌ 丢失 | ✅ 保留 |
| 文件上传 | ❌ 本地处理 | ✅ 需上传 |
| 隐私性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 大文件 | ❌ 易崩溃 | ✅ 稳定处理 |

### 选择建议

**使用前端版本 (web/)：**
- ✅ 注重隐私，不想上传文件
- ✅ 简单文本检查，不需要保留格式
- ✅ 快速检查，无需复杂处理

**使用后端版本 (web_py/)：**
- ✅ 需要保留完整 Excel 格式
- ✅ 需要颜色标注功能
- ✅ 处理复杂或大型文件
- ✅ 团队协作，共享词库

---

## 🔧 故障排查

### 1. 后端启动失败

**检查：**
```bash
# 查看详细错误
cat logs/backend.log

# 检查端口占用
lsof -i:5000

# 检查 Python 依赖
pip3 list | grep -E "Flask|openpyxl|flask-cors"
```

### 2. Nginx 502 错误

**原因：** 后端未启动或连接失败

**解决：**
```bash
# 检查后端状态
./status.sh

# 重启后端
./restart.sh

# 检查 Nginx 配置
sudo nginx -t
```

### 3. 文件上传失败

**检查：**
```bash
# 检查文件权限
ls -la /tmp/transtool_uploads/

# 检查磁盘空间
df -h /tmp

# 检查 Nginx 上传限制
grep client_max_body_size /etc/nginx/nginx.conf
```

### 4. 词库加载失败

**检查：**
```bash
# 验证 JSON 格式
python3 -m json.tool data/projects.json
python3 -m json.tool data/errDict.json

# 检查文件权限
ls -la data/
```

---

## 📈 优化建议

### 1. 使用 Gunicorn（生产环境）

修改 `start.sh`，使用 Gunicorn：

```bash
cd backend
gunicorn -w 4 \
  -b 127.0.0.1:5000 \
  --timeout 300 \
  --access-logfile ../logs/access.log \
  --error-logfile ../logs/error.log \
  app:app
```

### 2. 配置 Systemd 服务

创建 `/etc/systemd/system/transtool-py.service`：

```ini
[Unit]
Description=Translation Tool Backend
After=network.target

[Service]
Type=simple
User=<你的 Linux 用户>
WorkingDirectory=<项目根目录>/backend
ExecStart=/usr/bin/python3 app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable transtool-py
sudo systemctl start transtool-py
```

### 3. 日志轮转

创建 `/etc/logrotate.d/transtool-py`：

```
<项目根目录>/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

---

## 🔐 安全建议

1. **文件上传限制**
   - 已限制文件类型 (.xlsx)
   - 已限制文件大小 (100MB)
   - 建议添加病毒扫描

2. **访问控制**
   - 建议使用 HTTPS
   - 可添加 Basic Auth 或 JWT 认证
   - IP 白名单限制

3. **临时文件清理**
   - 已自动清理处理后的文件
   - 建议定期清理 `/tmp/transtool_uploads/`

---

## 📚 相关文档

- [openpyxl 官方文档](https://openpyxl.readthedocs.io/)
- [Flask 官方文档](https://flask.palletsprojects.com/)
- [Nginx 反向代理配置](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)

---

## 📝 更新日志

### v2.0.0 (2025-10-01)
- ✨ 完整保留 Excel 格式
- ✨ 支持字符级颜色标注
- ✨ 多项目配置支持
- ✨ 后端 API 实现
- ✨ 完善的运维脚本

---

## 💡 常见问题

### Q: 为什么需要上传文件？
A: 因为要使用 openpyxl 保留完整格式，必须在服务器端处理。前端 SheetJS 无法保留格式。

### Q: 上传的文件会保存吗？
A: 不会。处理完成后自动删除临时文件。

### Q: 能否离线使用？
A: 后端版本需要服务器。如需离线，可使用原始 `CHTchecker_v3.0.py` 脚本。

### Q: 支持哪些 Excel 版本？
A: 仅支持 .xlsx 格式（Excel 2007+），不支持 .xls（Excel 97-2003）。

---

**开发者：** 基于 CHTchecker_v3.0.py 改造  
**版本：** 2.0.0  
**最后更新：** 2025-10-01


