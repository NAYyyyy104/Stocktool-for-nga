# StockToolForNga

非常感谢NGA大时代各位大佬的知识传授和灵感提供。

本项目是一个本地桌面股票观察与持仓管理工具，技术栈为：
- 前端：Vue 3 + Element Plus + Vite
- 桌面壳：Electron
- 后端：Python（本地 HTTP 服务）
- 本地存储：JSON + SQLite（休市日数据库）

## 功能概览

- 观察列表
  - 批量输入代码后查询并追加
  - 常规买点（0.382）/ 618 强撑（0.618）
  - 按分类筛选查看
  - 一键加入持仓

- 持仓管理
  - 按代码追加持仓
  - 成本价、数量、持仓后最高可手动维护
  - 自动刷新行情时，若行情高点更高会自动上调“持仓后最高”
  - 支持两套止盈止损规则（可按持仓选择）

- 分类系统
  - 观察列表与持仓标签互通
  - 独立分类管理（新增、重命名、删除）

- 交易日与休市日
  - 规则2按“交易日”计算（排除周末与休市）
  - 内置 2026 年休市日
  - 支持在界面中新增/删除休市日（持久化到 SQLite）

## 环境要求

- Node.js 18+
- Python 3.9+

## 安装依赖

```bash
npm install
```

## 启动方式

开发模式（推荐）：
```bash
npm run dev
```

生产模式：
```bash
npm start
```

> `npm start` 会先构建前端（Vite build），再启动 Electron。

如果你的 Python 命令不是 `python`，可先设置环境变量：

PowerShell:
```powershell
$env:CGP_PYTHON = "py"
npm run dev
```

CMD:
```cmd
set CGP_PYTHON=py
npm run dev
```

## Docker 一键部署（可能会有bug，容易镜像下载不下来）

### 前置条件
- 安装 Docker Desktop（Windows/macOS）或 Docker Engine（Linux）

### 部署
```bash
docker compose up -d --build
```

启动后访问：
- `http://localhost:8080`

停止服务：
```bash
docker compose down
```

Windows 用户可直接双击：
- `start-docker.bat`（启动）
- `stop-docker.bat`（停止）

## 目录结构

```text
.
├─ backend/
│  └─ server.py              # Python 本地服务（行情/状态/休市日 API）
├─ src/
│  ├─ App.vue                # 主界面
│  └─ main.js                # Vue 入口
├─ index.html                # Vite 页面入口
├─ main.js                   # Electron 主进程
├─ preload.js                # Electron preload
├─ vite.config.js
├─ Dockerfile.frontend       # Docker 前端镜像
├─ Dockerfile.backend        # Docker 后端镜像
├─ docker-compose.yml        # Docker 一键部署
├─ nginx.conf                # 前端容器反向代理配置
├─ start-docker.bat          # Windows Docker 一键启动
├─ stop-docker.bat           # Windows Docker 一键停止
├─ package.json
└─ start-cgp.bat             # Windows 快速启动脚本（可选）
```

## 数据文件说明（本地）

运行时会在项目目录生成以下文件（已加入 `.gitignore`）：
- `cgp-data.json`
- `cgp-data.backup.json`
- `market-calendar.db`

Docker 部署默认持久化目录：
- `data/`

## 开源建议

- 提交源码，不提交本地数据文件
- PR 前可先执行：
```bash
npm run build:web
python -m py_compile backend/server.py
```

## 免责声明

本项目为vibe coding产物。
本工具仅用于学习与策略记录，不构成任何投资建议。
