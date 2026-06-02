"""Report generator for creating structured analysis reports."""

import os
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..processor.chunk_processor import ProcessingResult
from ..llm.client import AnalysisResult
from ..utils.helpers import ensure_dir, get_file_size_str


@dataclass
class ReportSection:
    title: str
    content: str
    section_type: str = "text"
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'content': self.content,
            'section_type': self.section_type,
            'data': self.data
        }


@dataclass
class Report:
    title: str
    generated_at: datetime
    file_path: str
    file_size: str
    total_lines: int
    total_errors: int
    total_warnings: int
    sections: List[ReportSection] = field(default_factory=list)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'file_path': self.file_path,
            'file_size': self.file_size,
            'total_lines': self.total_lines,
            'total_errors': self.total_errors,
            'total_warnings': self.total_warnings,
            'summary': self.summary,
            'sections': [s.to_dict() for s in self.sections],
            'metadata': self.metadata
        }

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}\n",
            f"**生成时间**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**文件**: {self.file_path}\n",
            f"**文件大小**: {self.file_size}\n",
            f"**总行数**: {self.total_lines:,}\n",
            f"**总错误数**: {self.total_errors:,}\n",
            f"**总警告数**: {self.total_warnings:,}\n",
            "---\n"
        ]

        for section in self.sections:
            lines.append(f"## {section.title}\n")
            lines.append(f"{section.content}\n")
            if section.data:
                lines.append("**数据统计**:\n")
                lines.append("```json\n")
                lines.append(json.dumps(section.data, indent=2, ensure_ascii=False) + "\n")
                lines.append("```\n")
            lines.append("\n")

        if self.summary:
            lines.append("---\n\n")
            lines.append(f"## 总体摘要\n\n{self.summary}\n")

        return "".join(lines)


class ReportGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        ensure_dir(output_dir)

    def generate_combined_report(self, results: List[ProcessingResult]) -> Report:
        """生成多个文件的综合分析报告"""
        total_lines = sum(r.total_lines for r in results)
        total_errors = sum(
            r.statistics.get('by_level', {}).get('ERROR', 0) +
            r.statistics.get('by_level', {}).get('FATAL', 0)
            for r in results
        )
        total_warnings = sum(
            r.statistics.get('by_level', {}).get('WARN', 0)
            for r in results
        )
        processed_files = sum(1 for r in results if r.status == 'completed')

        report = Report(
            title=f"综合日志分析报告 - {len(results)} 个文件",
            generated_at=datetime.now(),
            file_path=f"{processed_files} 个文件",
            file_size=f"{len(results)} 个文件",
            total_lines=total_lines,
            total_errors=total_errors,
            total_warnings=total_warnings,
            metadata={
                'total_files': len(results),
                'processed_files': processed_files,
                'file_names': [os.path.basename(r.file_path) for r in results]
            }
        )

        # 添加概览
        report.sections.append(self._create_combined_overview_section(results))
        
        # 添加各文件摘要
        report.sections.append(self._create_file_summaries_section(results))
        
        # 添加综合统计
        report.sections.append(self._create_combined_statistics_section(results))
        
        # 添加综合建议
        report.sections.append(self._create_combined_suggestions_section(results))

        report.summary = self._generate_combined_summary(results)

        return report

    def generate_report(self, result: ProcessingResult) -> Report:
        total_errors = (
            result.statistics.get('by_level', {}).get('ERROR', 0) +
            result.statistics.get('by_level', {}).get('FATAL', 0)
        )
        total_warnings = result.statistics.get('by_level', {}).get('WARN', 0)

        report = Report(
            title=f"日志分析报告 - {os.path.basename(result.file_path)}",
            generated_at=datetime.now(),
            file_path=result.file_path,
            file_size=get_file_size_str(result.file_path),
            total_lines=result.total_lines,
            total_errors=total_errors,
            total_warnings=total_warnings,
            metadata={
                'processed_lines': result.processed_lines,
                'total_chunks': result.total_chunks,
                'completed_chunks': result.completed_chunks,
                'status': result.status
            }
        )

        report.sections.append(self._create_overview_section(result))
        report.sections.append(self._create_statistics_section(result))
        report.sections.append(self._create_combined_error_section(result))
        report.sections.append(self._create_trends_timeline_section(result))
        report.sections.append(self._create_root_cause_analysis_section(result))
        report.sections.append(self._create_disposal_remediation_section(result))

        report.summary = self._generate_summary(result)

        return report

    def _create_overview_section(self, result: ProcessingResult) -> ReportSection:
        overview_data = {
            '处理状态': result.status,
            '文件路径': result.file_path,
            '总行数': result.total_lines,
            '已处理行数': result.processed_lines,
            '处理进度': f"{result.get_progress_percentage():.2f}%",
            '总块数': result.total_chunks,
            '已完成块数': result.completed_chunks
        }

        content = f"""
**处理状态**: {result.status}
**处理进度**: {result.get_progress_percentage():.2f}%
**已处理**: {result.processed_lines:,} / {result.total_lines:,} 行
**已完成**: {result.completed_chunks} / {result.total_chunks} 块
"""
        if result.error_message:
            content += f"\n**错误信息**: {result.error_message}\n"

        return ReportSection(
            title="1. 处理概览",
            content=content.strip(),
            section_type="overview",
            data=overview_data
        )

    def _create_statistics_section(self, result: ProcessingResult) -> ReportSection:
        by_level = result.statistics.get('by_level', {})
        error_types = result.statistics.get('error_types', {})
        top_classes = result.statistics.get('top_classes', {})

        stats_data = {
            '错误级别分布': by_level,
            '错误类型统计': dict(list(error_types.items())[:20]),
            '高频错误类': dict(list(top_classes.items())[:20])
        }

        level_lines = [f"- **{level}**: {count:,}" for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True)]

        content = f"""
### 错误级别分布
{chr(10).join(level_lines)}

### 错误类型统计 (Top 20)
"""
        for error_type, count in list(error_types.items())[:20]:
            content += f"- {error_type}: {count:,}\n"

        content += "\n### 高频错误类 (Top 20)\n"
        for class_name, count in list(top_classes.items())[:20]:
            content += f"- {class_name}: {count:,}\n"

        return ReportSection(
            title="2. 统计分析",
            content=content.strip(),
            section_type="statistics",
            data=stats_data
        )

    def _create_error_analysis_section(self, result: ProcessingResult) -> ReportSection:
        all_errors = []
        for analysis in result.analysis_results:
            for error in analysis.key_errors:
                all_errors.append(error)

        all_errors.sort(key=lambda x: x.get('count', 0), reverse=True)
        top_errors = all_errors[:10]

        errors_data = {'关键错误': top_errors}

        content = "### 关键错误分析\n\n"
        for idx, error in enumerate(top_errors, 1):
            error_type = error.get('error_type', 'Unknown')
            description = error.get('description', '')
            count = error.get('count', 0)
            severity = error.get('severity', 'medium')

            content += f"#### {idx}. {error_type}\n"
            content += f"- **描述**: {description}\n"
            content += f"- **出现次数**: {count:,}\n"
            content += f"- **严重程度**: {severity}\n\n"

        return ReportSection(
            title="关键错误分析",
            content=content.strip(),
            section_type="error_analysis",
            data=errors_data
        )

    def _create_pattern_analysis_section(self, result: ProcessingResult) -> ReportSection:
        all_patterns: Dict[str, int] = {}
        for analysis in result.analysis_results:
            freq_stats = analysis.frequency_stats
            if isinstance(freq_stats, dict):
                for pattern_type, value in freq_stats.items():
                    if isinstance(value, int):
                        all_patterns[pattern_type] = all_patterns.get(pattern_type, 0) + value
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, int):
                                combined_key = f"{pattern_type}.{sub_key}"
                                all_patterns[combined_key] = all_patterns.get(combined_key, 0) + sub_value

        patterns_sorted = sorted(all_patterns.items(), key=lambda x: x[1], reverse=True)
        patterns_data = {'错误模式统计': dict(patterns_sorted)}

        content = "### 错误模式识别\n\n"
        for pattern_type, count in patterns_sorted:
            content += f"- **{pattern_type}**: {count:,} 次\n"

        return ReportSection(
            title="错误模式分析",
            content=content.strip(),
            section_type="pattern_analysis",
            data=patterns_data
        )

    def _create_trends_section(self, result: ProcessingResult) -> ReportSection:
        all_trends = []
        for analysis in result.analysis_results:
            all_trends.extend(analysis.trends)

        seen = set()
        unique_trends = []
        for trend in all_trends:
            if trend not in seen:
                seen.add(trend)
                unique_trends.append(trend)

        trends_data = {'趋势识别': unique_trends}

        content = "### 趋势识别\n\n"
        for idx, trend in enumerate(unique_trends[:10], 1):
            content += f"{idx}. {trend}\n"

        return ReportSection(
            title="趋势识别",
            content=content.strip(),
            section_type="trends",
            data=trends_data
        )

    def _create_suggestions_section(self, result: ProcessingResult) -> ReportSection:
        all_ops_suggestions = []
        all_dev_suggestions = []
        
        for analysis in result.analysis_results:
            # 收集运维建议
            for suggestion in analysis.ops_suggestions:
                if suggestion and suggestion not in all_ops_suggestions:
                    all_ops_suggestions.append(suggestion)
            
            # 收集开发建议
            for suggestion in analysis.dev_suggestions:
                if suggestion and suggestion not in all_dev_suggestions:
                    all_dev_suggestions.append(suggestion)
        
        # 处理建议数据，提取category和suggestion字段
        processed_ops = []
        for s in all_ops_suggestions[:3]:
            if isinstance(s, dict):
                processed_ops.append({
                    'category': s.get('category', ''),
                    'suggestion': s.get('suggestion', '')
                })
            else:
                processed_ops.append({'category': '', 'suggestion': str(s)})
        
        processed_dev = []
        for s in all_dev_suggestions[:3]:
            if isinstance(s, dict):
                processed_dev.append({
                    'category': s.get('category', ''),
                    'suggestion': s.get('suggestion', '')
                })
            else:
                processed_dev.append({'category': '', 'suggestion': str(s)})
        
        suggestions_data = {
            '运维建议': processed_ops,
            '开发建议': processed_dev
        }
        
        content = "### 解决建议\n\n"
        
        # 运维建议部分
        if processed_ops:
            content += "#### 运维建议\n\n"
            for idx, item in enumerate(processed_ops, 1):
                category = item.get('category', '')
                suggestion = item.get('suggestion', '')
                if category:
                    content += f"{idx}. **{category}**: {suggestion}\n"
                else:
                    content += f"{idx}. {suggestion}\n"
            content += "\n"
        
        # 开发建议部分
        if processed_dev:
            content += "#### 开发建议\n\n"
            for idx, item in enumerate(processed_dev, 1):
                category = item.get('category', '')
                suggestion = item.get('suggestion', '')
                if category:
                    content += f"{idx}. **{category}**: {suggestion}\n"
                else:
                    content += f"{idx}. {suggestion}\n"
        
        return ReportSection(
            title="解决建议",
            content=content.strip(),
            section_type="suggestions",
            data=suggestions_data
        )

    def _create_timeline_section(self, result: ProcessingResult) -> ReportSection:
        all_timelines = []
        for analysis in result.analysis_results:
            if analysis.timeline:
                all_timelines.append(analysis.timeline)

        if not all_timelines:
            return ReportSection(
                title="故障时间线",
                content="暂无故障时间线数据",
                section_type="timeline",
                data={}
            )

        timeline_data = all_timelines[0] if all_timelines else {}

        description = timeline_data.get('description', '')
        key_events = timeline_data.get('key_events', [])
        total_duration = timeline_data.get('total_duration', '')

        content = f"### 故障时间线\n\n"
        if description:
            content += f"{description}\n\n"
        if total_duration:
            content += f"**总时长**: {total_duration}\n\n"

        if key_events:
            content += "#### 关键事件\n\n"
            event_type_names = {
                'first_abnormal': '首次异常',
                'peak_error': '错误峰值',
                'recovery': '恢复',
                'fault_confirmed': '故障确认'
            }
            for idx, event in enumerate(key_events, 1):
                event_time = event.get('time', 'N/A')
                event_type = event.get('event_type', 'unknown')
                event_desc = event.get('description', '')

                display_type = event_type_names.get(event_type, event_type)
                content += f"**{idx}. [{event_time}] {display_type}**\n"
                content += f"- 描述: {event_desc}\n\n"

        return ReportSection(
            title="一、故障时间线（Fault Timeline）",
            content=content.strip(),
            section_type="timeline",
            data={'timeline': timeline_data}
        )

    def _create_root_cause_section(self, result: ProcessingResult) -> ReportSection:
        all_root_causes = []
        for analysis in result.analysis_results:
            if analysis.root_cause:
                all_root_causes.append(analysis.root_cause)

        if not all_root_causes:
            return ReportSection(
                title="根因推断",
                content="暂无根因分析数据",
                section_type="root_cause",
                data={}
            )

        root_cause_data = all_root_causes[0] if all_root_causes else {}

        direct_cause = root_cause_data.get('direct_cause', '')
        fundamental_cause = root_cause_data.get('fundamental_cause', '')
        confidence = root_cause_data.get('confidence', '')
        reasoning = root_cause_data.get('reasoning', '')

        content = "### 根因推断（Root Cause Inference）\n\n"
        content += f"**直接原因（Direct Cause）**: {direct_cause}\n\n"
        content += f"**根本原因（Root Cause）**: {fundamental_cause}\n\n"

        if confidence:
            confidence_display = {'high': '高', 'medium': '中', 'low': '低'}.get(confidence.lower(), confidence)
            content += f"**置信度**: {confidence_display}\n\n"
        if reasoning:
            content += f"**推断依据**: {reasoning}\n\n"

        return ReportSection(
            title="二、根因推断（Root Cause Inference）",
            content=content.strip(),
            section_type="root_cause",
            data={'root_cause': root_cause_data}
        )

    def _create_causal_chain_section(self, result: ProcessingResult) -> ReportSection:
        all_causal_chains = []
        for analysis in result.analysis_results:
            if analysis.causal_chain:
                all_causal_chains.append(analysis.causal_chain)

        if not all_causal_chains:
            return ReportSection(
                title="故障因果链",
                content="暂无因果链数据",
                section_type="causal_chain",
                data={}
            )

        causal_chain_data = all_causal_chains[0] if all_causal_chains else {}

        chain_description = causal_chain_data.get('chain_description', '')
        chain_steps = causal_chain_data.get('chain_steps', [])

        content = "### 故障因果链（Causal Chain）\n\n"
        if chain_description:
            content += f"{chain_description}\n\n"

        if chain_steps:
            content += "#### 因果传播路径\n\n"
            for step in chain_steps:
                step_num = step.get('step', 0)
                cause = step.get('cause', '')
                effect = step.get('effect', '')
                evidence = step.get('evidence', '')
                timestamp = step.get('timestamp', '')

                content += f"**步骤 {step_num}**\n"
                if timestamp:
                    content += f"- 时间: {timestamp}\n"
                content += f"- 原因: {cause}\n"
                content += f"- 结果: {effect}\n"
                if evidence:
                    content += f"- 证据: {evidence}\n"
                content += "\n"

        return ReportSection(
            title="三、故障因果链（Causal Chain）",
            content=content.strip(),
            section_type="causal_chain",
            data={'causal_chain': causal_chain_data}
        )

    def _create_evidence_chain_section(self, result: ProcessingResult) -> ReportSection:
        all_evidence_chains = []
        for analysis in result.analysis_results:
            if analysis.evidence_chain:
                all_evidence_chains.append(analysis.evidence_chain)

        if not all_evidence_chains:
            return ReportSection(
                title="证据链",
                content="暂无证据链数据",
                section_type="evidence_chain",
                data={}
            )

        evidence_chain_data = all_evidence_chains[0] if all_evidence_chains else {}

        description = evidence_chain_data.get('description', '')
        evidences = evidence_chain_data.get('evidences', [])

        content = "### 证据链（Evidence Chain）\n\n"
        if description:
            content += f"{description}\n\n"

        if evidences:
            content += "#### 关键证据\n\n"
            relevance_names = {
                'direct': '直接关联',
                'indirect': '间接关联',
                'supporting': '辅助支撑'
            }
            evidence_type_names = {
                'log': '日志条目',
                'exception': '异常信息',
                'metric': '系统指标',
                'trace': '链路追踪'
            }
            for idx, ev in enumerate(evidences, 1):
                ev_timestamp = ev.get('timestamp', 'N/A')
                ev_type = ev.get('evidence_type', 'unknown')
                ev_content = ev.get('content', '')
                ev_relevance = ev.get('relevance', '')

                display_type = evidence_type_names.get(ev_type, ev_type)
                display_relevance = relevance_names.get(ev_relevance, ev_relevance)

                content += f"**证据 {idx}** [{ev_timestamp}]\n"
                content += f"- 类型: {display_type}\n"
                content += f"- 内容: {ev_content}\n"
                content += f"- 关联度: {display_relevance}\n\n"

        return ReportSection(
            title="四、证据链（Evidence Chain）",
            content=content.strip(),
            section_type="evidence_chain",
            data={'evidence_chain': evidence_chain_data}
        )

    def _create_response_actions_section(self, result: ProcessingResult) -> ReportSection:
        all_response_actions = []
        for analysis in result.analysis_results:
            if analysis.response_actions:
                all_response_actions.append(analysis.response_actions)

        if not all_response_actions:
            return ReportSection(
                title="处置动作建议",
                content="暂无处置动作建议数据",
                section_type="response_actions",
                data={}
            )

        response_data = all_response_actions[0] if all_response_actions else {}

        description = response_data.get('description', '')
        emergency_actions = response_data.get('emergency_actions', [])
        troubleshooting_actions = response_data.get('troubleshooting_actions', [])
        recovery_actions = response_data.get('recovery_actions', [])

        content = "### 处置动作建议（Immediate Response Actions）\n\n"
        if description:
            content += f"{description}\n\n"

        if emergency_actions:
            content += "#### 应急止血动作\n\n"
            for action in emergency_actions:
                action_name = action.get('action_name', '')
                timing = action.get('timing', '')
                steps = action.get('steps', '')
                expected_effect = action.get('expected_effect', '')
                notes = action.get('notes', '')

                content += f"- **{action_name}**\n"
                if timing:
                    content += f"  - 执行时机: {timing}\n"
                if steps:
                    content += f"  - 执行步骤: {steps}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if notes:
                    content += f"  - 注意事项: {notes}\n"
                content += "\n"

        if troubleshooting_actions:
            content += "#### 排查定位动作\n\n"
            for action in troubleshooting_actions:
                action_name = action.get('action_name', '')
                timing = action.get('timing', '')
                steps = action.get('steps', '')
                expected_effect = action.get('expected_effect', '')
                notes = action.get('notes', '')

                content += f"- **{action_name}**\n"
                if timing:
                    content += f"  - 执行时机: {timing}\n"
                if steps:
                    content += f"  - 执行步骤: {steps}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if notes:
                    content += f"  - 注意事项: {notes}\n"
                content += "\n"

        if recovery_actions:
            content += "#### 恢复验证动作\n\n"
            for action in recovery_actions:
                action_name = action.get('action_name', '')
                timing = action.get('timing', '')
                steps = action.get('steps', '')
                expected_effect = action.get('expected_effect', '')
                notes = action.get('notes', '')

                content += f"- **{action_name}**\n"
                if timing:
                    content += f"  - 执行时机: {timing}\n"
                if steps:
                    content += f"  - 执行步骤: {steps}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if notes:
                    content += f"  - 注意事项: {notes}\n"
                content += "\n"

        return ReportSection(
            title="五、处置动作建议（Immediate Response Actions）",
            content=content.strip(),
            section_type="response_actions",
            data={'response_actions': response_data}
        )

    def _create_remediation_section(self, result: ProcessingResult) -> ReportSection:
        all_remediations = []
        for analysis in result.analysis_results:
            if analysis.remediation:
                all_remediations.append(analysis.remediation)

        if not all_remediations:
            return ReportSection(
                title="整改建议",
                content="暂无整改建议数据",
                section_type="remediation",
                data={}
            )

        remediation_data = all_remediations[0] if all_remediations else {}

        immediate = remediation_data.get('immediate', [])
        root_cause_fix = remediation_data.get('root_cause_fix', [])
        architecture_monitoring = remediation_data.get('architecture_monitoring', [])

        content = "### 整改建议（Rectification Suggestions）\n\n"

        if immediate:
            content += "#### 立即处置（Immediate Actions）\n\n"
            content += "**目标**: 快速恢复服务，最小化业务影响 | **时间要求**: 1小时内可执行\n\n"
            for action in immediate:
                action_text = action.get('action', '')
                target = action.get('target', '')
                expected_effect = action.get('expected_effect', '')
                effort = action.get('effort_estimate', '')

                content += f"- **{action_text}**\n"
                if target:
                    content += f"  - 目标: {target}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if effort:
                    content += f"  - 工作量: {effort}\n"
                content += "\n"

        if root_cause_fix:
            content += "#### 根因解决（Root Cause Fix）\n\n"
            content += "**目标**: 彻底修复导致故障的根本问题 | **时间要求**: 短期Sprint内完成（1-2周）\n\n"
            for action in root_cause_fix:
                action_text = action.get('action', '')
                target = action.get('target', '')
                expected_effect = action.get('expected_effect', '')
                effort = action.get('effort_estimate', '')

                content += f"- **{action_text}**\n"
                if target:
                    content += f"  - 目标: {target}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if effort:
                    content += f"  - 工作量: {effort}\n"
                content += "\n"

        if architecture_monitoring:
            content += "#### 架构/监控改进（Architecture & Monitoring）\n\n"
            content += "**目标**: 提升系统整体稳定性和可观测性 | **时间要求**: 季度规划级别（1-3个月）\n\n"
            for action in architecture_monitoring:
                action_text = action.get('action', '')
                target = action.get('target', '')
                expected_effect = action.get('expected_effect', '')
                effort = action.get('effort_estimate', '')

                content += f"- **{action_text}**\n"
                if target:
                    content += f"  - 目标: {target}\n"
                if expected_effect:
                    content += f"  - 预期效果: {expected_effect}\n"
                if effort:
                    content += f"  - 工作量: {effort}\n"
                content += "\n"

        return ReportSection(
            title="六、整改建议（Rectification Suggestions）",
            content=content.strip(),
            section_type="remediation",
            data={'remediation': remediation_data}
        )

    def _create_combined_error_section(self, result: ProcessingResult) -> ReportSection:
        error_section = self._create_error_analysis_section(result)
        pattern_section = self._create_pattern_analysis_section(result)

        content = "### 错误分析\n\n"
        content += "#### 关键错误分析\n\n"
        content += error_section.content.replace("### 关键错误分析\n\n", "") + "\n\n"
        content += "#### 错误模式分析\n\n"
        content += pattern_section.content.replace("### 错误模式分析\n\n", "")

        combined_data = {
            '关键错误': error_section.data.get('关键错误', []),
            '错误模式统计': pattern_section.data.get('错误模式统计', {})
        }

        return ReportSection(
            title="3. 错误分析",
            content=content.strip(),
            section_type="combined_error",
            data=combined_data
        )

    def _create_trends_timeline_section(self, result: ProcessingResult) -> ReportSection:
        trends_section = self._create_trends_section(result)
        timeline_section = self._create_timeline_section(result)

        content = "### 趋势识别与故障时间线\n\n"
        content += "#### 趋势识别\n\n"
        content += trends_section.content.replace("### 趋势识别\n\n", "") + "\n\n"
        content += "#### 故障时间线\n\n"
        content += timeline_section.content.replace("### 故障时间线\n\n", "")

        combined_data = {
            '趋势识别': trends_section.data.get('趋势识别', []),
            '时间线': timeline_section.data.get('timeline', {})
        }

        return ReportSection(
            title="4. 趋势识别与故障时间线",
            content=content.strip(),
            section_type="trends_timeline",
            data=combined_data
        )

    def _create_root_cause_analysis_section(self, result: ProcessingResult) -> ReportSection:
        root_cause_section = self._create_root_cause_section(result)
        causal_chain_section = self._create_causal_chain_section(result)
        evidence_chain_section = self._create_evidence_chain_section(result)

        content = "### 根因分析\n\n"
        content += "#### 5.1 根因推断\n\n"
        content += root_cause_section.content.replace("### 根因推断（Root Cause Inference）\n\n", "") + "\n\n"
        content += "#### 5.2 故障因果链\n\n"
        content += causal_chain_section.content.replace("### 故障因果链（Causal Chain）\n\n", "") + "\n\n"
        content += "#### 5.3 证据链\n\n"
        content += evidence_chain_section.content.replace("### 证据链（Evidence Chain）\n\n", "")

        combined_data = {
            '根因推断': root_cause_section.data.get('root_cause', {}),
            '因果链': causal_chain_section.data.get('causal_chain', {}),
            '证据链': evidence_chain_section.data.get('evidence_chain', {})
        }

        return ReportSection(
            title="5. 根因分析",
            content=content.strip(),
            section_type="root_cause_analysis",
            data=combined_data
        )

    def _create_disposal_remediation_section(self, result: ProcessingResult) -> ReportSection:
        response_section = self._create_response_actions_section(result)
        remediation_section = self._create_remediation_section(result)
        suggestions_section = self._create_suggestions_section(result)

        content = "### 处置与整改建议\n\n"
        content += "#### 6.1 处置动作建议\n\n"
        content += response_section.content.replace("### 处置动作建议（Immediate Response Actions）\n\n", "") + "\n\n"
        content += "#### 6.2 整改建议\n\n"
        content += remediation_section.content.replace("### 整改建议（Rectification Suggestions）\n\n", "") + "\n\n"
        content += "#### 6.3 解决建议（运维+开发建议）\n\n"
        content += suggestions_section.content.replace("### 解决建议\n\n", "")

        combined_data = {
            '处置动作建议': response_section.data.get('response_actions', {}),
            '整改建议': remediation_section.data.get('remediation', {}),
            '解决建议': suggestions_section.data
        }

        return ReportSection(
            title="6. 处置与整改建议",
            content=content.strip(),
            section_type="disposal_remediation",
            data=combined_data
        )

    def _generate_summary(self, result: ProcessingResult) -> str:
        summaries = []
        for analysis in result.analysis_results:
            if analysis.summary:
                summaries.append(analysis.summary)

        if not summaries:
            return f"本次分析处理了 {result.total_lines:,} 行日志数据，识别了 {result.statistics.get('by_level', {}).get('ERROR', 0):,} 个错误。"

        return " ".join(summaries[:3])

    def to_html(self, report: Report) -> str:
        """Generate HTML report with light theme."""
        sections_html = ""
        
        for section in report.sections:
            if section.section_type == "suggestions":
                sections_html += self._generate_suggestions_html(section)
            elif section.section_type == "error_analysis":
                sections_html += self._generate_error_analysis_html(section)
            elif section.section_type == "statistics":
                sections_html += self._generate_statistics_html(section)
            else:
                sections_html += self._generate_default_section_html(section)
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.title}</title>
    <style>
        :root {{
            --primary: #007AFF;
            --success: #34C759;
            --warning: #FF9500;
            --danger: #FF3B30;
            --bg: #FFFFFF;
            --bg-card: #FAFAFA;
            --bg-hover: #F5F5F7;
            --text: #1D1D1F;
            --text-secondary: #6E6E73;
            --text-tertiary: #8E8E93;
            --border: #E5E5EA;
            --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
            --radius: 12px;
            --radius-sm: 8px;
            --font: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.5; }}
        
        .header {{ 
            background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%); 
            color: white; 
            padding: 2rem; 
            text-align: center;
        }}
        .header h1 {{ font-size: 1.75rem; font-weight: 600; margin-bottom: 0.5rem; }}
        .header p {{ opacity: 0.9; font-size: 0.95rem; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
            max-width: 1200px;
            margin: -2rem auto 2rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.25rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            text-align: center;
        }}
        .stat-value {{ font-size: 1.75rem; font-weight: 700; color: var(--primary); }}
        .stat-label {{ font-size: 0.875rem; color: var(--text-secondary); margin-top: 0.25rem; }}
        .stat-value.success {{ color: var(--success); }}
        .stat-value.warning {{ color: var(--warning); }}
        .stat-value.danger {{ color: var(--danger); }}
        
        .main {{ max-width: 1200px; margin: 0 auto; padding: 0 1.5rem 3rem; }}
        
        .section-card {{
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            margin-bottom: 1rem;
            overflow: hidden;
        }}
        .section-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-header:hover {{ background: var(--bg-hover); }}
        .section-title {{ font-weight: 600; font-size: 1rem; }}
        .section-toggle {{ color: var(--text-tertiary); transition: transform 0.3s; }}
        .section-toggle.expanded {{ transform: rotate(180deg); }}
        .section-body {{ padding: 1.5rem; }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        .data-table th {{
            text-align: left;
            padding: 0.75rem;
            background: var(--bg-card);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
        }}
        .data-table td {{
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
        }}
        .data-table tr:hover {{ background: var(--bg-hover); }}
        
        .severity-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .severity-critical {{ background: rgba(255, 59, 48, 0.15); color: var(--danger); }}
        .severity-high {{ background: rgba(255, 149, 0, 0.15); color: var(--warning); }}
        .severity-medium {{ background: rgba(0, 122, 255, 0.15); color: var(--primary); }}
        
        .suggestions-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }}
        .suggestion-card {{
            background: var(--bg-card);
            padding: 1.25rem;
            border-radius: var(--radius-sm);
            border-left: 3px solid var(--primary);
        }}
        .suggestion-header {{
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        .suggestion-list {{
            list-style: none;
        }}
        .suggestion-list li {{
            padding: 0.5rem 0;
            font-size: 0.9rem;
            border-bottom: 1px solid var(--border);
        }}
        .suggestion-list li:last-child {{ border-bottom: none; }}
        
        .trend-list {{
            list-style: none;
            counter-reset: trend;
        }}
        .trend-list li {{
            position: relative;
            padding: 0.75rem 0 0.75rem 2.5rem;
            border-bottom: 1px solid var(--border);
            counter-increment: trend;
        }}
        .trend-list li::before {{
            content: counter(trend);
            position: absolute;
            left: 0;
            width: 24px;
            height: 24px;
            background: rgba(0, 122, 255, 0.1);
            color: var(--primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .summary-text {{ font-size: 1rem; line-height: 1.7; color: var(--text); }}
        
        .chart-bar-container {{
            display: flex;
            align-items: flex-end;
            gap: 0.5rem;
            height: 100px;
            padding: 1rem 0;
        }}
        .chart-bar {{
            flex: 1;
            background: linear-gradient(180deg, var(--primary) 0%, rgba(0, 122, 255, 0.6) 100%);
            border-radius: 4px 4px 0 0;
            position: relative;
        }}
        .chart-bar-label {{
            position: absolute;
            bottom: -1.5rem;
            left: 50%;
            transform: translateX(-50%);
            font-size: 0.7rem;
            color: var(--text-secondary);
            white-space: nowrap;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .suggestions-grid {{ grid-template-columns: 1fr; }}
            .section-body {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {report.title}</h1>
        <p>{report.generated_at.strftime('%Y-%m-%d %H:%M:%S')} | {report.file_size}</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{report.total_lines:,}</div>
            <div class="stat-label">总行数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value danger">{report.total_errors:,}</div>
            <div class="stat-label">错误数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value warning">{report.total_warnings:,}</div>
            <div class="stat-label">警告数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value success">100%</div>
            <div class="stat-label">处理进度</div>
        </div>
    </div>
    
    <div class="main">
        {sections_html}
    </div>
    
    <script>
        document.querySelectorAll('.section-header').forEach(header => {{
            header.addEventListener('click', () => {{
                const card = header.parentElement;
                const body = header.nextElementSibling;
                const toggle = header.querySelector('.section-toggle');
                body.style.display = body.style.display === 'none' ? 'block' : 'none';
                toggle.classList.toggle('expanded');
            }});
        }});
    </script>
</body>
</html>"""

    def _generate_default_section_html(self, section: ReportSection) -> str:
        content = section.content.replace('\n', '<br>').replace('**', '<strong>').replace('</strong>', '</strong>')
        return f"""
<div class="section-card">
    <div class="section-header">
        <span class="section-title">📄 {section.title}</span>
        <span class="section-toggle">▼</span>
    </div>
    <div class="section-body" style="display: block;">
        <div class="summary-text">{content}</div>
    </div>
</div>"""

    def _generate_statistics_html(self, section: ReportSection) -> str:
        data = section.data or {}
        by_level = data.get('错误级别分布', {})
        error_types = data.get('错误类型统计', {})
        top_classes = data.get('高频错误类', {})
        
        level_rows = ''.join([f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in by_level.items()])
        type_rows = ''.join([f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in list(error_types.items())[:10]])
        class_rows = ''.join([f'<tr><td>{k}</td><td>{v:,}</td></tr>' for k, v in list(top_classes.items())[:10]])
        
        return f"""
<div class="section-card">
    <div class="section-header">
        <span class="section-title">📊 {section.title}</span>
        <span class="section-toggle">▼</span>
    </div>
    <div class="section-body" style="display: block;">
        <h4 style="margin: 0 0 1rem; font-weight: 600;">错误级别分布</h4>
        <div class="chart-bar-container">
            {' '.join([f'<div class="chart-bar" style="height:{(v/max(list(by_level.values()) + [1]))*100}%"><div class="chart-bar-label">{k}</div></div>' for k, v in by_level.items()])}
        </div>
        
        <h4 style="margin: 1.5rem 0 1rem; font-weight: 600;">错误类型统计</h4>
        <table class="data-table">
            <thead><tr><th>类型</th><th>数量</th></tr></thead>
            <tbody>{type_rows}</tbody>
        </table>
        
        <h4 style="margin: 1.5rem 0 1rem; font-weight: 600;">高频错误类</h4>
        <table class="data-table">
            <thead><tr><th>类名</th><th>数量</th></tr></thead>
            <tbody>{class_rows}</tbody>
        </table>
    </div>
</div>"""

    def _generate_error_analysis_html(self, section: ReportSection) -> str:
        errors = section.data.get('关键错误', []) if section.data else []
        rows = ''
        for error in errors[:8]:
            severity_class = 'severity-' + error.get('severity', 'medium').lower()
            rows += f"""
<tr>
    <td>{error.get('error_type', '')}</td>
    <td>{error.get('description', '')}</td>
    <td>{error.get('count', 0):,}</td>
    <td><span class="severity-badge {severity_class}">{error.get('severity', '')}</span></td>
</tr>"""
        
        return f"""
<div class="section-card">
    <div class="section-header">
        <span class="section-title">🔴 {section.title}</span>
        <span class="section-toggle">▼</span>
    </div>
    <div class="section-body" style="display: block;">
        <table class="data-table">
            <thead><tr><th>错误类型</th><th>描述</th><th>次数</th><th>严重程度</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
</div>"""

    def _generate_suggestions_html(self, section: ReportSection) -> str:
        data = section.data or {}
        ops = data.get('运维建议', [])
        dev = data.get('开发建议', [])
        
        ops_items = ''.join([f'<li>{item.get("suggestion", "")}</li>' for item in ops])
        dev_items = ''.join([f'<li>{item.get("suggestion", "")}</li>' for item in dev])
        
        return f"""
<div class="section-card">
    <div class="section-header">
        <span class="section-title">💡 {section.title}</span>
        <span class="section-toggle">▼</span>
    </div>
    <div class="section-body" style="display: block;">
        <div class="suggestions-grid">
            <div class="suggestion-card">
                <div class="suggestion-header">🔧 运维建议</div>
                <ul class="suggestion-list">{ops_items}</ul>
            </div>
            <div class="suggestion-card">
                <div class="suggestion-header">👨💻 开发建议</div>
                <ul class="suggestion-list">{dev_items}</ul>
            </div>
        </div>
    </div>
</div>"""

    def save_report(
        self,
        report: Report,
        format: str = "all",
        prefix: str = "report"
    ) -> List[str]:
        saved_files = []
        base_name = os.path.splitext(os.path.basename(report.file_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"{prefix}_【{base_name}】_{timestamp}"

        formats = format.split('+') if '+' in format else [format]
        
        need_json = format == "all" or "json" in formats
        need_md = format == "all" or "markdown" in formats or "md" in formats
        need_html = format == "all" or "html" in formats
        need_pdf = format == "all" or "pdf" in formats
        need_word = format == "all" or "word" in formats or "docx" in formats

        if need_json:
            json_path = os.path.join(self.output_dir, f"{report_name}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
            saved_files.append(json_path)

        if need_md:
            md_path = os.path.join(self.output_dir, f"{report_name}.md")
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(report.to_markdown())
            saved_files.append(md_path)

        if need_html:
            html_path = os.path.join(self.output_dir, f"{report_name}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.to_html(report))
            saved_files.append(html_path)

        if need_pdf:
            try:
                pdf_path = os.path.join(self.output_dir, f"{report_name}.pdf")
                self._save_as_pdf(report, pdf_path)
                saved_files.append(pdf_path)
            except ImportError:
                logging.warning("PDF 生成跳过: reportlab 模块未安装")
            except Exception as e:
                logging.warning(f"PDF 生成失败: {e}")

        if need_word:
            try:
                word_path = os.path.join(self.output_dir, f"{report_name}.docx")
                self._save_as_word(report, word_path)
                saved_files.append(word_path)
            except ImportError:
                logging.warning("Word 生成跳过: python-docx 模块未安装")
            except Exception as e:
                logging.warning(f"Word 生成失败: {e}")

        return saved_files

    def _convert_markdown_to_pdf_paragraph(self, md_content: str) -> str:
        """将 Markdown 格式转换为 PDF 支持的 HTML-like 格式"""
        if not md_content:
            return ""
        
        import re
        
        content = md_content
        
        # 处理代码块（先保存再处理，避免干扰其他转换）
        code_blocks = []
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"
        content = re.sub(r'```[\s\S]*?```', save_code_block, content)
        
        # 处理表格（先保存）
        table_blocks = []
        def save_table(match):
            table_blocks.append(match.group(0))
            return f"__TABLE_BLOCK_{len(table_blocks)-1}__"
        content = re.sub(r'\|.*\|\n\|[-|]+\|\n([\s\S]*?)(?=\n\n|\Z)', save_table, content)
        
        # 处理内联代码
        content = re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', content)
        
        # 正确处理粗体标记：**text** → <b>text</b>
        content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', content)
        content = re.sub(r'__(.+?)__', r'<b>\1</b>', content)
        
        # 处理斜体
        content = re.sub(r'\*(.+?)\*', r'<i>\1</i>', content)
        content = re.sub(r'_(.+?)_', r'<i>\1</i>', content)
        
        # 处理标题（简化处理）
        content = re.sub(r'\n### (.+)', r'\n<br/><b fontsize="12">\1</b>', content)
        content = re.sub(r'\n## (.+)', r'\n<br/><b fontsize="14">\1</b>', content)
        content = re.sub(r'\n# (.+)', r'\n<br/><b fontsize="16">\1</b>', content)
        
        # 处理有序列表
        content = re.sub(r'\n(\d+)\. ', r'\n<br/>\1. ', content)
        
        # 处理无序列表
        content = re.sub(r'\n- ', r'\n<br/>• ', content)
        content = re.sub(r'\n\* ', r'\n<br/>• ', content)
        
        # 处理嵌套列表（增加缩进）
        content = re.sub(r'(\n• )(\s+• )', r'\1&nbsp;&nbsp;&nbsp;&nbsp;• ', content)
        
        # 处理链接（简化处理）
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'<u>\1</u>', content)
        
        # 处理水平线
        content = re.sub(r'\n[-*=_]{3,}\n', r'\n<br/>────────────────────────────────────────<br/>\n', content)
        
        # 恢复表格（转换为文本格式）
        for i, table_content in enumerate(table_blocks):
            content = content.replace(f"__TABLE_BLOCK_{i}__", 
                                     self._convert_markdown_table_to_pdf(table_content))
        
        # 恢复代码块
        for i, code_block in enumerate(code_blocks):
            # 移除代码块标记
            code_content = re.sub(r'```(\w+)?\n?', '', code_block)
            code_content = code_content.replace('\n', '<br/>')
            code_content = code_content.replace('&', '&amp;')
            code_content = code_content.replace('<', '&lt;')
            code_content = code_content.replace('>', '&gt;')
            content = content.replace(f"__CODE_BLOCK_{i}__", 
                                     f'<br/><font name="Courier" fontSize="8">{code_content}</font><br/>')
        
        # 处理换行
        content = content.replace('\n', '<br/>')
        
        # 处理中文标点符号（确保正确显示）
        content = content.replace('，', '，')
        content = content.replace('。', '。')
        content = content.replace('！', '！')
        content = content.replace('？', '？')
        content = content.replace('；', '；')
        content = content.replace('：', '：')
        content = content.replace('（', '（')
        content = content.replace('）', '）')
        content = content.replace('【', '【')
        content = content.replace('】', '】')
        content = content.replace('“', '“')
        content = content.replace('”', '”')
        content = content.replace('‘', '‘')
        content = content.replace('’', '’')
        
        # 处理特殊字符
        content = content.replace('&', '&amp;')
        content = content.replace('<', '&lt;')
        content = content.replace('>', '&gt;')
        
        return content
    
    def _convert_markdown_table_to_pdf(self, table_content: str) -> str:
        """将Markdown表格转换为PDF支持的文本格式"""
        import re
        
        lines = table_content.strip().split('\n')
        if len(lines) < 2:
            return ""
        
        # 解析表格
        header = lines[0].strip('|').split('|')
        body = lines[2:]
        
        # 移除空白字符
        header = [cell.strip() for cell in header]
        body_rows = []
        for line in body:
            cells = line.strip('|').split('|')
            cells = [cell.strip() for cell in cells]
            body_rows.append(cells)
        
        # 计算最大列宽
        max_cols = max(len(header), max(len(row) for row in body_rows))
        col_widths = [0] * max_cols
        
        for i, cell in enumerate(header):
            col_widths[i] = max(col_widths[i], len(cell))
        for row in body_rows:
            for i, cell in enumerate(row):
                if i < max_cols:
                    col_widths[i] = max(col_widths[i], len(cell))
        
        # 生成表格文本
        result = '<br/>'
        separator = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
        
        result += separator + '<br/>'
        
        # 表头
        row_cells = []
        for i, cell in enumerate(header):
            padding = col_widths[i] - len(cell)
            row_cells.append(f' {cell}{" " * padding} ')
        result += '|' + '|'.join(row_cells) + '|<br/>'
        
        result += separator + '<br/>'
        
        # 表体
        for row in body_rows:
            row_cells = []
            for i in range(max_cols):
                cell = row[i] if i < len(row) else ''
                padding = col_widths[i] - len(cell)
                row_cells.append(f' {cell}{" " * padding} ')
            result += '|' + '|'.join(row_cells) + '|<br/>'
        
        result += separator + '<br/>'
        
        return result

    def _save_as_pdf(self, report: Report, output_path: str) -> None:
        """将报告保存为 PDF 格式"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        )
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        # 注册中文字体
        try:
            font_path = None
            subfont_index = 0
            
            # macOS 系统字体路径（TTC 集合文件需要指定 subfontIndex）
            mac_fonts = [
                ('/System/Library/Fonts/PingFang.ttc', 0),
                ('/System/Library/Fonts/PingFang.ttc', 1),
                ('/System/Library/Fonts/STHeiti Light.ttc', 0),
                ('/System/Library/Fonts/Supplemental/Songti.ttc', 0),
                ('/Library/Fonts/Arial Unicode.ttf', 0),
            ]
            # 其他系统字体路径
            other_fonts = [
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            ]
            
            for fp, idx in mac_fonts:
                if os.path.exists(fp):
                    font_path = fp
                    subfont_index = idx
                    break
            
            if not font_path:
                for fp in other_fonts:
                    if os.path.exists(fp):
                        font_path = fp
                        subfont_index = 0
                        break
            
            if font_path:
                pdfmetrics.registerFont(TTFont('Chinese', font_path, subfontIndex=subfont_index))
                chinese_font = 'Chinese'
            else:
                chinese_font = 'Helvetica'
                logging.warning("未找到中文字体，PDF 中的中文可能无法正常显示")
        except Exception as e:
            chinese_font = 'Helvetica'
            logging.warning(f"注册中文字体失败: {e}")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=report.title
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            textColor=colors.HexColor('#1D1D1F'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=chinese_font
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#007AFF'),
            spaceBefore=15,
            spaceAfter=10,
            fontName=chinese_font
        )
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=8,
            fontName=chinese_font
        )
        code_style = ParagraphStyle(
            'CodeStyle',
            parent=styles['Code'],
            fontSize=8,
            leading=10,
            fontName=chinese_font
        )

        story = []
        story.append(Paragraph(report.title, title_style))
        story.append(Paragraph(
            f"生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            body_style
        ))
        story.append(Paragraph(f"文件: {report.file_path}", body_style))
        story.append(Paragraph(f"文件大小: {report.file_size}", body_style))
        story.append(Spacer(1, 0.5*cm))

        stats_data = [
            ['总行数', f"{report.total_lines:,}"],
            ['错误数', f"{report.total_errors:,}"],
            ['警告数', f"{report.total_warnings:,}"],
            ['处理进度', '100%']
        ]
        stats_table = Table(stats_data, colWidths=[4*cm, 6*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F5F5F7')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1D1D1F')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E5EA'))
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.8*cm))

        for section in report.sections:
            # 章节标题（与Word/MD保持一致，不添加图标）
            story.append(Paragraph(section.title, heading_style))
            
            # 转换 Markdown 格式
            content = self._convert_markdown_to_pdf_paragraph(section.content)
            story.append(Paragraph(content, body_style))
            
            # 数据详情部分（与Word/MD保持一致，使用更美观的格式）
            if section.data:
                # 只在有实际数据时显示
                data_text = json.dumps(section.data, indent=2, ensure_ascii=False)
                # 检查数据是否非空
                if data_text and data_text != '{}' and data_text != '[]':
                    story.append(Spacer(1, 0.2*cm))
                    story.append(Paragraph("<b>数据统计:</b>", body_style))
                    # 使用等宽字体显示JSON数据
                    data_lines = data_text.split('\n')
                    for line in data_lines:
                        if line.strip():
                            story.append(Paragraph(f'<font name="Courier" fontSize="8">{line}</font>', body_style))
            
            story.append(Spacer(1, 0.6*cm))

        # 总体摘要（与Word/MD保持一致，不添加图标）
        if report.summary:
            story.append(Paragraph("7. 总体摘要", heading_style))
            summary_content = self._convert_markdown_to_pdf_paragraph(report.summary)
            story.append(Paragraph(summary_content, body_style))

        doc.build(story)

    def _add_markdown_paragraph_to_word(self, doc, md_content):
        """将 Markdown 格式内容添加到 Word 文档"""
        if not md_content:
            return
        
        import re
        
        # 分割段落
        paragraphs = re.split(r'\n\n+', md_content)
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # 检查是否为代码块
            if para.startswith('```'):
                # 移除代码块标记
                code_content = re.sub(r'```(\w+)?\n?', '', para)
                code_para = doc.add_paragraph(code_content.strip())
                code_para.style = 'No Spacing'
                for run in code_para.runs:
                    run.font.name = 'Courier New'
                    run.font.size = Pt(9)
                doc.add_paragraph()
                continue
            
            # 检查是否为表格
            if '|' in para and re.match(r'^\|.*\|$', para.split('\n')[0]):
                self._add_markdown_table_to_word(doc, para)
                doc.add_paragraph()
                continue
            
            # 检查是否为标题
            title_match = re.match(r'^(#{1,6})\s+(.+)', para)
            if title_match:
                level = len(title_match.group(1))
                doc.add_heading(title_match.group(2), level=level)
                continue
            
            # 检查是否为列表项
            list_match = re.match(r'^(\d+)\.\s+(.+)', para)
            if list_match:
                # 有序列表
                current_para = doc.add_paragraph()
                current_para.style = 'List Number'
                self._add_formatted_run_to_word(current_para, list_match.group(2))
                continue
            
            if para.startswith(('- ', '* ', '+ ')):
                # 无序列表
                current_para = doc.add_paragraph()
                current_para.style = 'List Bullet'
                self._add_formatted_run_to_word(current_para, para[2:])
                continue
            
            # 检查是否为水平线
            if re.match(r'^[-*=_]{3,}$', para.strip()):
                doc.add_paragraph().add_run('─' * 50).font.size = Pt(1)
                doc.add_paragraph()
                continue
            
            # 普通段落（处理行内格式）
            current_para = doc.add_paragraph()
            self._add_formatted_run_to_word(current_para, para)
    
    def _add_formatted_run_to_word(self, para, text):
        """向Word段落添加带格式的文本"""
        import re
        
        # 使用正则表达式匹配所有格式元素
        pattern = r'(\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|`[^`]+`|\[([^\]]+)\]\([^)]+\))'
        parts = re.split(pattern, text)
        
        for part in parts:
            if not part:
                continue
            
            # 粗体
            if (part.startswith('**') and part.endswith('**')) or (part.startswith('__') and part.endswith('__')):
                run = para.add_run(part[2:-2])
                run.bold = True
            # 斜体
            elif (part.startswith('*') and part.endswith('*')) or (part.startswith('_') and part.endswith('_')):
                run = para.add_run(part[1:-1])
                run.italic = True
            # 行内代码
            elif part.startswith('`') and part.endswith('`'):
                run = para.add_run(part[1:-1])
                run.font.name = 'Courier New'
                run.font.size = Pt(9)
            # 链接
            elif '[' in part and '](' in part and part.endswith(')'):
                link_match = re.match(r'\[([^\]]+)\]\([^)]+\)', part)
                if link_match:
                    run = para.add_run(link_match.group(1))
                    run.underline = True
            else:
                para.add_run(part)
    
    def _add_markdown_table_to_word(self, doc, table_content):
        """将Markdown表格转换为Word表格"""
        import re
        
        lines = table_content.strip().split('\n')
        if len(lines) < 2:
            return
        
        # 解析表格
        header = lines[0].strip('|').split('|')
        separator = lines[1]
        body = lines[2:]
        
        # 移除空白字符
        header = [cell.strip() for cell in header]
        body_rows = []
        for line in body:
            cells = line.strip('|').split('|')
            cells = [cell.strip() for cell in cells]
            body_rows.append(cells)
        
        # 创建表格
        num_rows = len(body_rows) + 1
        num_cols = len(header)
        
        table = doc.add_table(rows=num_rows, cols=num_cols)
        table.style = 'Light Grid Accent 1'
        
        # 设置表头
        for i, cell_text in enumerate(header):
            table.cell(0, i).text = cell_text
            for run in table.cell(0, i).paragraphs[0].runs:
                run.bold = True
        
        # 设置表体
        for i, row in enumerate(body_rows):
            for j, cell_text in enumerate(row):
                if j < num_cols:
                    table.cell(i + 1, j).text = cell_text

    def _save_as_word(self, report: Report, output_path: str) -> None:
        """将报告保存为 Word 格式"""
        from docx import Document
        from docx.shared import Pt, RGBColor, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        
        title = doc.add_heading(report.title, level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        info_para = doc.add_paragraph()
        info_para.add_run(f"生成时间: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n").italic = True
        info_para.add_run(f"文件: {report.file_path}\n").italic = True
        info_para.add_run(f"文件大小: {report.file_size}").italic = True

        doc.add_paragraph()
        stats_table = doc.add_table(rows=4, cols=2)
        stats_table.style = 'Light Grid Accent 1'
        stats_data = [
            ('总行数', f"{report.total_lines:,}"),
            ('错误数', f"{report.total_errors:,}"),
            ('警告数', f"{report.total_warnings:,}"),
            ('处理进度', '100%')
        ]
        for i, (k, v) in enumerate(stats_data):
            stats_table.cell(i, 0).text = k
            stats_table.cell(i, 1).text = v

        doc.add_paragraph()

        for section in report.sections:
            # 移除图标，与PDF格式保持一致
            doc.add_heading(section.title, level=1)
            # 使用新方法处理 Markdown 格式
            self._add_markdown_paragraph_to_word(doc, section.content)
            
            # 数据详情部分（与PDF格式保持一致）
            if section.data:
                data_text = json.dumps(section.data, indent=2, ensure_ascii=False)
                # 检查数据是否非空
                if data_text and data_text != '{}' and data_text != '[]':
                    doc.add_paragraph().add_run("数据统计:").bold = True
                    code_para = doc.add_paragraph(data_text)
                    for run in code_para.runs:
                        run.font.name = 'Courier New'
                        run.font.size = Pt(8)

        # 总体摘要（与PDF格式保持一致）
        if report.summary:
            doc.add_heading("7. 总体摘要", level=1)
            self._add_markdown_paragraph_to_word(doc, report.summary)

        doc.save(output_path)

    def _create_combined_overview_section(self, results: List[ProcessingResult]) -> ReportSection:
        """创建综合概览部分"""
        completed = sum(1 for r in results if r.status == 'completed')
        total_lines = sum(r.total_lines for r in results)
        total_errors = sum(
            r.statistics.get('by_level', {}).get('ERROR', 0) +
            r.statistics.get('by_level', {}).get('FATAL', 0)
            for r in results
        )
        
        content = f"""
**分析文件数**: {len(results)} 个
**已完成**: {completed}/{len(results)}
**总行数**: {total_lines:,}
**总错误数**: {total_errors:,}

### 文件列表
"""
        for i, result in enumerate(results, 1):
            content += f"{i}. `{os.path.basename(result.file_path)}` - {result.status}\n"

        return ReportSection(
            title="综合概览",
            content=content.strip(),
            section_type="overview",
            data={
                'total_files': len(results),
                'completed_files': completed,
                'total_lines': total_lines,
                'total_errors': total_errors
            }
        )

    def _create_file_summaries_section(self, results: List[ProcessingResult]) -> ReportSection:
        """创建各文件摘要部分"""
        content = ""
        for result in results:
            if result.status != 'completed':
                continue
                
            file_errors = (
                result.statistics.get('by_level', {}).get('ERROR', 0) +
                result.statistics.get('by_level', {}).get('FATAL', 0)
            )
            file_warnings = result.statistics.get('by_level', {}).get('WARN', 0)
            
            content += f"### {os.path.basename(result.file_path)}\n"
            content += f"- 状态: {result.status}\n"
            content += f"- 行数: {result.total_lines:,}\n"
            content += f"- 错误数: {file_errors:,}\n"
            content += f"- 警告数: {file_warnings:,}\n"
            
            # 添加分析摘要
            summaries = [a.summary for a in result.analysis_results if a.summary]
            if summaries:
                content += f"- 摘要: {summaries[0][:100]}...\n"
            
            content += "\n"

        return ReportSection(
            title="各文件分析摘要",
            content=content.strip(),
            section_type="summaries"
        )

    def _create_combined_statistics_section(self, results: List[ProcessingResult]) -> ReportSection:
        """创建综合统计部分"""
        all_stats = {
            'by_level': {'ERROR': 0, 'WARN': 0, 'INFO': 0, 'DEBUG': 0, 'FATAL': 0},
            'error_types': {},
            'top_classes': {}
        }

        for result in results:
            stats = result.statistics
            for level, count in stats.get('by_level', {}).items():
                if level in all_stats['by_level']:
                    all_stats['by_level'][level] += count
            
            for error_type, count in stats.get('error_types', {}).items():
                all_stats['error_types'][error_type] = all_stats['error_types'].get(error_type, 0) + count
            
            for class_name, count in stats.get('top_classes', {}).items():
                all_stats['top_classes'][class_name] = all_stats['top_classes'].get(class_name, 0) + count

        content = "### 错误级别分布\n\n"
        for level in ['ERROR', 'FATAL', 'WARN', 'INFO', 'DEBUG']:
            content += f"- {level}: {all_stats['by_level'][level]:,}\n"

        content += "\n### 错误类型Top 10\n\n"
        top_errors = sorted(all_stats['error_types'].items(), key=lambda x: x[1], reverse=True)[:10]
        for error_type, count in top_errors:
            content += f"- {error_type}: {count:,}\n"

        content += "\n### 涉及类Top 10\n\n"
        top_classes = sorted(all_stats['top_classes'].items(), key=lambda x: x[1], reverse=True)[:10]
        for class_name, count in top_classes:
            content += f"- {class_name}: {count:,}\n"

        return ReportSection(
            title="综合统计分析",
            content=content.strip(),
            section_type="statistics",
            data=all_stats
        )

    def _create_combined_suggestions_section(self, results: List[ProcessingResult]) -> ReportSection:
        """创建综合建议部分"""
        all_suggestions = []
        
        for result in results:
            for analysis in result.analysis_results:
                if analysis.suggestions:
                    all_suggestions.extend(analysis.suggestions)
        
        # 去重并排序
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        
        content = "基于所有文件的分析，以下是综合解决建议：\n\n"
        for idx, suggestion in enumerate(unique_suggestions[:5], 1):
            content += f"{idx}. {suggestion}\n"

        return ReportSection(
            title="综合解决建议",
            content=content.strip(),
            section_type="suggestions",
            data={'total_suggestions': len(unique_suggestions)}
        )

    def _generate_combined_summary(self, results: List[ProcessingResult]) -> str:
        """生成综合摘要"""
        completed = sum(1 for r in results if r.status == 'completed')
        total_errors = sum(
            r.statistics.get('by_level', {}).get('ERROR', 0) +
            r.statistics.get('by_level', {}).get('FATAL', 0)
            for r in results
        )
        
        summary = f"本次综合分析处理了 {len(results)} 个文件（{completed} 个成功），"
        summary += f"共 {sum(r.total_lines for r in results):,} 行日志，"
        summary += f"识别了 {total_errors:,} 个错误。"
        
        return summary

    def generate_batch_reports(
        self,
        results: List[ProcessingResult],
        format: str = "both"
    ) -> Dict[str, List[str]]:
        all_reports = {}

        for result in results:
            if result.status == "completed":
                report = self.generate_report(result)
                saved_files = self.save_report(report, format)
                all_reports[result.file_path] = saved_files

        return all_reports
