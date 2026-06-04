def weather_for(city: str = "杭州"):
    return {
        "city": city,
        "current": {"temp": 24, "condition": "多云", "humidity": "68%", "wind": "东北风 2级", "air": "优 32"},
        "forecast": [
            {"day": "今天", "temp": "20-26°C", "condition": "多云"},
            {"day": "明天", "temp": "21-27°C", "condition": "晴"},
            {"day": "周五", "temp": "22-28°C", "condition": "阵雨"},
            {"day": "周六", "temp": "21-25°C", "condition": "小雨"},
            {"day": "周日", "temp": "20-26°C", "condition": "多云"},
            {"day": "周一", "temp": "22-29°C", "condition": "晴"},
            {"day": "周二", "temp": "23-30°C", "condition": "晴"},
        ],
        "travelAdvice": ["上午适合湖边步行", "午后注意防晒补水", "傍晚适合拍摄落日"],
    }
