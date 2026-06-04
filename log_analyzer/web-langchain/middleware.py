
"""
中间件模块 - 并发控制等中间件
"""
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse


class ConcurrencyLimitMiddleware(BaseHTTPMiddleware):
    """
    并发限流中间件 - 使用信号量控制最大并发请求数
    
    功能：
    - 限制同时处理的最大请求数量
    - 防止服务器过载
    - 提供超时等待机制
    """
    
    def __init__(self, app, max_concurrent: int = 200):
        """
        初始化中间件
        
        Args:
            app: FastAPI应用
            max_concurrent: 最大并发请求数
        """
        super().__init__(app)
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_requests = 0
        self.max_concurrent = max_concurrent
        self._lock = asyncio.Lock()
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求
        
        Args:
            request: 请求对象
            call_next: 下一个处理函数
        
        Returns:
            响应对象
        """
        try:
            # 等待获取信号量，超时30秒
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            # 超时返回503
            return JSONResponse(
                status_code=503,
                content={"detail": "Server is busy, please retry later"}
            )
        
        try:
            # 更新活跃请求计数
            async with self._lock:
                self.active_requests += 1
            
            # 处理请求
            response = await call_next(request)
            
            # 添加活跃请求头
            response.headers["X-Active-Requests"] = str(self.active_requests)
            
            return response
        finally:
            # 减少活跃请求计数并释放信号量
            async with self._lock:
                self.active_requests -= 1
            self.semaphore.release()

