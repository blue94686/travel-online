# tpt_data_jingdian.sql 清洗摘要

生成时间：2026-06-03

## 处理范围

- 根目录 SQL：`tpt_data_jingdian.sql`
- 后端镜像 SQL：`backend/app/data/tpt_data_jingdian.sql`
- SQLite：`backend/app/data/scenic_online.sqlite3`
- 前台接口来源：`scenic_spots`、`tpt_jingdian`、`tpt_jingdian_fts`

## 清洗结果

| 阶段 | 输入行数 | 保留行数 | 删除行数 | 主要原因 |
| --- | ---: | ---: | ---: | --- |
| 第一轮 | 324,498 | 281,224 | 43,274 | 门/入口/停车/售票/游客中心等附属点，同名同地址/近坐标重复 |
| 第二轮 | 281,224 | 280,283 | 941 | 主景区下馆、区、池、亭等子 POI |
| 第三轮 | 280,283 | 278,681 | 1,602 | 跨区县但同城市的主景区子 POI、动物园/植物园内部短后缀点 |
| 第四轮 | 278,681 | 267,286 | 11,395 | 社区/文体/健身/低价值城市广场、管理机构、住宅/餐饮/商业混入点 |
| 第五轮 | 267,286 | 267,199 | 87 | 核心景区前缀下讲解服务、购物点、投诉点、展览、执勤点、码头等子 POI |
| 第六轮 | 267,199 | 266,908 | 291 | 扩展表结构，按网站主题分类补全介绍；继续删除低价值企业/设施/短标题数据 |
| 第七轮 | 266,908 | 268,594 | 0 | 官方查询入口优先、公开网页辅助补齐 4A/5A 等级、网页地址、经纬度和来源字段；追加旧库缺失的 A 级主景区 |

清洗阶段累计删除：57,590 条；第七轮追加 A 级主景区后，较原始 324,498 条净减少 55,904 条。

## 规则说明

- 保留原始 `id`，便于从 `sql-{source_id}-...` 追溯来源。
- 删除明显不是独立景区的门、入口、出口、停车场、售票处、检票口、游客中心、服务中心、管理处、卫生间等记录。
- 同名同区同地址、同名同区近坐标重复记录只保留质量分最高的一条。
- 主景区存在时，压缩同城同名前缀且近距离/同地址的馆、区、池、亭、园内设施等子 POI。
- 删除社区广场、文体广场、健身广场、管理办公室、培训中心、住宅小区、餐饮/商业混入等不适合作为前台独立景区的记录。
- 城市广场类只保留天安门广场、五四广场、星海广场、泉城广场、朝天门广场等高识别度地标关键词。
- 保留 `风景区`、`景区`、`旅游区`、`度假区`、`森林公园`、`湿地公园`、`国家公园`、`地质公园` 等正式主景区后缀。
- 不按“同地址不同名”粗暴删除，避免误删独立寺庙、博物馆、纪念馆等。
- 第六轮新增 `province`、`city`、`district`、`main_category`、`theme_slugs`、`theme_names`、`tags`、`summary`、`description`、`best_season`、`audience`、`recommended_duration`、`route_idea`、`quality_score`、`data_version`、`updated_at` 等扩展字段。
- 第七轮新增 `official_level`、`level_source`、`level_source_url`、`level_verified_at`、`a_level_year`、`web_province`、`web_city`、`web_district`、`web_address`、`web_longitude`、`web_latitude`、`web_source_confidence`、`web_update_note` 等网络核验字段。
- 4A/5A 来源策略：以文旅部 5A 官方查询入口作为官方核验入口，公开网页/API 辅助补齐批量字段；同名同省等级冲突时 5A 优先，坐标兜底匹配必须同时满足名称相关，避免把等级贴到附近子点。
- 主题分类对齐网站 `theme_catalog.py`：徒步登山、人文古迹、摄影打卡、自然风光、美食之旅、自驾旅行、亲子乐园、避暑胜地、赏花踏青、冰雪世界。

