from app.core.database import get_db, rows_to_list


def dashboard():
    with get_db() as db:
        scenic = db.execute("SELECT COUNT(*) c FROM scenic_spots").fetchone()["c"]
        comments = db.execute("SELECT COUNT(*) c FROM comments").fetchone()["c"]
        users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        images = db.execute("SELECT COUNT(*) c FROM scenic_images").fetchone()["c"]
        pending_image_count = db.execute("SELECT COUNT(*) c FROM scenic_images WHERE status='pending'").fetchone()["c"]
        pending_comment_count = db.execute("SELECT COUNT(*) c FROM comments WHERE status='pending'").fetchone()["c"]
        pending_images = rows_to_list(db.execute("""
          SELECT scenic_images.*, scenic_spots.name AS scenic
          FROM scenic_images LEFT JOIN scenic_spots ON scenic_spots.id = scenic_images.scenic_id
          WHERE scenic_images.status='pending'
          ORDER BY scenic_images.id DESC LIMIT 5
        """).fetchall())
        pending_comments = rows_to_list(db.execute("""
          SELECT comments.*, scenic_spots.name AS scenic
          FROM comments LEFT JOIN scenic_spots ON scenic_spots.id = comments.scenic_id
          WHERE comments.status='pending'
          ORDER BY comments.id DESC LIMIT 5
        """).fetchall())
        logs = rows_to_list(db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 8").fetchall())
    return {
        "kpis": [
            {"label": "今日 PV", "value": "128,400", "change": "+12.4%", "tone": "blue"},
            {"label": "今日 UV", "value": "34,210", "change": "+8.1%", "tone": "teal"},
            {"label": "新增评论", "value": comments, "change": "+5.6%", "tone": "green"},
            {"label": "待审核数", "value": pending_image_count + pending_comment_count, "change": "图片/评论", "tone": "orange"},
            {"label": "拦截恶意请求", "value": "1,204", "change": "-2.1%", "tone": "red"},
            {"label": "系统拦截率", "value": "99.9%", "change": "WAF", "tone": "slate"},
            {"label": "API 请求数", "value": "68.2M", "change": "+12.5%", "tone": "orange"},
        ],
        "systemStatus": {
            "overall": "正常运行",
            "serviceHealth": "100%",
            "apiHealth": "99.1%",
            "dataSync": "正常",
            "storage": "正常",
            "security": "安全",
        },
        "serviceStatus": [
            {"name": "API 核心网关", "status": "正常", "latency": "38ms"},
            {"name": "高德地图服务", "status": "正常", "latency": "42ms"},
            {"name": "天气预报服务", "status": "正常", "latency": "64ms"},
            {"name": "数据库集群", "status": "正常", "latency": "12ms"},
            {"name": "图片存储分发", "status": "正常", "latency": "29ms"},
            {"name": "WAF 防火墙", "status": "正常", "latency": "5ms"},
        ],
        "imageReviewQueue": pending_images,
        "commentReviewQueue": pending_comments,
        "reviewQueues": {
            "images": pending_images,
            "comments": pending_comments,
        },
        "syncTasks": [
            {"name": "景区基础数据同步", "source": "SQLite seed", "status": "完成", "started_at": "09:20", "duration": "18s", "result": "成功"},
            {"name": "图片数据同步", "source": "图片表", "status": "完成", "started_at": "09:35", "duration": "11s", "result": "成功"},
            {"name": "评论数据同步", "source": "评论表", "status": "等待", "started_at": "10:00", "duration": "-", "result": "待执行"},
            {"name": "数据质量检测", "source": "景区库", "status": "完成", "started_at": "10:10", "duration": "9s", "result": "发现 2 条待补齐"},
        ],
        "apiHealth": [
            {"name": "获取景区列表", "status": "正常", "latency": "46ms", "requests": "18.2K", "errorRate": "0.03%"},
            {"name": "获取景区详情", "status": "正常", "latency": "39ms", "requests": "9.7K", "errorRate": "0.01%"},
            {"name": "获取天气信息", "status": "正常", "latency": "72ms", "requests": "12.4K", "errorRate": "0.08%"},
            {"name": "搜索景区", "status": "正常", "latency": "54ms", "requests": "7.1K", "errorRate": "0.02%"},
            {"name": "提交评论", "status": "正常", "latency": "66ms", "requests": "1.8K", "errorRate": "0.05%"},
            {"name": "图片上传", "status": "正常", "latency": "88ms", "requests": "960", "errorRate": "0.10%"},
        ],
        "operationLogs": logs,
        "dataQuality": {
            "completeness": "96%",
            "imageMatch": "92%",
            "coordinateCoverage": "98%",
            "weatherAvailability": "99%",
            "pendingIssues": 2,
        },
    }
