#!/usr/bin/env python3
import json
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "backend" / "app" / "data" / "scenic_online.sqlite3"


CORE_SCENIC = [
    {
        "slug": "core-gugong-bowuyuan",
        "name": "故宫博物院",
        "aliases": ["故宫博物院"],
        "province": "北京市",
        "city": "北京市",
        "district": "东城区",
        "level": "5A",
        "rating": 4.9,
        "address": "北京市东城区景山前街4号",
        "latitude": 39.916345,
        "longitude": 116.397155,
        "official_website": "https://www.dpm.org.cn/",
        "source_url": "https://www.dpm.org.cn/Home.html",
        "summary": "故宫博物院是在明清两代皇宫及其收藏基础上建立的综合性博物馆，是北京核心文化地标。",
        "description": "故宫博物院位于北京中轴线中心区域，依托紫禁城宫殿建筑群展示中国古代宫廷建筑、文物收藏与历史文化。适合安排半日至一日游览，重点关注午门、太和殿、中和殿、保和殿、乾清宫、珍宝馆和钟表馆等区域。出行前应通过官方渠道核对预约、开放时间、闭馆日和展览信息。",
        "tags": ["5A", "世界遗产", "博物馆", "古建筑", "历史文化", "北京中轴线"],
        "ticket_price": "以故宫博物院官方预约购票页面为准",
        "opening_hours": "以故宫博物院官网当日公告为准，通常周一闭馆，法定节假日安排可能调整",
        "best_season": "春季、秋季",
        "slogan": "走进紫禁城，阅读中国宫廷建筑与文物收藏。",
        "suitable_groups": ["历史文化爱好者", "亲子家庭", "摄影爱好者", "首次到访北京游客"],
        "recommended_duration": "4-6 小时",
        "history_culture": "故宫博物院以明清皇宫紫禁城为院址，院藏文物和宫殿建筑共同构成中国古代宫廷文化的重要展示体系。",
        "highlights": "午门、三大殿、乾清宫、御花园、珍宝馆、钟表馆和主题展览是核心看点。",
        "traffic_info": "建议优先选择地铁、公交到达天安门及周边区域后步行进入，周边道路和停车资源在高峰期较紧张。",
        "parking_info": "故宫周边停车资源有限，不建议自驾直接前往。",
        "public_transport": "可结合地铁 1 号线、8 号线及周边公交线路到达天安门、王府井、景山等片区后步行。",
        "self_driving_route": "自驾建议停放在外围合规停车场后换乘公共交通或步行。",
        "accessibility_tips": "无障碍参观、轮椅服务和特殊通行安排以故宫博物院官网及现场服务为准。",
        "must_see_spots": ["午门", "太和殿", "乾清宫", "御花园", "珍宝馆", "钟表馆"],
        "photo_spots": ["午门广场", "太和殿前广场", "宫墙角楼", "御花园"],
    },
    {
        "slug": "core-hangzhou-xihu",
        "name": "杭州西湖",
        "aliases": ["杭州西湖"],
        "province": "浙江省",
        "city": "杭州市",
        "district": "西湖区",
        "level": "5A",
        "rating": 4.8,
        "address": "浙江省杭州市西湖区龙井路1号周边",
        "latitude": 30.244796,
        "longitude": 120.143179,
        "official_website": "https://westlake.hangzhou.gov.cn/",
        "source_url": "https://westlake.hangzhou.gov.cn/",
        "summary": "杭州西湖以湖山景观、历史遗存和城市生活融合闻名，是杭州最具代表性的旅游目的地。",
        "description": "杭州西湖适合慢行游览，湖区可串联苏堤、白堤、断桥、雷峰塔、三潭印月、花港观鱼、曲院风荷等经典点位。不同季节都有鲜明景观，春看柳浪与花事，夏赏荷，秋游湖山，冬观断桥残雪。建议结合步行、公交、水上游船和周边街区安排半日至一日路线。",
        "tags": ["5A", "世界遗产", "湖泊", "城市漫步", "摄影", "人文古迹"],
        "ticket_price": "湖区公共游览空间多为开放式，游船及部分场馆以官方公示为准",
        "opening_hours": "开放式湖区以现场管理公告为准",
        "best_season": "春季、秋季、夏季荷花期",
        "slogan": "在湖山之间体验杭州的诗意日常。",
        "suitable_groups": ["城市漫步", "摄影爱好者", "亲子家庭", "情侣出行"],
        "recommended_duration": "4-8 小时",
        "history_culture": "西湖长期与杭州城市发展、诗词书画和园林营造相互交织，是中国湖景文化的重要代表。",
        "highlights": "断桥、苏堤、白堤、三潭印月、雷峰塔、曲院风荷和花港观鱼。",
        "traffic_info": "湖区周边游客密集，建议优先选择地铁、公交、步行和共享单车组合出行。",
        "parking_info": "节假日湖滨、北山街、南山路周边停车紧张，建议外围换乘。",
        "public_transport": "可乘地铁至龙翔桥、凤起路、黄龙洞、吴山广场等站点后步行或换乘公交。",
        "self_driving_route": "自驾应避开湖滨核心拥堵路段，按实时交通选择外围停车点。",
        "accessibility_tips": "湖滨和部分景点步道较平缓，具体无障碍条件以现场导览为准。",
        "must_see_spots": ["断桥残雪", "苏堤春晓", "三潭印月", "雷峰塔", "曲院风荷"],
        "photo_spots": ["断桥", "苏堤", "湖滨夕照", "雷峰塔远景"],
    },
    {
        "slug": "core-huangshan-fengjingqu",
        "name": "黄山风景区",
        "aliases": ["黄山风景区"],
        "province": "安徽省",
        "city": "黄山市",
        "district": "黄山区",
        "level": "5A",
        "rating": 4.9,
        "address": "安徽省黄山市黄山区汤口镇",
        "latitude": 30.132992,
        "longitude": 118.168171,
        "official_website": "https://hsgwh.huangshan.gov.cn/",
        "source_url": "https://hsgwh.huangshan.gov.cn/",
        "summary": "黄山风景区以奇松、怪石、云海、温泉等景观闻名，是山岳型景区代表。",
        "description": "黄山风景区适合安排一日至两日游览。常见路线包括云谷寺、白鹅岭、光明顶、飞来石、西海大峡谷、莲花峰或始信峰等节点。山地天气变化快，建议根据索道、步道、日出点和体力安排路线，并提前关注景区公告、索道运行和气象信息。",
        "tags": ["5A", "世界遗产", "山岳", "摄影", "徒步", "云海"],
        "ticket_price": "以黄山风景区官方票务公告为准",
        "opening_hours": "以黄山风景区官方公告和索道运营时间为准",
        "best_season": "春季、秋季、冬季雪后",
        "slogan": "登黄山，看奇松怪石与云海日出。",
        "suitable_groups": ["徒步爱好者", "摄影爱好者", "自然风光游客"],
        "recommended_duration": "1-2 天",
        "history_culture": "黄山在中国山水审美、诗画传统和现代自然旅游中具有重要地位。",
        "highlights": "迎客松、光明顶、西海大峡谷、始信峰、云海和日出。",
        "traffic_info": "游客通常经黄山北站、黄山站或汤口镇换乘景区交通进入。",
        "parking_info": "自驾可停放汤口周边游客集散区，按景区交通换乘进入山门。",
        "public_transport": "黄山北站至汤口方向有旅游交通接驳，具体班次以当地公示为准。",
        "self_driving_route": "导航至黄山风景区汤口游客中心，按现场指引换乘景区交通。",
        "accessibility_tips": "山地步道坡度大，索道可降低体力消耗；雨雪天气需谨慎出行。",
        "must_see_spots": ["迎客松", "光明顶", "西海大峡谷", "始信峰", "飞来石"],
        "photo_spots": ["光明顶日出", "迎客松", "西海大峡谷观景点", "云海观景台"],
    },
    {
        "slug": "core-jiuzhaigou",
        "name": "九寨沟风景名胜区",
        "aliases": ["九寨沟风景名胜区"],
        "province": "四川省",
        "city": "阿坝藏族羌族自治州",
        "district": "九寨沟县",
        "level": "5A",
        "rating": 4.9,
        "address": "四川省阿坝藏族羌族自治州九寨沟县漳扎镇",
        "latitude": 33.257591,
        "longitude": 103.918025,
        "official_website": "https://www.jiuzhai.com/",
        "source_url": "https://www.jiuzhai.com/",
        "summary": "九寨沟以彩林、湖泊、瀑布、雪峰和藏羌文化景观著称，是川西北经典自然景区。",
        "description": "九寨沟沟谷纵深较长，常见游览围绕树正沟、日则沟、则查洼沟展开，重点包括五花海、珍珠滩瀑布、诺日朗瀑布、长海、五彩池、树正群海等。建议根据官方开放线路、观光车运行和季节水量安排一日或两日行程。",
        "tags": ["5A", "世界遗产", "湖泊", "瀑布", "彩林", "摄影"],
        "ticket_price": "以九寨沟官方票务信息为准",
        "opening_hours": "以九寨沟官网当季公告为准",
        "best_season": "秋季彩林期、夏季丰水期",
        "slogan": "走进九寨沟，看高山海子与彩林瀑布。",
        "suitable_groups": ["自然风光游客", "摄影爱好者", "家庭旅行"],
        "recommended_duration": "1-2 天",
        "history_culture": "九寨沟自然景观与当地藏羌文化共同构成独特的山地旅游体验。",
        "highlights": "五花海、珍珠滩瀑布、诺日朗瀑布、长海、五彩池、树正群海。",
        "traffic_info": "可结合九寨沟黄龙机场、成都方向长途交通和景区接驳安排出行。",
        "parking_info": "自驾游客按景区游客中心与停车场指引停放，旺季需预留入场时间。",
        "public_transport": "成都、松潘、黄龙等方向交通方式以当地客运和官方公告为准。",
        "self_driving_route": "导航至九寨沟景区游客中心，山区道路需关注天气和交通管制。",
        "accessibility_tips": "景区海拔较高，建议关注身体状态，老人儿童注意保暖和休息。",
        "must_see_spots": ["五花海", "珍珠滩瀑布", "诺日朗瀑布", "长海", "五彩池"],
        "photo_spots": ["五花海观景点", "珍珠滩瀑布", "长海湖畔", "树正群海"],
    },
    {
        "slug": "core-badaling-great-wall",
        "name": "八达岭长城",
        "aliases": ["八达岭长城"],
        "province": "北京市",
        "city": "北京市",
        "district": "延庆区",
        "level": "5A",
        "rating": 4.8,
        "address": "北京市延庆区军都山关沟古道北口",
        "latitude": 40.359941,
        "longitude": 116.020157,
        "official_website": "https://www.badaling.cn/",
        "source_url": "https://www.badaling.cn/",
        "summary": "八达岭长城是北京长城游览最具代表性的段落之一，适合首次体验长城的游客。",
        "description": "八达岭长城位于北京市延庆区，城墙保存较好，配套交通和游客服务成熟。可根据体力选择步行登城、索道或滑车等方式，游览时注意风大、台阶高差和客流高峰。建议提前核对预约、开放时间和交通换乘信息。",
        "tags": ["5A", "长城", "世界遗产", "历史文化", "北京"],
        "ticket_price": "以八达岭长城官方票务公告为准",
        "opening_hours": "以八达岭长城官网当日公告为准",
        "best_season": "春季、秋季、冬季晴朗日",
        "slogan": "登八达岭，远眺群山与长城关隘。",
        "suitable_groups": ["首次到访北京游客", "历史文化爱好者", "家庭旅行"],
        "recommended_duration": "2-4 小时",
        "history_culture": "八达岭是明长城重要关隘段落，长期承担军事防御与交通关口功能。",
        "highlights": "北段登城路线、烽火台、关城视角和长城山脊线。",
        "traffic_info": "可选择市郊铁路、旅游巴士或自驾至延庆八达岭片区。",
        "parking_info": "景区周边设有停车区，旺季按现场分流和接驳安排通行。",
        "public_transport": "可查询市郊铁路 S2 线、高铁或旅游专线到达方式。",
        "self_driving_route": "导航至八达岭长城景区，关注京藏高速及景区分流提示。",
        "accessibility_tips": "长城台阶坡度明显，老人儿童应量力而行，可选择辅助交通方式。",
        "must_see_spots": ["关城", "北段城墙", "烽火台", "长城博物馆周边"],
        "photo_spots": ["北段高点", "关城入口", "城墙转角", "山脊线远景"],
    },
    {
        "slug": "core-zhangjiajie-forest-park",
        "name": "张家界国家森林公园",
        "aliases": ["张家界国家森林公园"],
        "province": "湖南省",
        "city": "张家界市",
        "district": "武陵源区",
        "level": "5A",
        "rating": 4.9,
        "address": "湖南省张家界市武陵源区",
        "latitude": 29.342011,
        "longitude": 110.443941,
        "official_website": "http://www.zjjpark.com/",
        "source_url": "http://www.zjjpark.com/",
        "summary": "张家界国家森林公园以石英砂岩峰林地貌闻名，是武陵源核心自然景区。",
        "description": "张家界国家森林公园适合安排一至两日游览，核心看点包括袁家界、天子山、金鞭溪、黄石寨和杨家界等。景区山地道路、索道和观光车组合较多，建议按天气、体力和官方开放线路规划路线。雨后云雾、晴日峰林和峡谷溪流是主要观景体验。",
        "tags": ["5A", "世界遗产", "山岳", "峰林", "徒步", "摄影"],
        "ticket_price": "以张家界景区官方票务公告为准",
        "opening_hours": "以张家界景区官方公告和观光交通运营时间为准",
        "best_season": "春季、秋季、雨后云雾天气",
        "slogan": "在张家界峰林之间看山地云雾与峡谷溪流。",
        "suitable_groups": ["自然风光游客", "摄影爱好者", "徒步爱好者"],
        "recommended_duration": "1-2 天",
        "history_culture": "张家界峰林地貌是武陵源自然景观的重要组成部分，具有鲜明的地质和景观价值。",
        "highlights": "袁家界、金鞭溪、天子山、黄石寨、杨家界。",
        "traffic_info": "可从张家界市区或武陵源片区换乘景区交通进入不同游览区。",
        "parking_info": "自驾按游客中心或景区入口停车场分流停放。",
        "public_transport": "张家界市区至武陵源方向有公共交通和旅游接驳，班次以当地公示为准。",
        "self_driving_route": "导航至张家界国家森林公园或武陵源游客中心，按入口选择路线。",
        "accessibility_tips": "景区高差明显，索道和观光车可降低体力负担，雨天注意防滑。",
        "must_see_spots": ["袁家界", "金鞭溪", "天子山", "黄石寨", "杨家界"],
        "photo_spots": ["袁家界观景台", "金鞭溪步道", "天子山云海", "峰林远景"],
    },
    {
        "slug": "core-guilin-lijiang",
        "name": "桂林漓江风景区",
        "aliases": ["桂林漓江风景区"],
        "province": "广西壮族自治区",
        "city": "桂林市",
        "district": "阳朔县",
        "level": "5A",
        "rating": 4.8,
        "address": "广西壮族自治区桂林市至阳朔漓江沿线",
        "latitude": 25.161775,
        "longitude": 110.424047,
        "official_website": "http://www.liriver.com.cn/",
        "source_url": "http://www.liriver.com.cn/",
        "summary": "桂林漓江风景区以喀斯特山水、江上游船和阳朔田园景观著称。",
        "description": "桂林漓江风景区适合以游船或分段慢游方式体验，经典印象包括黄布倒影、九马画山、兴坪江段和阳朔山水。不同水位和天气会影响观景效果，建议提前核对船班、码头、票务和天气情况，并结合阳朔西街、遇龙河等周边路线安排。",
        "tags": ["5A", "山水", "游船", "喀斯特", "摄影", "自驾"],
        "ticket_price": "以漓江官方票务和船班公告为准",
        "opening_hours": "以漓江官方船班和景区公告为准",
        "best_season": "春季、秋季、雨后云雾天气",
        "slogan": "乘船看漓江山水，体验桂林到阳朔的经典画卷。",
        "suitable_groups": ["自然风光游客", "摄影爱好者", "家庭旅行"],
        "recommended_duration": "半日-1 天",
        "history_culture": "漓江山水长期作为桂林旅游和中国山水审美的重要代表。",
        "highlights": "黄布倒影、九马画山、兴坪古镇、阳朔山水。",
        "traffic_info": "可从桂林市区码头乘船至阳朔，也可分段前往兴坪等江段。",
        "parking_info": "自驾需按码头和古镇周边停车场分流，旺季提前到达。",
        "public_transport": "桂林市区、阳朔和兴坪之间有客运及旅游交通，班次以当地公示为准。",
        "self_driving_route": "根据船班选择桂林或阳朔方向码头，避免错过登船时间。",
        "accessibility_tips": "游船上下船和码头台阶需注意老人儿童安全。",
        "must_see_spots": ["黄布倒影", "九马画山", "兴坪江段", "阳朔山水"],
        "photo_spots": ["兴坪江畔", "黄布倒影观景点", "游船甲板", "阳朔田园远景"],
    },
    {
        "slug": "core-qiandaohu",
        "name": "千岛湖风景区",
        "aliases": ["千岛湖风景区", "千岛湖国家森林公园"],
        "province": "浙江省",
        "city": "杭州市",
        "district": "淳安县",
        "level": "5A",
        "rating": 4.7,
        "address": "浙江省杭州市淳安县千岛湖镇",
        "latitude": 29.608986,
        "longitude": 119.043668,
        "official_website": "https://www.qiandaohu.cc/",
        "source_url": "https://www.qiandaohu.cc/",
        "summary": "千岛湖风景区以湖岛景观、游船线路和生态休闲体验为主要特色。",
        "description": "千岛湖风景区适合安排半日至一日湖区游览，常见体验包括中心湖区或东南湖区游船、登岛观景、骑行和湖畔度假。不同码头、船班和岛屿开放情况会随季节调整，建议提前核对官方票务与交通信息。",
        "tags": ["5A", "湖泊", "游船", "生态", "亲子", "自驾"],
        "ticket_price": "以千岛湖官方票务和船班公告为准",
        "opening_hours": "以千岛湖官方景区和码头公告为准",
        "best_season": "春季、秋季、夏季亲水季",
        "slogan": "在千岛湖看湖岛交错与生态山水。",
        "suitable_groups": ["亲子家庭", "自驾游客", "湖泊风光游客"],
        "recommended_duration": "半日-1 天",
        "history_culture": "千岛湖以人工湖形成的岛屿景观和生态保护价值成为杭州西部重要旅游目的地。",
        "highlights": "中心湖区、东南湖区、游船登岛、湖畔骑行。",
        "traffic_info": "可从杭州、黄山等方向抵达淳安千岛湖镇后换乘码头交通。",
        "parking_info": "码头周边设停车场，旺季按现场分流停放。",
        "public_transport": "杭州至千岛湖有高铁、客运和旅游接驳方式，班次以官方公示为准。",
        "self_driving_route": "导航至千岛湖中心湖区或东南湖区码头，按船班时间预留到达余量。",
        "accessibility_tips": "游船登岛涉及上下船和部分台阶，老人儿童需注意防滑和防晒。",
        "must_see_spots": ["中心湖区", "东南湖区", "梅峰岛", "湖畔骑行道"],
        "photo_spots": ["梅峰观景台", "湖区游船", "湖畔日落", "岛屿远景"],
    },
    {
        "slug": "core-yiheyuan",
        "name": "颐和园",
        "aliases": ["颐和园"],
        "province": "北京市",
        "city": "北京市",
        "district": "海淀区",
        "level": "5A",
        "rating": 4.8,
        "address": "北京市海淀区新建宫门路19号",
        "latitude": 39.999704,
        "longitude": 116.275467,
        "official_website": "https://www.summerpalace-china.com/",
        "source_url": "https://www.summerpalace-china.com/",
        "summary": "颐和园是以昆明湖、万寿山为主体的大型皇家园林，兼具湖山景观和古建筑群。",
        "description": "颐和园适合半日至一日游览，经典路线可串联东宫门、仁寿殿、长廊、排云殿、佛香阁、昆明湖、十七孔桥和苏州街等区域。园区面积较大，建议根据入口、体力和季节选择环湖或山前路线。",
        "tags": ["5A", "世界遗产", "皇家园林", "湖泊", "古建筑"],
        "ticket_price": "以颐和园官方票务公告为准",
        "opening_hours": "以颐和园官网季节性开放公告为准",
        "best_season": "春季、秋季、夏季荷花期",
        "slogan": "在昆明湖与万寿山之间漫游皇家园林。",
        "suitable_groups": ["历史文化爱好者", "摄影爱好者", "亲子家庭"],
        "recommended_duration": "3-5 小时",
        "history_culture": "颐和园是中国现存规模较大的皇家园林之一，集中体现清代园林营造与湖山格局。",
        "highlights": "长廊、佛香阁、昆明湖、十七孔桥、苏州街、万寿山。",
        "traffic_info": "可通过地铁和公交到达北宫门、东宫门、新建宫门等入口。",
        "parking_info": "周边停车紧张，建议公共交通前往。",
        "public_transport": "可乘地铁 4 号线北宫门站或西苑站后步行/换乘。",
        "self_driving_route": "自驾按入口选择新建宫门或北宫门周边停车点，节假日需预留排队时间。",
        "accessibility_tips": "湖边路线相对平缓，登万寿山和佛香阁台阶较多。",
        "must_see_spots": ["长廊", "佛香阁", "昆明湖", "十七孔桥", "苏州街"],
        "photo_spots": ["十七孔桥夕照", "昆明湖岸", "佛香阁远景", "长廊彩画"],
    },
    {
        "slug": "core-tiantan-park",
        "name": "天坛公园",
        "aliases": ["天坛公园"],
        "province": "北京市",
        "city": "北京市",
        "district": "东城区",
        "level": "5A",
        "rating": 4.8,
        "address": "北京市东城区天坛东里甲1号",
        "latitude": 39.882215,
        "longitude": 116.406605,
        "official_website": "https://www.tiantanpark.com/",
        "source_url": "https://www.tiantanpark.com/",
        "summary": "天坛公园以祈年殿、圜丘、回音壁等祭天建筑群闻名，是北京中轴线重要文化景观。",
        "description": "天坛公园适合半日游览，经典看点包括祈年殿、皇穹宇、回音壁、圜丘坛、斋宫和古柏群。公园兼具文物参观和城市休闲属性，建议避开客流高峰并提前核对联票、开放时间和展区安排。",
        "tags": ["5A", "世界遗产", "古建筑", "北京中轴线", "公园"],
        "ticket_price": "以天坛公园官方票务公告为准",
        "opening_hours": "以天坛公园官网季节性开放公告为准",
        "best_season": "春季、秋季",
        "slogan": "看祈年殿，理解北京礼制建筑之美。",
        "suitable_groups": ["历史文化爱好者", "城市漫步", "亲子家庭"],
        "recommended_duration": "2-4 小时",
        "history_culture": "天坛是明清时期祭天礼制建筑群，体现中国古代礼制、建筑和城市规划思想。",
        "highlights": "祈年殿、圜丘坛、皇穹宇、回音壁、古柏群。",
        "traffic_info": "地铁和公交可到达天坛东门、南门、西门等入口。",
        "parking_info": "核心城区停车有限，建议公共交通出行。",
        "public_transport": "可乘地铁 5 号线天坛东门站或结合多条公交线路到达。",
        "self_driving_route": "自驾需关注东城区道路管制和景区周边停车位情况。",
        "accessibility_tips": "公园步道较平缓，古建筑台基区域有台阶。",
        "must_see_spots": ["祈年殿", "圜丘坛", "皇穹宇", "回音壁", "斋宫"],
        "photo_spots": ["祈年殿广场", "丹陛桥", "古柏道", "圜丘坛"],
    },
]