## 当前数据量

| 数据源 | 当前行数 |
| --- | ---: |
| `tpt_data_jingdian.sql` | 268,594 |
| `backend/app/data/tpt_data_jingdian.sql` | 268,594 |
| `tpt_jingdian` | 需重新导入 SQL 后同步 |
| `tpt_jingdian_fts` | 需重新导入 SQL 后同步 |
| `scenic_spots` | 238,639 |
| `scenic_spots` 中 `sql-*` 来源 | 238,629 |

## A 级景区网络更新

- 网络去重记录：3,983 条。
- 5A：359 条。
- 4A：3,624 条。
- 合并方式：名称地区匹配 1,513 条，名称相关 + 5km 坐标兜底 784 条，追加缺失主景区 1,686 条。
- 未匹配：0 条。
- 报告文件：`docs/tpt_data_jingdian_web_update_report.json`。
- 主要公开辅助来源：`https://services.kcloudtech.cn/geo/scenicspots`。
- 官方查询入口：`https://zwfw.mct.gov.cn/wycx/5ajlyjq/`。

## 文件体积

- 清洗前约 68M。
- 清洗后约 53M。
- 主题增强后约 300M，增加了介绍、主题、标签、季节、人群、路线建议和质量分字段。
- 4A/5A 网络字段更新后约 276M。

## 核心景区资料补全

新增脚本：`scripts/enrich_core_scenic_info.py`

已用官网/公开来源补齐 10 个核心景区的官网、简介、开放/票务提示、交通、游玩时长、适合人群、必看点、拍照点和出行提示：

- 故宫博物院
- 杭州西湖
- 黄山风景区
- 九寨沟风景名胜区
- 张家界国家森林公园
- 桂林漓江风景区
- 千岛湖风景区
- 八达岭长城
- 颐和园
- 天坛公园

脚本会把文本补全写入 `scenic_spots` 正式字段，并把来源记录写入 `scenic_candidates`，方便后台追踪。外部图片仍不直接覆盖正式封面，应通过 `scenic_image_candidates` 审核后采纳。

## 关键验证

- SQL 行数校验：根目录和后端镜像均为 268,594 行。
- 新版 SQL 解析无错误，`official_level` 分布为 `5A=359`、`4A=3624`。
- 抽样导入 8,000 行后 `tpt_jingdian_fts` 索引 8,000 行。
- `/api/scenic?keyword=北京动物园` 只返回 `北京动物园` 主景区。
- `/api/scenic?keyword=北京植物园` 只返回 `北京植物园` 主景区。
- `故宫博物院` 已作为核心主景区补入数据库。

## 备份

脚本每次实际写入都会在 `backend/app/data/backups/` 下生成 SQL 和 SQLite 备份。最近几次备份文件名以：

- `tpt_data_jingdian-before-clean-20260602-...sql`
- `tpt_data_jingdian-before-enhance-20260603-...sql`
- `tpt_data_jingdian-before-web-update-20260603-...sql`
- `scenic_online-before-clean-20260602-...sqlite3`

为前缀，可用于回滚或抽样对比。

## 脚本

- 主脚本：`scripts/clean_tpt_jingdian_sql.py`
- 主题增强脚本：`scripts/enhance_tpt_jingdian_sql.py`
- A 级景区网络更新脚本：`scripts/update_tpt_scenic_from_web.py`
- 兼容入口：`scripts/optimize_sql.py`

常用命令：

```bash
python3 scripts/clean_tpt_jingdian_sql.py --dry-run
python3 scripts/clean_tpt_jingdian_sql.py --sync-db
python3 scripts/enhance_tpt_jingdian_sql.py --dry-run
python3 scripts/enhance_tpt_jingdian_sql.py
python3 scripts/update_tpt_scenic_from_web.py --dry-run --include-4a --append-missing
python3 scripts/update_tpt_scenic_from_web.py --include-4a --append-missing
python3 scripts/enrich_core_scenic_info.py
```
