"""LLM client with retry logic and resource optimization."""

import asyncio
import time
import json
import logging
import httpx
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from ..config.settings import LLMConfig


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    CUSTOM = "custom"


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def is_success(self) -> bool:
        return self.error is None and self.content is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'model': self.model,
            'provider': self.provider,
            'tokens_used': self.tokens_used,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'latency_ms': self.latency_ms,
            'error': self.error
        }


@dataclass
class AnalysisResult:
    chunk_id: int
    summary: str
    key_errors: List[Dict[str, Any]] = field(default_factory=list)
    frequency_stats: Dict[str, int] = field(default_factory=dict)
    trends: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    ops_suggestions: List[str] = field(default_factory=list)
    dev_suggestions: List[str] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    root_cause: Dict[str, Any] = field(default_factory=dict)
    causal_chain: Dict[str, Any] = field(default_factory=dict)
    remediation: Dict[str, Any] = field(default_factory=dict)
    response_actions: Dict[str, Any] = field(default_factory=dict)
    evidence_chain: Dict[str, Any] = field(default_factory=dict)
    raw_llm_response: Optional[LLMResponse] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'summary': self.summary,
            'key_errors': self.key_errors,
            'frequency_stats': self.frequency_stats,
            'trends': self.trends,
            'suggestions': self.suggestions,
            'ops_suggestions': self.ops_suggestions,
            'dev_suggestions': self.dev_suggestions,
            'timeline': self.timeline,
            'root_cause': self.root_cause,
            'causal_chain': self.causal_chain,
            'remediation': self.remediation,
            'response_actions': self.response_actions,
            'evidence_chain': self.evidence_chain
        }


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 120.0
    ):
        self.config = config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.provider = self._detect_provider()
        self._session: Optional[httpx.AsyncClient] = None

        logger.info("=" * 80)
        logger.info("LLM Client 初始化完成")
        logger.info(f"  API URL: {self.config.api_url}")
        logger.info(f"  Model: {self.config.model_name}")
        logger.info(f"  Provider: {self.provider.value}")
        logger.info(f"  Max Retries: {self.max_retries}")
        logger.info(f"  Timeout: {self.timeout}s")
        logger.info("=" * 80)

    def _detect_provider(self) -> LLMProvider:
        url = self.config.api_url.lower()
        if 'deepseek' in url:
            return LLMProvider.DEEPSEEK
        elif 'qwen' in url or 'dashscope' in url:
            return LLMProvider.QWEN
        elif 'openai' in url:
            return LLMProvider.OPENAI
        return LLMProvider.CUSTOM

    async def _get_client(self) -> httpx.AsyncClient:
        # 检查并修复事件循环状态
        try:
            loop = asyncio.get_running_loop()
            if loop.is_closed():
                logger.warning("[LLM Client] 检测到事件循环已关闭，重新创建...")
                # 重置会话以强制重新创建
                if self._session and not self._session.is_closed:
                    await self._session.aclose()
                self._session = None
        except RuntimeError:
            # 没有运行中的事件循环，可能需要创建新的
            logger.debug("[LLM Client] 没有运行中的事件循环")
        
        if self._session is None or self._session.is_closed:
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._session

    async def close(self):
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        payload = {
            "model": model or self.config.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if self.provider == LLMProvider.DEEPSEEK:
            payload["max_tokens"] = min(max_tokens, 4096)

        return payload

    async def _make_request(
        self,
        payload: Dict[str, Any]
    ) -> LLMResponse:
        start_time = time.time()
        client = await self._get_client()

        logger.info("-" * 80)
        logger.info("[LLM Request] 准备发送请求")
        logger.info(f"  URL: {self.config.api_url}")
        logger.info(f"  Model: {payload.get('model')}")
        logger.info(f"  Temperature: {payload.get('temperature')}")
        logger.info(f"  Max Tokens: {payload.get('max_tokens')}")

        logger.info("-" * 80)
        logger.info("[LLM Request] 完整请求 Payload")
        logger.info("=" * 80)
        logger.info(json.dumps(payload, ensure_ascii=False, indent=2))
        logger.info("=" * 80)

        messages = payload.get('messages', [])
        logger.info(f"  Messages Count: {len(messages)}")
        for idx, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            content_preview = content[:200] + '...' if len(content) > 200 else content
            logger.info(f"    [{idx}] Role: {role}")
            logger.info(f"        Content Preview: {content_preview}")
            logger.info(f"        Content Length: {len(content)} chars")

        logger.info("-" * 80)

        try:
            response = await client.post(
                self.config.api_url,
                json=payload
            )

            latency_ms = (time.time() - start_time) * 1000

            logger.info("-" * 80)
            logger.info("[LLM Response] 收到响应")
            logger.info(f"  Status Code: {response.status_code}")
            logger.info(f"  Latency: {latency_ms:.2f}ms")

            if response.status_code != 200:
                logger.error(f"  Response Body: {response.text[:500]}")

            response.raise_for_status()

            data = response.json()

            logger.info("-" * 80)
            logger.info("[LLM Response] 完整响应")
            logger.info("=" * 80)
            logger.info(json.dumps(data, ensure_ascii=False, indent=2))
            logger.info("=" * 80)

            content = ""
            if 'choices' in data and len(data['choices']) > 0:
                content = data['choices'][0].get('message', {}).get('content', '')
                logger.info(f"  Extracted Content Length: {len(content)} chars")

            usage = data.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens')
            completion_tokens = usage.get('completion_tokens')
            total_tokens = usage.get('total_tokens')

            logger.info(f"  Token Usage:")
            logger.info(f"    Prompt Tokens: {prompt_tokens}")
            logger.info(f"    Completion Tokens: {completion_tokens}")
            logger.info(f"    Total Tokens: {total_tokens}")
            logger.info("-" * 80)

            return LLMResponse(
                content=content,
                model=payload.get('model', self.config.model_name),
                provider=self.provider.value,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                raw_response=data
            )

        except httpx.HTTPStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:500]}"
            logger.error(f"[LLM Error] HTTP Status Error: {error_msg}")
            logger.info("-" * 80)
            return LLMResponse(
                content="",
                model=payload.get('model', self.config.model_name),
                provider=self.provider.value,
                latency_ms=latency_ms,
                error=error_msg
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"[LLM Error] Exception: {error_msg}")
            logger.info("-" * 80)
            return LLMResponse(
                content="",
                model=payload.get('model', self.config.model_name),
                provider=self.provider.value,
                latency_ms=latency_ms,
                error=error_msg
            )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048
    ) -> LLMResponse:
        payload = self._build_payload(messages, model, temperature, max_tokens)
        last_error = None

        for attempt in range(self.max_retries):
            logger.info(f"[Retry Info] Attempt {attempt + 1}/{self.max_retries}")

            response = await self._make_request(payload)

            if response.is_success():
                logger.info(f"[Success] LLM 调用成功")
                return response

            last_error = response.error
            logger.warning(f"[Retry] 请求失败：{last_error}")

            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.info(f"[Retry] 等待 {wait_time}s 后重试...")

                await asyncio.sleep(wait_time)

                if self.config.backup_model and model != self.config.backup_model:
                    logger.info(f"[Retry] 切换到备用模型：{self.config.backup_model}")
                    payload['model'] = self.config.backup_model

        logger.error(f"[Failed] LLM 调用失败，已重试 {self.max_retries} 次")
        return LLMResponse(
            content="",
            model=payload.get('model', self.config.model_name),
            provider=self.provider.value,
            error=f"Max retries exceeded. Last error: {last_error}"
        )

    def build_log_analysis_prompt(
        self,
        error_entries: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        logger.info("=" * 80)
        logger.info("[Prompt Building] 构建日志分析提示词")
        logger.info(f"  Error Entries Count: {len(error_entries)}")
        logger.info(f"  Statistics Keys: {list(statistics.keys())}")
        logger.info(f"  Context Provided: {'Yes' if context else 'No'}")

        system_prompt = """你是一个资深的专业日志分析工程师和故障排查专家，擅长分析应用程序错误日志、定位故障根因、构建证据链，并提供可落地的处置和整改方案。

你的任务是对提供的错误日志数据进行深度分析，生成一份结构化的故障分析总结报告。报告应当专业、准确、可操作。

## 报告结构要求

生成的报告必须包含以下核心环节：

### 一、故障时间线（Fault Timeline）
按时间顺序梳理故障的完整生命周期，包括：
- **首次异常时间**：第一条异常/错误日志的时间戳
- **故障确认时间**：错误达到阈值或明确表示故障的时间点
- **错误峰值时间**：错误频率最高或影响最大的时间段
- **故障恢复时间**：第一条恢复迹象或业务恢复正常的时间
- **时间跨度分析**：从发生到恢复的总时长，识别关键时间节点

### 二、根因推断（Root Cause Inference）
基于错误日志的模式识别、关联分析和上下文推断，找出故障的根本原因：

**分析方法**：
- 识别错误日志中的异常模式（频率突增、特定错误类型集中出现等）
- 分析错误之间的因果关系和依赖链
- 结合业务上下文判断最可能的原因

**输出要求**：
- **直接原因（Direct Cause）**：直接触发故障的表面原因（如：某个接口超时、某个服务不可用）
- **根本原因（Root Cause）**：深层次的系统性问题（如：缺乏熔断机制、资源配置不足、架构设计缺陷）
- **置信度评估**：对根因推断的置信度进行评分（高/中/低），并说明依据

### 三、故障因果链与证据链（Causal Chain & Evidence Chain）
构建完整的故障传播路径，并提供支撑推断的关键证据：

**因果链（Causal Chain）**：
描述故障从源头到最终影响的完整传播路径，格式为：
```
[故障源头] → [中间环节1] → [中间环节2] → ... → [最终表现]
```

每个环节应包含：
- **原因（Cause）**：该环节的输入事件或状态
- **结果（Effect）**：该环节导致的输出或状态变化
- **证据（Evidence）**：支撑该环节推断的关键日志条目（包含时间戳、错误类型、关键信息）

**证据链（Evidence Chain）**：
列出支撑根因推断的关键证据，每条证据应包含：
- **时间戳**：证据产生的时间
- **证据类型**：日志条目、错误堆栈、异常信息、系统指标等
- **证据内容**：具体的日志内容或错误信息（精简但完整）
- **关联度**：该证据与根因的关联程度（直接/间接/辅助）

### 四、处置动作建议（Immediate Response Actions）
**本节重点关注：故障发生时的应急处置动作**

针对该故障类型，给出具体的、可立即执行的处置动作清单：

**分类**：
1. **应急止血动作**（发现故障后立即执行）：
   - 服务降级/熔断
   - 流量切换/隔离
   - 资源扩容
   - 数据备份/保护
   - 通知相关人员

2. **排查定位动作**（应急处置后，定位根因前）：
   - 日志检索关键错误信息
   - 监控指标检查（CPU、内存、网络、磁盘等）
   - 链路追踪分析
   - 配置核查
   - 依赖服务状态确认

3. **恢复验证动作**（根因修复后，确认恢复）：
   - 功能验证测试
   - 监控指标观察
   - 用户反馈收集
   - 灰度发布验证

**输出格式**：
每个动作应包含：
- **动作名称**：简洁明确的动作描述
- **执行时机**：何时执行该动作
- **执行步骤**：具体的操作步骤（简明扼要）
- **预期效果**：执行后预期达到的效果
- **注意事项**：执行过程中的风险点或关键注意项

### 五、整改建议（Rectification Suggestions）
**本节重点关注：从根本上解决问题，防止故障再次发生**

从三个维度给出具体可落地的整改建议：

#### 5.1 立即处置（Immediate Actions）
**目标**：快速恢复服务，最小化业务影响
**时间要求**：1小时内可执行
**建议内容**：
- 配置调整（超时时间、重试次数、线程池大小等）
- 服务重启/切换
- 临时降级方案
- 数据清理/修复

#### 5.2 根因解决（Root Cause Fix）
**目标**：彻底修复导致故障的根本问题
**时间要求**：短期Sprint内完成（1-2周）
**建议内容**：
- 代码缺陷修复
- 异常处理完善
- 参数校验增强
- 资源泄漏修复
- 依赖服务替换/升级

#### 5.3 架构/监控改进（Architecture & Monitoring Improvements）
**目标**：提升系统整体稳定性和可观测性
**时间要求**：季度规划级别（1-3个月）
**建议内容**：
- **架构优化**：
  - 引入熔断/降级机制
  - 优化资源分配策略
  - 改进负载均衡算法
  - 增强系统弹性设计
  
- **监控增强**：
  - 新增关键指标监控（业务指标、系统指标、链路指标）
  - 优化告警规则（减少误报、提高灵敏度）
  - 完善监控大盘（故障排查视图、根因分析视图）
  - 建立故障预案和SOP文档

- **流程改进**：
  - 建立变更管理制度（代码审查、灰度发布、回滚预案）
  - 完善故障演练机制
  - 加强团队协作和知识共享

### 六、传统分析维度（Traditional Analysis）
保留经典的错误分析维度，便于快速理解：
1. **关键错误摘要**：列出最重要的5-10个错误类型
2. **错误频率统计**：按错误类型、时间段、服务模块等维度统计
3. **错误趋势识别**：识别错误的周期性、传播性、关联性等趋势
4. **解决建议分类**：按运维（Ops）和开发（Dev）角度分类建议

## 输出格式要求

**必须使用有效的 JSON 格式输出**，包含以下字段：

```json
{
  "summary": "故障分析总体摘要（150字以内，简明扼要地总结故障原因、影响和处置结果）",
  
  "timeline": {
    "description": "故障时间线描述",
    "key_events": [
      {
        "time": "2026-06-02T10:30:00",
        "event_type": "first_abnormal | peak_error | recovery | ...",
        "description": "事件描述"
      }
    ],
    "total_duration": "故障总时长（如：2小时30分钟）"
  },
  
  "root_cause": {
    "direct_cause": "直接原因描述",
    "fundamental_cause": "根本原因描述",
    "confidence": "high | medium | low",
    "reasoning": "根因推断的逻辑和依据"
  },
  
  "causal_chain": {
    "chain_description": "因果链总体描述",
    "chain_steps": [
      {
        "step": 1,
        "cause": "故障源头或触发事件",
        "effect": "导致的后果或状态",
        "evidence": "关键证据（日志条目、错误信息等）",
        "timestamp": "时间戳（如果有）"
      }
    ]
  },
  
  "evidence_chain": {
    "description": "证据链说明",
    "evidences": [
      {
        "timestamp": "证据时间戳",
        "evidence_type": "log | exception | metric | trace",
        "content": "证据内容（精简但完整）",
        "relevance": "direct | indirect | supporting"
      }
    ]
  },
  
  "response_actions": {
    "description": "处置动作建议总述",
    "emergency_actions": [
      {
        "action_name": "动作名称",
        "timing": "执行时机",
        "steps": "执行步骤",
        "expected_effect": "预期效果",
        "notes": "注意事项"
      }
    ],
    "troubleshooting_actions": [],
    "recovery_actions": []
  },
  
  "remediation": {
    "immediate": [
      {
        "action": "具体行动",
        "target": "目标（如：配置、代码、流程）",
        "expected_effect": "预期效果",
        "effort_estimate": "工作量评估（人天）"
      }
    ],
    "root_cause_fix": [],
    "architecture_monitoring": []
  },
  
  "key_errors": [
    {
      "error_type": "错误类型",
      "description": "错误描述",
      "count": 123,
      "severity": "critical | high | medium | low",
      "first_occurrence": "首次出现时间",
      "sample_log": "示例日志（精简）"
    }
  ],
  
  "frequency_stats": {
    "error_type_1": 123,
    "error_type_2": 456
  },
  
  "trends": [
    {
      "trend_type": "periodic | propagating | correlated | ...",
      "description": "趋势描述",
      "evidence": "支撑数据或日志"
    }
  ],
  
  "ops_suggestions": [
    {
      "category": "监控 | 告警 | 配置 | 部署 | 容量规划",
      "suggestion": "具体建议内容",
      "priority": "high | medium | low"
    }
  ],
  
  "dev_suggestions": [
    {
      "category": "代码修复 | 异常处理 | 参数验证 | 架构优化 | 日志改进",
      "suggestion": "具体建议内容",
      "priority": "high | medium | low"
    }
  ]
}
```

## 分析原则

1. **基于证据**：所有推断必须有日志证据支撑，避免主观猜测
2. **区分概率**：对不确定的推断，明确标注置信度
3. **可操作性**：所有建议必须具体、可落地、可验证
4. **优先级明确**：区分紧急、重要、长期的改进项
5. **业务视角**：从业务影响角度评估故障严重程度

## 注意事项

- 如果日志数据不足，明确说明限制和需要进一步信息
- 如果错误模式不明确，提供多种可能性并标注概率
- 确保输出的 JSON 格式有效，便于程序解析
- 中文输出，术语准确，表达专业"""

        error_samples = []
        for entry in error_entries[:20]:
            error_samples.append({
                'timestamp': entry.get('timestamp', ''),
                'error_type': entry.get('error_type', 'Unknown'),
                'message': entry.get('message', '')[:200],
                'class': entry.get('class_name', '')
            })

        user_content = f"错误日志统计:\n{json.dumps(statistics, indent=2, ensure_ascii=False)}\n\n"
        user_content += f"错误样本:\n{json.dumps(error_samples, indent=2, ensure_ascii=False)}\n\n"

        if context:
            user_content += f"上下文信息:\n{context}\n\n"

        user_content += "\n请分析以上错误日志并生成 JSON 格式的报告。"

        logger.info("=" * 80)
        logger.info("[Prompt Building] System Prompt 内容:")
        logger.info("-" * 80)
        logger.info(system_prompt)
        logger.info("=" * 80)
        logger.info("[Prompt Building] User Prompt 内容 (发送给 LLM 的用户消息):")
        logger.info("-" * 80)
        logger.info(user_content)
        logger.info("=" * 80)
        logger.info(f"  System Prompt Length: {len(system_prompt)} chars")
        logger.info(f"  User Content Length: {len(user_content)} chars")
        logger.info(f"  错误样本数量：{len(error_samples)} 条")
        logger.info("=" * 80)

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

    async def analyze_log_chunk(
        self,
        error_entries: List[Dict[str, Any]],
        statistics: Dict[str, Any],
        chunk_id: int,
        context: Optional[str] = None
    ) -> AnalysisResult:
        logger.info("=" * 80)
        logger.info(f"[Chunk Analysis] 开始分析 Chunk #{chunk_id}")
        logger.info(f"  Error Entries: {len(error_entries)}")
        logger.info(f"  Statistics: {json.dumps(statistics, indent=2, ensure_ascii=False)}")
        logger.info(f"  Context Provided: {'Yes' if context else 'No'}")
        logger.info("=" * 80)

        messages = self.build_log_analysis_prompt(error_entries, statistics, context)

        logger.info(f"[Chunk #{chunk_id}] 准备发送 {len(messages)} 条消息到 LLM")

        response = await self.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=2048
        )

        result = AnalysisResult(
            chunk_id=chunk_id,
            summary="",
            raw_llm_response=response
        )

        if response.is_success() and response.content:
            logger.info(f"[Chunk #{chunk_id}] 成功收到 LLM 响应")
            logger.info(f"  Response Content Length: {len(response.content)} chars")
            logger.info(f"[Chunk #{chunk_id}] LLM 完整响应内容:")
            logger.info("-" * 80)
            logger.info(response.content)
            logger.info("-" * 80)

            try:
                content = response.content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]

                parsed = json.loads(content.strip())

                result.summary = parsed.get('summary', '')
                result.key_errors = parsed.get('key_errors', [])
                result.frequency_stats = parsed.get('frequency_stats', {})
                
                # 处理 trends：LLM 返回的可能是字典列表或字符串列表
                trends_data = parsed.get('trends', [])
                result.trends = []
                for trend in trends_data:
                    if isinstance(trend, dict):
                        # 如果是字典，提取 description 字段
                        description = trend.get('description', '')
                        if description:
                            result.trends.append(description)
                        else:
                            result.trends.append(str(trend))
                    else:
                        # 如果是字符串，直接使用
                        result.trends.append(str(trend))
                
                result.ops_suggestions = parsed.get('ops_suggestions', [])
                result.dev_suggestions = parsed.get('dev_suggestions', [])
                
                # 新增故障分析字段
                result.timeline = parsed.get('timeline', {})
                result.root_cause = parsed.get('root_cause', {})
                result.causal_chain = parsed.get('causal_chain', {})
                result.remediation = parsed.get('remediation', {})
                result.response_actions = parsed.get('response_actions', {})
                result.evidence_chain = parsed.get('evidence_chain', {})

                logger.info(f"[Chunk #{chunk_id}] 成功解析 LLM 响应")
                logger.info(f"  Summary: {result.summary[:100]}...")
                logger.info(f"  Key Errors Count: {len(result.key_errors)}")
                logger.info(f"  Trends Count: {len(result.trends)}")
                logger.info(f"  Ops Suggestions Count: {len(result.ops_suggestions)}")
                logger.info(f"  Dev Suggestions Count: {len(result.dev_suggestions)}")
                logger.info(f"  Timeline Events: {len(result.timeline.get('key_events', [])) if isinstance(result.timeline, dict) else 0}")
                logger.info(f"  Remediation Categories: {len(result.remediation) if isinstance(result.remediation, dict) else 0}")

            except json.JSONDecodeError as e:
                logger.error(f"[Chunk #{chunk_id}] JSON 解析失败：{e}")
                result.summary = f"解析 LLM 响应失败：{str(e)}"
        else:
            logger.error(f"[Chunk #{chunk_id}] LLM 调用失败：{response.error}")
            result.summary = f"LLM 调用失败：{response.error}"

        logger.info(f"[Chunk #{chunk_id}] 分析完成")
        logger.info("=" * 80)

        return result

    def _aggregate_errors(
        self,
        all_error_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        智能错误聚合函数：将大量错误条目聚合为结构化的摘要数据
        保留关键信息的同时显著减少字符数量
        """
        original_chars = len(json.dumps(all_error_entries, ensure_ascii=False))
        
        # 1. 按错误类型分组
        errors_by_type = {}
        timestamps = []
        
        for entry in all_error_entries:
            error_type = entry.get('error_type', 'Unknown')
            timestamp = entry.get('timestamp', '')
            
            if timestamp:
                timestamps.append(timestamp)
            
            if error_type not in errors_by_type:
                errors_by_type[error_type] = {
                    'count': 0,
                    'examples': [],
                    'timestamps': [],
                    'classes': set(),
                    'messages': set()
                }
            
            errors_by_type[error_type]['count'] += 1
            errors_by_type[error_type]['timestamps'].append(timestamp)
            
            if entry.get('class_name'):
                errors_by_type[error_type]['classes'].add(entry['class_name'])
            
            message = entry.get('message', '')[:200]
            if message:
                errors_by_type[error_type]['messages'].add(message)
        
        # 2. 为每个错误类型生成结构化摘要
        aggregated_errors = []
        max_examples_per_type = 3  # 每个错误类型最多保留3个示例
        max_types = 15  # 最多保留15种错误类型
        
        # 按出现频率排序
        sorted_types = sorted(
            errors_by_type.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:max_types]
        
        for error_type, data in sorted_types:
            # 获取时间范围
            type_timestamps = [t for t in data['timestamps'] if t]
            time_range = None
            if type_timestamps:
                time_range = {
                    'start': min(type_timestamps),
                    'end': max(type_timestamps)
                }
            
            # 取前N个典型消息作为示例
            examples = []
            messages_list = list(data['messages'])[:max_examples_per_type]
            for msg in messages_list:
                examples.append({
                    'message': msg,
                    'class': next(iter(data['classes']), '') if data['classes'] else ''
                })
            
            aggregated_errors.append({
                'error_type': error_type,
                'count': data['count'],
                'time_range': time_range,
                'affected_classes': list(data['classes'])[:5],
                'examples': examples
            })
        
        # 3. 计算整体时间范围
        overall_time_range = None
        if timestamps:
            overall_time_range = {
                'start': min(timestamps),
                'end': max(timestamps)
            }
        
        # 4. 生成聚合摘要
        summary = {
            'total_errors': len(all_error_entries),
            'unique_error_types': len(errors_by_type),
            'top_error_types': [t[0] for t in sorted_types[:5]],
            'time_range': overall_time_range,
            'aggregated_errors': aggregated_errors
        }
        
        compressed_chars = len(json.dumps(summary, ensure_ascii=False))
        compression_ratio = ((original_chars - compressed_chars) / original_chars) * 100
        
        logger.info(f"[Error Aggregation] 智能聚合完成")
        logger.info(f"  原始条目数: {len(all_error_entries)}")
        logger.info(f"  聚合后错误类型数: {len(aggregated_errors)}")
        logger.info(f"  原始字符数: {original_chars:,}")
        logger.info(f"  压缩后字符数: {compressed_chars:,}")
        logger.info(f"  压缩率: {compression_ratio:.1f}%")
        
        return summary, original_chars, compressed_chars, compression_ratio

    def build_merged_analysis_prompt(
        self,
        all_error_entries: List[Dict[str, Any]],
        all_statistics: List[Dict[str, Any]],
        total_chunks: int
    ) -> List[Dict[str, str]]:
        logger.info("=" * 80)
        logger.info("[Prompt Building] 构建合并日志分析提示词")
        logger.info(f"  Total Chunks: {total_chunks}")
        logger.info(f"  Total Error Entries: {len(all_error_entries)}")
        logger.info(f"  Statistics Count: {len(all_statistics)}")

        merged_statistics = {
            'total_chunks': total_chunks,
            'total_error_entries': len(all_error_entries),
            'by_level': {},
            'error_types': {},
            'patterns': {},
            'top_classes': {},
            'time_range': {
                'start': None,
                'end': None
            }
        }

        timestamps = []
        
        for stats in all_statistics:
            for level, count in stats.get('by_level', {}).items():
                merged_statistics['by_level'][level] = merged_statistics['by_level'].get(level, 0) + count
            
            for error_type, count in stats.get('error_types', {}).items():
                merged_statistics['error_types'][error_type] = merged_statistics['error_types'].get(error_type, 0) + count
            
            for pattern, count in stats.get('patterns', {}).items():
                merged_statistics['patterns'][pattern] = merged_statistics['patterns'].get(pattern, 0) + count
            
            for class_name, count in stats.get('top_classes', {}).items():
                merged_statistics['top_classes'][class_name] = merged_statistics['top_classes'].get(class_name, 0) + count
            
            time_range = stats.get('time_range', {})
            if time_range.get('start'):
                timestamps.append(time_range['start'])
            if time_range.get('end'):
                timestamps.append(time_range['end'])
        
        if timestamps:
            merged_statistics['time_range']['start'] = min(timestamps)
            merged_statistics['time_range']['end'] = max(timestamps)
        
        merged_statistics['top_classes'] = dict(sorted(
            merged_statistics['top_classes'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])
        
        merged_statistics['error_types'] = dict(sorted(
            merged_statistics['error_types'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:20])

        # 使用智能错误聚合
        error_summary, original_chars, compressed_chars, compression_ratio = self._aggregate_errors(all_error_entries)
        
        # 记录优化效果到统计信息中
        merged_statistics['compression_stats'] = {
            'original_chars': original_chars,
            'compressed_chars': compressed_chars,
            'compression_ratio': f"{compression_ratio:.1f}%"
        }

        context = (
            f"这是一次合并分析，共合并 {total_chunks} 个日志分块。"
            "请把这些分块视为同一个日志文件的连续上下文，生成一份跨所有分块的综合故障分析报告。\n\n"
            f"智能聚合错误摘要:\n{json.dumps(error_summary, indent=2, ensure_ascii=False)}\n\n"
            "分析时请优先使用合并统计信息和智能聚合错误摘要来构建故障时间线、根因推断、因果链、"
            "证据链、处置动作和整改建议。"
        )

        logger.info("=" * 80)
        logger.info("[Prompt Building] 合并分析复用标准日志分析提示词")
        logger.info(f"  压缩前字符数: {original_chars:,}")
        logger.info(f"  压缩后字符数: {compressed_chars:,}")
        logger.info(f"  压缩率: {compression_ratio:.1f}%")
        logger.info("=" * 80)

        return self.build_log_analysis_prompt(
            error_entries=all_error_entries,
            statistics=merged_statistics,
            context=context
        )

    async def analyze_merged_chunks(
        self,
        all_error_entries: List[Dict[str, Any]],
        all_statistics: List[Dict[str, Any]],
        total_chunks: int
    ) -> AnalysisResult:
        logger.info("=" * 80)
        logger.info(f"[Merged Analysis] 开始合并分析 {total_chunks} 个分块")
        logger.info(f"  Total Error Entries: {len(all_error_entries)}")
        logger.info(f"  Statistics Count: {len(all_statistics)}")
        logger.info("=" * 80)

        messages = self.build_merged_analysis_prompt(all_error_entries, all_statistics, total_chunks)

        logger.info(f"[Merged Analysis] 准备发送 {len(messages)} 条消息到 LLM")

        response = await self.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )

        result = AnalysisResult(
            chunk_id=0,
            summary="",
            raw_llm_response=response
        )

        if response.is_success() and response.content:
            logger.info(f"[Merged Analysis] 成功收到 LLM 响应")
            logger.info(f"  Response Content Length: {len(response.content)} chars")

            try:
                content = response.content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.startswith('```'):
                    content = content[3:]
                if content.endswith('```'):
                    content = content[:-3]

                parsed = json.loads(content.strip())

                result.summary = parsed.get('summary', '')
                result.key_errors = parsed.get('key_errors', [])
                result.frequency_stats = parsed.get('frequency_stats', {})
                
                # 处理 trends：LLM 返回的可能是字典列表或字符串列表
                trends_data = parsed.get('trends', [])
                result.trends = []
                for trend in trends_data:
                    if isinstance(trend, dict):
                        # 如果是字典，提取 description 字段或拼接信息
                        description = trend.get('description', '')
                        if description:
                            result.trends.append(description)
                        else:
                            result.trends.append(str(trend))
                    else:
                        # 如果是字符串，直接使用
                        result.trends.append(str(trend))
                
                result.ops_suggestions = parsed.get('ops_suggestions', [])
                result.dev_suggestions = parsed.get('dev_suggestions', [])
                
                # 故障深度分析字段，与单 chunk 分析保持一致
                result.timeline = parsed.get('timeline', {})
                result.root_cause = parsed.get('root_cause', {})
                result.causal_chain = parsed.get('causal_chain', {})
                result.remediation = parsed.get('remediation', {})
                result.response_actions = parsed.get('response_actions', {})
                result.evidence_chain = parsed.get('evidence_chain', {})

                logger.info(f"[Merged Analysis] 成功解析 LLM 响应")
                logger.info(f"  Summary: {result.summary[:100]}...")
                logger.info(f"  Key Errors Count: {len(result.key_errors)}")
                logger.info(f"  Trends Count: {len(result.trends)}")
                logger.info(f"  Ops Suggestions Count: {len(result.ops_suggestions)}")
                logger.info(f"  Dev Suggestions Count: {len(result.dev_suggestions)}")
                logger.info(f"  Timeline Events: {len(result.timeline.get('key_events', [])) if isinstance(result.timeline, dict) else 0}")
                logger.info(f"  Remediation Categories: {len(result.remediation) if isinstance(result.remediation, dict) else 0}")
                logger.info(f"  Trends Type: {type(result.trends[0]) if result.trends else 'empty'}")

            except json.JSONDecodeError as e:
                logger.error(f"[Merged Analysis] JSON 解析失败：{e}")
                result.summary = f"解析 LLM 响应失败：{str(e)}"
        else:
            logger.error(f"[Merged Analysis] LLM 调用失败：{response.error}")
            result.summary = f"LLM 调用失败：{response.error}"

        logger.info(f"[Merged Analysis] 合并分析完成")
        logger.info("=" * 80)

        return result

    async def batch_analyze(
        self,
        chunks_data: List[tuple],
        progress_callback: Optional[callable] = None,
        max_concurrent: int = 4
    ) -> List[AnalysisResult]:
        results = [None] * len(chunks_data)
        total = len(chunks_data)

        logger.info("=" * 80)
        logger.info(f"[Batch Analysis] 开始批量分析")
        logger.info(f"  Total Chunks: {total}")
        logger.info(f"  Max Concurrent: {max_concurrent}")
        logger.info("=" * 80)

        async def process_chunk(idx: int, chunk_id: int, error_entries: List[Dict[str, Any]], statistics: Dict[str, Any]):
            try:
                result = await self.analyze_log_chunk(error_entries, statistics, chunk_id)
                results[idx] = result

                if progress_callback:
                    progress_callback(sum(1 for r in results if r is not None), total)

            except Exception as e:
                logger.error(f"[Batch] Chunk #{chunk_id} 处理异常：{e}")
                results[idx] = AnalysisResult(
                    chunk_id=chunk_id,
                    summary=f"处理失败：{str(e)}"
                )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_process(idx: int, chunk_id: int, error_entries: List[Dict[str, Any]], statistics: Dict[str, Any]):
            async with semaphore:
                await process_chunk(idx, chunk_id, error_entries, statistics)

        tasks = []
        for idx, (chunk_id, error_entries, statistics) in enumerate(chunks_data):
            tasks.append(bounded_process(idx, chunk_id, error_entries, statistics))

        await asyncio.gather(*tasks)

        logger.info("=" * 80)
        logger.info(f"[Batch Analysis] 批量分析完成")
        logger.info(f"  Successful: {sum(1 for r in results if r and r.summary and '失败' not in r.summary)}")
        logger.info(f"  Failed: {sum(1 for r in results if r and '失败' in r.summary)}")
        logger.info("=" * 80)

        return results
