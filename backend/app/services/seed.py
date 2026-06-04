import json

from app.core.auth import hash_password
from app.core.database import get_db
from app.core.config import AMAP_WEB_SERVICE_ENDPOINT, TPT_JINGDIAN_SQL_PATH
from app.core.region_utils import is_fallback_area_label
from app.services.amap_service import mask_amap_key
from app.services.theme_catalog import THEME_CATALOG
from app.services.tpt_jingdian_importer import ensure_tpt_jingdian_loaded


SCENIC_SEED = [
    {
        "slug": "hangzhou-west-lake",
        "name": "杭州西湖",
        "province": "浙江省",
        "city": "杭州市",
        "district": "西湖区",
        "level": "5A",
        "rating": 4.8,
        "address": "浙江省杭州市西湖区龙井路1号",
        "latitude": 30.2428,
        "longitude": 120.1417,
        "summary": "湖山相映、人文荟萃的世界文化遗产。",
        "description": "西湖以湖光山色、历史遗迹和城市公共空间闻名，适合半日漫步、骑行和深度人文游。",
        "tags": ["湖光山色", "世界文化遗产", "摄影", "城市漫步"],
        "ticket_price": "免费，部分景点另收费",
        "opening_hours": "全天开放",
        "best_season": "3-5月、9-11月",
        "cover_image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&w=900&q=80",
        ],
        "weather": {"city": "杭州", "temp": 24, "condition": "多云", "air": "优 32"},
        "map_point": {"lat": 30.2428, "lng": 120.1417},
        "nearby_pois": ["苏堤", "雷峰塔", "灵隐寺", "曲院风荷"],
        "recommended_routes": ["经典半日游", "深度一日游", "亲子休闲线"],
    },
    ("huangshan", "黄山风景区", "安徽省", "黄山市", "黄山区", "5A", 4.9, "奇松、怪石、云海与温泉构成的山岳经典。", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1400&q=80"),
    ("jiuzhaigou", "九寨沟风景名胜区", "四川省", "阿坝藏族羌族自治州", "九寨沟县", "5A", 4.9, "高山湖泊、瀑布群与彩林构成的自然保护地。", "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1400&q=80"),
    ("zhangjiajie", "张家界国家森林公园", "湖南省", "张家界市", "武陵源区", "5A", 4.7, "石英砂岩峰林地貌，适合观景与徒步。", "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1400&q=80"),
    ("guilin-lijiang", "桂林漓江风景区", "广西壮族自治区", "桂林市", "阳朔县", "5A", 4.7, "山水画卷般的喀斯特河谷风光。", "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1400&q=80"),
    ("qiandao-lake", "千岛湖风景区", "浙江省", "杭州市", "淳安县", "5A", 4.6, "湖岛密布、水质清澈的休闲度假目的地。", "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1400&q=80"),
    ("lingyin-temple", "灵隐寺", "浙江省", "杭州市", "西湖区", "4A", 4.6, "古刹、飞来峰造像与山林步道结合的人文景区。", "https://images.unsplash.com/photo-1528181304800-259b08848526?auto=format&fit=crop&w=1400&q=80"),
    ("leifeng-pagoda", "雷峰塔景区", "浙江省", "杭州市", "西湖区", "4A", 4.5, "俯瞰西湖南线的城市文化地标。", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1400&q=80"),
    ("quyuan-fenghe", "曲院风荷", "浙江省", "杭州市", "西湖区", "经典", 4.6, "夏季赏荷与湖畔散步的西湖名景。", "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1400&q=80"),
]

EARTH_ONLINE_SEED = [
    ("earthcam", "EarthCam", "global_featured", "全球", "", "EarthCam", "https://www.earthcam.com/", "全球旅游、城市、地标、海滩、景点直播摄像头网络。", 1, 0, "approved", "unknown", "low", "未确认嵌入授权，前台仅外链打开。", ""),
    ("skylinewebcams", "SkylineWebcams", "global_featured", "全球", "", "SkylineWebcams", "https://www.skylinewebcams.com/en.html", "全球城市、海滩、广场与旅游目的地公开实况平台。", 1, 0, "approved", "unknown", "low", "未确认嵌入授权，前台仅外链打开。", ""),
    ("webcamtaxi", "Webcamtaxi", "city_live", "全球", "", "Webcamtaxi", "https://www.webcamtaxi.com/en/", "城市、海岸、交通与旅游目的地公开实况目录。", 1, 0, "approved", "unknown", "low", "未确认嵌入授权，前台仅外链打开。", ""),
    ("explore-org", "Explore.org", "nature_live", "全球", "", "Explore.org", "https://explore.org/livecams/currently-live", "动物、海洋、森林与自然保护区公开直播。", 1, 0, "approved", "unknown", "low", "未确认嵌入授权，前台仅外链打开。", ""),
    ("windy-webcams", "Windy Webcams", "weather_earth", "全球", "", "Windy", "https://www.windy.com/webcams", "天气地图、公开摄像头与出行天气观察。", 1, 0, "approved", "unknown", "low", "外链打开，嵌入需另行确认。", ""),
    ("zoom-earth", "Zoom Earth", "weather_earth", "全球", "", "Zoom Earth", "https://zoom.earth/", "云图、雷达、风雨与全球天气地球观察。", 0, 0, "approved", "unknown", "low", "外链打开，嵌入需另行确认。", ""),
    ("google-earth-web", "Google Earth Web", "satellite_earth", "全球", "", "Google Earth", "https://earth.google.com/web", "卫星地球与三维地理浏览。", 0, 0, "approved", "unknown", "low", "外链打开，不直接嵌入。", ""),
    ("openstreetmap", "OpenStreetMap", "map_poi", "全球", "", "OpenStreetMap", "https://www.openstreetmap.org/", "开放地图与 POI 数据浏览。", 0, 0, "approved", "unknown", "low", "遵守开放地图授权和署名要求。", "注意 OSM 授权和署名要求。"),
    ("nasa-worldview", "NASA Worldview", "satellite_earth", "全球", "", "NASA", "https://worldview.earthdata.nasa.gov/", "NASA 全球卫星影像与地球观测浏览。", 0, 0, "approved", "unknown", "low", "公开科普与观测来源，前台外链打开。", ""),
    ("nasa-earthdata", "NASA Earthdata", "satellite_earth", "全球", "", "NASA", "https://www.earthdata.nasa.gov/", "NASA 地球科学数据入口。", 0, 0, "approved", "unknown", "low", "公开科普与观测来源，前台外链打开。", ""),
    ("nasa-eyes-earth", "NASA Eyes on the Earth", "space_earth", "全球", "", "NASA", "https://eyes.nasa.gov/apps/earth", "从任务和卫星视角理解地球观测。", 0, 0, "approved", "unknown", "low", "公开科普来源，前台外链打开。", ""),
    ("esa-earth-online", "ESA Earth Online", "satellite_earth", "欧洲", "", "ESA", "https://earth.esa.int/", "ESA 地球观测任务、数据和应用入口。", 0, 0, "approved", "unknown", "low", "公开科普与观测来源，前台外链打开。", ""),
    ("copernicus-browser", "Copernicus Browser", "satellite_earth", "欧洲", "", "Copernicus", "https://browser.dataspace.copernicus.eu/", "Copernicus 卫星影像浏览器。", 0, 0, "approved", "unknown", "low", "公开观测来源，前台外链打开。", ""),
    ("copernicus-data-space", "Copernicus Data Space", "satellite_earth", "欧洲", "", "Copernicus", "https://dataspace.copernicus.eu/", "Copernicus 数据空间入口。", 0, 0, "approved", "unknown", "low", "公开观测来源，前台外链打开。", ""),
    ("nasa-iss-hdev", "NASA ISS Earth Viewing / HDEV", "space_earth", "全球", "", "NASA", "https://eol.jsc.nasa.gov/esrs/hdev/", "国际空间站地球视角相关公开内容。", 1, 0, "approved", "unknown", "low", "公开科普来源，前台外链打开。", ""),
    ("nasa-hdev-stem", "NASA HDEV STEM Content", "space_earth", "全球", "", "NASA", "https://www.nasa.gov/stem-content/high-definition-earth-viewing-system/", "NASA 高分辨率地球观看系统科普内容。", 0, 0, "approved", "unknown", "low", "公开科普来源，前台外链打开。", ""),
    ("sen-earth-live", "Sen Earth Live", "space_earth", "全球", "", "Sen", "https://www.sen.com/live", "商业平台太空视角直播入口，需确认授权。", 1, 0, "candidate", "unknown", "medium", "商业平台，需确认嵌入和使用条款。", ""),
    ("sen", "Sen", "space_earth", "全球", "", "Sen", "https://www.sen.com/", "商业平台太空影像服务，需确认授权。", 0, 0, "candidate", "unknown", "medium", "商业平台，需确认嵌入和使用条款。", ""),
]

REGION_SEED = [
    ("华北", "北京市", "北京市", "东城区"),
    ("华北", "天津市", "天津市", "和平区"),
    ("华北", "河北省", "石家庄市", "长安区"),
    ("华北", "山西省", "太原市", "迎泽区"),
    ("华北", "内蒙古自治区", "呼和浩特市", "新城区"),
    ("东北", "辽宁省", "沈阳市", "沈河区"),
    ("东北", "吉林省", "长春市", "南关区"),
    ("东北", "黑龙江省", "哈尔滨市", "道里区"),
    ("华东", "上海市", "上海市", "黄浦区"),
    ("华东", "江苏省", "南京市", "玄武区"),
    ("华东", "浙江省", "杭州市", "西湖区"),
    ("华东", "浙江省", "杭州市", "淳安县"),
    ("华东", "安徽省", "黄山市", "黄山区"),
    ("华东", "福建省", "厦门市", "思明区"),
    ("华东", "江西省", "上饶市", "婺源县"),
    ("华东", "山东省", "济南市", "历下区"),
    ("华中", "河南省", "洛阳市", "洛龙区"),
    ("华中", "湖北省", "武汉市", "武昌区"),
    ("华中", "湖南省", "张家界市", "武陵源区"),
    ("华南", "广东省", "广州市", "越秀区"),
    ("华南", "广西壮族自治区", "桂林市", "阳朔县"),
    ("华南", "海南省", "三亚市", "吉阳区"),
    ("西南", "重庆市", "重庆市", "渝中区"),
    ("西南", "四川省", "成都市", "武侯区"),
    ("西南", "四川省", "阿坝藏族羌族自治州", "九寨沟县"),
    ("西南", "贵州省", "贵阳市", "南明区"),
    ("西南", "云南省", "丽江市", "古城区"),
    ("西南", "西藏自治区", "拉萨市", "城关区"),
    ("西北", "陕西省", "西安市", "雁塔区"),
    ("西北", "甘肃省", "兰州市", "城关区"),
    ("西北", "青海省", "西宁市", "城中区"),
    ("西北", "宁夏回族自治区", "银川市", "兴庆区"),
    ("西北", "新疆维吾尔自治区", "乌鲁木齐市", "天山区"),
    ("华南", "香港特别行政区", "香港", "中西区"),
    ("华南", "澳门特别行政区", "澳门", "花地玛堂区"),
    ("华东", "台湾省", "台北市", "中正区"),
]

HOT_SEARCH_SEED = [
    ("杭州西湖", "scenic", 328, 1),
    ("黄山", "scenic", 276, 1),
    ("九寨沟", "scenic", 215, 1),
    ("张家界", "scenic", 198, 1),
    ("桂林漓江", "scenic", 187, 1),
    ("丽江古城", "scenic", 165, 1),
    ("西安兵马俑", "scenic", 152, 1),
    ("北京故宫", "scenic", 148, 1),
    ("成都", "city", 134, 1),
    ("三亚", "city", 128, 1),
    ("厦门", "city", 119, 1),
    ("摄影打卡", "theme", 96, 1),
    ("避暑胜地", "theme", 88, 1),
    ("自驾游", "theme", 82, 1),
    ("亲子旅行", "theme", 75, 1),
]

COMPONENT_TEMPLATE_SEED = [
    ("全宽搜索 Hero", "hero", "基础文本组件", {"title": "今天去哪玩？", "subtitle": "极客旅行 · 精准规划 · 实时掌握", "width": "full", "dataSource": "scenic"}),
    ("景区卡片列表", "scenic_cards", "图文展示组件", {"title": "精选景区", "width": "half", "limit": 6, "dataSource": "scenic"}),
    ("主题旅行卡片", "theme_cards", "图文展示组件", {"title": "热门主题", "width": "half", "limit": 9, "dataSource": "scenic"}),
    ("路线规划面板", "map_tool", "地图天气组件", {"title": "路线规划", "width": "full", "dataSource": "scenic"}),
    ("城市天气面板", "weather_card", "地图天气组件", {"title": "天气实况", "width": "half", "dataSource": "weather"}),
    ("地球 Online 来源列表", "live_source", "内容列表组件", {"title": "公开来源", "width": "full", "dataSource": "earth_online"}),
    ("省份列表", "province_entry", "内容列表组件", {"title": "省份浏览", "width": "half", "dataSource": "scenic"}),
    ("评论列表", "comments", "内容列表组件", {"title": "游客社区精选", "width": "half", "dataSource": "community"}),
    ("KPI 卡片", "kpi_cards", "数据统计组件", {"title": "KPI 卡片", "width": "full", "dataSource": "admin"}),
    ("审核队列", "review_queue", "后台组件", {"title": "审核队列", "width": "half", "dataSource": "admin"}),
    ("服务状态", "service_status", "后台组件", {"title": "服务状态", "width": "half", "dataSource": "admin"}),
    ("API 状态", "api_status", "后台组件", {"title": "API 状态", "width": "half", "dataSource": "admin"}),
    ("数据质量", "data_quality", "后台组件", {"title": "数据质量", "width": "half", "dataSource": "admin"}),
    ("操作日志", "operation_logs", "后台组件", {"title": "操作日志", "width": "half", "dataSource": "admin"}),
]


def _ensure_seed_user(db, email, password, nickname, role, status="active"):
    if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        return
    db.execute(
        "INSERT INTO users (email,password_hash,nickname,role,status) VALUES (?,?,?,?,?)",
        (email, hash_password(password), nickname, role, status),
    )


def normalize_seed(item):
    if isinstance(item, dict):
        return item
    slug, name, province, city, district, level, rating, summary, image = item
    return {
        "slug": slug,
        "name": name,
        "province": province,
        "city": city,
        "district": district,
        "level": level,
        "rating": rating,
        "address": f"{province}{city}{district}",
        "latitude": 30.0 + rating,
        "longitude": 110.0 + rating,
        "summary": summary,
        "description": f"{name}是高热度目的地，适合摄影、徒步、家庭出行和周末度假。",
        "tags": ["精选推荐", "摄影", "自然风光"],
        "ticket_price": "以景区公示为准",
        "opening_hours": "08:00-17:30",
        "best_season": "春秋两季",
        "cover_image_url": image,
        "gallery": [image, image.replace("1400", "900"), image.replace("q=80", "q=75")],
        "weather": {"city": city.replace("市", ""), "temp": 22, "condition": "晴间多云", "air": "良 46"},
        "map_point": {"lat": 30.0 + rating, "lng": 110.0 + rating},
        "nearby_pois": ["观景台", "游客中心", "步道入口"],
        "recommended_routes": ["精华半日线", "经典一日线", "轻徒步路线"],
    }


def seed_data():
    with get_db() as db:
        ensure_tpt_jingdian_loaded(db, TPT_JINGDIAN_SQL_PATH)
        for theme in THEME_CATALOG:
            db.execute(
                """
                INSERT INTO scenic_themes (
                  slug,name,description,guide,image_url,icon,keywords_json,season,audience,route_idea,sort_order,is_active
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)
                ON CONFLICT(slug) DO UPDATE SET
                  name=excluded.name,
                  description=excluded.description,
                  guide=excluded.guide,
                  image_url=excluded.image_url,
                  icon=excluded.icon,
                  keywords_json=excluded.keywords_json,
                  season=excluded.season,
                  audience=excluded.audience,
                  route_idea=excluded.route_idea,
                  sort_order=excluded.sort_order,
                  is_active=1,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (
                    theme["slug"],
                    theme["name"],
                    theme["description"],
                    theme["guide"],
                    theme["image_url"],
                    theme["icon"],
                    json.dumps(theme["keywords"], ensure_ascii=False),
                    theme["season"],
                    theme["audience"],
                    theme["route_idea"],
                    theme["sort_order"],
                ),
            )
        count = db.execute("SELECT COUNT(*) AS c FROM scenic_spots").fetchone()["c"]
        if count == 0:
            for raw in SCENIC_SEED:
                item = normalize_seed(raw)
                db.execute(
                    """
                    INSERT INTO scenic_spots (
                      slug,name,province,city,district,level,rating,address,latitude,longitude,summary,description,
                      tags,ticket_price,opening_hours,best_season,cover_image_url,gallery,weather,map_point,nearby_pois,recommended_routes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item["slug"], item["name"], item["province"], item["city"], item["district"], item["level"], item["rating"],
                        item["address"], item["latitude"], item["longitude"], item["summary"], item["description"],
                        json.dumps(item["tags"], ensure_ascii=False), item["ticket_price"], item["opening_hours"], item["best_season"],
                        item["cover_image_url"], json.dumps(item["gallery"], ensure_ascii=False), json.dumps(item["weather"], ensure_ascii=False),
                        json.dumps(item["map_point"], ensure_ascii=False), json.dumps(item["nearby_pois"], ensure_ascii=False),
                        json.dumps(item["recommended_routes"], ensure_ascii=False),
                    ),
                )
            db.executemany(
                "INSERT INTO comments (scenic_id,user_id,nickname,content,rating,status,images,ip) VALUES (?,?,?,?,?,?,?,?)",
                [
                    (1, 1, "旅行的风", "西湖傍晚很美，建议从曲院风荷一路走到苏堤。", 5, "approved", "[]", "127.0.0.1"),
                    (2, 1, "山野记录员", "黄山日出值得早起，山上温差明显。", 4.8, "pending", "[]", "127.0.0.1"),
                    (1, 2, "半日游玩家", "路线清晰，公共交通也方便。", 4.7, "approved", "[]", "127.0.0.1"),
                ],
            )
            db.executemany(
                "INSERT INTO scenic_images (scenic_id,url,status,is_cover,source) VALUES (?,?,?,?,?)",
                [
                    (1, SCENIC_SEED[0]["cover_image_url"], "pending", 0, "user_upload"),
                    (2, normalize_seed(SCENIC_SEED[1])["cover_image_url"], "pending", 0, "user_upload"),
                    (3, normalize_seed(SCENIC_SEED[2])["cover_image_url"], "approved", 1, "seed"),
                ],
            )
            _ensure_seed_user(db, "traveler@example.com", "Traveler123", "风景收藏家", "user")
            _ensure_seed_user(db, "admin@example.com", "Admin123456", "审核员", "admin")
        for provider, label in [
            ("amap", "高德地图"),
            ("map", "地图 API 配置"),
            ("mapbox", "Mapbox 地图服务"),
            ("weather", "天气 API 配置"),
            ("qweather", "和风天气 API"),
            ("amap_weather", "高德天气"),
            ("image", "图片 API 配置"),
            ("scenic", "景区数据 API 配置"),
            ("object_storage", "对象存储图片上传"),
            ("mail_sms", "邮件 / 短信通知"),
            ("webhook", "Webhook 配置"),
            ("bing_search", "Bing Search API"),
            ("bing_image", "Bing Image Search API"),
            ("amap_web_service", "高德 Web 服务 API"),
            ("amap_js", "高德地图前端 JS API"),
            ("amap_js_security", "高德 JS 安全密钥"),
            ("wikimedia_commons", "Wikimedia Commons 图片"),
            ("wikipedia", "Wikipedia 景区介绍"),
            ("wikivoyage", "Wikivoyage 徒步与攻略"),
            ("openstreetmap_overpass", "OpenStreetMap Overpass"),
            ("mct_official", "国家文旅部官方名录"),
            ("ctrip_open", "携程开放平台"),
            ("mafengwo", "马蜂窝 API"),
            ("baidu_map", "百度地图 POI"),
            ("tencent_lbs", "腾讯位置服务"),
            ("scenic_enrichment", "景区资料补全服务"),
            ("earth_check", "地球 Online 来源检测服务"),
            ("image_candidate", "图片候选审核服务"),
        ]:
            db.execute(
                "INSERT OR IGNORE INTO api_configs (provider,label,enabled,status) VALUES (?,?,?,?)",
                (provider, label, 0, "not_configured"),
            )
        db.execute(
            """
            INSERT INTO api_configs (provider,label,enabled,endpoint,api_key_masked,status)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(provider) DO UPDATE SET
              label=excluded.label,
              endpoint=excluded.endpoint,
              api_key_masked=excluded.api_key_masked,
              updated_at=CURRENT_TIMESTAMP
            """,
            ("amap_web_service", "高德 Web 服务 API", 0, AMAP_WEB_SERVICE_ENDPOINT, mask_amap_key(), "not_configured"),
        )
        for name, label, perms in [
            ("guest", "游客", ["scenic:view", "weather:view", "earth:view"]),
            ("user", "注册用户", ["scenic:view", "comment:create", "trip:create", "earth:view", "earth:favorite"]),
            ("admin", "管理员", ["admin:review", "scenic:manage", "earth:review"]),
            ("super_admin", "超级管理员", ["system:manage", "role:manage", "api:manage", "earth:policy"]),
        ]:
            db.execute(
                "INSERT OR IGNORE INTO roles (name,label,permissions) VALUES (?,?,?)",
                (name, label, json.dumps(perms, ensure_ascii=False)),
            )
        default_settings = {
            "siteName": "景区在线 Scenic Online",
            "defaultCity": "杭州",
            "homeRecommendation": "quality",
            "imageFallback": "/images/hero-mountain-lake.jpg",
            "reviewRequired": True,
            "userUploadEnabled": True,
            "autoEnrichmentEnabled": True,
            "earthOnlineEnabled": True,
            "imageStorage": "local-or-remote",
            "syncSchedule": "每天 02:00",
            "announcement": "",
        }
        for key, value in default_settings.items():
            value_type = "boolean" if isinstance(value, bool) else "string"
            db.execute(
                "INSERT OR IGNORE INTO system_settings (setting_key,setting_value,value_type) VALUES (?,?,?)",
                (key, json.dumps(value, ensure_ascii=False), value_type),
            )
        _ensure_seed_user(db, "user@scenic.local", "User123456", "演示用户", "user")
        _ensure_seed_user(db, "admin@scenic.local", "Admin123456", "演示管理员", "admin")
        _ensure_seed_user(db, "superadmin@scenic.local", "SuperAdmin123456", "超级管理员", "super_admin")
        for index, (group, province, city, district) in enumerate(REGION_SEED, start=1):
            db.execute(
                "INSERT OR IGNORE INTO regions (region_group,province,city,district,sort_order) VALUES (?,?,?,?,?)",
                (group, province, city, district, index),
            )
        for keyword, category, count, is_manual in HOT_SEARCH_SEED:
            db.execute(
                "INSERT OR IGNORE INTO hot_searches (keyword, category, search_count, is_manual) VALUES (?,?,?,?)",
                (keyword, category, count, is_manual),
            )
        scenic_regions = db.execute("SELECT DISTINCT province, city, district FROM scenic_spots").fetchall()
        for row in scenic_regions:
            if (
                is_fallback_area_label(row["province"])
                or is_fallback_area_label(row["city"])
                or is_fallback_area_label(row["district"])
            ):
                continue
            db.execute(
                "INSERT OR IGNORE INTO regions (region_group,province,city,district,sort_order) VALUES (?,?,?,?,?)",
                ("重点目的地", row["province"], row["city"], row["district"], 1000),
            )
        community_count = db.execute("SELECT COUNT(*) AS c FROM community_posts").fetchone()["c"]
        if community_count == 0:
            db.executemany(
                """
                INSERT INTO community_posts (user_id,scenic_id,nickname,category,title,content,images,status,likes,reports)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (1, 1, "旅行的风", "点评", "西湖傍晚路线", "西湖傍晚很美，建议从曲院风荷一路走到苏堤。", "[]", "approved", 18, 0),
                    (1, 2, "山野记录员", "图文", "黄山日出提醒", "黄山日出值得早起，山上温差明显。", "[]", "pending", 7, 0),
                ],
            )
        for name, template_type, category, config in COMPONENT_TEMPLATE_SEED:
            db.execute(
                """
                INSERT OR IGNORE INTO component_templates (name,type,category,config_json,preview_image,created_by)
                VALUES (?,?,?,?,?,?)
                """,
                (name, template_type, category, json.dumps(config, ensure_ascii=False), "/images/hero-mountain-lake.jpg", "system"),
            )
        image_count = db.execute("SELECT COUNT(*) AS c FROM scenic_images").fetchone()["c"]
        if image_count == 0:
            db.executemany(
                "INSERT INTO scenic_images (scenic_id,url,status,is_cover,source) VALUES (?,?,?,?,?)",
                [
                    (1, normalize_seed(SCENIC_SEED[0])["cover_image_url"], "pending", 0, "user_upload"),
                    (2, normalize_seed(SCENIC_SEED[1])["cover_image_url"], "pending", 0, "user_upload"),
                    (3, normalize_seed(SCENIC_SEED[2])["cover_image_url"], "approved", 1, "seed"),
                ],
            )
        for item in EARTH_ONLINE_SEED:
            db.execute(
                """
                INSERT OR IGNORE INTO earth_online_sources (
                  slug,name,category,country,city,source_platform,source_url,description,is_live,is_embeddable,
                  review_status,availability_status,risk_level,authorization_note,license_note
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                item,
            )

        # Seed Banners
        for banner in [
            ("寻找内心的宁静：治愈系风景指南", "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1400&q=80", "/destinations?theme=自然风光", 1, 1),
            ("初夏的微风：小众避暑秘境", "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1400&q=80", "/themes/避暑胜地", 2, 1),
        ]:
            db.execute(
                """
                INSERT INTO banners (title, image_url, link_url, order_index, is_active)
                SELECT ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                  SELECT 1 FROM banners
                  WHERE title=? AND image_url=? AND link_url=? AND order_index=?
                )
                """,
                (*banner, banner[0], banner[1], banner[2], banner[3]),
            )

        # Seed Articles
        for article in [
            ("杭州西湖深度游指南", "西湖不仅仅是断桥和雷峰塔，还有隐秘的茶园与古刹...", "攻略", "旅行达人", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80", 1),
            ("2024 全国 5A 景区名录更新公告", "根据最新文旅部发布，全国 5A 级旅游景区名单已增加...", "公告", "官方运营", "https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=800&q=80", 1),
            ("川藏线自驾避雷指南：你必须知道的 10 件事", "高反、路况、油站... 自驾川藏线需要做足充分准备...", "资讯", "老司机", "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80", 1),
        ]:
            db.execute(
                """
                INSERT INTO articles (title, content, category, author, cover_image, is_published)
                SELECT ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                  SELECT 1 FROM articles
                  WHERE title=? AND category=? AND author=?
                )
                """,
                (*article, article[0], article[2], article[3]),
            )

        for scope in ("home", "admin", "user:1"):
            row = db.execute("SELECT layout FROM page_layouts WHERE scope=?", (scope,)).fetchone()
            if row and "地球 Online" not in row["layout"]:
                layout = json.loads(row["layout"])
                layout.append({"id": f"{scope}-earth-online", "title": "地球 Online", "visible": True, "order": len(layout)})
                db.execute("UPDATE page_layouts SET layout=?, updated_at=CURRENT_TIMESTAMP WHERE scope=?", (json.dumps(layout, ensure_ascii=False), scope))