def dumps(value):
    return json.dumps(value, ensure_ascii=False)


def itinerary(name):
    return [
        {"title": "半日重点游", "content": f"优先游览{name}核心看点，预留拍照、休息和交通换乘时间。"},
        {"title": "一日深度游", "content": f"结合{name}周边餐饮、博物馆或同城景点，安排更完整的城市旅行路线。"},
    ]


def tips(name):
    return [
        f"出发前通过{name}官方渠道核对开放时间、预约规则和临时公告。",
        "旺季建议错峰到达，预留安检、购票、换乘和排队时间。",
        "尊重文物、生态和现场管理要求，按导览路线游览。",
    ]


def update_or_insert(db, item):
    now = datetime.now().isoformat(timespec="seconds")
    row = None
    for alias in item["aliases"]:
        row = db.execute(
            "SELECT * FROM scenic_spots WHERE name=? AND (province=? OR normalized_province=?) ORDER BY rating DESC, id ASC LIMIT 1",
            (alias, item["province"], item["province"]),
        ).fetchone()
        if row:
            break
    payload = {
        "slug": item["slug"],
        "name": item["name"],
        "province": item["province"],
        "city": item["city"],
        "district": item["district"],
        "normalized_province": item["province"],
        "normalized_city": item["city"],
        "normalized_district": item["district"],
        "level": item["level"],
        "rating": item["rating"],
        "address": item["address"],
        "latitude": item["latitude"],
        "longitude": item["longitude"],
        "summary": item["summary"],
        "description": item["description"],
        "tags": dumps(item["tags"]),
        "ticket_price": item["ticket_price"],
        "opening_hours": item["opening_hours"],
        "best_season": item["best_season"],
        "official_website": item["official_website"],
        "source_url": item["source_url"],
        "last_enriched_at": now,
        "slogan": item["slogan"],
        "suitable_groups": dumps(item["suitable_groups"]),
        "recommended_duration": item["recommended_duration"],
        "history_culture": item["history_culture"],
        "highlights": item["highlights"],
        "traffic_info": item["traffic_info"],
        "parking_info": item["parking_info"],
        "public_transport": item["public_transport"],
        "self_driving_route": item["self_driving_route"],
        "accessibility_tips": item["accessibility_tips"],
        "must_see_spots": dumps(item["must_see_spots"]),
        "recommended_itinerary": dumps(itinerary(item["name"])),
        "photo_spots": dumps(item["photo_spots"]),
        "travel_tips": dumps(tips(item["name"])),
        "completeness_score": 98,
    }
    if row:
        set_sql = ", ".join(f"{key}=?" for key in payload if key != "slug")
        values = [value for key, value in payload.items() if key != "slug"]
        values.append(row["id"])
        db.execute(f"UPDATE scenic_spots SET {set_sql} WHERE id=?", values)
        scenic_id = row["id"]
        action = "updated"
    else:
        columns = ",".join(payload)
        placeholders = ",".join("?" for _ in payload)
        cur = db.execute(
            f"INSERT INTO scenic_spots ({columns}) VALUES ({placeholders})",
            list(payload.values()),
        )
        scenic_id = cur.lastrowid
        action = "inserted"
    db.execute(
        """
        INSERT INTO audit_logs (operator, module, action, result)
        VALUES ('system', 'scenic_enrichment', ?, 'success')
        """,
        (f"core_scenic_enriched:{action}:{scenic_id}:{item['name']}",),
    )
    for field_name in ("official_website", "summary", "description", "traffic_info"):
        db.execute(
            """
            DELETE FROM scenic_candidates
            WHERE scenic_id=? AND field_name=? AND source_url=? AND review_status='approved'
            """,
            (scenic_id, field_name, item["source_url"]),
        )
        db.execute(
            """
            INSERT INTO scenic_candidates
            (scenic_id, field_name, candidate_value, source_url, confidence, review_status)
            VALUES (?, ?, ?, ?, 0.95, 'approved')
            """,
            (scenic_id, field_name, payload[field_name], item["source_url"]),
        )
    return action, scenic_id, item["name"]


def main():
    results = []
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        for item in CORE_SCENIC:
            results.append(update_or_insert(db, item))
        db.commit()
    print(json.dumps({"updated": len(results), "items": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
