"""
Log Analyzer Skill - 示例代码集合

本文件包含使用日志分析组件的实用示例。
每个示例演示了一个特定的使用场景或集成模式。

前置条件：
    pip install requests
"""

import requests
import time
import os
from typing import Optional, Dict, Any

# 配置
BASE_URL = os.environ.get('LOG_ANALYZER_URL', 'http://localhost:8000')
USER_ID = 'example_user'


# ============================================================================
# 基础示例
# ============================================================================

def example_1_simple_upload_and_analyze():
    """
    示例1：简单的文件上传和分析
    
    这是最基本的工作流：上传日志文件并进行分析。
    """
    print("\n=== 示例1：简单上传和分析 ===")
    
    # 步骤1：上传文件
    log_file = 'sample.log'
    
    with open(log_file, 'rb') as f:
        response = requests.post(
            f'{BASE_URL}/api/upload',
            files={'file': f},
            headers={'X-User-Id': USER_ID}
        )
    
    if response.status_code != 200:
        print(f"上传失败：{response.text}")
        return
    
    file_path = response.json()['data']['file_path']
    print(f"文件已上传至：{file_path}")
    
    # 步骤2：开始分析
    response = requests.post(
        f'{BASE_URL}/api/process',
        json={
            'file_path': file_path,
            'source': 'upload',
            'use_llm': True
        },
        headers={'X-User-Id': USER_ID}
    )
    
    task_id = response.json()['data']['task_id']
    print(f"任务已创建：{task_id}")
    
    # 步骤3：等待完成
    while True:
        response = requests.get(
            f'{BASE_URL}/api/task/{task_id}',
            headers={'X-User-Id': USER_ID}
        )
        data = response.json()['data']
        status = data['status']
        progress = data.get('progress', 0)
        
        print(f"状态：{status}，进度：{progress}%")
        
        if status in ['completed', 'failed', 'cancelled']:
            break
        
        time.sleep(2)
    
    print(f"分析完成，最终状态：{status}")


def example_2_rule_mode_analysis():
    """
    示例2：基于规则的分析（不需要LLM）
    
    使用规则模式进行快速、免费的分析，无需API调用。
    """
    print("\n=== 示例2：规则模式分析 ===")
    
    # 上传文件
    with open('sample.log', 'rb') as f:
        upload_response = requests.post(
            f'{BASE_URL}/api/upload',
            files={'file': f},
            headers={'X-User-Id': USER_ID}
        )
    
    file_path = upload_response.json()['data']['file_path']
    
    # 使用规则模式处理（use_llm=False）
    response = requests.post(
        f'{BASE_URL}/api/process',
        json={
            'file_path': file_path,
            'source': 'upload',
            'use_llm': False,  # 规则模式
            'chunk_size': 50000
        },
        headers={'X-User-Id': USER_ID}
    )
    
    print(f"规则模式任务：{response.json()['data']['task_id']}")


def example_3_download_reports():
    """
    示例3：下载分析报告
    
    下载各种格式生成的报告。
    """
    print("\n=== 示例3：下载报告 ===")
    
    # 获取报告列表
    response = requests.get(
        f'{BASE_URL}/api/reports',
        headers={'X-User-Id': USER_ID}
    )
    
    reports = response.json()['data']['reports']
    print(f"发现 {len(reports)} 个报告")
    
    # 下载每个报告
    for report in reports[:3]:  # 下载前3个
        report_name = report['name']
        print(f"正在下载：{report_name}")
        
        response = requests.get(
            f'{BASE_URL}/api/report/download/{report_name}',
            headers={'X-User-Id': USER_ID}
        )
        
        if response.status_code == 200:
            with open(f'downloaded_{report_name}', 'wb') as f:
                f.write(response.content)
            print(f"  已保存：downloaded_{report_name}")


# ============================================================================
# 服务器路径示例
# ============================================================================

def example_4_analyze_server_path():
    """
    示例4：分析服务器路径的日志
    
    直接从服务器文件系统读取和分析日志。
    """
    print("\n=== 示例4：服务器路径分析 ===")
    
    # 首先验证路径
    path = '/var/log/nginx'
    
    validate_response = requests.post(
        f'{BASE_URL}/api/list-dir',
        json={
            'path': path,
            'validate_only': True
        },
        headers={'X-User-Id': USER_ID}
    )
    
    if validate_response.status_code == 200:
        print(f"路径 {path} 有效")
        
        # 从服务器路径开始分析
        process_response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': f'{path}/error.log',
                'source': 'server',
                'use_llm': True
            },
            headers={'X-User-Id': USER_ID}
        )
        
        print(f"服务器路径任务：{process_response.json()['data']['task_id']}")
    else:
        print(f"路径验证失败：{validate_response.text}")


