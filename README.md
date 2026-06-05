# 景区在线 Scenic Online

极客旅游。

Scenic Online 是一个面向国内旅行场景的前后端分离项目，覆盖景区搜索、目的地浏览、路线与天气、游客社区、地球 Online 公开来源、用户中心，以及后台运营管理、数据导入、内容审核和页面编排。

项目适合用于旅游产品原型、景区数据管理、前后端联调样板和本地数据治理实验。后端启动时会自动建表、迁移并写入开发种子数据；景区详情会优先读取数据库中已审核资料，并在缺少真实来源时按需从公开来源补全摘要、图片 URL、来源、授权和坐标。

## 项目概览

景区在线是一个完整的旅游信息平台，覆盖前台浏览和后台管理两大场景：

- 前台用户：搜索景区、查看图片/天气/路线、浏览目的地和主题、社区发帖、收藏景区、创建行程。
- 后台管理员：景区数据管理、图片/评论审核、API 接入配置、页面可视化编排、数据导入、资料补全、服务监控。

项目当前使用 React + FastAPI 的轻量架构，开发默认使用 PostgreSQL，SQLite 作为显式可选的轻量本地模式。第三方地图、天气、搜索等能力均为可选配置；没有 Key 时后端会使用公开来源和规则化降级，保证核心页面可用。

## 功能概览

- 前台：推荐首页、全文搜索、目的地/省份浏览、主题旅行、景区详情、路线规划、天气实况、社区内容、地球 Online、榜单、攻略详情、用户中心。
- 后台：运营总览、景区库管理、图片/评论审核、用户和权限、数据导入、API 接入、服务状态、地球 Online 来源管理、资料补全、页面布局编排。
- 数据：开发默认 PostgreSQL，支持显式切换 SQLite；支持 `tpt_data_jingdian.sql` 全国景区数据清洗、4A/5A 网络核验、预览、幂等导入、按需公开来源补全和错误记录。
- 外部服务：高德/Mapbox 地图、和风/高德天气、Bing 搜索/图片搜索、Wikipedia/Wikimedia Commons 等均通过后端封装，前端不暴露密钥。
- 验证：包含后端单元测试、前端构建、页面巡检、响应式截图、按钮检查和 API smoke 脚本。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 18, Vite, React Router, lucide-react, Recharts |
| 后端 | FastAPI, Pydantic, Uvicorn/Gunicorn |
| 数据库 | PostgreSQL 开发默认, SQLite 显式可选 |
| 测试与巡检 | unittest, Playwright, Node.js smoke scripts |
| 部署 | Docker, Docker Compose, Nginx |
| 外部服务 | 高德, Mapbox, 和风天气, Bing Search，可选接入 |

前端默认通过相对路径请求 `/api`，由 Vite dev server 或 Nginx 代理到后端。如需直连远端 API，可设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```
