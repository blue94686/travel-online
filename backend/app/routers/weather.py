from fastapi import APIRouter

from app.core.response import ok
from app.services.weather_provider_service import route_weather, weather_for, weather_live as weather_live_for

router = APIRouter()


@router.get("/weather")
def weather(city: str = "杭州"):
    return ok(weather_for(city))


@router.get("/weather/forecast")
def weather_forecast(city: str = "杭州"):
    return ok(weather_for(city).get("forecast", []))


@router.get("/weather/live")
def weather_live(city: str = "杭州"):
    return ok(weather_live_for(city or "杭州"))


@router.get("/weather/route")
def weather_route(cities: str = "杭州,黄山"):
    return ok(route_weather([item.strip() for item in cities.split(",") if item.strip()]))
