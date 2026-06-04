import unittest
from unittest.mock import patch

import app.services.map_provider_service as map_provider_service


class LocationMapProviderTest(unittest.TestCase):
    def test_ip_location_uses_amap_when_key_is_configured(self):
        payload = {
            "status": "1",
            "province": "江苏省",
            "city": "苏州市",
            "adcode": "320500",
            "rectangle": "120.1,31.1;120.9,31.5",
        }

        with patch.object(map_provider_service, "get_secret", return_value="amap-key"):
            with patch.object(map_provider_service, "get_provider_config", return_value={"enabled": 1}):
                with patch.object(map_provider_service, "_http_json", return_value=payload):
                    result = map_provider_service.ip_location()

        self.assertEqual(result["province"], "江苏省")
        self.assertEqual(result["city"], "苏州市")
        self.assertEqual(result["adcode"], "320500")
        self.assertEqual(result["provider"], "amap")

    def test_map_client_config_does_not_expose_web_service_key_as_js_key(self):
        def fake_secret(provider, env_name=""):
            values = {
                ("amap_web_service", "AMAP_WEB_SERVICE_KEY"): "web-service-key",
                ("amap", "AMAP_WEB_SERVICE_KEY"): "legacy-web-key",
                ("amap_js", "AMAP_JS_API_KEY"): "",
                ("amap_js_security", "AMAP_JS_SECURITY_CODE"): "",
            }
            return values.get((provider, env_name), "")

        with patch.object(map_provider_service, "get_secret", side_effect=fake_secret):
            result = map_provider_service.map_client_config()

        self.assertEqual(result["amap_js_key"], "")
        self.assertEqual(result["amap_security_code"], "")

    def test_reverse_geocode_rejects_amap_hangzhou_for_suzhou_coordinates(self):
        payload = {
            "status": "1",
            "regeocode": {
                "addressComponent": {
                    "province": "",
                    "city": "杭州市",
                    "district": "",
                }
            },
        }

        with patch.object(map_provider_service, "get_secret", return_value="amap-key"):
            with patch.object(map_provider_service, "get_provider_config", return_value={"enabled": 1}):
                with patch.object(map_provider_service, "_http_json", return_value=payload):
                    with patch.object(map_provider_service, "_record_map_log"):
                        result = map_provider_service.reverse_geocode(lat=31.299, lng=120.585)

        self.assertEqual(result["province"], "江苏省")
        self.assertEqual(result["city"], "苏州市")
        self.assertEqual(result["provider"], "fallback")

    def test_intercity_train_route_returns_estimated_steps(self):
        with patch.object(map_provider_service, "_record_map_log"):
            result = map_provider_service.route("120.585,31.299", "120.155,30.274", "train")

        self.assertEqual(result["mode"], "train")
        self.assertEqual(result["source"], "规则估算")
        self.assertGreater(result["distance_km"], 0)
        self.assertIn("高铁", result["steps"][0])

    def test_amap_empty_driving_route_falls_back_to_estimate(self):
        payload = {"route": {"paths": [{"distance": "0", "duration": "0", "steps": []}]}}

        with patch.object(map_provider_service, "get_secret", return_value="amap-key"):
            with patch.object(map_provider_service, "get_provider_config", return_value={"enabled": 1}):
                with patch.object(map_provider_service, "_http_json", return_value=payload):
                    with patch.object(map_provider_service, "_record_map_log"):
                        result = map_provider_service.route("120.585,31.299", "120.1417,30.2428", "driving")

        self.assertEqual(result["provider"], "fallback")
        self.assertGreater(result["distance_km"], 0)
        self.assertGreater(result["duration_minutes"], 0)


if __name__ == "__main__":
    unittest.main()
