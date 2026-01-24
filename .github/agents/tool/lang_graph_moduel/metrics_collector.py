"""
metrics_collector.py

**Metrics Collector Module**

Responsibility: Collect and expose decision and execution metrics for monitoring and analysis.

Architecture:
- MetricType: Enumeration of metric types (Counter, Gauge, Histogram)
- MetricPoint: Individual metric data point
- MetricsCollector: Main collector with export capabilities

**Service Layer Module**: MUST follow SRP
**Responsibility**: Metrics collection and export
**Internal Layers**: 2 (MetricPoint, Collector)

Supports:
- Counter: Monotonically increasing values (e.g., retry count, decision count)
- Gauge: Point-in-time values (e.g., confidence, credit balance)
- Histogram: Distribution of values (e.g., execution time, confidence distribution)
- Prometheus text format export
- JSON summary export
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import json


class MetricType(Enum):
    """Type of metric"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class MetricPoint:
    """
    Individual metric data point.
    
    Attributes:
        name: Metric name
        value: Metric value
        metric_type: Type of metric
        labels: Optional labels for metric dimensions
        timestamp: When metric was recorded
    """
    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "labels": self.labels,
            "timestamp": self.timestamp
        }


class MetricsCollector:
    """
    Main metrics collector for decision and execution metrics.
    
    Collects three types of metrics:
    1. Counters - Monotonically increasing values (retries, decisions, events)
    2. Gauges - Current value snapshots (confidence, credit, load)
    3. Histograms - Value distributions (execution time, confidence distribution)
    
    Internal Architecture (2 layers):
    1. Metric Storage (store counters, gauges, histograms)
    2. Export Logic (Prometheus format, JSON summary)
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        # Storage for different metric types
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Metric metadata
        self._counter_labels: Dict[str, Dict[str, str]] = {}
        self._gauge_labels: Dict[str, Dict[str, str]] = {}
        self._histogram_labels: Dict[str, Dict[str, str]] = {}
        
        # Metric history
        self._history: List[MetricPoint] = []
        
        # Configuration
        self._max_history_size = 10000  # Keep last 10k metrics
    
    # ========================================================================
    # Layer 1: Metric Storage
    # ========================================================================
    
    def increment_counter(self, name: str, value: float = 1.0, 
                         labels: Optional[Dict[str, str]] = None):
        """
        Increment a counter metric.
        
        Args:
            name: Counter name (e.g., "retry_attempted_total")
            value: Increment value (default 1.0)
            labels: Optional labels for metric dimensions
        """
        label_key = self._make_label_key(name, labels or {})
        self._counters[label_key] += value
        
        if labels:
            self._counter_labels[label_key] = labels
        
        # Record in history
        self._add_to_history(MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        ))
    
    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None):
        """
        Set a gauge metric value.
        
        Args:
            name: Gauge name (e.g., "routing_confidence")
            value: Current value
            labels: Optional labels for metric dimensions
        """
        label_key = self._make_label_key(name, labels or {})
        self._gauges[label_key] = value
        
        if labels:
            self._gauge_labels[label_key] = labels
        
        # Record in history
        self._add_to_history(MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        ))
    
    def observe_histogram(self, name: str, value: float,
                         labels: Optional[Dict[str, str]] = None):
        """
        Add observation to histogram metric.
        
        Args:
            name: Histogram name (e.g., "tier_execution_duration_ms")
            value: Observed value
            labels: Optional labels for metric dimensions
        """
        label_key = self._make_label_key(name, labels or {})
        self._histograms[label_key].append(value)
        
        if labels:
            self._histogram_labels[label_key] = labels
        
        # Record in history
        self._add_to_history(MetricPoint(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        ))
    
    # ========================================================================
    # Common Decision Metrics (Convenience Methods)
    # ========================================================================
    
    def record_decision_required(self, tier: str, confidence: float):
        """Record a decision required event (low confidence)"""
        self.increment_counter("decision_required_total", labels={"tier": tier})
        self.set_gauge("routing_confidence", confidence, labels={"tier": tier})
    
    def record_retry_attempted(self, tier: str, retry_count: int):
        """Record a retry attempt"""
        self.increment_counter("retry_attempted_total", labels={"tier": tier})
        self.set_gauge("current_retry_count", retry_count, labels={"tier": tier})
    
    def record_circuit_breaker_open(self, tier: str):
        """Record circuit breaker opening"""
        self.increment_counter("circuit_breaker_open_total", labels={"tier": tier})
    
    def record_circuit_breaker_closed(self, tier: str):
        """Record circuit breaker closing"""
        self.increment_counter("circuit_breaker_closed_total", labels={"tier": tier})
    
    def record_tier_execution(self, tier: str, duration_ms: float, 
                             status: str, confidence: float):
        """Record tier execution with multiple metrics"""
        self.observe_histogram("tier_execution_duration_ms", duration_ms, 
                              labels={"tier": tier, "status": status})
        self.observe_histogram("routing_confidence_distribution", confidence,
                              labels={"tier": tier})
        self.increment_counter("tier_execution_total", 
                              labels={"tier": tier, "status": status})
    
    def record_policy_evaluated(self, policy_name: str, matched: bool):
        """Record policy evaluation"""
        self.increment_counter("policy_evaluated_total", 
                              labels={"policy": policy_name, "matched": str(matched)})
    
    def record_human_decision(self, tier: str, approved: bool):
        """Record human decision"""
        self.increment_counter("human_decision_total",
                              labels={"tier": tier, "approved": str(approved)})
    
    # ========================================================================
    # Layer 2: Export Logic
    # ========================================================================
    
    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text format.
        
        Returns:
            Prometheus-formatted metrics text
        """
        lines = []
        
        # Export counters
        for label_key, value in sorted(self._counters.items()):
            name, labels_str = self._parse_label_key(label_key)
            metric_line = f"{name}{labels_str} {value}"
            lines.append(metric_line)
        
        # Export gauges
        for label_key, value in sorted(self._gauges.items()):
            name, labels_str = self._parse_label_key(label_key)
            metric_line = f"{name}{labels_str} {value}"
            lines.append(metric_line)
        
        # Export histogram summaries
        for label_key, values in sorted(self._histograms.items()):
            if not values:
                continue
            
            name, labels_str = self._parse_label_key(label_key)
            
            # Calculate statistics
            count = len(values)
            total = sum(values)
            avg = total / count if count > 0 else 0
            min_val = min(values)
            max_val = max(values)
            
            # Export histogram metrics
            lines.append(f"{name}_count{labels_str} {count}")
            lines.append(f"{name}_sum{labels_str} {total}")
            lines.append(f"{name}_avg{labels_str} {avg}")
            lines.append(f"{name}_min{labels_str} {min_val}")
            lines.append(f"{name}_max{labels_str} {max_val}")
        
        return "\n".join(lines)
    
    def export_json(self) -> Dict[str, Any]:
        """
        Export metrics as JSON summary.
        
        Returns:
            Dictionary containing all metrics
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "counters": self._export_counters_json(),
            "gauges": self._export_gauges_json(),
            "histograms": self._export_histograms_json(),
            "summary": self._generate_summary()
        }
    
    def _export_counters_json(self) -> List[Dict[str, Any]]:
        """Export counters in JSON format"""
        result = []
        for label_key, value in sorted(self._counters.items()):
            name, _ = self._parse_label_key(label_key)
            labels = self._counter_labels.get(label_key, {})
            result.append({
                "name": name,
                "value": value,
                "labels": labels
            })
        return result
    
    def _export_gauges_json(self) -> List[Dict[str, Any]]:
        """Export gauges in JSON format"""
        result = []
        for label_key, value in sorted(self._gauges.items()):
            name, _ = self._parse_label_key(label_key)
            labels = self._gauge_labels.get(label_key, {})
            result.append({
                "name": name,
                "value": value,
                "labels": labels
            })
        return result
    
    def _export_histograms_json(self) -> List[Dict[str, Any]]:
        """Export histograms in JSON format"""
        result = []
        for label_key, values in sorted(self._histograms.items()):
            if not values:
                continue
            
            name, _ = self._parse_label_key(label_key)
            labels = self._histogram_labels.get(label_key, {})
            
            # Calculate statistics
            count = len(values)
            total = sum(values)
            avg = total / count if count > 0 else 0
            min_val = min(values)
            max_val = max(values)
            
            # Calculate percentiles
            sorted_values = sorted(values)
            p50 = self._percentile(sorted_values, 0.50)
            p95 = self._percentile(sorted_values, 0.95)
            p99 = self._percentile(sorted_values, 0.99)
            
            result.append({
                "name": name,
                "labels": labels,
                "count": count,
                "sum": total,
                "avg": avg,
                "min": min_val,
                "max": max_val,
                "p50": p50,
                "p95": p95,
                "p99": p99
            })
        
        return result
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        return {
            "total_counters": len(self._counters),
            "total_gauges": len(self._gauges),
            "total_histograms": len(self._histograms),
            "total_history_points": len(self._history),
            "history_size_limit": self._max_history_size
        }
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value"""
        label_key = self._make_label_key(name, labels or {})
        return self._counters.get(label_key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current gauge value"""
        label_key = self._make_label_key(name, labels or {})
        return self._gauges.get(label_key)
    
    def get_histogram_stats(self, name: str, 
                           labels: Optional[Dict[str, str]] = None) -> Optional[Dict[str, float]]:
        """Get histogram statistics"""
        label_key = self._make_label_key(name, labels or {})
        values = self._histograms.get(label_key)
        
        if not values:
            return None
        
        count = len(values)
        total = sum(values)
        avg = total / count if count > 0 else 0
        
        sorted_values = sorted(values)
        
        return {
            "count": count,
            "sum": total,
            "avg": avg,
            "min": min(values),
            "max": max(values),
            "p50": self._percentile(sorted_values, 0.50),
            "p95": self._percentile(sorted_values, 0.95),
            "p99": self._percentile(sorted_values, 0.99)
        }
    
    def reset(self):
        """Reset all metrics"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._counter_labels.clear()
        self._gauge_labels.clear()
        self._histogram_labels.clear()
        self._history.clear()
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get metric history.
        
        Args:
            limit: Optional limit on number of recent metrics to return
        
        Returns:
            List of metric points as dictionaries
        """
        history = self._history
        if limit:
            history = history[-limit:]
        
        return [m.to_dict() for m in history]
    
    def analyze_patterns(self, tier: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Analyze execution patterns from metrics history.
        
        This method extracts patterns from historical metrics to support
        metrics-based routing decisions. Analyzes success rates, common
        failure patterns, and execution trends.
        
        Args:
            tier: Optional tier filter (A-F). If None, analyzes all tiers.
            limit: Number of recent metrics to analyze (default: 100)
        
        Returns:
            Dictionary containing:
            - tier_success_rates: Dict[str, float] - Success rate per tier
            - tier_failure_rates: Dict[str, float] - Failure rate per tier
            - common_failure_patterns: List[Dict] - Most common failure transitions
            - avg_execution_time: Dict[str, float] - Average execution time per tier
            - confidence_trends: Dict[str, List[float]] - Recent confidence scores per tier
            - recommended_confidence_threshold: float - Dynamic threshold based on recent success
        """
        from collections import defaultdict
        
        # Get recent history
        recent_history = self._history[-limit:] if len(self._history) > limit else self._history
        
        # Initialize analysis structures
        tier_executions = defaultdict(int)
        tier_successes = defaultdict(int)
        tier_failures = defaultdict(int)
        execution_times = defaultdict(list)
        confidence_scores = defaultdict(list)
        failure_transitions = []
        
        # Analyze metrics history
        for metric in recent_history:
            labels = metric.labels
            
            # Track tier executions
            if "tier" in labels and metric.name == "tier_execution_total":
                tier_label = labels["tier"]
                if tier and tier_label != tier:
                    continue
                
                tier_executions[tier_label] += 1
                if labels.get("status") == "SUCCESS":
                    tier_successes[tier_label] += 1
                else:
                    tier_failures[tier_label] += 1
                    failure_transitions.append({
                        "tier": tier_label,
                        "status": labels.get("status"),
                        "timestamp": metric.timestamp
                    })
            
            # Track execution times
            if "tier" in labels and metric.name == "tier_execution_duration_ms":
                tier_label = labels["tier"]
                if tier and tier_label != tier:
                    continue
                execution_times[tier_label].append(metric.value)
            
            # Track confidence scores
            if "tier" in labels and metric.name == "routing_confidence":
                tier_label = labels["tier"]
                if tier and tier_label != tier:
                    continue
                confidence_scores[tier_label].append(metric.value)
        
        # Calculate success rates
        tier_success_rates = {}
        tier_failure_rates = {}
        for tier_label in tier_executions:
            total = tier_executions[tier_label]
            success = tier_successes[tier_label]
            failure = tier_failures[tier_label]
            tier_success_rates[tier_label] = success / total if total > 0 else 0.0
            tier_failure_rates[tier_label] = failure / total if total > 0 else 0.0
        
        # Calculate average execution times
        avg_execution_time = {}
        for tier_label, times in execution_times.items():
            avg_execution_time[tier_label] = sum(times) / len(times) if times else 0.0
        
        # Identify common failure patterns (last 10 failures)
        common_failure_patterns = failure_transitions[-10:] if failure_transitions else []
        
        # Calculate recommended confidence threshold
        # Use overall success rate to dynamically adjust threshold
        overall_success_rate = (
            sum(tier_successes.values()) / sum(tier_executions.values())
            if sum(tier_executions.values()) > 0 else 0.5
        )
        
        # If success rate is high (>80%), lower threshold to 0.6
        # If success rate is medium (50-80%), keep at 0.7
        # If success rate is low (<50%), raise to 0.8
        if overall_success_rate > 0.8:
            recommended_threshold = 0.6
        elif overall_success_rate > 0.5:
            recommended_threshold = 0.7
        else:
            recommended_threshold = 0.8
        
        return {
            "tier_success_rates": dict(tier_success_rates),
            "tier_failure_rates": dict(tier_failure_rates),
            "common_failure_patterns": common_failure_patterns,
            "avg_execution_time": dict(avg_execution_time),
            "confidence_trends": {k: list(v[-10:]) for k, v in confidence_scores.items()},
            "recommended_confidence_threshold": recommended_threshold,
            "total_executions_analyzed": sum(tier_executions.values()),
            "overall_success_rate": overall_success_rate
        }
    
    def save_to_file(self, filepath: str, format: str = "json"):
        """
        Save metrics to file.
        
        Args:
            filepath: Output file path
            format: Export format ("json" or "prometheus")
        """
        if format == "json":
            with open(filepath, 'w') as f:
                json.dump(self.export_json(), f, indent=2)
        elif format == "prometheus":
            with open(filepath, 'w') as f:
                f.write(self.export_prometheus())
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # ========================================================================
    # Internal Helper Methods
    # ========================================================================
    
    def _make_label_key(self, name: str, labels: Dict[str, str]) -> str:
        """Create unique key from metric name and labels"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _parse_label_key(self, label_key: str) -> tuple[str, str]:
        """Parse label key into name and labels string"""
        if "{" not in label_key:
            return label_key, ""
        
        name, labels_part = label_key.split("{", 1)
        labels_str = "{" + labels_part
        return name, labels_str
    
    def _add_to_history(self, metric: MetricPoint):
        """Add metric to history, maintaining size limit"""
        self._history.append(metric)
        
        # Trim history if exceeds limit
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]
    
    @staticmethod
    def _percentile(sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0
        
        index = int(len(sorted_values) * percentile)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


# ============================================================================
# Global Metrics Instance (Singleton Pattern)
# ============================================================================

# Global metrics collector instance
_global_metrics = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    return _global_metrics


def reset_metrics():
    """Reset global metrics collector"""
    _global_metrics.reset()