def example_5_browse_server_directory():
    """
    示例5：浏览服务器目录
    
    列出服务器目录中的文件。
    """
    print("\n=== 示例5：浏览服务器目录 ===")
    
    response = requests.post(
        f'{BASE_URL}/api/list-dir',
        json={
            'path': '/var/log',
            'validate_only': False,
            'file_patterns': ['*.log']
        },
        headers={'X-User-Id': USER_ID}
    )
    
    if response.status_code == 200:
        data = response.json()['data']
        print(f"当前路径：{data['current_path']}")
        print(f"发现文件：{len(data['files'])} 个")
        
        for file in data['files'][:5]:
            print(f"  - {file['name']} ({file['size_str']})")


# ============================================================================
# 任务管理示例
# ============================================================================

def example_6_cancel_task():
    """
    示例6：取消运行中的任务
    
    停止一个长时间运行的分析任务。
    """
    print("\n=== 示例6：取消任务 ===")
    
    # 先启动一个任务
    with open('large_file.log', 'rb') as f:
        upload_response = requests.post(
            f'{BASE_URL}/api/upload',
            files={'file': f},
            headers={'X-User-Id': USER_ID}
        )
    
    file_path = upload_response.json()['data']['file_path']
    
    process_response = requests.post(
        f'{BASE_URL}/api/process',
        json={
            'file_path': file_path,
            'source': 'upload',
            'use_llm': True
        },
        headers={'X-User-Id': USER_ID}
    )
    
    task_id = process_response.json()['data']['task_id']
    print(f"任务已启动：{task_id}")
    
    # 等待一段时间后取消
    time.sleep(2)
    
    cancel_response = requests.post(
        f'{BASE_URL}/api/task/{task_id}/cancel',
        headers={'X-User-Id': USER_ID}
    )
    
    print(f"取消结果：{cancel_response.json()}")


def example_7_monitor_multiple_tasks():
    """
    示例7：监控多个任务
    
    同时跟踪多个分析任务。
    """
    print("\n=== 示例7：监控多个任务 ===")
    
    # 获取所有任务（通常需要存储任务ID）
    # 此示例展示监控模式
    
    task_ids = ['task_1', 'task_2', 'task_3']  # 示例ID
    
    for task_id in task_ids:
        response = requests.get(
            f'{BASE_URL}/api/task/{task_id}',
            headers={'X-User-Id': USER_ID}
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"任务 {task_id}：{data['status']} ({data.get('progress', 0)}%)")


# ============================================================================
# 集成模式示例
# ============================================================================

