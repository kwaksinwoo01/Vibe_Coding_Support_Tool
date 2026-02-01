"""
Unit tests for metrics_collector.py

Tests counter, gauge, histogram metrics, Prometheus export, and JSON export.
"""

import unittest
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lang_graph_moduel.metrics_collector import (
    MetricType,
    MetricPoint,
    MetricsCollector,
    get_metrics_collector,
    reset_metrics
)


class TestMetricPoint(unittest.TestCase):
    """Test MetricPoint model"""
    
    def test_basic_metric_creation(self):
        """Test creating basic metric point"""
        metric = MetricPoint(
            name="test_counter",
            value=5.0,
            metric_type=MetricType.COUNTER
        )
        
        self.assertEqual(metric.name, "test_counter")
        self.assertEqual(metric.value, 5.0)
        self.assertEqual(metric.metric_type, MetricType.COUNTER)
    
    def test_metric_with_labels(self):
        """Test metric with labels"""
        metric = MetricPoint(
            name="tier_execution",
            value=1.0,
            metric_type=MetricType.COUNTER,
            labels={"tier": "A", "status": "SUCCESS"}
        )
        
        self.assertEqual(metric.labels["tier"], "A")
        self.assertEqual(metric.labels["status"], "SUCCESS")
    
    def test_to_dict(self):
        """Test converting metric to dictionary"""
        metric = MetricPoint(
            name="test_metric",
            value=10.0,
            metric_type=MetricType.GAUGE,
            labels={"tier": "B"}
        )
        
        result = metric.to_dict()
        
        self.assertEqual(result["name"], "test_metric")
        self.assertEqual(result["value"], 10.0)
        self.assertEqual(result["type"], "gauge")
        self.assertEqual(result["labels"]["tier"], "B")


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector functionality"""
    
    def setUp(self):
        """Set up test collector"""
        self.collector = MetricsCollector()
    
    def tearDown(self):
        """Clean up after test"""
        self.collector.reset()
    
    def test_increment_counter(self):
        """Test incrementing counter metric"""
        self.collector.increment_counter("test_total", 1.0)
        self.collector.increment_counter("test_total", 2.0)
        
        value = self.collector.get_counter("test_total")
        
        self.assertEqual(value, 3.0)
    
    def test_counter_with_labels(self):
        """Test counter with labels"""
        self.collector.increment_counter("requests_total", 1.0, labels={"tier": "A"})
        self.collector.increment_counter("requests_total", 1.0, labels={"tier": "B"})
        self.collector.increment_counter("requests_total", 2.0, labels={"tier": "A"})
        
        value_a = self.collector.get_counter("requests_total", labels={"tier": "A"})
        value_b = self.collector.get_counter("requests_total", labels={"tier": "B"})
        
        self.assertEqual(value_a, 3.0)
        self.assertEqual(value_b, 1.0)
    
    def test_set_gauge(self):
        """Test setting gauge metric"""
        self.collector.set_gauge("temperature", 25.5)
        self.collector.set_gauge("temperature", 30.0)
        
        value = self.collector.get_gauge("temperature")
        
        self.assertEqual(value, 30.0)  # Gauge should be overwritten
    
    def test_gauge_with_labels(self):
        """Test gauge with labels"""
        self.collector.set_gauge("confidence", 0.8, labels={"tier": "A"})
        self.collector.set_gauge("confidence", 0.6, labels={"tier": "B"})
        
        value_a = self.collector.get_gauge("confidence", labels={"tier": "A"})
        value_b = self.collector.get_gauge("confidence", labels={"tier": "B"})
        
        self.assertEqual(value_a, 0.8)
        self.assertEqual(value_b, 0.6)
    
    def test_observe_histogram(self):
        """Test observing histogram values"""
        self.collector.observe_histogram("duration_ms", 100.0)
        self.collector.observe_histogram("duration_ms", 200.0)
        self.collector.observe_histogram("duration_ms", 150.0)
        
        stats = self.collector.get_histogram_stats("duration_ms")
        
        self.assertIsNotNone(stats)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["sum"], 450.0)
        self.assertEqual(stats["avg"], 150.0)
        self.assertEqual(stats["min"], 100.0)
        self.assertEqual(stats["max"], 200.0)
    
    def test_histogram_percentiles(self):
        """Test histogram percentile calculation"""
        # Add 100 values
        for i in range(100):
            self.collector.observe_histogram("latency", float(i))
        
        stats = self.collector.get_histogram_stats("latency")
        
        self.assertIsNotNone(stats)
        self.assertAlmostEqual(stats["p50"], 50.0, delta=5.0)
        self.assertAlmostEqual(stats["p95"], 95.0, delta=5.0)
        self.assertAlmostEqual(stats["p99"], 99.0, delta=5.0)
    
    def test_convenience_methods(self):
        """Test convenience methods for common metrics"""
        self.collector.record_decision_required("A", 0.3)
        self.collector.record_retry_attempted("B", 2)
        self.collector.record_circuit_breaker_open("C")
        self.collector.record_tier_execution("D", 500.0, "SUCCESS", 0.8)
        
        # Check counters were incremented
        self.assertEqual(self.collector.get_counter("decision_required_total", labels={"tier": "A"}), 1.0)
        self.assertEqual(self.collector.get_counter("retry_attempted_total", labels={"tier": "B"}), 1.0)
        self.assertEqual(self.collector.get_counter("circuit_breaker_open_total", labels={"tier": "C"}), 1.0)
    
    def test_export_prometheus(self):
        """Test Prometheus text format export"""
        self.collector.increment_counter("requests_total", 5.0, labels={"tier": "A"})
        self.collector.set_gauge("current_users", 10.0)
        self.collector.observe_histogram("latency_ms", 100.0)
        self.collector.observe_histogram("latency_ms", 200.0)
        
        prometheus_text = self.collector.export_prometheus()
        
        self.assertIn("requests_total", prometheus_text)
        self.assertIn("current_users", prometheus_text)
        self.assertIn("latency_ms_count", prometheus_text)
        self.assertIn("latency_ms_sum", prometheus_text)
    
    def test_export_json(self):
        """Test JSON export"""
        self.collector.increment_counter("requests_total", 3.0)
        self.collector.set_gauge("temperature", 25.0)
        self.collector.observe_histogram("duration", 100.0)
        
        json_data = self.collector.export_json()
        
        self.assertIn("timestamp", json_data)
        self.assertIn("counters", json_data)
        self.assertIn("gauges", json_data)
        self.assertIn("histograms", json_data)
        self.assertIn("summary", json_data)
        
        # Check counter
        self.assertEqual(len(json_data["counters"]), 1)
        self.assertEqual(json_data["counters"][0]["name"], "requests_total")
        self.assertEqual(json_data["counters"][0]["value"], 3.0)
    
    def test_history_tracking(self):
        """Test metric history tracking"""
        self.collector.increment_counter("test", 1.0)
        self.collector.set_gauge("test", 2.0)
        self.collector.observe_histogram("test", 3.0)
        
        history = self.collector.get_history()
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["name"], "test")
        self.assertEqual(history[0]["type"], "counter")
    
    def test_history_limit(self):
        """Test history size limit"""
        collector = MetricsCollector()
        collector._max_history_size = 10
        
        # Add more than limit
        for i in range(20):
            collector.increment_counter("test", 1.0)
        
        history = collector.get_history()
        
        # Should be limited to max size
        self.assertLessEqual(len(history), 10)
    
    def test_reset(self):
        """Test resetting all metrics"""
        self.collector.increment_counter("test_counter", 5.0)
        self.collector.set_gauge("test_gauge", 10.0)
        self.collector.observe_histogram("test_histogram", 15.0)
        
        self.collector.reset()
        
        self.assertEqual(self.collector.get_counter("test_counter"), 0.0)
        self.assertIsNone(self.collector.get_gauge("test_gauge"))
        self.assertIsNone(self.collector.get_histogram_stats("test_histogram"))
    
    def test_save_to_file_json(self):
        """Test saving metrics to JSON file"""
        import tempfile
        
        self.collector.increment_counter("test", 5.0)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.collector.save_to_file(temp_path, format="json")
            
            # Read back and verify
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            self.assertIn("counters", data)
            self.assertGreater(len(data["counters"]), 0)
        finally:
            Path(temp_path).unlink()
    
    def test_save_to_file_prometheus(self):
        """Test saving metrics to Prometheus format file"""
        import tempfile
        
        self.collector.increment_counter("requests_total", 10.0)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.prom', delete=False) as f:
            temp_path = f.name
        
        try:
            self.collector.save_to_file(temp_path, format="prometheus")
            
            # Read back and verify
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn("requests_total", content)
        finally:
            Path(temp_path).unlink()


class TestGlobalMetrics(unittest.TestCase):
    """Test global metrics instance"""
    
    def test_get_metrics_collector(self):
        """Test getting global metrics collector"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        # Should be same instance
        self.assertIs(collector1, collector2)
    
    def test_reset_metrics(self):
        """Test resetting global metrics"""
        collector = get_metrics_collector()
        collector.increment_counter("test", 5.0)
        
        reset_metrics()
        
        # Should be reset
        self.assertEqual(collector.get_counter("test"), 0.0)


