# 景区在线 Scenic Online

极客旅游。

Scenic Online 是一个面向国内旅行场景的前后端分离项目，覆盖景区搜索、目的地浏览、路线与天气、游客社区、地球 Online 公开来源、用户中心，以及后台运营管理、数据导入、内容审核和页面编排。

项目适合用于旅游产品原型、景区数据管理、前后端联调样板和本地数据治理实验。后端启动时会自动建表、迁移并写入开发种子数据；景区详情会优先读取数据库中已审核资料，并在缺少真实来源时按需从公开来源补全摘要、图片 URL、来源、授权和坐标。

## 目录

- [项目概览](#项目概览)
- [功能概览](#功能概览)
- [技术栈](#技术栈)
- [系统架构图](#系统架构图)
- [业务流程图](#业务流程图)
- [页面路由图](#页面路由图)
- [数据模型关系图](#数据模型关系图)
- [前端组件逻辑图](#前端组件逻辑图)
- [后端模块逻辑图](#后端模块逻辑图)
- [目录结构](#目录结构)
- [快速启动](#快速启动)
- [Docker 启动](#docker-启动)
- [演示账号](#演示账号)
- [常用页面](#常用页面)
- [主要 API](#主要-api)
- [配置项](#配置项)
- [数据与导入](#数据与导入)
- [数据真实性与图片策略](#数据真实性与图片策略)
- [数据库表总览](#数据库表总览)
- [验证与测试](#验证与测试)
- [开发约定](#开发约定)
- [参考文档](#参考文档)
- [License](#license)

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

## 系统架构图

```mermaid
graph LR
    User["用户浏览器"] -->|"HTTP"| Web

    subgraph Frontend["前端层"]
        Web["Nginx / Vite Dev Server"]
        SPA["React SPA"]
        Web --> SPA
    end

    subgraph Backend["后端层 FastAPI :8000"]
        Router["路由层<br/>17 个 router 模块"]
        Service["业务层<br/>景区/搜索/天气/地图/导入/补全/后台"]
        Core["基础层<br/>config / database / auth / response / sanitize"]
        Router --> Service
        Service --> Core
    end

    subgraph Data["数据层"]
        Postgres[("PostgreSQL<br/>开发默认")]
        SQLite[("SQLite<br/>显式可选")]
        SQLFile["tpt_data_jingdian.sql<br/>全国景区来源"]
    end

    subgraph Provider["外部服务，可选"]
        Map["高德 / Mapbox"]
        Weather["和风天气 / 高德天气"]
        Search["Bing Search / Bing Image Search"]
    end

    SPA -->|"/api/*"| Router
    Service --> SQLite
    Service --> Postgres
    Service --> SQLFile
    Service -.->|"有 Key 调用；无 Key fallback"| Provider
```

## 业务流程图

### 用户前台核心流程

```mermaid
flowchart TD
    Start([访问网站]) --> Home["首页<br/>搜索 + 推荐 + 天气入口"]
    Home --> Search{"搜索景区或目的地"}
    Search -->|是| Result["搜索/目的地列表<br/>筛选、排序、分页"]
    Search -->|否| Browse{"浏览模块"}

    Browse --> Theme["主题旅行"]
    Browse --> Province["省份浏览"]
    Browse --> Earth["地球 Online"]
    Browse --> Community["游客社区"]
    Browse --> Ranking["榜单/攻略"]

    Result --> Detail["景区详情<br/>图集、信息、路线、附近推荐、评论"]
    Detail --> Action{"登录后操作"}
    Action --> Favorite["收藏景区"]
    Action --> Comment["提交评论/图片"]
    Action --> Trip["创建行程或路线"]

    Trip --> Planning["路线规划<br/>地图、天气、交通方式、途经点"]
    Planning --> Export["保存/导出路线"]

    Start --> Auth{"需要登录"}
    Auth --> Login["登录/注册"]
    Login --> User["用户中心<br/>收藏、行程、工作台"]
```

### 后台管理核心流程

```mermaid
flowchart TD
    AdminLogin([管理员登录]) --> Dashboard["管理总览<br/>KPI、服务状态、审核队列"]

    Dashboard --> Scenic["景区管理<br/>增删改查、资料补全"]
    Dashboard --> Review["内容审核<br/>图片、评论、文章、Banner"]
    Dashboard --> Data["数据管理<br/>SQL 导入、备份、质量检查"]
    Dashboard --> API["API 接入<br/>地图、天气、搜索、存储"]
    Dashboard --> Layout["页面编排<br/>组件模板、画布、发布、版本"]
    Dashboard --> System["系统管理<br/>用户、角色、安全、日志"]
    Dashboard --> Earth["地球 Online 来源管理"]

    Data --> Import["全国景区 SQL<br/>预览、分批导入、错误记录"]
    Scenic --> Enrich["资料补全<br/>官网、图片、介绍、坐标、附近推荐"]
    Review --> Publish["通过/驳回/隐藏/下架"]
    Layout --> Version["保存草稿、发布、恢复历史版本"]
```

## 页面路由图

```mermaid
graph LR
    subgraph Public["前台页面"]
        Home["/"]
        Search["/search"]
        Dest["/destinations"]
        Themes["/themes"]
        Provinces["/provinces"]
        Detail["/scenic/:id"]
        Planning["/trip-planning"]
        Community["/community"]
        Earth["/earth-online"]
        Sources["/sources"]
        Rankings["/rankings"]
        Guides["/guides/:id"]
        Auth["/auth"]
        User["/user"]
    end

    subgraph Legacy["兼容入口"]
        Map["/map"]
        Weather["/weather"]
    end

    subgraph Admin["后台页面"]
        AdminHome["/admin"]
        AdminScenic["/admin/scenic"]
        AdminContent["/admin/content"]
        AdminData["/admin/data"]
        AdminAPI["/admin/api"]
        AdminEarth["/admin/earth-online"]
        AdminLayout["/admin/workbench"]
        AdminSystem["/admin/system"]
    end

    Home --> Search
    Search --> Dest
    Dest --> Detail
    Detail --> Planning
    Detail --> Community
    Home --> Themes
    Home --> Provinces
    Home --> Earth
    Home --> Rankings
    Guides --> Detail
    Auth --> User
    Map --> Planning
    Weather --> Planning
    AdminHome --> AdminScenic
    AdminHome --> AdminContent
    AdminHome --> AdminData
    AdminHome --> AdminAPI
    AdminHome --> AdminEarth
    AdminHome --> AdminLayout
    AdminHome --> AdminSystem
```

## 数据模型关系图

```mermaid
erDiagram
    users ||--o{ comments : "发表"
    users ||--o{ favorites : "收藏"
    users ||--o{ trips : "创建"
    users ||--o{ uploads : "上传"
    users ||--o{ community_posts : "发布"
    users ||--o{ earth_online_favorites : "收藏来源"
    users ||--o{ user_layouts : "拥有布局"

    scenic_spots ||--o{ scenic_images : "包含图片"
    scenic_spots ||--o{ comments : "拥有评论"
    scenic_spots ||--o{ favorites : "被收藏"
    scenic_spots ||--o{ trip_routes : "纳入行程"
    scenic_spots ||--o{ scenic_candidates : "资料候选"
    scenic_spots ||--o{ scenic_image_candidates : "图片候选"
    scenic_spots ||--o{ nearby_recommendations : "附近推荐"

    trips ||--o{ trip_routes : "包含路线"
    earth_online_sources ||--o{ earth_online_checks : "检测记录"
    earth_online_sources ||--o{ earth_online_favorites : "被收藏"
    page_layouts ||--o{ page_layout_versions : "历史版本"
    user_layouts ||--o{ user_layout_versions : "历史版本"
    api_configs ||--o{ api_logs : "调用日志"

    users {
        int id PK
        string email
        string password_hash
        string nickname
        string role
        string status
    }

    scenic_spots {
        int id PK
        string name
        string province
        string city
        string district
        string address
        string level
        string description
        float latitude
        float longitude
        string official_website
        string tags
        float quality_score
    }

    scenic_images {
        int id PK
        int scenic_id FK
        string url
        string source
        string status
        boolean is_cover
    }

    page_layouts {
        int id PK
        string page_key
        text layout_json
        string status
    }

    api_configs {
        int id PK
        string provider
        string api_key_masked
        boolean enabled
    }
```

## 前端组件逻辑图

```mermaid
graph TB
    subgraph Entry["入口"]
        Main["main.jsx"] --> App["App.jsx"]
        App --> Router["router.jsx<br/>createBrowserRouter"]
    end

    subgraph Pages["页面层"]
        PublicPages["前台页面<br/>首页、搜索、目的地、详情、路线、社区、地球 Online、用户中心"]
        AdminPages["后台页面<br/>运营、内容、数据、API、系统、编排、自动化、集成"]
    end

    subgraph Shared["共享层"]
        Common["common 组件<br/>Navbar、ScenicCard、HeroSection、MapPanel、WeatherCard、Toast、DataTable"]
        AdminComponents["admin 组件<br/>Sidebar、Topbar、KPI、Table、Workbench"]
        Hooks["hooks<br/>useAuth、useToast、useAutoLocation"]
        Styles["styles<br/>global、tokens、layout、pages、search、sources"]
    end

    subgraph Data["数据层"]
        Client["api/client.js<br/>统一请求 + Bearer Token + fallback"]
        Modules["业务 API<br/>scenic、search、weather、map、user、admin、earth、layouts、location"]
        Fallback["fallback.js<br/>离线演示数据"]
    end

    Router --> Pages
    Pages --> PublicPages
    Pages --> AdminPages
    PublicPages --> Common
    AdminPages --> AdminComponents
    Common --> Hooks
    AdminComponents --> Hooks
    Common --> Styles
    Client --> Modules
    Modules --> Fallback
    Pages --> Client
```

## 后端模块逻辑图

```mermaid
graph TB
    Main["main.py<br/>FastAPI + CORS + 全局异常处理 + startup 初始化"]

    subgraph Routers["路由层，17 个 router 模块"]
        PublicR["公共/用户<br/>public、scenic、search、map_provider、weather、comments、earth_online、user、public_content"]
        AdminR["后台<br/>admin_dashboard、admin_scenic、admin_review、admin_content、admin_api、admin_earth_online、admin_enrichment、admin_system"]
    end

    subgraph Services["服务层"]
        Scenic["景区与搜索<br/>scenic_service、search_service、tpt_jingdian_importer"]
        Provider["外部适配<br/>amap_service、map_provider_service、weather_provider_service、weather_service"]
        Admin["后台与审计<br/>admin_service、audit_service、provider_config_service"]
        Enrich["资料补全<br/>scenic_enrichment、external_enrichment、profile_search、batch_enrichment、content_merge"]
        Quality["质量与推荐<br/>image_quality、scenic_quality_score、nearby_recommendation"]
        Seed["seed.py、theme_catalog.py"]
    end

    subgraph Core["基础层"]
        Config["config.py"]
        DB["database.py / database_adapters.py"]
        Auth["auth.py"]
        Response["response.py"]
        Sanitize["sanitize.py"]
        Region["region_utils.py"]
    end

    subgraph SchemaModel["模型与 Schema"]
        Models["models<br/>scenic、user、comment、trip、admin"]
        Schemas["schemas<br/>scenic、user、comment、common、admin"]
    end

    Main --> Routers
    Routers --> PublicR
    Routers --> AdminR
    PublicR --> Services
    AdminR --> Services
    Services --> Core
    Services --> SchemaModel
```

## 目录结构

```text
.
├── backend/                  # FastAPI 应用、模型、路由、服务、测试和数据文件
│   ├── app/
│   │   ├── core/             # 配置、数据库、认证、响应封装
│   │   ├── models/           # 数据模型
│   │   ├── routers/          # /api 下的公共、用户、后台接口
│   │   ├── schemas/          # Pydantic Schema
│   │   ├── services/         # 景区、搜索、天气、地图、导入、补全等业务逻辑
│   │   └── data/             # SQLite、SQL 数据、备份
│   └── tests/                # 后端 unittest 测试
├── frontend/                 # Vite React 前端
│   ├── src/
│   │   ├── api/              # 前端 API client 与业务接口封装
│   │   ├── components/       # 通用组件、后台组件、页面编排组件
│   │   ├── hooks/            # 认证、Toast、定位等 hooks
│   │   ├── pages/            # 前台页面和后台页面
│   │   ├── styles/           # 全局样式与设计令牌
│   │   ├── utils/            # 页面工具函数
│   │   └── router.jsx        # React Router 路由表
│   └── tests/                # 前端页面和工具测试
├── scripts/                  # 数据清洗、迁移、巡检、API smoke 脚本
├── docs/                     # API、工程流、UI 模板和数据清洗报告
├── docker-compose.yml        # Postgres + FastAPI + Nginx 前端
├── README.md                 # 合并后的项目文档
└── tpt_data_jingdian.sql     # 全国景区 SQL 数据源
```

## 快速启动

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端默认连接本机 PostgreSQL：

```text
postgresql://scenic:scenic@localhost:5432/scenic_online
```

如需临时使用 SQLite，可设置：

```bash
SCENIC_DATABASE_BACKEND=sqlite uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动时会执行：

- `init_db()`：创建和迁移表结构。
- `seed_data()`：写入演示景区、用户、主题、地球 Online 来源、组件模板等数据。
- `ensure_tpt_jingdian_loaded()`：如检测到 SQL 数据，会加载全国景区来源表。

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：http://localhost:5173
- 后端健康检查：http://127.0.0.1:8000/api/health
- 后端 OpenAPI：http://127.0.0.1:8000/docs

`frontend/vite.config.js` 已将 `/api` 代理到 `http://127.0.0.1:8000`，本地开发通常不需要额外配置 `VITE_API_BASE_URL`。

## Docker 启动

```bash
docker compose up --build
```

Docker Compose 会启动：

- `scenic-online-postgres`：PostgreSQL 16，端口 `5432`
- `scenic-online-backend`：FastAPI/Gunicorn，端口 `8000`
- `scenic-online-frontend`：Nginx 静态服务，端口 `80`，并把 `/api/` 反向代理到后端容器

访问：

- 前端：http://localhost
- 后端：http://127.0.0.1:8000/api/health

Compose 默认挂载根目录的 `tpt_data_jingdian.sql` 到后端容器，并设置：

```text
DATABASE_URL=postgresql://scenic:scenic@postgres:5432/scenic_online
TPT_JINGDIAN_SQL_PATH=/app/backend/tpt_data_jingdian.sql
```

## 演示账号

| 角色 | 邮箱 | 密码 |
| --- | --- | --- |
| 普通用户 | `user@scenic.local` | `User123456` |
| 管理员 | `admin@scenic.local` | `Admin123456` |
| 超级管理员 | `superadmin@scenic.local` | `SuperAdmin123456` |
| 普通用户 | `traveler@example.com` | `Traveler123` |
| 管理员 | `admin@example.com` | `Admin123456` |

登录态保存在浏览器 `localStorage` 中，后端接口已保留角色字段和 Bearer Token 接收逻辑，适合继续接入更完整的 JWT/Session 权限体系。

## 常用页面

### 前台

| 路由 | 说明 |
| --- | --- |
| `/` | 推荐首页、搜索、定位天气、精选景区、主题、省份、社区入口 |
| `/search` | 搜索页、热搜、建议词、搜索历史 |
| `/destinations` | 目的地浏览 |
| `/themes`、`/themes/:slug` | 主题旅行 |
| `/provinces`、`/provinces/:province` | 省份/区域浏览 |
| `/scenic/:id` | 景区详情、图片、基础信息、附近推荐、评论 |
| `/trip-planning` | 路线规划、地图、天气相关功能 |
| `/map`、`/weather` | 兼容旧入口，重定向到 `/trip-planning` 对应 tab |
| `/community` | 游客社区 |
| `/earth-online` | 已审核的公开地球/直播/地图来源 |
| `/sources` | 来源浏览 |
| `/rankings` | 榜单 |
| `/guides/:id` | 攻略详情 |
| `/user` | 用户中心，需登录 |
| `/auth` | 登录注册 |

### 后台

后台入口为 `/admin`，需要管理员或超级管理员账号。

| 路由 | 说明 |
| --- | --- |
| `/admin` | 运营总览、KPI、服务状态、日志 |
| `/admin/scenic`、`/admin/database` | 正式景区库、数据库表工作台 |
| `/admin/images`、`/admin/comments`、`/admin/content` | 图片、评论、内容管理 |
| `/admin/users`、`/admin/roles`、`/admin/security` | 用户、角色、安全 |
| `/admin/data` | 数据总览、同步、备份 |
| `/admin/data/source`、`/admin/data/quality` | 全国源表、数据质量检查 |
| `/admin/api` | 外部 API Key 配置、连通性测试、日志 |
| `/admin/services`、`/admin/system` | 服务和系统设置 |
| `/admin/earth-online` | 地球 Online 来源审核、检测、导入导出 |
| `/admin/enrichment` | 景区资料补全、候选审核 |
| `/admin/workbench`、`/admin/layout` | 页面布局编排、版本、组件模板 |
| `/admin/automation`、`/admin/integration` | 自动化与集成页 |

## 主要 API

所有接口默认挂在 `/api` 下，响应结构统一为：

```json
{
  "success": true,
  "data": {},
  "message": "",
  "timestamp": ""
}
```

### 公共接口

- `GET /api/health`
- `GET /api/scenic`
- `GET /api/scenic/search`
- `GET /api/scenic/{id}`
- `GET /api/scenic/{id}/profile`
- `GET /api/scenic/{id}/nearby`
- `GET /api/scenic/regions`
- `GET /api/scenic/themes`
- `GET /api/search`
- `GET /api/search/suggestions`
- `GET /api/search/hot`
- `GET /api/provinces`
- `GET /api/regions/provinces`
- `GET /api/regions/cities`
- `GET /api/regions/districts`
- `GET /api/weather`
- `GET /api/weather/forecast`
- `GET /api/weather/live`
- `GET /api/weather/route`
- `GET /api/map/config`
- `GET /api/map/geocode`
- `GET /api/map/reverse-geocode`
- `GET /api/location/ip`
- `GET /api/location/reverse`
- `GET /api/map/route`
- `GET /api/map/static-preview`
- `GET /api/map/poi`
- `GET /api/routes/plan`
- `GET /api/community/posts`
- `POST /api/community/posts`
- `POST /api/uploads`
- `GET /api/earth-online/sources`
- `GET /api/earth-online/categories`
- `GET /api/earth-online/featured`
- `GET /api/layouts/{page_key}`
- `GET /api/banners`
- `GET /api/articles`

### 认证与用户接口

- `POST /api/auth/send-code`
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `GET /api/user/profile`
- `GET /api/user/favorites`
- `POST /api/user/favorites`
- `DELETE /api/user/favorites/{favorite_id}`
- `GET /api/user/trips`
- `POST /api/user/trips`
- `GET /api/user/routes`
- `POST /api/user/routes`
- `GET /api/user/export/trip/{trip_id}`
- `GET /api/user/export/route/{route_id}`
- `GET /api/user/workbench-layout`
- `PUT /api/user/workbench-layout`
- `POST /api/user/workbench-layout/reset`
- `POST /api/user/workbench-layout/publish`
- `GET /api/user/workbench-layout/versions`
- `POST /api/user/workbench-layout/versions/{version_id}/restore`
- `GET /api/user/search-history`
- `DELETE /api/user/search-history`

### 后台接口分组

- `/api/admin/dashboard`
- `/api/admin/scenic`
- `/api/admin/images/*`
- `/api/admin/comments/*`
- `/api/admin/users/*`
- `/api/admin/roles`
- `/api/admin/security/*`
- `/api/admin/system/settings`
- `/api/admin/database/*`
- `/api/admin/data/*`
- `/api/admin/api/*`
- `/api/admin/services/*`
- `/api/admin/earth-online/*`
- `/api/admin/enrichment/*`
- `/api/admin/layouts/*`
- `/api/admin/component-templates`

完整接口以 `backend/app/routers/` 中的路由定义和 FastAPI `/docs` 为准。

## 配置项

后端配置集中在 `backend/app/core/config.py`。

| 环境变量 | 说明 |
| --- | --- |
| `DEBUG` | `true/1/t` 时开启调试模式 |
| `DATABASE_URL` | 未设置时默认 `postgresql://scenic:scenic@localhost:5432/scenic_online`；以 `postgresql://` 或 `postgres://` 开头时使用 PostgreSQL |
| `SCENIC_DATABASE_BACKEND` | 设置为 `sqlite` 时显式启用 SQLite 本地模式 |
| `CORS_ORIGINS` | 逗号分隔的允许来源；未设置时允许本地开发常用端口 |
| `AMAP_WEB_SERVICE_KEY` | 高德 Web 服务 Key，用于地理编码、路线、POI |
| `AMAP_JS_API_KEY` | 高德 JS API Key，预留给前端地图 SDK 场景 |
| `AMAP_JS_SECURITY_CODE` | 高德 JS 安全密钥 |
| `MAPBOX_TOKEN` | Mapbox Token |
| `QWEATHER_KEY` | 和风天气 Key |
| `AMAP_WEATHER_KEY` | 高德天气 Key |

前端默认通过相对路径请求 `/api`，由 Vite dev server 或 Nginx 代理到后端。如需直连远端 API，可设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

## 数据与导入

### PostgreSQL 开发库

默认开发数据库：

```text
postgresql://scenic:scenic@localhost:5432/scenic_online
```

### SQLite 可选模式

显式启用 SQLite 后使用的数据库文件：

```text
backend/app/data/scenic_online.sqlite3
```

数据库初始化和迁移逻辑在：

```text
backend/app/core/database.py
```

种子数据在：

```text
backend/app/services/seed.py
```

### 全国景区 SQL

项目根目录包含 `tpt_data_jingdian.sql`，清洗、按网站主题增强，并用“官方查询入口优先 + 公开网页辅助”的策略补齐 4A/5A 信息后，共 268,594 条记录。其中网络核验等级字段包含 5A 359 条、4A 3,624 条；记录会保留等级来源、来源 URL、核验日期、网页地址和网页坐标。清洗摘要见：

```text
docs/tpt_data_jingdian_clean_summary.md
```

相关脚本：

```bash
python3 scripts/clean_tpt_jingdian_sql.py --dry-run
python3 scripts/clean_tpt_jingdian_sql.py --sync-db
python3 scripts/enhance_tpt_jingdian_sql.py --dry-run
python3 scripts/update_tpt_scenic_from_web.py --dry-run --include-4a --append-missing
python3 scripts/update_tpt_scenic_from_web.py --include-4a --append-missing
python3 scripts/enrich_core_scenic_info.py
```

前台浏览策略：

- `/api/scenic` 的总数和列表由 `scenic_spots` 正式景区库 + `tpt_jingdian` 全国源表组成。
- `scenic_spots` 只保存审核后的轻量景区档案。
- `tpt_jingdian` 保存 268,594 条全国源表数据，支撑省/市/区三级浏览、搜索和源表详情。
- 源表详情使用 `/scenic/jingdian-{source_id}`，例如 `/scenic/jingdian-1`。

后台导入接口：

- `GET /api/admin/data/scenic-sql/status`
- `GET /api/admin/data/scenic-sql/preview`
- `POST /api/admin/data/scenic-sql/import`
- `GET /api/admin/scenic-source/jingdian/status`
- `POST /api/admin/scenic-source/jingdian/import`

`tpt_jingdian` 源表导入服务位于 `backend/app/services/tpt_jingdian_importer.py`。正式景区库导入服务位于 `backend/app/services/scenic_sql_import_service.py`，按 `name + province + city` 幂等去重，并记录导入任务与错误行。

### PostgreSQL 迁移

开发和 Docker Compose 均默认使用 PostgreSQL。手动迁移旧 SQLite 数据到 PostgreSQL 可参考：

```bash
python3 scripts/migrate_sqlite_to_postgres.py
```

## 数据真实性与图片策略

### 来源优先级

景区详情页使用分层数据策略：

1. 本地数据库中已审核资料和图片索引。
2. 按需公开来源补全：Wikipedia 摘要、坐标和页面主图，Wikimedia Commons 图片及授权信息。
3. 已配置 Key 时，可扩展高德 POI、Bing Search、Bing Image Search 候选。
4. 仍失败时返回本地基础资料和统一占位图，不让页面白屏。

### 图片存储

服务器不保存大图，只保存轻量索引：

- `scenic_images.url`
- `thumbnail_url`
- `source_url`
- `license`
- `attribution`
- `provider`
- `quality_score`
- `last_checked_at`

有真实公开图片时，详情接口会过滤旧的开发种子/Unsplash 景区图，避免把装饰图当成真实景区图。首页、主题页等视觉背景仍可使用装饰图；景区详情、图库和后台审核必须展示来源可追溯的图片 URL。

### 按需补全

用户打开 `/api/scenic/{id}/profile` 时，如果景区缺少 `source_url`、缺少已审核外链图片，或封面仍是开发种子图，后端会尝试公开来源补全：

```text
景区详情请求
→ 读取 scenic_spots / scenic_images
→ 缺真实来源时调用 Wikipedia / Wikimedia Commons
→ 写入 scenic_profile_candidates / scenic_image_candidates
→ 将公开图片作为 approved 轻量索引缓存
→ 返回带 source_url、media_assets、image_policy 的详情数据
```

### 全国源表图片任务

后台数据页提供“全国源表图片任务”，用于按队列补全 `tpt_jingdian` 的真实图片外链：

```bash
curl -fsS -X POST 'http://127.0.0.1:8000/api/admin/enrichment/tpt/media-job/start?batch_size=20&max_total=268594&a_level_only=false&only_missing=true&include_public_sources=true&use_amap=false&include_osm=false&sleep_seconds=0.2'
curl -fsS http://127.0.0.1:8000/api/admin/enrichment/tpt/media-job/status
curl -fsS -X POST http://127.0.0.1:8000/api/admin/enrichment/tpt/media-job/stop
```

任务默认优先处理 5A/4A、旧 `rate_limited`、`error`、`source_unavailable` 和缺图数据。公开来源返回 429 时会进入短暂冷却，并把行状态记为 `rate_limited`，不再误写成 `not_found`；当 Wikipedia / Wikivoyage / Commons 全部处于冷却期时，worker 会暂停等待，不继续消耗全国源表行。本地仍只保存 `cover_image_url`、`gallery`、`image_source`、`image_license`、`image_attribution` 等轻量字段，不下载图片文件。

### 数据质量检查

常用检查命令：

```bash
curl -fsS http://127.0.0.1:8000/api/admin/enrichment/overview
curl -fsS http://127.0.0.1:8000/api/admin/enrichment/profile/completion-stats
curl -fsS http://127.0.0.1:8000/api/scenic/1/profile
```

生产或准生产数据要求：

- 景区详情的 `source_url` 应指向官方或公开资料页。
- `media_assets` 中每张图片都应有 `source` 或 `source_url`。
- 4A/5A 等级以文化和旅游主管部门公告、政务服务查询或省级文旅厅名录为准。
- 外部候选进入后台审核池，人工确认后再大规模合并正式字段。

## 数据库表总览

当前数据库包含 50 张非系统表，其中包括业务表、导入表和 FTS 辅助表。核心表按功能分组如下。

### 用户与权限

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `users` | 用户表 | 存储邮箱、密码哈希、昵称、角色、状态等 |
| `auth_codes` | 验证码 | 登录/注册验证码记录 |
| `roles` | 角色表 | 注册用户、管理员、超级管理员等角色 |
| `permissions` | 权限表 | 细粒度权限点定义 |

### 景区核心

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `scenic_spots` | 景区主表 | 景区名称、省市区、等级、简介、经纬度、封面、官网、标签、质量分 |
| `scenic_images` | 景区图片 | 图片 URL、来源、审核状态、是否封面 |
| `scenic_themes` | 主题旅行 | 主题分类、关键词、推荐路线和排序 |
| `scenic_candidates` | 景区候选 | 资料补全发现的待确认景区信息 |
| `scenic_image_candidates` | 图片候选 | 自动采集或补全得到的待审核图片 |
| `scenic_profile_candidates` | 档案候选 | 官网、介绍、开放时间等档案补全候选 |
| `nearby_recommendations` | 附近推荐 | 景区间地理推荐关系 |

### 社区互动

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `comments` | 评论表 | 用户对景区的评分评论和审核状态 |
| `community_posts` | 社区帖子 | 图文游记/攻略、分类、点赞、举报、审核 |
| `favorites` | 景区收藏 | 用户和景区的收藏关系 |
| `earth_online_favorites` | 地球 Online 收藏 | 用户收藏的公开来源 |
| `uploads` | 上传记录 | 图片路径、大小、MIME 类型和关联对象 |

### 搜索与景区来源

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `search_history` | 搜索历史 | 登录用户最近搜索记录 |
| `hot_searches` | 热门搜索 | 全站热门关键词和搜索次数 |
| `tpt_data_jingdian` | 原始景区数据 | 全国景区 SQL 导入来源表 |
| `tpt_jingdian` | 清洗景区数据 | 清洗后景区来源 |
| `tpt_jingdian_fts*` | FTS 辅助表 | SQLite 全文检索索引及其内部表 |

### 行程规划

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `trips` | 行程主表 | 用户创建的行程，包含标题、描述、起止日期 |
| `trip_routes` | 行程路线 | 每天访问的景区和顺序 |

### 地球 Online

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `earth_online_sources` | 来源表 | 公开来源名称、URL、分类、风险等级、状态 |
| `earth_online_checks` | 检测记录 | 来源可用性检测、状态码、响应时间 |

### 资料补全

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `enrichment_tasks` | 补全任务 | 缺官网、缺图、缺介绍、缺坐标等批次任务 |
| `enrichment_results` | 补全结果 | 发现的数据、匹配度、审核和采纳状态 |

### 内容与页面编排

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `banners` | Banner | 前台 Banner 内容 |
| `articles` | 文章 | 攻略、公告或内容文章 |
| `page_layouts` | 页面布局 | 页面组件、位置、属性的 JSON 配置 |
| `page_layout_versions` | 布局版本 | 页面布局历史版本 |
| `component_templates` | 组件模板 | 编排器可复用组件模板 |
| `user_layouts` | 用户布局 | 用户工作台布局配置 |
| `user_layout_versions` | 用户布局版本 | 用户工作台布局历史版本 |

### 系统运维

| 表名 | 含义 | 作用 |
| --- | --- | --- |
| `api_configs` | API 配置 | 第三方服务 Key 脱敏存储和启停状态 |
| `api_logs` | API 日志 | 第三方 API 调用记录 |
| `weather_cache` | 天气缓存 | 城市天气查询结果缓存 |
| `map_request_logs` | 地图日志 | 地理编码、路线、POI 请求日志 |
| `audit_logs` | 审计日志 | 后台关键操作记录 |
| `sync_tasks` | 同步任务 | 后台同步任务执行状态 |
| `ip_blacklist` | IP 黑名单 | 访问控制 |
| `scenic_import_tasks` | 导入任务 | 全国景区 SQL 导入批次 |
| `scenic_import_errors` | 导入错误 | 导入过程中的错误行与错误信息 |
| `system_settings` | 系统设置 | 后台配置项 |
| `regions` | 行政区划 | 全国省、市、区县三级行政区划 |

## 验证与测试

### 后端

```bash
cd backend
python3 -m compileall app
python3 -m unittest discover -s tests -p '*_unittest.py'
```

### 前端

```bash
cd frontend
npm install
npm run build
npm run check:pages
npm run check:responsive
npm run check:buttons
```

### API smoke

先启动后端，然后执行：

```bash
./scripts/api_smoke.sh
```

如需指定 API 地址：

```bash
SCENIC_ONLINE_API_BASE_URL=http://127.0.0.1:8000 ./scripts/api_smoke.sh
```

脚本会检查健康接口、景区、天气、社区、地球 Online、页面布局、用户工作台和后台状态等关键接口。

### PostgreSQL 兼容与真实资料回归

切换 PostgreSQL 默认开发后，以下接口必须作为固定回归项：

```bash
curl -fsS http://127.0.0.1:8000/api/regions/provinces
curl -fsS 'http://127.0.0.1:8000/api/regions/cities?province=云南省'
curl -fsS 'http://127.0.0.1:8000/api/regions/districts?province=云南省&city=丽江市'
curl -fsS 'http://127.0.0.1:8000/api/scenic?limit=12'
curl -fsS 'http://127.0.0.1:8000/api/scenic?province=云南省&city=丽江市&district=古城区&limit=8'
curl -fsS http://127.0.0.1:8000/api/scenic/jingdian-1/profile
curl -fsS http://127.0.0.1:8000/api/scenic/2/nearby
curl -fsS http://127.0.0.1:8000/api/scenic/2/profile
```

对应后端测试：

```bash
cd backend
SCENIC_DATABASE_BACKEND=sqlite python3 -m unittest \
  tests.test_postgres_sql_translation_unittest \
  tests.test_postgres_runtime_queries_unittest \
  tests.test_scenic_media_pipeline_unittest \
  tests.test_scenic_external_enrichment_unittest
```

### 全站页面检查

Docker 或本地服务启动后执行：

```bash
node scripts/check-pages.mjs
node scripts/check-buttons.mjs
node scripts/check-data-consistency.mjs
```

在受限沙盒里，Node/Playwright 访问 `127.0.0.1` 可能报 `connect EPERM`；这属于本地执行权限问题，不代表站点不可访问。可先用 `curl -I http://127.0.0.1/` 和 `./scripts/api_smoke.sh` 判断服务状态，再在允许 Node 访问本机端口的环境中重跑页面检查。

页面检查需要能访问前端站点和后端 API。默认检查 `http://127.0.0.1`，如使用其它地址，可通过脚本环境变量覆盖。

## 开发约定

- 前端请求统一走 `frontend/src/api/client.js`，接口不可用时页面应优雅降级，不应白屏。
- 后端新增接口保持统一响应结构，路由文件放在 `backend/app/routers/`，业务逻辑优先放到 `backend/app/services/`。
- 外部 API Key 只放后端环境变量或后台 API 接入页，不要写入前端源码。
- 数据导入、资料补全、图片候选等高风险动作应先进后台审核，不直接覆盖正式展示内容。
- 页面布局编排数据保存在 `page_layouts`、`page_layout_versions`、`component_templates`、`user_layouts` 等表中。
- 大数据清洗脚本执行前建议先使用 `--dry-run`，并确认 `backend/app/data/backups/` 已生成备份。

## 参考文档

- `docs/api-contract.md`：统一响应格式与接口分组
- `docs/engineering-flow.md`：本地开发流程
- `docs/ui-template.md`：UI 模板说明
- `docs/tpt_data_jingdian_clean_summary.md`：全国景区 SQL 清洗摘要
- `docs/tpt_data_jingdian_clean_report.json`：清洗报告原始数据
- `docs/tpt_data_jingdian_web_update_report.json`：4A/5A 网络核验与合并报告

## License

本项目仅供学习和演示用途。