class LogAnalyzerClient:
    """
    示例8：可复用的客户端类
    
    用于将日志分析器集成到应用程序中的可复用客户端。
    """
    
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
    
    def upload(self, file_path: str) -> Dict[str, Any]:
        """上传文件。"""
        with open(file_path, 'rb') as f:
            response = requests.post(
                f'{self.base_url}/api/upload',
                files={'file': f},
                headers={'X-User-Id': self.user_id}
            )
        return response.json()
    
    def analyze(self, file_path: str, use_llm: bool = True) -> str:
        """开始分析并返回任务ID。"""
        response = requests.post(
            f'{self.base_url}/api/process',
            json={
                'file_path': file_path,
                'source': 'upload',
                'use_llm': use_llm
            },
            headers={'X-User-Id': self.user_id}
        )
        return response.json()['data']['task_id']
    
    def get_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态。"""
        response = requests.get(
            f'{self.base_url}/api/task/{task_id}',
            headers={'X-User-Id': self.user_id}
        )
        return response.json()['data']
    
    def wait_for_completion(self, task_id: str, timeout: int = 300) -> str:
        """等待任务完成。"""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_status(task_id)['status']
            if status in ['completed', 'failed', 'cancelled']:
                return status
            time.sleep(2)
        return 'timeout'
    
    def get_reports(self) -> list:
        """获取报告列表。"""
        response = requests.get(
            f'{self.base_url}/api/reports',
            headers={'X-User-Id': self.user_id}
        )
        return response.json()['data']['reports']
    
    def download_report(self, report_name: str, output_path: str):
        """下载报告。"""
        response = requests.get(
            f'{self.base_url}/api/report/download/{report_name}',
            headers={'X-User-Id': self.user_id}
        )
        with open(output_path, 'wb') as f:
            f.write(response.content)


def example_8_client_usage():
    """LogAnalyzerClient客户端类的使用示例。"""
    print("\n=== 示例8：客户端类使用 ===")
    
    client = LogAnalyzerClient(BASE_URL, USER_ID)
    
    # 上传并分析
    upload_result = client.upload('sample.log')
    task_id = client.analyze(upload_result['data']['file_path'])
    
    # 等待完成
    final_status = client.wait_for_completion(task_id)
    print(f"任务完成，最终状态：{final_status}")
    
    # 获取报告
    reports = client.get_reports()
    print(f"生成了 {len(reports)} 个报告")


# ============================================================================
# CI/CD集成示例
# ============================================================================

def example_9_ci_pipeline_check():
    """
    示例9：CI/CD流水线集成
    
    分析日志并在发现关键错误时使构建失败。
    """
    print("\n=== 示例9：CI流水线检查 ===")
    
    client = LogAnalyzerClient(BASE_URL, 'ci_pipeline')
    
    # 分析测试日志
    upload_result = client.upload('test_results.log')
    task_id = client.analyze(upload_result['data']['file_path'], use_llm=False)
    
    # 等待完成
    status = client.wait_for_completion(task_id)
    
    if status == 'completed':
        # 检查报告中是否有关键错误
        reports = client.get_reports()
        if reports:
            # 下载并解析报告
            client.download_report(reports[0]['name'], 'ci_report.json')
            
            # 在实际CI中，你会解析报告并做出决定
            print("日志分析完成 - 请查看报告了解详情")
    else:
        print(f"分析失败，状态：{status}")
        # 在CI中，你可能会在这里 exit(1)


# ============================================================================
# 监控集成示例
# ============================================================================

def example_10_alert_webhook():
    """
    示例10：监控告警webhook集成
    
    在告警触发时自动分析相关日志。
    """
    print("\n=== 示例10：告警Webhook集成 ===")
    
    def handle_alert(alert_data: dict):
        """处理传入的告警，分析相关日志。"""
        # 从告警中提取日志路径
        log_path = alert_data.get('log_path', '/var/log/app/error.log')
        
        client = LogAnalyzerClient(BASE_URL, 'monitoring_system')
        
        # 分析日志
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': log_path,
                'source': 'server',
                'use_llm': True
            },
            headers={'X-User-Id': 'monitoring_system'}
        )
        
        if response.status_code == 200:
            task_id = response.json()['data']['task_id']
            print(f"已开始分析告警：{task_id}")
            return task_id
        return None
    
    # 模拟告警
    alert = {
        'alert_name': 'High Error Rate',
        'log_path': '/var/log/app/error.log',
        'severity': 'critical'
    }
    
    task_id = handle_alert(alert)
    print(f"告警已处理，任务ID：{task_id}")


# ============================================================================
# 批量处理示例
# ============================================================================

def example_11_batch_analysis():
    """
    示例11：批量分析多个文件
    
    批量分析多个日志文件。
    """
    print("\n=== 示例11：批量分析 ===")
    
    log_files = ['app1.log', 'app2.log', 'app3.log']
    task_ids = []
    
    client = LogAnalyzerClient(BASE_URL, USER_ID)
    
    # 为每个文件上传并启动分析
    for log_file in log_files:
        if os.path.exists(log_file):
            upload_result = client.upload(log_file)
            task_id = client.analyze(
                upload_result['data']['file_path'],
                use_llm=False  # 使用规则模式以提高速度
            )
            task_ids.append(task_id)
            print(f"开始分析 {log_file}：{task_id}")
    
    # 监控所有任务
    print("\n正在监控任务...")
    for task_id in task_ids:
        status = client.wait_for_completion(task_id, timeout=60)
        print(f"任务 {task_id}：{status}")


# ============================================================================
# 错误处理示例
# ============================================================================

def example_12_error_handling():
    """
    示例12：正确的错误处理
    
    优雅地处理各种错误场景。
    """
    print("\n=== 示例12：错误处理 ===")
    
    try:
        # 尝试上传不存在的文件
        with open('nonexistent.log', 'rb') as f:
            response = requests.post(
                f'{BASE_URL}/api/upload',
                files={'file': f},
                headers={'X-User-Id': USER_ID}
            )
    except FileNotFoundError:
        print("错误：文件不存在")
    
    # 处理API错误
    response = requests.post(
        f'{BASE_URL}/api/process',
        json={'file_path': '/invalid/path'},
        headers={'X-User-Id': USER_ID}
    )
    
    if response.status_code != 200:
        error_data = response.json()
        print(f"API错误：{error_data.get('message', '未知错误')}")
    
    # 处理任务失败
    response = requests.get(
        f'{BASE_URL}/api/task/invalid_task_id',
        headers={'X-User-Id': USER_ID}
    )
    
    if response.status_code == 404:
        print("错误：任务不存在")


# ============================================================================
# 主函数
# ============================================================================

if __name__ == '__main__':
    print("Log Analyzer Skill - 示例代码")
    print("=" * 50)
    print("\n可用示例：")
    print("1. 简单上传和分析")
    print("2. 规则模式分析")
    print("3. 下载报告")
    print("4. 服务器路径分析")
    print("5. 浏览服务器目录")
    print("6. 取消任务")
    print("7. 监控多个任务")
    print("8. 客户端类使用")
    print("9. CI流水线检查")
    print("10. 告警Webhook集成")
    print("11. 批量分析")
    print("12. 错误处理")
    
    # 运行选定的示例
    # 注意：这些需要运行中的日志分析服务器
    
    # 取消注释以运行：
    # example_1_simple_upload_and_analyze()
    # example_2_rule_mode_analysis()
    # example_3_download_reports()
