# 主公的军师团 🏯

> 多 AI 角色协作的决策辅助工具，让一个人也能获得多维度的思考碰撞。

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

---

## 📖 项目简介

**主公的军师团** 是一款创新的 AI 决策辅助工具。用户扮演"主公"，向 4 位不同思维模式的 AI 军师提出问题，军师们轮流发言、观点交锋、逐步深入，最终帮助主公理清思路、达成决策。

**核心价值**：打破"人机一对一"的局限，用多角色头脑风暴的方式，让一个人也能获得多维度的思考碰撞。

**开发背景**：本项目使用 DeepSeek 和智谱 GLM 等 AI 模型协助开发，所有代码均有完整开发记录。

---

## 👥 军师阵容

| 军师 | 职能标签 | 思维特点 | 默认模型 |
|------|----------|----------|----------|
| **诸葛亮** | 战略家 | 全局观、谋定后动、善于长远规划 | 智谱 GLM-4-Flash / Kimi |
| **司马懿** | 风险管控 | 隐忍谨慎、计算风险、善于发现隐患 | 硅基 Qwen2.5-7B |
| **周瑜** | 行动派 | 果断、追求效率、相信执行胜于空谈 | Ollama（本地） |
| **荀彧** | 稳健规划 | 步步为营、注重细节、善于分配资源 | Ollama（本地） |

---

## 🚀 功能特性

### 核心功能
- ✅ **多角色讨论**：4 位军师依次发言，观点交锋
- ✅ **主公介入**：随时发表看法，引导讨论方向
- ✅ **智能收束**：检测观点重复或讨论充分时自动总结
- ✅ **议题管理**：同一会话支持多个议题，历史记录完整保存

### 技术特性
- ✅ **多模型支持**：智谱、硅基、Ollama、Kimi 等
- ✅ **模型热切换**：Web 界面实时切换，无需重启
- ✅ **实时通信**：WebSocket 推送，消息即时呈现
- ✅ **数据持久化**：所有对话记录保存在本地 JSON 文件

### 用户体验
- ✅ **会话管理**：新建、重命名、删除会话
- ✅ **内联编辑**：点击会话名称直接重命名
- ✅ **模型可视化**：军师发言旁显示当前使用的模型名
- ✅ **自定义模型配置**：为每位军师独立配置服务商和模型
- ✅ **一键运行**：Windows 打包版本，双击即可运行

---

## 🔧 支持的服务商

| 服务商 | 说明 | 默认模型 |
|--------|------|----------|
| **智谱** | 国内领先大模型 | `glm-4-flash`（免费） |
| **硅基流动** | 开源模型 API 平台 | `Qwen/Qwen2.5-7B-Instruct` |
| **本地 Ollama** | 本地运行开源模型 | `qwen2.5:3b` / `deepseek-r1:1.5b` |
| **Kimi** | 月之暗面 | `moonshot-v1-8k`（免费） |
| **DeepSeek** | 深度求索（预留） | — |
| **火山引擎** | 字节跳动（预留） | — |
| **千问** | 阿里云（预留） | — |

---

## 📦 安装与运行

### 方式一：Windows 打包版本（推荐非开发用户）

1. 下载 `MilitaryAdvisors.zip`
2. 解压到任意目录
3. 双击 `MilitaryAdvisors.exe`
4. 浏览器访问 `http://127.0.0.1:8000`

### 方式二：源码运行（开发环境）

**环境要求**：Python 3.10+

```bash
# 1. 克隆项目
git clone https://github.com/你的用户名/你的仓库名.git
cd MilitaryAdvisors

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Mac/Linux

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 配置 .env（可选）
cp backend/.env.example backend/.env
# 编辑 .env，填入你的 API Key

# 5. 启动服务
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 6. 浏览器访问
# http://127.0.0.1:8000
🔑 API Key 配置
在 Web 界面左下角点击 「更换 API」，为每个军师独立配置：

字段	说明
服务商名称	选择智谱/硅基/Ollama/Kimi 等
API 密钥	填入对应平台的 API Key
模型名称	填入具体的模型名称
免费模型推荐：

智谱：glm-4-flash

硅基：Qwen/Qwen2.5-7B-Instruct

Kimi：moonshot-v1-8k

本地：qwen2.5:3b / deepseek-r1:1.5b

🗂️ 项目结构
text
MilitaryAdvisors/
├── backend/              # 后端服务
│   ├── app/
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 核心服务（调度器、模型调用、记忆）
│   │   └── main.py       # FastAPI 入口
│   └── data/             # 数据存储（运行时生成）
├── frontend-web/         # 前端静态文件
│   ├── css/
│   ├── js/
│   └── index.html
└── requirements.txt      # Python 依赖
📜 免责声明
重要说明

AI 生成内容免责：本项目所有军师发言均由 AI 模型生成，仅供参考。用户应独立判断并承担使用后果，项目开发者不对 AI 生成的任何内容负责。

API 费用：使用云端模型（智谱、硅基、Kimi 等）可能产生费用，请自行关注账户余额。

本地部署安全：本项目所有数据存储在本地，不上传任何用户数据到第三方服务器。

无病毒保证：本项目源代码完全公开，欢迎审查。打包版本使用 PyInstaller 生成，无任何恶意代码。

使用风险：用户自行承担使用本软件的所有风险。开发者不对因使用本软件导致的任何直接或间接损失负责。

🤝 贡献与反馈
欢迎提交 Issue 和 Pull Request。

📄 许可证
MIT License

🙏 致谢
FastAPI — 高性能 Web 框架

智谱 AI — GLM 模型

硅基流动 — 开源模型 API

Ollama — 本地模型运行

DeepSeek — 开发辅助

Font Awesome — 图标库

让每一次决策都有军师相伴 ⚔️

text

---

## 总结

| 内容 | 是否放入 README |
|------|-----------------|
| API Key 配置 | ✅ 要 |
| 项目结构 | ✅ 要 |
| 免责声明 | ✅ 要 |
| 许可证 | ✅ 要 |
| 致谢 | ✅ 要 |
| “关于文件格式”对话记录 | ❌ 不要 |
| “推送时建议重命名”操作说明 | ❌ 不要 |
| 多余的 `text` 标签 | ❌ 不要 |
