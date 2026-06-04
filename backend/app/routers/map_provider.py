from fastapi import APIRouter, Query

from app.core.response import ok
from app.services.map_provider_service import geocode, ip_location, map_client_config, poi, reverse_geocode, route, static_preview

router = APIRouter()


@router.get("/map/config")
def map_config():
    config = map_client_config()
    return ok({"amap_key": config["amap_js_key"], **config})


@router.get("/map/geocode")
def map_geocode(address: str = Query("杭州")):
    return ok(geocode(address))


@router.get("/map/reverse-geocode")
def map_reverse_geocode(lat: float = Query(...), lng: float = Query(...)):
    return ok(reverse_geocode(lat=lat, lng=lng))


@router.get("/location/reverse")
def location_reverse(lat: float = Query(...), lng: float = Query(...)):
    return ok(reverse_geocode(lat=lat, lng=lng))


@router.get("/location/ip")
def location_ip():
    return ok(ip_location())


@router.get("/map/route")
def map_route(origin: str = Query(...), destination: str = Query(...), mode: str = Query("driving")):
    return ok(route(origin=origin, destination=destination, mode=mode))


@router.get("/map/static-preview")
def map_static_preview(city: str = Query("杭州"), scenic_id: int | None = Query(None)):
    return ok(static_preview(city=city, scenic_id=scenic_id))


@router.get("/map/poi")
def map_poi(keyword: str = Query("景区"), city: str = Query("")):
    return ok(poi(keyword=keyword, city=city))
