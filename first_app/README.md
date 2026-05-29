# TNR 流浪动物管理系统

规范城市流浪动物管理，标准化落地 TNR（捕捉 - 绝育 - 放归）治理模式，实现全市流浪动物可溯源、可监管、可闭环治理。

## 系统四大角色端口

| 端口 | 目录 | 说明 |
|------|------|------|
| 🏠 收容所端 | 	nr-system-mockups/shelter/ | 收容登记、转运下发、物料采购、放归、领养审核 |
| 🏥 宠物医院端 | 	nr-system-mockups/hospital/ | 交接接收、诊疗操作、物料库存、领养维护 |
| 👤 领养人端 | 	nr-system-mockups/adopter/ | 领养大厅、宠物档案、月度打卡回访 |
| 📊 政府监管端 | 	nr-system-mockups/government/ | 数据大屏、机构管理、物料监管、全局台账 |

## 快速启动

### 方式一：Python 后端（推荐）

`ash
cd first_app
pip install -r requirements.txt
python server.py
# 访问 http://localhost:8889
`

### 方式二：直接打开

直接用浏览器打开 irst_app/index.html。

## 核心设计原则

- **无物业独立端口**：物业信息、交接、签字流程内嵌至收容所端
- **物料统一管控**：收容所统一采购下发，医院领用消耗，双端台账独立留存
- **全流程电子化留痕**：拍照、定位、签字、单据、库存、操作日志全程可追溯
- **多分支业务闭环**：主人领回、TNR 放归、领养、安乐死四大闭环分支
- **领养流程轻量化**：线下审核 + 线下协议存档

## 技术栈

- 前端：原生 HTML/CSS/JavaScript（零依赖）
- 后端：Python + FastAPI + SQLite
