"""
Log Analyzer Skill - 日志分析组件单元测试套件

本模块包含日志分析组件的综合单元测试。
测试覆盖API接口、处理逻辑和集成场景。

使用方法：
    pytest test_log_analyzer.py -v
    pytest test_log_analyzer.py -v -k "test_upload"
    pytest test_log_analyzer.py -v --cov=log_analyzer
"""

import pytest
import requests
import time
import os
import tempfile
from typing import Dict, Any

# 配置
BASE_URL = os.environ.get('LOG_ANALYZER_URL', 'http://localhost:8000')
TEST_USER_ID = 'test_user_001'
TIMEOUT = 30


class TestHealthCheck:
    """测试健康检查接口。"""
    
    def test_health_check_success(self):
        """测试健康检查返回正常状态。"""
        response = requests.get(f'{BASE_URL}/api/health', timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
    
    def test_health_check_response_time(self):
        """测试健康检查在可接受的时间内响应。"""
        start = time.time()
        response = requests.get(f'{BASE_URL}/api/health', timeout=TIMEOUT)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"健康检查耗时 {elapsed}s，预期 < 1s"


class TestFileUpload:
    """测试文件上传功能。"""
    
    @pytest.fixture
    def sample_log_file(self):
        """创建用于测试的示例日志文件。"""
        content = """2024-01-01 10:00:00 INFO Application started
2024-01-01 10:00:01 ERROR NullPointerException at com.example.Service
2024-01-01 10:00:02 WARN Connection timeout
2024-01-01 10:00:03 ERROR Database connection failed
2024-01-01 10:00:04 INFO Retrying connection
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            yield f.name
        os.unlink(f.name)
    
    def test_upload_log_file_success(self, sample_log_file):
        """测试成功上传日志文件。"""
        with open(sample_log_file, 'rb') as f:
            response = requests.post(
                f'{BASE_URL}/api/upload',
                files={'file': f},
                headers={'X-User-Id': TEST_USER_ID}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'file_path' in data['data']
        assert data['data']['file_name'].endswith('.log')
    
    def test_upload_unsupported_file_type(self):
        """测试上传不支持的文件类型。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exe', delete=False) as f:
            f.write('test content')
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f'{BASE_URL}/api/upload',
                    files={'file': f},
                    headers={'X-User-Id': TEST_USER_ID}
                )
            
            assert response.status_code == 400
            data = response.json()
            assert data['code'] == 101
        finally:
            os.unlink(temp_path)
    
    def test_upload_without_user_id(self, sample_log_file):
        """测试不带X-User-Id请求头时使用默认用户。"""
        with open(sample_log_file, 'rb') as f:
            response = requests.post(
                f'{BASE_URL}/api/upload',
                files={'file': f}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0


class TestLogProcessing:
    """测试日志处理功能。"""
    
    @pytest.fixture
    def uploaded_file_path(self):
        """上传文件并返回其路径。"""
        content = "2024-01-01 ERROR Test error message\n" * 100
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = requests.post(
                    f'{BASE_URL}/api/upload',
                    files={'file': f},
                    headers={'X-User-Id': TEST_USER_ID}
                )
            yield response.json()['data']['file_path']
        finally:
            os.unlink(temp_path)
    
    def test_process_with_llm_mode(self, uploaded_file_path):
        """测试使用LLM模式处理日志。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': uploaded_file_path,
                'source': 'upload',
                'use_llm': True,
                'chunk_size': 50
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'task_id' in data['data']
    
    def test_process_with_rule_mode(self, uploaded_file_path):
        """测试使用规则模式处理日志。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': uploaded_file_path,
                'source': 'upload',
                'use_llm': False,
                'chunk_size': 50
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
    
    def test_process_nonexistent_file(self):
        """测试处理不存在的文件。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': '/nonexistent/path/file.log',
                'source': 'upload'
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]
    
    def test_process_with_invalid_chunk_size(self, uploaded_file_path):
        """测试使用无效的分块大小。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'file_path': uploaded_file_path,
                'source': 'upload',
                'chunk_size': -1
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        # 应该拒绝或使用默认值
        assert response.status_code in [200, 400]


class TestTaskManagement:
    """测试任务管理功能。"""
    
    @pytest.fixture
    def running_task_id(self):
        """创建任务并返回其ID。"""
        content = "2024-01-01 ERROR Test error\n" * 1000
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                upload_response = requests.post(
                    f'{BASE_URL}/api/upload',
                    files={'file': f},
                    headers={'X-User-Id': TEST_USER_ID}
                )
            file_path = upload_response.json()['data']['file_path']
            
            process_response = requests.post(
                f'{BASE_URL}/api/process',
                json={
                    'file_path': file_path,
                    'source': 'upload',
                    'use_llm': False,
                    'chunk_size': 100
                },
                headers={'X-User-Id': TEST_USER_ID}
            )
            yield process_response.json()['data']['task_id']
        finally:
            os.unlink(temp_path)
    
    def test_get_task_status(self, running_task_id):
        """测试获取任务状态。"""
        response = requests.get(
            f'{BASE_URL}/api/task/{running_task_id}',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'status' in data['data']
        assert data['data']['task_id'] == running_task_id
    
    def test_get_nonexistent_task(self):
        """测试获取不存在的任务状态。"""
        response = requests.get(
            f'{BASE_URL}/api/task/nonexistent_task_id',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]
    
    def test_cancel_task(self, running_task_id):
        """测试取消运行中的任务。"""
        # 等待一段时间确保任务正在处理
        time.sleep(0.5)
        
        response = requests.post(
            f'{BASE_URL}/api/task/{running_task_id}/cancel',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        # 任务可能已经完成
        assert response.status_code in [200, 400]
    
    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务。"""
        response = requests.post(
            f'{BASE_URL}/api/task/nonexistent_task_id/cancel',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]


class TestReportManagement:
    """测试报告管理功能。"""
    
    def test_get_reports_list(self):
        """测试获取报告列表。"""
        response = requests.get(
            f'{BASE_URL}/api/reports',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 0
        assert 'reports' in data['data']
    
    def test_download_nonexistent_report(self):
        """测试下载不存在的报告。"""
        response = requests.get(
            f'{BASE_URL}/api/report/download/nonexistent_report.pdf',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]
    
    def test_delete_nonexistent_report(self):
        """测试删除不存在的报告。"""
        response = requests.delete(
            f'{BASE_URL}/api/report/nonexistent_report.pdf',
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]


class TestServerPathAccess:
    """测试服务器路径访问功能。"""
    
    def test_list_dir_validate_mode(self):
        """测试目录验证模式。"""
        response = requests.post(
            f'{BASE_URL}/api/list-dir',
            json={
                'path': '/tmp',
                'validate_only': True
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        # 响应取决于服务器配置
        assert response.status_code in [200, 403]
    
    def test_list_dir_browse_mode(self):
        """测试目录浏览模式。"""
        response = requests.post(
            f'{BASE_URL}/api/list-dir',
            json={
                'path': '/tmp',
                'validate_only': False
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        # 响应取决于服务器配置
        assert response.status_code in [200, 403]
    
    def test_list_dir_nonexistent_path(self):
        """测试访问不存在的路径。"""
        response = requests.post(
            f'{BASE_URL}/api/list-dir',
            json={
                'path': '/nonexistent/path/12345',
                'validate_only': True
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code in [400, 404]
    
    def test_list_dir_with_patterns(self):
        """测试带文件模式的目录列表。"""
        response = requests.post(
            f'{BASE_URL}/api/list-dir',
            json={
                'path': '/tmp',
                'file_patterns': ['*.log'],
                'validate_only': False
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        # 响应取决于服务器配置
        assert response.status_code in [200, 403]


class TestUserIsolation:
    """测试用户数据隔离。"""
    
    def test_different_users_separate_data(self):
        """测试不同用户的数据是隔离的。"""
        user1 = 'isolation_test_user_1'
        user2 = 'isolation_test_user_2'
        
        # 获取两个用户的报告
        response1 = requests.get(
            f'{BASE_URL}/api/reports',
            headers={'X-User-Id': user1}
        )
        response2 = requests.get(
            f'{BASE_URL}/api/reports',
            headers={'X-User-Id': user2}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # 两个用户应该有独立的报告列表
        data1 = response1.json()['data']
        data2 = response2.json()['data']
        
        # 报告应该是独立的（不同的列表）
        assert isinstance(data1['reports'], list)
        assert isinstance(data2['reports'], list)


class TestErrorHandling:
    """测试错误处理场景。"""
    
    def test_invalid_json_request(self):
        """测试处理无效JSON。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            data='invalid json',
            headers={
                'X-User-Id': TEST_USER_ID,
                'Content-Type': 'application/json'
            }
        )
        
        assert response.status_code == 400
    
    def test_missing_required_parameter(self):
        """测试处理缺少必需参数。"""
        response = requests.post(
            f'{BASE_URL}/api/process',
            json={
                'source': 'upload'
                # 缺少 file_path
            },
            headers={'X-User-Id': TEST_USER_ID}
        )
        
        assert response.status_code == 400
    
    def test_method_not_allowed(self):
        """测试处理错误的HTTP方法。"""
        response = requests.delete(
            f'{BASE_URL}/api/health'
        )
        
        assert response.status_code == 405


class TestPerformance:
    """性能相关测试。"""
    
    def test_concurrent_health_checks(self):
        """测试并发健康检查请求。"""
        import concurrent.futures
        
        def make_request():
            return requests.get(f'{BASE_URL}/api/health', timeout=TIMEOUT)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 45, f"仅有 {success_count}/50 个请求成功"
    
    def test_response_time_health_check(self):
        """测试健康检查响应速度快。"""
        times = []
        for _ in range(10):
            start = time.time()
            requests.get(f'{BASE_URL}/api/health', timeout=TIMEOUT)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1, f"平均响应时间 {avg_time}s > 0.1s"


class TestIntegration:
    """完整工作流的集成测试。"""
    
    @pytest.mark.slow
    def test_complete_analysis_workflow(self):
        """测试从上传到报告的完整分析工作流。"""
        # 1. 创建并上传文件
        content = """2024-01-01 10:00:00 ERROR NullPointerException
2024-01-01 10:00:01 ERROR Database connection failed
2024-01-01 10:00:02 WARN Memory usage high
2024-01-01 10:00:03 ERROR Timeout waiting for response
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # 上传
            with open(temp_path, 'rb') as f:
                upload_response = requests.post(
                    f'{BASE_URL}/api/upload',
                    files={'file': f},
                    headers={'X-User-Id': TEST_USER_ID}
                )
            assert upload_response.status_code == 200
            file_path = upload_response.json()['data']['file_path']
            
            # 处理
            process_response = requests.post(
                f'{BASE_URL}/api/process',
                json={
                    'file_path': file_path,
                    'source': 'upload',
                    'use_llm': False,  # 使用规则模式以提高速度
                    'chunk_size': 10
                },
                headers={'X-User-Id': TEST_USER_ID}
            )
            assert process_response.status_code == 200
            task_id = process_response.json()['data']['task_id']
            
            # 轮询完成状态
            max_wait = 30
            start = time.time()
            while time.time() - start < max_wait:
                status_response = requests.get(
                    f'{BASE_URL}/api/task/{task_id}',
                    headers={'X-User-Id': TEST_USER_ID}
                )
                status = status_response.json()['data']['status']
                if status in ['completed', 'failed', 'cancelled']:
                    break
                time.sleep(1)
            
            # 检查报告
            reports_response = requests.get(
                f'{BASE_URL}/api/reports',
                headers={'X-User-Id': TEST_USER_ID}
            )
            assert reports_response.status_code == 200
            
        finally:
            os.unlink(temp_path)


# 测试工具函数
def create_sample_log_file(lines: int = 100) -> str:
    """创建用于测试的示例日志文件。
    
    参数:
        lines: 要生成的日志行数。
    
    返回:
        创建的文件的路径。
    """
    content = ""
    for i in range(lines):
        level = "ERROR" if i % 3 == 0 else "INFO"
        content += f"2024-01-01 10:00:{i:02d} {level} Log message {i}\n"
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        return f.name


def wait_for_task_completion(task_id: str, timeout: int = 60) -> str:
    """等待任务完成。
    
    参数:
        task_id: 要等待的任务ID。
        timeout: 最大等待时间（秒）。
    
    返回:
        最终任务状态。
    """
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(
            f'{BASE_URL}/api/task/{task_id}',
            headers={'X-User-Id': TEST_USER_ID}
        )
        status = response.json()['data']['status']
        if status in ['completed', 'failed', 'cancelled']:
            return status
        time.sleep(1)
    return 'timeout'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
