"""
StealthMark API Concurrency Test
多线程并发压测脚本，验证 API 在高并发下的稳定性
"""
import os
import sys
import time
import json
import tempfile
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] requests library not found. Install with: pip install requests")
    sys.exit(1)


DEFAULT_API_URL = "http://127.0.0.1:8001"
TEST_IMAGE = r"D:\work\code\stealthmark\tests\fixtures\test.png"


def parse_args():
    parser = argparse.ArgumentParser(description="StealthMark API Concurrency Test")
    parser.add_argument("--url", default=DEFAULT_API_URL, help=f"API base URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--workers", type=int, default=20, help="Number of concurrent workers (default: 20)")
    parser.add_argument("--total", type=int, default=200, help="Total number of requests (default: 200)")
    parser.add_argument("--test-image", default=TEST_IMAGE, help="Path to test image file")
    return parser.parse_args()


class ResultTracker:
    """线程安全的结果收集器"""
    def __init__(self):
        self.results = []
        self.lock_count = 0  # 统计锁争用次数
        self._lock = __import__('threading').Lock()

    def add(self, success, elapsed, error=None):
        with self._lock:
            self.results.append({
                "success": success,
                "elapsed": elapsed,
                "error": error,
                "thread_id": __import__('threading').get_ident()
            })

    def get_stats(self):
        total = len(self.results)
        success = sum(1 for r in self.results if r["success"])
        failed = total - success
        elapsed_list = [r["elapsed"] for r in self.results]
        avg_elapsed = sum(elapsed_list) / total if total else 0
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "error_rate": f"{failed / total * 100:.1f}%" if total else "0%",
            "avg_elapsed_ms": f"{avg_elapsed * 1000:.1f}",
            "min_ms": f"{min(elapsed_list) * 1000:.1f}" if elapsed_list else "0",
            "max_ms": f"{max(elapsed_list) * 1000:.1f}" if elapsed_list else "0",
        }


def test_embed(worker_id, api_url, image_path, tracker):
    """单次 embed 请求"""
    start = time.time()
    try:
        with open(image_path, "rb") as f:
            files = {"file": ("test.png", f, "image/png")}
            data = {
                "watermark": json.dumps({
                    "v": 1,
                    "type": "copyright",
                    "issuer": f"did:example:worker-{worker_id}",
                    "timestamp": "2026-05-05T12:00:00Z",
                    "payload": f"concurrency-test-{worker_id}",
                    "nonce": f"{worker_id:08x}"
                })
            }
            resp = requests.post(f"{api_url}/embed", files=files, data=data, timeout=30)
            elapsed = time.time() - start
            if resp.status_code == 200:
                tracker.add(True, elapsed)
                return resp.json()
            else:
                tracker.add(False, elapsed, f"HTTP {resp.status_code}: {resp.text[:100]}")
                return None
    except Exception as e:
        elapsed = time.time() - start
        tracker.add(False, elapsed, str(e)[:100])
        return None


def test_extract(worker_id, api_url, image_path, tracker):
    """单次 extract 请求"""
    start = time.time()
    try:
        with open(image_path, "rb") as f:
            files = {"file": ("test.png", f, "image/png")}
            resp = requests.post(f"{api_url}/extract", files=files, timeout=30)
            elapsed = time.time() - start
            if resp.status_code == 200:
                result = resp.json()
                tracker.add(True, elapsed)
                return result
            else:
                tracker.add(False, elapsed, f"HTTP {resp.status_code}")
                return None
    except Exception as e:
        elapsed = time.time() - start
        tracker.add(False, elapsed, str(e)[:100])
        return None


