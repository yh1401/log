#!/usr/bin/env python3
"""
并发性能评估测试脚本（使用标准库）

功能：
1. 测试服务的并发处理能力
2. 测试QPS（每秒查询率）
3. 识别并发问题
4. 性能瓶颈分析
"""

import asyncio
import urllib.request
import urllib.error
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import statistics
import concurrent.futures
import threading


class ConcurrencyTester:
    """并发性能测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()

    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        headers: Dict = None,
        request_id: int = 0
    ) -> Dict[str, Any]:
        """发送单个请求并记录结果"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {}

        # 添加用户认证头
        headers["X-User-Id"] = f"test_user_{request_id % 10}"
        headers["X-User_Name"] = f"test_user_{request_id % 10}"

        start_time = time.time()
        result = {
            "request_id": request_id,
            "endpoint": endpoint,
            "method": method,
            "start_time": start_time,
            "status": None,
            "response_time": None,
            "error": None
        }

        try:
            # 创建请求
            req_data = None
            if data:
                req_data = json.dumps(data).encode('utf-8')
                headers['Content-Type'] = 'application/json'

            request = urllib.request.Request(
                url,
                data=req_data,
                headers=headers,
                method=method
            )

            # 发送请求
            with urllib.request.urlopen(request, timeout=30) as response:
                result["status"] = response.status
                result["response_time"] = time.time() - start_time

        except urllib.error.HTTPError as e:
            result["status"] = e.code
            result["response_time"] = time.time() - start_time
            result["error"] = str(e)
        except urllib.error.URLError as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time
        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time

        return result

    def test_concurrent_requests(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        method: str = "GET",
        data: Dict = None
    ) -> List[Dict]:
        """测试并发请求"""
        print(f"\n测试端点: {endpoint}")
        print(f"总请求数: {num_requests}, 并发数: {concurrency}")

        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = []
            for i in range(num_requests):
                future = executor.submit(
                    self.make_request,
                    endpoint,
                    method,
                    data,
                    request_id=i
                )
                futures.append(future)

            start_time = time.time()
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "status": None,
                        "response_time": None,
                        "error": str(e)
                    })

            total_time = time.time() - start_time

        # 计算统计数据
        successful_requests = [r for r in results if r.get("status") == 200]
        failed_requests = [r for r in results if r.get("status") != 200]

        # 打印失败请求的错误信息（前5个）
        if failed_requests:
            print(f"\n失败请求示例（前5个）:")
            for i, req in enumerate(failed_requests[:5]):
                print(f"  [{i+1}] 状态码: {req.get('status')}, 错误: {req.get('error')}")

        response_times = [r["response_time"] for r in successful_requests if r.get("response_time")]

        if response_times:
            stats = {
                "endpoint": endpoint,
                "total_requests": num_requests,
                "concurrency": concurrency,
                "total_time": total_time,
                "successful": len(successful_requests),
                "failed": len(failed_requests),
                "qps": len(successful_requests) / total_time if total_time > 0 else 0,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "median_response_time": statistics.median(response_times) if response_times else 0,
                "p95_response_time": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) >= 20 else 0,
                "p99_response_time": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) >= 100 else 0,
            }
        else:
            stats = {
                "endpoint": endpoint,
                "total_requests": num_requests,
                "concurrency": concurrency,
                "total_time": total_time,
                "successful": 0,
                "failed": len(failed_requests),
                "qps": 0,
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "median_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
            }

        with self.lock:
            self.results.append(stats)

        return results

    def print_stats(self, stats: Dict):
        """打印统计信息"""
        print("\n" + "="*80)
        print(f"测试结果统计")
        print("="*80)
        print(f"端点: {stats['endpoint']}")
        print(f"总请求数: {stats['total_requests']}")
        print(f"并发数: {stats['concurrency']}")
        print(f"总耗时: {stats['total_time']:.3f}秒")
        print(f"成功请求: {stats['successful']}")
        print(f"失败请求: {stats['failed']}")
        print(f"QPS: {stats['qps']:.2f} 请求/秒")
        print(f"\n响应时间统计:")
        print(f"  平均: {stats['avg_response_time']*1000:.2f}ms")
        print(f"  最小: {stats['min_response_time']*1000:.2f}ms")
        print(f"  最大: {stats['max_response_time']*1000:.2f}ms")
        print(f"  中位数: {stats['median_response_time']*1000:.2f}ms")
        print(f"  P95: {stats['p95_response_time']*1000:.2f}ms")
        print(f"  P99: {stats['p99_response_time']*1000:.2f}ms")
        print("="*80)

    def generate_report(self, output_file: str = "concurrency_test_report.md"):
        """生成测试报告"""
        report_path = Path(__file__).parent / output_file

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 并发性能测试报告\n\n")
            f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 测试概览\n\n")
            f.write("| 端点 | 总请求数 | 并发数 | QPS | 平均响应时间(ms) | P95(ms) | P99(ms) | 成功率 |\n")
            f.write("|------|---------|--------|-----|----------------|---------|---------|--------|\n")

            for stats in self.results:
                success_rate = (stats['successful'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
                f.write(f"| {stats['endpoint']} | {stats['total_requests']} | {stats['concurrency']} | "
                       f"{stats['qps']:.2f} | {stats['avg_response_time']*1000:.2f} | "
                       f"{stats['p95_response_time']*1000:.2f} | {stats['p99_response_time']*1000:.2f} | "
                       f"{success_rate:.1f}% |\n")

            f.write("\n## 性能分析\n\n")

            # 找出最佳性能
            best_qps = max(self.results, key=lambda x: x['qps'])
            f.write(f"**最高QPS**: {best_qps['qps']:.2f} (端点: {best_qps['endpoint']})\n\n")

            # 找出最慢响应
            slowest = max(self.results, key=lambda x: x['avg_response_time'])
            f.write(f"**最慢响应**: {slowest['avg_response_time']*1000:.2f}ms (端点: {slowest['endpoint']})\n\n")

            f.write("## 并发问题识别\n\n")
            f.write("### 潜在问题\n\n")
            f.write("1. **全局状态竞争**: `processing_tasks` 字典在多线程环境下无锁保护\n")
            f.write("2. **文件写入冲突**: 多个任务同时写入JSON文件可能导致数据损坏\n")
            f.write("3. **用户数据竞争**: `users.json` 文件并发读写无同步机制\n")
            f.write("4. **任务状态不一致**: 任务状态更新和检查存在竞争条件\n\n")

            f.write("## 优化建议\n\n")
            f.write("### 短期优化\n\n")
            f.write("1. 添加线程锁保护全局状态\n")
            f.write("2. 使用文件锁保护文件写入操作\n")
            f.write("3. 实现任务队列管理机制\n\n")

            f.write("### 长期优化\n\n")
            f.write("1. 使用Redis替代内存字典存储任务状态\n")
            f.write("2. 使用数据库替代文件存储\n")
            f.write("3. 实现分布式任务队列（Celery）\n")
            f.write("4. 添加限流和熔断机制\n")

        print(f"\n测试报告已生成: {report_path}")
        return report_path


def main():
    """主测试函数"""
    tester = ConcurrencyTester()

    print("="*80)
    print("开始并发性能测试")
    print("="*80)

    # 测试1: 健康检查端点（轻量级）
    print("\n[测试1] 健康检查端点 - 基准测试")
    results = tester.test_concurrent_requests(
        endpoint="/api/health",
        num_requests=100,
        concurrency=10
    )
    tester.print_stats(tester.results[-1])

    # 测试2: 用户认证端点
    print("\n[测试2] 用户认证端点 - 中等负载")
    results = tester.test_concurrent_requests(
        endpoint="/api/auth/current",
        num_requests=100,
        concurrency=20
    )
    tester.print_stats(tester.results[-1])

    # 测试3: 报告列表端点
    print("\n[测试3] 报告列表端点 - 文件I/O测试")
    results = tester.test_concurrent_requests(
        endpoint="/api/reports",
        num_requests=50,
        concurrency=10
    )
    tester.print_stats(tester.results[-1])

    # 测试4: 高并发测试
    print("\n[测试4] 高并发测试 - 压力测试")
    results = tester.test_concurrent_requests(
        endpoint="/api/health",
        num_requests=500,
        concurrency=50
    )
    tester.print_stats(tester.results[-1])

    # 测试5: 极限并发测试
    print("\n[测试5] 极限并发测试 - 寻找瓶颈")
    results = tester.test_concurrent_requests(
        endpoint="/api/health",
        num_requests=1000,
        concurrency=100
    )
    tester.print_stats(tester.results[-1])

    # 生成报告
    tester.generate_report()

    print("\n" + "="*80)
    print("测试完成!")
    print("="*80)


if __name__ == "__main__":
    main()
