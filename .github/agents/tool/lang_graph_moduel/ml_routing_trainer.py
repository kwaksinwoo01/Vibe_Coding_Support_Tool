"""
ml_routing_trainer.py

**ML-Based Routing Training Module**

Responsibility: Collect training data from routing decisions and execution
outcomes to enable future ML-based intelligent routing.

Architecture:
- RoutingFeatures: Feature vector for ML training
- RoutingOutcome: Labeled outcome for training data
- TrainingDataPoint: Complete training data point (features + outcome)
- MLRoutingTrainer: Data collection and export logic

**Service Layer Module**: MUST follow SRP
**Responsibility**: Training data collection and export
**Internal Layers**: 2 (Collection, Export)
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from pathlib import Path


@dataclass
class RoutingFeatures:
    """
    Feature vector for ML-based routing decisions.
    
    Contains all features that may influence routing decisions including
    tier state, execution metrics, and historical patterns.
    """
    
    # Tier context
    current_tier: str
    user_input_length: int
    user_input_keywords: List[str] = field(default_factory=list)
    
    # Execution metrics
    execution_time_ms: float = 0.0
    retry_count: int = 0
    confidence_score: float = 0.5
    
    # Historical patterns
    previous_tier_sequence: List[str] = field(default_factory=list)
    failure_count_24h: int = 0
    success_rate_7d: float = 1.0
    avg_execution_time_7d: float = 0.0
    
    # Quality metrics
    quality_score: float = 1.0
    completion_percentage: float = 1.0
    validation_passed: bool = True
    
    # Resource metrics
    estimated_cost: float = 0.0
    credit_available: float = float('inf')
    
    # Temporal features
    hour_of_day: int = 0
    day_of_week: int = 0
    is_business_hours: bool = True
    
    # Metadata
    feature_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class RoutingOutcome:
    """
    Labeled outcome for training data.
    
    Contains the actual routing decision made and the execution result,
    which serves as the training label.
    """
    
    # Routing decision
    routed_to_tier: Optional[str]
    decision_confidence: float
    decision_method: str  # "manual", "policy", "confidence", "default"
    
    # Execution result
    execution_status: str  # "SUCCESS", "FAILED", "PARTIAL"
    execution_time_ms: float
    quality_score: float = 1.0
    
    # Feedback
    required_retry: bool = False
    required_human_intervention: bool = False
    optimal_routing: Optional[str] = None  # What should have been routed (if different)
    
    # Metadata
    outcome_version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


@dataclass
class TrainingDataPoint:
    """
    Complete training data point combining features and outcome.
    
    This is the unit of data that will be used for ML training.
    """
    
    # Core data
    features: RoutingFeatures
    outcome: RoutingOutcome
    
    # Identifiers
    task_id: str
    session_id: str
    
    # Annotations
    is_validated: bool = False  # Human validation of correctness
    validation_notes: str = ""
    quality_rating: int = 0  # 1-5 rating from user
    
    # Metadata
    data_point_version: str = "1.0.0"
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "features": self.features.to_dict(),
            "outcome": self.outcome.to_dict(),
            "task_id": self.task_id,
            "session_id": self.session_id,
            "is_validated": self.is_validated,
            "validation_notes": self.validation_notes,
            "quality_rating": self.quality_rating,
            "data_point_version": self.data_point_version,
            "collected_at": self.collected_at
        }


class MLRoutingTrainer:
    """
    Core trainer for ML-based routing data collection.
    
    Collects training data from routing decisions and execution outcomes:
    - Feature extraction from execution context
    - Outcome labeling from execution results
    - Data validation and quality checks
    - Export to various formats (JSON, CSV, Parquet)
    
    Internal Architecture (2 layers):
    1. Collection Layer (collect_training_data, extract_features, label_outcome)
    2. Export Layer (export_json, export_csv, get_statistics)
    """
    
    # Configuration constants
    DEFAULT_STORAGE_PATH = ".github/agents/tool/training_data"
    MAX_TRAINING_POINTS = 10000  # Max points to keep in memory
    FEATURE_VERSION = "1.0.0"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize ML routing trainer.
        
        Args:
            storage_path: Directory path for storing training data
        """
        self.storage_path = Path(storage_path or self.DEFAULT_STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Internal state
        self.training_data: List[TrainingDataPoint] = []
        self.current_session_id = self._generate_session_id()
    
    # ========================================================================
    # Layer 1: Collection
    # ========================================================================
    
    def collect_training_data(self, 
                             task_id: str,
                             features: RoutingFeatures,
                             outcome: RoutingOutcome,
                             **kwargs) -> TrainingDataPoint:
        """
        Collect a training data point.
        
        Args:
            task_id: Unique task identifier
            features: Feature vector
            outcome: Routing outcome
            **kwargs: Additional metadata
        
        Returns:
            Created TrainingDataPoint
        """
        # Create data point
        data_point = TrainingDataPoint(
            features=features,
            outcome=outcome,
            task_id=task_id,
            session_id=self.current_session_id,
            **kwargs
        )
        
        # Add to collection
        self.training_data.append(data_point)
        
        # Trim if exceeds max
        if len(self.training_data) > self.MAX_TRAINING_POINTS:
            self.training_data = self.training_data[-self.MAX_TRAINING_POINTS:]
        
        # Auto-save periodically (every 100 points)
        if len(self.training_data) % 100 == 0:
            self._auto_save()
        
        return data_point
    
    def extract_features(self, context: Dict[str, Any]) -> RoutingFeatures:
        """
        Extract feature vector from execution context.
        
        Args:
            context: Execution context dictionary
        
        Returns:
            RoutingFeatures instance
        """
        # Extract user input features
        user_input = context.get("user_input", "")
        user_input_length = len(user_input)
        user_input_keywords = self._extract_keywords(user_input)
        
        # Extract execution metrics
        execution_time_ms = context.get("execution_time_ms", 0.0)
        retry_count = context.get("retry_count", 0)
        confidence_score = context.get("confidence", 0.5)
        
        # Extract historical patterns
        decision_trace = context.get("decision_trace", [])
        previous_tier_sequence = [d.get("tier", "") for d in decision_trace[-5:]]
        
        # Extract quality metrics
        quality_score = context.get("quality_score", 1.0)
        completion_percentage = context.get("completion_percentage", 1.0)
        validation_passed = context.get("validation_passed", True)
        
        # Extract resource metrics
        estimated_cost = context.get("estimated_cost", 0.0)
        credit_available = context.get("available_credit", float('inf'))
        
        # Extract temporal features
        now = datetime.now()
        hour_of_day = now.hour
        day_of_week = now.weekday()
        is_business_hours = (9 <= hour_of_day <= 17) and (day_of_week < 5)
        
        return RoutingFeatures(
            current_tier=context.get("tier", ""),
            user_input_length=user_input_length,
            user_input_keywords=user_input_keywords,
            execution_time_ms=execution_time_ms,
            retry_count=retry_count,
            confidence_score=confidence_score,
            previous_tier_sequence=previous_tier_sequence,
            quality_score=quality_score,
            completion_percentage=completion_percentage,
            validation_passed=validation_passed,
            estimated_cost=estimated_cost,
            credit_available=credit_available,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            is_business_hours=is_business_hours,
            feature_version=self.FEATURE_VERSION
        )
    
    def label_outcome(self, result: Dict[str, Any]) -> RoutingOutcome:
        """
        Label routing outcome from execution result.
        
        Args:
            result: Execution result dictionary
        
        Returns:
            RoutingOutcome instance
        """
        return RoutingOutcome(
            routed_to_tier=result.get("next_tier"),
            decision_confidence=result.get("confidence", 0.5),
            decision_method=result.get("decision_method", "default"),
            execution_status=result.get("status", "UNKNOWN"),
            execution_time_ms=result.get("execution_time_ms", 0.0),
            quality_score=result.get("quality_score", 1.0),
            required_retry=result.get("retry_count", 0) > 0,
            required_human_intervention=result.get("human_intervention", False),
            optimal_routing=result.get("optimal_routing"),
            outcome_version="1.0.0"
        )
    
    # ========================================================================
    # Layer 2: Export and Analysis
    # ========================================================================
    
    def export_json(self, filepath: Optional[str] = None) -> str:
        """
        Export training data to JSON file.
        
        Args:
            filepath: Optional custom filepath
        
        Returns:
            Path to exported file
        """
        if filepath is None:
            filepath = self.storage_path / f"training_data_{self.current_session_id}.json"
        else:
            filepath = Path(filepath)
        
        # Convert to dictionaries
        data = [dp.to_dict() for dp in self.training_data]
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def export_csv(self, filepath: Optional[str] = None) -> str:
        """
        Export training data to CSV file (flattened format).
        
        Args:
            filepath: Optional custom filepath
        
        Returns:
            Path to exported file
        """
        if filepath is None:
            filepath = self.storage_path / f"training_data_{self.current_session_id}.csv"
        else:
            filepath = Path(filepath)
        
        # Flatten data points
        rows = []
        for dp in self.training_data:
            row = {
                "task_id": dp.task_id,
                "session_id": dp.session_id,
                "collected_at": dp.collected_at,
                # Features
                "current_tier": dp.features.current_tier,
                "user_input_length": dp.features.user_input_length,
                "execution_time_ms": dp.features.execution_time_ms,
                "retry_count": dp.features.retry_count,
                "confidence_score": dp.features.confidence_score,
                "quality_score": dp.features.quality_score,
                "completion_percentage": dp.features.completion_percentage,
                # Outcome
                "routed_to_tier": dp.outcome.routed_to_tier,
                "decision_confidence": dp.outcome.decision_confidence,
                "execution_status": dp.outcome.execution_status,
                "required_retry": dp.outcome.required_retry,
                "optimal_routing": dp.outcome.optimal_routing
            }
            rows.append(row)
        
        # Write CSV
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        return str(filepath)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about collected training data.
        
        Returns:
            Dictionary of statistics
        """
        if not self.training_data:
            return {
                "total_points": 0,
                "session_id": self.current_session_id
            }
        
        # Calculate statistics
        total = len(self.training_data)
        
        # Status distribution
        status_counts = {}
        for dp in self.training_data:
            status = dp.outcome.execution_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Tier distribution
        tier_counts = {}
        for dp in self.training_data:
            tier = dp.features.current_tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Routing distribution
        routing_counts = {}
        for dp in self.training_data:
            routing = dp.outcome.routed_to_tier or "None"
            routing_counts[routing] = routing_counts.get(routing, 0) + 1
        
        # Quality metrics
        avg_confidence = sum(dp.features.confidence_score for dp in self.training_data) / total
        avg_quality = sum(dp.features.quality_score for dp in self.training_data) / total
        retry_rate = sum(1 for dp in self.training_data if dp.outcome.required_retry) / total
        
        return {
            "total_points": total,
            "session_id": self.current_session_id,
            "status_distribution": status_counts,
            "tier_distribution": tier_counts,
            "routing_distribution": routing_counts,
            "avg_confidence": round(avg_confidence, 3),
            "avg_quality": round(avg_quality, 3),
            "retry_rate": round(retry_rate, 3),
            "storage_path": str(self.storage_path)
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text using simple tokenization"""
        # Simple word extraction (can be enhanced with NLP)
        words = text.lower().split()
        # Filter common words and keep only meaningful ones
        keywords = [w for w in words if len(w) > 3]
        return keywords[:10]  # Keep top 10
    
    def _auto_save(self):
        """Auto-save training data periodically"""
        try:
            self.export_json()
        except Exception as e:
            # Silent fail on auto-save
            pass
    
    def clear_data(self):
        """Clear all training data from memory"""
        self.training_data.clear()
    
    def new_session(self):
        """Start a new training session"""
        # Save current session
        if self.training_data:
            self.export_json()
        
        # Reset
        self.training_data.clear()
        self.current_session_id = self._generate_session_id()


# ============================================================================
# Utility Functions
# ============================================================================

def create_trainer(storage_path: Optional[str] = None) -> MLRoutingTrainer:
    """
    Create ML routing trainer instance.
    
    Args:
        storage_path: Optional storage directory path
    
    Returns:
        MLRoutingTrainer instance
    """
    return MLRoutingTrainer(storage_path=storage_path)


# Global singleton instance
_trainer_instance: Optional[MLRoutingTrainer] = None


def get_ml_trainer() -> MLRoutingTrainer:
    """
    Get global ML routing trainer instance.
    
    Returns:
        Singleton MLRoutingTrainer instance
    """
    global _trainer_instance
    if _trainer_instance is None:
        _trainer_instance = MLRoutingTrainer()
    return _trainer_instance