def run_concurrency_test(api_url, workers, total_requests, test_image):
    """运行并发测试"""
    print(f"\n{'='*60}")
    print(f"  StealthMark API Concurrency Test")
    print(f"{'='*60}")
    print(f"  API URL   : {api_url}")
    print(f"  Workers   : {workers}")
    print(f"  Total Req : {total_requests}")
    print(f"  Test File : {test_image}")
    print(f"{'='*60}\n")

    # 检查测试文件
    if not os.path.exists(test_image):
        print(f"[ERROR] Test file not found: {test_image}")
        return

    # 检查 API 健康
    try:
        resp = requests.get(f"{api_url}/health", timeout=5)
        print(f"[OK] API health check: {resp.status_code}")
    except Exception as e:
        print(f"[WARN] API health check failed: {e}")
        print(f"       Will try anyway...\n")

    tracker = ResultTracker()

    # 阶段1：并发 embed
    print(f"[Phase 1] Running {total_requests} concurrent embed requests...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(test_embed, i, api_url, test_image, tracker)
            for i in range(total_requests)
        ]
        done = 0
        for f in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  progress: {done}/{total_requests}")
    t1 = time.time()

    embed_stats = tracker.get_stats()
    print(f"\n[Embed Results]")
    print(f"  Total    : {embed_stats['total']}")
    print(f"  Success  : {embed_stats['success']}")
    print(f"  Failed   : {embed_stats['failed']}")
    print(f"  Error Rate: {embed_stats['error_rate']}")
    print(f"  Avg Time : {embed_stats['avg_elapsed_ms']} ms")
    print(f"  Min/Max  : {embed_stats['min_ms']} / {embed_stats['max_ms']} ms")
    print(f"  Duration : {(t1 - t0):.1f}s")
    print(f"  QPS      : {total_requests / (t1 - t0):.1f} req/s")

    # 阶段2：并发 extract（仅测试有水印的文件）
    print(f"\n[Phase 2] Running {total_requests} concurrent extract requests...")
    tracker2 = ResultTracker()
    t2 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(test_extract, i, api_url, test_image, tracker2)
            for i in range(total_requests)
        ]
        done = 0
        for f in as_completed(futures):
            done += 1
            if done % 50 == 0:
                print(f"  progress: {done}/{total_requests}")
    t3 = time.time()

    extract_stats = tracker2.get_stats()
    print(f"\n[Extract Results]")
    print(f"  Total    : {extract_stats['total']}")
    print(f"  Success  : {extract_stats['success']}")
    print(f"  Failed   : {extract_stats['failed']}")
    print(f"  Error Rate: {extract_stats['error_rate']}")
    print(f"  Avg Time : {extract_stats['avg_elapsed_ms']} ms")
    print(f"  Min/Max  : {extract_stats['min_ms']} / {extract_stats['max_ms']} ms")
    print(f"  Duration : {(t3 - t2):.1f}s")
    print(f"  QPS      : {total_requests / (t3 - t2):.1f} req/s")

    # 汇总
    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"{'='*60}")
    print(f"  Embed  - Success: {embed_stats['success']}/{embed_stats['total']}, Error Rate: {embed_stats['error_rate']}")
    print(f"  Extract- Success: {extract_stats['success']}/{extract_stats['total']}, Error Rate: {extract_stats['error_rate']}")

    total_time = (t1 - t0) + (t3 - t2)
    total_qps = (total_requests * 2) / total_time
    print(f"  Total Time: {total_time:.1f}s, Combined QPS: {total_qps:.1f} req/s")

    # 检查错误
    failed_embed = [r for r in tracker.results if not r["success"]]
    if failed_embed:
        print(f"\n[ERROR] Embed failed samples (first 5):")
        for r in failed_embed[:5]:
            print(f"  - {r['error']}")

    failed_extract = [r for r in tracker2.results if not r["success"]]
    if failed_extract:
        print(f"\n[ERROR] Extract failed samples (first 5):")
        for r in failed_extract[:5]:
            print(f"  - {r['error']}")

    # 判断结论
    if embed_stats['error_rate'] == "0.0%" and extract_stats['error_rate'] == "0.0%":
        print(f"\n[PASS] All requests succeeded. No race conditions detected.")
    else:
        print(f"\n[FAIL] Some requests failed. Check errors above.")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    args = parse_args()
    run_concurrency_test(args.url, args.workers, args.total, args.test_image)