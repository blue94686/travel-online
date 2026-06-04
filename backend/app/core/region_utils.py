import json
import re
from pathlib import Path

REGION_AREA_PREFIX = {
    "北京市": "11",
    "上海市": "31",
    "天津市": "12",
    "河北省": "13",
    "石家庄市": "1301",
    "保定市": "1306",
    "江苏省": "32",
    "浙江省": "33",
    "安徽省": "34",
    "湖南省": "43",
    "广东省": "44",
    "广西壮族自治区": "45",
    "重庆市": "50",
    "四川省": "51",
    "云南省": "53",
    "杭州市": "3301",
    "西湖区": "330106",
    "淳安县": "330127",
    "黄山市": "3410",
    "黄山区": "341003",
    "成都市": "5101",
    "乐山市": "5111",
    "阿坝州": "5132",
    "阿坝藏族羌族自治州": "5132",
    "九寨沟县": "513225",
    "汶川县": "513221",
    "张家界市": "4308",
    "武陵源区": "430811",
    "桂林市": "4503",
    "阳朔县": "450321",
}

PROVINCE_GROUPS = {
    "北京市": "华北",
    "天津市": "华北",
    "河北省": "华北",
    "山西省": "华北",
    "内蒙古自治区": "华北",
    "辽宁省": "东北",
    "吉林省": "东北",
    "黑龙江省": "东北",
    "上海市": "华东",
    "江苏省": "华东",
    "浙江省": "华东",
    "安徽省": "华东",
    "福建省": "华东",
    "江西省": "华东",
    "山东省": "华东",
    "河南省": "华中",
    "湖北省": "华中",
    "湖南省": "华中",
    "广东省": "华南",
    "广西壮族自治区": "华南",
    "海南省": "华南",
    "香港特别行政区": "华南",
    "澳门特别行政区": "华南",
    "重庆市": "西南",
    "四川省": "西南",
    "贵州省": "西南",
    "云南省": "西南",
    "西藏自治区": "西南",
    "陕西省": "西北",
    "甘肃省": "西北",
    "青海省": "西北",
    "宁夏回族自治区": "西北",
    "新疆维吾尔自治区": "西北",
    "台湾省": "华东",
}

_AREA_MAPPING_CACHE = None

def _get_area_mapping():
    global _AREA_MAPPING_CACHE
    if _AREA_MAPPING_CACHE is None:
        try:
            mapping_path = Path(__file__).resolve().parent / "area_mapping.json"
            if mapping_path.exists():
                with open(mapping_path, "r", encoding="utf-8") as f:
                    _AREA_MAPPING_CACHE = json.load(f)
            else:
                _AREA_MAPPING_CACHE = {}
        except Exception as e:
            print(f"Error loading area_mapping.json: {e}")
            _AREA_MAPPING_CACHE = {}
    return _AREA_MAPPING_CACHE

def normalize_region_name(value):
    value = (value or "").strip()
    if value in ("全部", "全部省份", "全部城市", "全部区县", "不限"):
        return ""
    aliases = {
        "河南": "河南省",
        "浙江": "浙江省",
        "四川": "四川省",
        "云南": "云南省",
        "江苏": "江苏省",
        "北京": "北京市",
        "上海": "上海市",
        "重庆": "重庆市",
        "天津": "天津市",
        "阿坝藏族羌族自治州": "阿坝州",
    }
    return aliases.get(value, value)

def region_group_for_province(province):
    return PROVINCE_GROUPS.get(normalize_region_name(province), "其他")

def is_fallback_area_label(value):
    return bool(re.match(r"^\d+(省级区域|地区|区县)$", value or ""))

def label_area(code, size):
    if not code:
        return ""
    mapping = _get_area_mapping()
    if code in mapping:
        name = mapping[code]
        if size == 4 and name == "市辖区":
            return mapping.get(code[:2], code)
        if size == 4 and name == "阿坝藏族羌族自治州":
            return "阿坝州"
        return name
    return f"{code}{'省级区域' if size == 2 else ('地区' if size == 4 else '区县')}"

def resolve_areaid(province=None, city=None, district=None):
    for value in (district, city, province):
        value = normalize_region_name(value)
        if value and str(value)[:6].isdigit():
            return str(value)[:6]
        if value and REGION_AREA_PREFIX.get(value):
            return REGION_AREA_PREFIX[value]
            
        mapping = _get_area_mapping()
        # Reverse lookup (slower but accurate)
        for code, name in mapping.items():
            if name == value or name.replace("省", "") == value or name.replace("市", "") == value:
                return code
                
    return ""