class TestComplexScenarios(unittest.TestCase):
    """Test complex metric scenarios"""
    
    def setUp(self):
        self.collector = MetricsCollector()
    
    def tearDown(self):
        self.collector.reset()
    
    def test_tier_execution_full_workflow(self):
        """Test full tier execution metric workflow"""
        # Simulate tier execution metrics
        for tier in ["A", "B", "C"]:
            for i in range(5):
                self.collector.record_tier_execution(
                    tier=tier,
                    duration_ms=100.0 + i * 50,
                    status="SUCCESS",
                    confidence=0.8 + i * 0.02
                )
        
        # Check histograms
        for tier in ["A", "B", "C"]:
            stats = self.collector.get_histogram_stats(
                "tier_execution_duration_ms",
                labels={"tier": tier, "status": "SUCCESS"}
            )
            self.assertIsNotNone(stats)
            self.assertEqual(stats["count"], 5)
    
    def test_decision_workflow_metrics(self):
        """Test decision workflow metrics"""
        # Low confidence decision required
        self.collector.record_decision_required("A", 0.3)
        
        # Retry attempted
        self.collector.record_retry_attempted("A", 1)
        self.collector.record_retry_attempted("A", 2)
        
        # Circuit breaker
        self.collector.record_circuit_breaker_open("A")
        
        # Decision automated (new metric for auto-approval)
        self.collector.increment_counter("decision_automated_total", labels={"tier": "A"})
        self.collector.set_gauge("routing_confidence", 0.85, labels={"tier": "A"})
        
        # Verify counts
        self.assertEqual(
            self.collector.get_counter("decision_required_total", labels={"tier": "A"}),
            1.0
        )
        self.assertEqual(
            self.collector.get_counter("retry_attempted_total", labels={"tier": "A"}),
            2.0
        )
        self.assertEqual(
            self.collector.get_counter("circuit_breaker_open_total", labels={"tier": "A"}),
            1.0
        )
        # Verify decision automated metric
        self.assertEqual(
            self.collector.get_counter("decision_automated_total", labels={"tier": "A"}),
            1.0
        )
        self.assertEqual(
            self.collector.get_gauge("routing_confidence", labels={"tier": "A"}),
            0.85
        )
    
    def test_policy_evaluation_metrics(self):
        """Test policy evaluation metrics"""
        self.collector.record_policy_evaluated("low_confidence_approval", matched=True)
        self.collector.record_policy_evaluated("low_confidence_approval", matched=False)
        self.collector.record_policy_evaluated("cost_limit", matched=True)
        
        # Check counters
        matched = self.collector.get_counter(
            "policy_evaluated_total",
            labels={"policy": "low_confidence_approval", "matched": "True"}
        )
        not_matched = self.collector.get_counter(
            "policy_evaluated_total",
            labels={"policy": "low_confidence_approval", "matched": "False"}
        )
        
        self.assertEqual(matched, 1.0)
        self.assertEqual(not_matched, 1.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.collector = MetricsCollector()
    
    def tearDown(self):
        self.collector.reset()
    
    def test_get_nonexistent_metric(self):
        """Test getting nonexistent metrics"""
        self.assertEqual(self.collector.get_counter("nonexistent"), 0.0)
        self.assertIsNone(self.collector.get_gauge("nonexistent"))
        self.assertIsNone(self.collector.get_histogram_stats("nonexistent"))
    
    def test_empty_histogram_stats(self):
        """Test stats for histogram with no observations"""
        stats = self.collector.get_histogram_stats("empty")
        self.assertIsNone(stats)
    
    def test_label_key_generation(self):
        """Test label key generation is consistent"""
        labels1 = {"tier": "A", "status": "SUCCESS"}
        labels2 = {"status": "SUCCESS", "tier": "A"}  # Different order
        
        self.collector.increment_counter("test", 1.0, labels=labels1)
        self.collector.increment_counter("test", 2.0, labels=labels2)
        
        # Should be same counter
        value = self.collector.get_counter("test", labels=labels1)
        self.assertEqual(value, 3.0)
    
    def test_invalid_format(self):
        """Test save with invalid format"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            with self.assertRaises(ValueError):
                self.collector.save_to_file(temp_path, format="invalid")
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestDecisionAutomatedMetrics(unittest.TestCase):
    """Test decision_automated_total metric usage"""
    
    def setUp(self):
        self.collector = MetricsCollector()
    
    def tearDown(self):
        self.collector.reset()
    
    def test_decision_automated_total_counter(self):
        """Test decision_automated_total counter is properly recorded"""
        # Record automated decisions for different tiers
        self.collector.increment_counter("decision_automated_total", labels={"tier": "A"})
        self.collector.increment_counter("decision_automated_total", labels={"tier": "B"})
        self.collector.increment_counter("decision_automated_total", labels={"tier": "A"})
        
        # Verify counts
        self.assertEqual(
            self.collector.get_counter("decision_automated_total", labels={"tier": "A"}),
            2.0
        )
        self.assertEqual(
            self.collector.get_counter("decision_automated_total", labels={"tier": "B"}),
            1.0
        )
    
    def test_routing_confidence_with_automated_decision(self):
        """Test routing_confidence gauge is set with automated decisions"""
        # Set routing confidence for automated decision
        self.collector.set_gauge("routing_confidence", 0.85, labels={"tier": "C"})
        self.collector.set_gauge("routing_confidence", 0.92, labels={"tier": "D"})
        
        # Verify gauges
        self.assertEqual(
            self.collector.get_gauge("routing_confidence", labels={"tier": "C"}),
            0.85
        )
        self.assertEqual(
            self.collector.get_gauge("routing_confidence", labels={"tier": "D"}),
            0.92
        )
    
    def test_auto_resolve_triggered_counter(self):
        """Test auto_resolve_triggered_total counter for D→C→B chain"""
        # Record auto-resolve trigger
        self.collector.increment_counter("auto_resolve_triggered_total", labels={"tier": "D"})
        self.collector.set_gauge("auto_resolve_confidence", 0.95, labels={"tier": "D"})
        
        # Verify metrics
        self.assertEqual(
            self.collector.get_counter("auto_resolve_triggered_total", labels={"tier": "D"}),
            1.0
        )
        self.assertEqual(
            self.collector.get_gauge("auto_resolve_confidence", labels={"tier": "D"}),
            0.95
        )
    
    def test_combined_automated_decision_workflow(self):
        """Test complete automated decision workflow metrics"""
        tier = "A"
        confidence = 0.78
        
        # Simulate automated decision workflow
        # 1. Decision required (low confidence initially)
        self.collector.record_decision_required(tier, 0.6)
        
        # 2. Decision automated (after confidence boost)
        self.collector.increment_counter("decision_automated_total", labels={"tier": tier})
        self.collector.set_gauge("routing_confidence", confidence, labels={"tier": tier})
        
        # 3. Tier execution
        self.collector.record_tier_execution(tier, 1250.0, "SUCCESS", confidence)
        
        # Verify all metrics recorded
        self.assertEqual(
            self.collector.get_counter("decision_required_total", labels={"tier": tier}),
            1.0
        )
        self.assertEqual(
            self.collector.get_counter("decision_automated_total", labels={"tier": tier}),
            1.0
        )
        self.assertEqual(
            self.collector.get_gauge("routing_confidence", labels={"tier": tier}),
            confidence
        )
        self.assertEqual(
            self.collector.get_counter("tier_execution_total", 
                                      labels={"tier": tier, "status": "SUCCESS"}),
            1.0
        )


if __name__ == "__main__":
    unittest.main()
