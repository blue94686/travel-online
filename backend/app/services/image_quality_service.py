"""Image quality check service using Pillow for basic validation."""
import os
from pathlib import Path

MIN_WIDTH = 400
MIN_HEIGHT = 300
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


def check_image(file_path: str) -> dict:
    """Run quality checks on an uploaded image file.

    Returns dict with pass/warn/reject status and reasons.
    """
    result = {"status": "pass", "checks": [], "reasons": []}

    if not os.path.exists(file_path):
        result["status"] = "reject"
        result["reasons"].append("文件不存在")
        return result

    # File size check
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        result["status"] = "reject"
        result["reasons"].append(f"文件过大 ({file_size / 1024 / 1024:.1f}MB > 10MB)")
    elif file_size < 1024:
        result["status"] = "warn"
        result["reasons"].append("文件过小，可能不是有效图片")
    result["checks"].append({"name": "文件大小", "value": f"{file_size / 1024:.0f}KB", "pass": file_size <= MAX_FILE_SIZE})

    # Try Pillow checks
    try:
        from PIL import Image
        img = Image.open(file_path)

        # Format check
        fmt = img.format
        fmt_ok = fmt in ALLOWED_FORMATS
        result["checks"].append({"name": "图片格式", "value": fmt, "pass": fmt_ok})
        if not fmt_ok:
            result["status"] = "reject"
            result["reasons"].append(f"不支持的格式: {fmt}")

        # Resolution check
        w, h = img.size
        res_ok = w >= MIN_WIDTH and h >= MIN_HEIGHT
        result["checks"].append({"name": "分辨率", "value": f"{w}x{h}", "pass": res_ok})
        if not res_ok:
            if result["status"] != "reject":
                result["status"] = "warn"
            result["reasons"].append(f"分辨率偏低 ({w}x{h}，最低 {MIN_WIDTH}x{MIN_HEIGHT})")

        # Color distribution check (detect solid-color images)
        try:
            extrema = img.getextrema()
            if isinstance(extrema, tuple) and len(extrema) > 0:
                is_solid = all(
                    (channel[1] - channel[0]) < 10
                    for channel in extrema
                    if isinstance(channel, tuple) and len(channel) == 2
                )
                result["checks"].append({"name": "色彩分布", "value": "正常" if not is_solid else "纯色图", "pass": not is_solid})
                if is_solid:
                    if result["status"] != "reject":
                        result["status"] = "warn"
                    result["reasons"].append("疑似纯色或异常图片")
        except Exception:
            pass

        img.close()
    except ImportError:
        result["checks"].append({"name": "Pillow", "value": "未安装", "pass": True})
    except Exception as e:
        result["status"] = "warn"
        result["reasons"].append(f"图片解析异常: {str(e)}")
        result["checks"].append({"name": "解析", "value": str(e)[:50], "pass": False})

    return result


def check_image_url(url: str) -> dict:
    """Basic URL validation for remote images."""
    result = {"status": "pass", "checks": [], "reasons": []}
    if not url:
        result["status"] = "reject"
        result["reasons"].append("URL 为空")
        return result
    if not url.startswith(("http://", "https://")):
        result["status"] = "warn"
        result["reasons"].append("非标准 URL")
    result["checks"].append({"name": "URL 格式", "value": "有效", "pass": True})
    return result
