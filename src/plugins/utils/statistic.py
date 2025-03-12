import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict
from loguru import logger

from ...common.database import Database


class LLMStatistics:
    def __init__(self, output_file: str = "llm_statistics.txt"):
        """初始化LLM统计类
        
        Args:
            output_file: 统计结果输出文件路径
        """
        self.db = Database.get_instance()
        self.output_file = output_file
        self.running = False
        self.stats_thread = None
        
    def start(self):
        """启动统计线程"""
        if not self.running:
            self.running = True
            self.stats_thread = threading.Thread(target=self._stats_loop)
            self.stats_thread.daemon = True
            self.stats_thread.start()
            
    def stop(self):
        """停止统计线程"""
        self.running = False
        if self.stats_thread:
            self.stats_thread.join()
            
    def _collect_statistics_for_period(self, start_time: datetime) -> Dict[str, Any]:
        """收集指定时间段的LLM请求统计数据
        
        Args:
            start_time: 统计开始时间
        """
        stats = {
            "total_requests": 0,
            "requests_by_type": defaultdict(int),
            "requests_by_user": defaultdict(int),
            "requests_by_model": defaultdict(int),
            "average_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "costs_by_user": defaultdict(float),
            "costs_by_type": defaultdict(float),
            "costs_by_model": defaultdict(float)
        }
        
        cursor = self.db.db.llm_usage.find({
            "timestamp": {"$gte": start_time}
        })
        
        total_requests = 0
        
        for doc in cursor:
            stats["total_requests"] += 1
            request_type = doc.get("request_type", "unknown")
            user_id = str(doc.get("user_id", "unknown"))
            model_name = doc.get("model_name", "unknown")
            
            stats["requests_by_type"][request_type] += 1
            stats["requests_by_user"][user_id] += 1
            stats["requests_by_model"][model_name] += 1
            
            prompt_tokens = doc.get("prompt_tokens", 0)
            completion_tokens = doc.get("completion_tokens", 0)
            stats["total_tokens"] += prompt_tokens + completion_tokens
            
            cost = doc.get("cost", 0.0)
            stats["total_cost"] += cost
            stats["costs_by_user"][user_id] += cost
            stats["costs_by_type"][request_type] += cost
            stats["costs_by_model"][model_name] += cost
            
            total_requests += 1
            
        if total_requests > 0:
            stats["average_tokens"] = stats["total_tokens"] / total_requests
            
        return stats
    
    def _collect_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """收集所有时间范围的统计数据"""
        now = datetime.now()
        
        return {
            "all_time": self._collect_statistics_for_period(datetime.min),
            "last_7_days": self._collect_statistics_for_period(now - timedelta(days=7)),
            "last_24_hours": self._collect_statistics_for_period(now - timedelta(days=1)),
            "last_hour": self._collect_statistics_for_period(now - timedelta(hours=1))
        }
    
    def _format_stats_section(self, stats: Dict[str, Any], title: str) -> str:
        """格式化统计部分的输出
        
        Args:
            stats: 统计数据
            title: 部分标题
        """
        output = []
        output.append(f"\n{title}")
        output.append("=" * len(title))
        
        output.append(f"总请求数: {stats['total_requests']}")
        if stats['total_requests'] > 0:
            output.append(f"总Token数: {stats['total_tokens']}")
            output.append(f"总花费: ¥{stats['total_cost']:.4f}")
            
            output.append("\n按模型统计:")
            for model_name, count in sorted(stats["requests_by_model"].items()):
                cost = stats["costs_by_model"][model_name]
                output.append(f"- {model_name}: {count}次 (花费: ¥{cost:.4f})")
            
            output.append("\n按请求类型统计:")
            for req_type, count in sorted(stats["requests_by_type"].items()):
                cost = stats["costs_by_type"][req_type]
                output.append(f"- {req_type}: {count}次 (花费: ¥{cost:.4f})")
        
        return "\n".join(output)
    
    def _save_statistics(self, all_stats: Dict[str, Dict[str, Any]]):
        """将统计结果保存到文件"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        output = []
        output.append(f"LLM请求统计报告 (生成时间: {current_time})")
        output.append("=" * 50)
        
        # 添加各个时间段的统计
        sections = [
            ("所有时间统计", "all_time"),
            ("最近7天统计", "last_7_days"),
            ("最近24小时统计", "last_24_hours"),
            ("最近1小时统计", "last_hour")
        ]
        
        for title, key in sections:
            output.append(self._format_stats_section(all_stats[key], title))
            
        # 写入文件
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
                
    def _stats_loop(self):
        """统计循环，每1分钟运行一次"""
        while self.running:
            try:
                all_stats = self._collect_all_statistics()
                self._save_statistics(all_stats)
            except Exception:
                logger.exception("统计数据处理失败")
            
            # 等待1分钟
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)
