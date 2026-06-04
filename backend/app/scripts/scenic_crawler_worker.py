import json
import sys

from app.services.scenic_crawler_enrichment_service import _run_job


def main():
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    _run_job(payload)


if __name__ == "__main__":
    main()
