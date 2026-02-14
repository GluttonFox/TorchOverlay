"""日志分析工具 - 分析应用日志，发现问题并提供优化建议"""
import re
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict, Counter

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str
    logger_name: str
    message: str
    line_number: int


@dataclass
class LogIssue:
    """日志问题"""
    severity: str  # ERROR, WARNING, INFO
    category: str  # MEMORY, PERFORMANCE, ERROR, WARNING
    message: str
    count: int
    examples: List[str]
    suggestions: List[str]


class LogAnalyzer:
    """日志分析器

    分析应用日志，识别问题和提供优化建议。
    """

    # 常见问题模式
    PATTERNS = {
        'memory': {
            'OutOfMemory': r'OutOfMemoryError|MemoryError|memory.*full',
            'HighMemory': r'memory.*high|memory.*warning',
            'Leak': r'leak|memory.*grow|memory.*increase'
        },
        'performance': {
            'SlowOperation': r'took.*\d+.*second|slow|timeout',
            'HighLatency': r'latency.*high|delay.*high',
            'ResourceHeavy': r'expensive|heavy.*resource'
        },
        'error': {
            'Exception': r'Exception|Error|Failed',
            'Connection': r'connection.*error|connect.*fail',
            'FileNotFound': r'FileNotFound|No such file'
        },
        'warning': {
            'Deprecation': r'deprecated|will be removed',
            'Inefficient': r'inefficient|not recommended',
            'Retry': r'retry|retrying'
        }
    }

    def __init__(self, log_dir: str = "logs"):
        """初始化日志分析器

        Args:
            log_dir: 日志目录
        """
        self._log_dir = log_dir
        self._entries: List[LogEntry] = []
        self._issues: List[LogIssue] = []

    def analyze(self, max_files: int = 10) -> Dict:
        """分析日志文件

        Args:
            max_files: 分析的最大文件数

        Returns:
            分析结果字典
        """
        if not os.path.exists(self._log_dir):
            return {
                'status': 'error',
                'message': f'日志目录不存在: {self._log_dir}'
            }

        # 获取日志文件
        log_files = self._get_log_files(max_files)

        if not log_files:
            return {
                'status': 'info',
                'message': f'没有找到日志文件',
                'issues': []
            }

        # 解析日志
        self._entries = []
        for log_file in log_files:
            self._parse_log_file(log_file)

        # 分析问题
        self._analyze_issues()

        # 生成报告
        return self._generate_report()

    def _get_log_files(self, max_files: int) -> List[str]:
        """获取日志文件列表

        Args:
            max_files: 最大文件数

        Returns:
            日志文件路径列表
        """
        files = []
        if os.path.isdir(self._log_dir):
            for filename in os.listdir(self._log_dir):
                if filename.endswith('.log'):
                    file_path = os.path.join(self._log_dir, filename)
                    files.append(file_path)

        # 按修改时间排序（最新的在前）
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        return files[:max_files]

    def _parse_log_file(self, log_path: str) -> None:
        """解析单个日志文件

        Args:
            log_path: 日志文件路径
        """
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_number = 0
                for line in f:
                    line_number += 1
                    entry = self._parse_log_line(line, line_number)
                    if entry:
                        self._entries.append(entry)

        except Exception as e:
            logger.warning(f"解析日志文件失败: {log_path}, 错误: {e}")

    def _parse_log_line(self, line: str, line_number: int) -> Optional[LogEntry]:
        """解析单行日志

        Args:
            line: 日志行
            line_number: 行号

        Returns:
            日志条目或None
        """
        # 匹配日志格式: [2024-02-14 12:00:00] [LEVEL] logger_name - message
        pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*\[(\w+)\]\s*\[([\w.]+)\]\s*-\s*(.+)'

        match = re.match(pattern, line)
        if match:
            timestamp_str, level, logger_name, message = match.groups()
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return LogEntry(
                    timestamp=timestamp,
                    level=level,
                    logger_name=logger_name,
                    message=message,
                    line_number=line_number
                )
            except ValueError:
                pass

        return None

    def _analyze_issues(self) -> None:
        """分析日志中的问题"""
        self._issues = []

        # 按严重程度和类别统计
        severity_counter = defaultdict(int)
        category_counter = defaultdict(int)
        message_examples = defaultdict(list)

        for entry in self._entries:
            # 检查各种问题模式
            for category, patterns in self.PATTERNS.items():
                for pattern_name, pattern_re in patterns.items():
                    pattern = re.compile(pattern_re, re.IGNORECASE)
                    if pattern.search(entry.message):
                        severity = self._get_severity(entry.level, category)

                        severity_counter[severity] += 1
                        category_counter[category] += 1

                        # 收集示例
                        key = f"{severity}:{category}:{pattern_name}"
                        if len(message_examples[key]) < 3:
                            message_examples[key].append(entry.message[:100])

        # 生成问题列表
        for key, examples in message_examples.items():
            severity, category, pattern_name = key.split(':')
            self._issues.append(LogIssue(
                severity=severity,
                category=category,
                message=f"{category} - {pattern_name}",
                count=len(examples),
                examples=examples,
                suggestions=self._get_suggestions(category, pattern_name)
            ))

    def _get_severity(self, level: str, category: str) -> str:
        """获取严重程度

        Args:
            level: 日志级别
            category: 问题类别

        Returns:
            严重程度（ERROR, WARNING, INFO）
        """
        if level in ['ERROR', 'CRITICAL']:
            return 'ERROR'
        elif level in ['WARNING']:
            return 'WARNING'
        elif category in ['error', 'memory']:
            return 'WARNING'
        else:
            return 'INFO'

    def _get_suggestions(self, category: str, pattern_name: str) -> List[str]:
        """获取优化建议

        Args:
            category: 问题类别
            pattern_name: 模式名称

        Returns:
            建议列表
        """
        suggestions = {
            'memory': {
                'OutOfMemory': [
                    '增加系统内存',
                    '优化缓存大小',
                    '检查内存泄漏',
                    '触发垃圾回收'
                ],
                'HighMemory': [
                    '优化缓存设置',
                    '减少资源占用',
                    '启用自动清理'
                ],
                'Leak': [
                    '检查资源释放',
                    '使用上下文管理器',
                    '限制缓存大小'
                ]
            },
            'performance': {
                'SlowOperation': [
                    '优化算法',
                    '使用异步处理',
                    '增加超时时间',
                    '检查资源瓶颈'
                ],
                'HighLatency': [
                    '优化网络连接',
                    '使用缓存',
                    '减少请求频率'
                ],
                'ResourceHeavy': [
                    '使用更高效的数据结构',
                    '延迟加载资源',
                    '分批处理'
                ]
            },
            'error': {
                'Exception': [
                    '检查异常处理',
                    '添加重试机制',
                    '完善错误日志'
                ],
                'Connection': [
                    '检查网络连接',
                    '增加超时时间',
                    '实现断线重连'
                ],
                'FileNotFound': [
                    '检查文件路径',
                    '添加文件存在检查',
                    '使用默认配置'
                ]
            },
            'warning': {
                'Deprecation': [
                    '更新到新API',
                    '迁移旧代码',
                    '查看迁移文档'
                ],
                'Inefficient': [
                    '优化代码逻辑',
                    '使用更高效的方法',
                    '查看性能文档'
                ],
                'Retry': [
                    '增加重试间隔',
                    '限制重试次数',
                    '记录重试日志'
                ]
            }
        }

        return suggestions.get(category, {}).get(pattern_name, [])

    def _generate_report(self) -> Dict:
        """生成分析报告

        Returns:
            报告字典
        """
        # 按严重程度分组
        issues_by_severity = defaultdict(list)
        for issue in self._issues:
            issues_by_severity[issue.severity].append(issue)

        return {
            'status': 'success',
            'summary': {
                'total_entries': len(self._entries),
                'total_issues': len(self._issues),
                'error_count': len(issues_by_severity['ERROR']),
                'warning_count': len(issues_by_severity['WARNING']),
                'info_count': len(issues_by_severity['INFO'])
            },
            'issues_by_severity': {
                severity: [
                    {
                        'category': issue.category,
                        'message': issue.message,
                        'count': issue.count,
                        'suggestions': issue.suggestions
                    }
                    for issue in issues
                ]
                for severity, issues in issues_by_severity.items()
            },
            'top_issues': sorted(
                self._issues,
                key=lambda x: x.count,
                reverse=True
            )[:10]
        }

    def export_report(self, report: Dict, output_path: str) -> None:
        """导出分析报告

        Args:
            report: 分析报告字典
            output_path: 输出文件路径
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 日志分析报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 摘要
            f.write("## 摘要\n\n")
            summary = report['summary']
            f.write(f"- 总日志条目: {summary['total_entries']}\n")
            f.write(f"- 总问题数: {summary['total_issues']}\n")
            f.write(f"- 错误: {summary['error_count']}\n")
            f.write(f"- 警告: {summary['warning_count']}\n")
            f.write(f"- 信息: {summary['info_count']}\n\n")

            # 按严重程度分组的问题
            f.write("## 问题详情（按严重程度）\n\n")
            for severity in ['ERROR', 'WARNING', 'INFO']:
                issues = report['issues_by_severity'].get(severity, [])
                if issues:
                    f.write(f"### {severity}\n\n")
                    for issue in issues:
                        f.write(f"- **{issue.category}**: {issue.message} ({issue.count}次)\n")
                        if issue.suggestions:
                            f.write(f"  - 建议: {', '.join(issue.suggestions[:3])}\n")
                        f.write("\n")

            # Top 10 问题
            f.write("## Top 10 问题\n\n")
            for i, issue in enumerate(report['top_issues'], 1):
                f.write(f"{i}. {issue.category}: {issue.message} ({issue.count}次)\n")
                f.write(f"   建议: {', '.join(issue.suggestions[:2])}\n\n")


def analyze_logs(log_dir: str = "logs", max_files: int = 10) -> Dict:
    """分析日志（便捷函数）

    Args:
        log_dir: 日志目录
        max_files: 最大文件数

    Returns:
        分析报告字典
    """
    analyzer = LogAnalyzer(log_dir)
    return analyzer.analyze(max_files)


def analyze_and_export(
    log_dir: str = "logs",
    output_path: str = "log_analysis_report.md",
    max_files: int = 10
) -> None:
    """分析日志并导出报告（便捷函数）

    Args:
        log_dir: 日志目录
        output_path: 输出文件路径
        max_files: 最大文件数
    """
    analyzer = LogAnalyzer(log_dir)
    report = analyzer.analyze(max_files)
    analyzer.export_report(report, output_path)
    logger.info(f"日志分析报告已生成: {output_path}")
