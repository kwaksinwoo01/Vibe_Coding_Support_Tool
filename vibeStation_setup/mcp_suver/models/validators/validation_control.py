"""
validation_control.py

**Centralized Control Validation (CCV) Module**

Responsibility: Provide unified validation orchestration for all tier states.

Architecture:
- CCV: Centralized validation controller with composer pattern
- Factory methods for tier-specific validators (for_tier_a, for_tier_b, for_tier_c)
- Integration with existing validator functions in tier_validators.py

**Service Layer Module**: MUST follow SRP
**Responsibility**: Validation orchestration and composition
**Reason to Change**: When validation composition patterns change

Usage:
    # In TierAState
    validation: CCV = field(default_factory=CCV.for_tier_a)
    is_valid, report = validation.validate(self)
    
    # In TierCState
    validation: CCV = field(default_factory=CCV.for_tier_c)
    is_valid, report = validation.validate(self)
"""

from typing import Dict, List, Tuple, Callable, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CCV:
    """
    Centralized Control Validation (CCV)
    
    Orchestrates multiple validation functions for tier states through a
    unified interface. Uses the Composite pattern to combine validators.
    
    **Responsibility**: Compose and execute validation functions
    **Reason to Change**: When validation orchestration patterns change
    
    Attributes:
        is_valid: Overall validation status (True if all validators pass)
        validation_results: Map of validator name -> pass/fail status
        validation_errors: List of error messages from failed validators
        validation_warnings: List of warning messages (non-fatal)
        validators: List of (name, function) tuples for validation
    
    Methods:
        add_validator: Register a new validation function
        validate: Execute all validators on target object
        to_dict: Serialize validation state
        from_dict: Deserialize validation state
        for_tier_a/b/c: Factory methods for tier-specific validators
    """
    
    # Validation results
    is_valid: bool = True
    validation_results: Dict[str, bool] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    
    # Validation functions registry
    _validators: List[Tuple[str, Callable]] = field(default_factory=list, repr=False)
    
    def add_validator(self, name: str, validator_func: Callable) -> "CCV":
        """
        Add a validation function to the registry.
        
        Args:
            name: Unique name for this validator
            validator_func: Callable that takes target object and returns
                           (is_valid: bool, messages: List[str])
        
        Returns:
            Self for method chaining
        """
        self._validators.append((name, validator_func))
        return self
    
    def validate(self, target: Any) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute all registered validators on target.
        
        Args:
            target: Object to validate (usually a TierState instance)
        
        Returns:
            Tuple of (is_valid, validation_report)
            - is_valid: True if all validators passed
            - validation_report: Dict with detailed results
        """
        # Clear previous results
        self.validation_results.clear()
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        # Execute each validator
        for name, validator_func in self._validators:
            try:
                is_valid, messages = validator_func(target)
                self.validation_results[name] = is_valid
                
                if not is_valid:
                    self.validation_errors.extend(
                        [f"{name}: {msg}" for msg in messages]
                    )
                else:
                    # Check for warnings (validator can return warnings even when valid)
                    if messages:
                        self.validation_warnings.extend(
                            [f"{name}: {msg}" for msg in messages]
                        )
                        
            except Exception as e:
                # Validator threw exception - treat as validation failure
                self.validation_results[name] = False
                self.validation_errors.append(f"{name}: Validator error - {str(e)}")
        
        # Overall status is AND of all results
        self.is_valid = all(self.validation_results.values()) if self.validation_results else True
        
        return self.is_valid, {
            "is_valid": self.is_valid,
            "results": self.validation_results.copy(),
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "validator_count": len(self._validators)
        }
    
    def get_failed_validators(self) -> List[str]:
        """Get list of validator names that failed."""
        return [
            name for name, passed in self.validation_results.items()
            if not passed
        ]
    
    def get_passed_validators(self) -> List[str]:
        """Get list of validator names that passed."""
        return [
            name for name, passed in self.validation_results.items()
            if passed
        ]
    
    def clear(self) -> "CCV":
        """Clear all validation results and errors."""
        self.is_valid = True
        self.validation_results.clear()
        self.validation_errors.clear()
        self.validation_warnings.clear()
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize validation state to dictionary.
        
        Note: Does not serialize validator functions (non-serializable)
        """
        return {
            "is_valid": self.is_valid,
            "validation_results": self.validation_results.copy(),
            "validation_errors": self.validation_errors.copy(),
            "validation_warnings": self.validation_warnings.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CCV":
        """
        Deserialize from dictionary.
        
        Note: Validator functions must be re-registered after deserialization
        """
        return cls(
            is_valid=data.get("is_valid", True),
            validation_results=data.get("validation_results", {}),
            validation_errors=data.get("validation_errors", []),
            validation_warnings=data.get("validation_warnings", [])
        )
    
    # ========================================================================
    # Factory Methods for Tier-Specific Validators
    # ========================================================================
    
    @classmethod
    def for_tier_a(cls) -> "CCV":
        """
        Create CCV instance with TierA-specific validators.
        
        Validators:
        - wpd_structure: Validates WPD document structure
        - metadata: Validates document metadata fields
        - hierarchy: Validates document hierarchy relationships
        - created_documents: Validates created document paths
        
        Returns:
            CCV instance pre-configured for TierAState validation
        """
        ccv = cls()
        
        # Import validators (lazy import to avoid circular dependencies)
        try:
            from .tier_validators import (
                validate_wpd_document_structure,
                validate_document_metadata,
                validate_document_hierarchy,
                validate_created_documents
            )
            
            ccv.add_validator("wpd_structure", validate_wpd_document_structure)
            ccv.add_validator("metadata", validate_document_metadata)
            ccv.add_validator("hierarchy", validate_document_hierarchy)
            ccv.add_validator("created_documents", validate_created_documents)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def for_tier_b(cls) -> "CCV":
        """
        Create CCV instance with TierB-specific validators.
        
        Validators:
        - execution_results: Validates execution results structure
        - phase_completion: Validates phase completion status
        - milestone_status: Validates milestone tracking
        - sources: Validates DocumentSources fields
        
        Returns:
            CCV instance pre-configured for TierBState validation
        """
        ccv = cls()
        
        try:
            from .tier_validators import (
                validate_execution_results,
                validate_phase_completion,
                validate_milestone_status,
                validate_document_sources
            )
            
            ccv.add_validator("execution_results", validate_execution_results)
            ccv.add_validator("phase_completion", validate_phase_completion)
            ccv.add_validator("milestone_status", validate_milestone_status)
            ccv.add_validator("sources", validate_document_sources)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def for_tier_c(cls) -> "CCV":
        """
        Create CCV instance with TierC-specific validators.
        
        Validators:
        - modifications: Validates document modification structure
        - affected_sections: Validates affected section tracking
        - target_document: Validates target document path
        - creation_context: Validates document creation context
        
        Returns:
            CCV instance pre-configured for TierCState validation
        """
        ccv = cls()
        
        try:
            from .tier_validators import (
                validate_document_modifications,
                validate_affected_sections,
                validate_target_document,
                validate_creation_context
            )
            
            ccv.add_validator("modifications", validate_document_modifications)
            ccv.add_validator("affected_sections", validate_affected_sections)
            ccv.add_validator("target_document", validate_target_document)
            ccv.add_validator("creation_context", validate_creation_context)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def for_tier_d(cls) -> "CCV":
        """
        Create CCV instance with TierD-specific validators.
        
        Validators:
        - issue_description: Validates issue description is not empty
        - analysis_results: Validates analysis results structure
        - suggested_fixes: Validates suggested fixes are provided
        
        Returns:
            CCV instance pre-configured for TierDState validation
        """
        ccv = cls()
        
        try:
            from .tier_validators import (
                validate_issue_description,
                validate_analysis_results,
                validate_suggested_fixes
            )
            
            ccv.add_validator("issue_description", validate_issue_description)
            ccv.add_validator("analysis_results", validate_analysis_results)
            ccv.add_validator("suggested_fixes", validate_suggested_fixes)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def for_tier_e(cls) -> "CCV":
        """
        Create CCV instance with TierE-specific validators.
        
        Validators:
        - sources: Validates DocumentSources fields
        - prd_operations: Validates PRD operations structure
        - sync_status: Validates synchronization status
        
        Returns:
            CCV instance pre-configured for TierEState validation
        """
        ccv = cls()
        
        try:
            from .tier_validators import (
                validate_document_sources,
                validate_prd_operations,
                validate_sync_status
            )
            
            ccv.add_validator("sources", validate_document_sources)
            ccv.add_validator("prd_operations", validate_prd_operations)
            ccv.add_validator("sync_status", validate_sync_status)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def for_tier_f(cls) -> "CCV":
        """
        Create CCV instance with TierF-specific validators.
        
        Validators:
        - classification_results: Validates classification results structure
        - confidence_score: Validates confidence score is in range [0, 1]
        - suggested_tier: Validates suggested tier is valid
        
        Returns:
            CCV instance pre-configured for TierFState validation
        """
        ccv = cls()
        
        try:
            from .tier_validators import (
                validate_classification_results,
                validate_confidence_score,
                validate_suggested_tier
            )
            
            ccv.add_validator("classification_results", validate_classification_results)
            ccv.add_validator("confidence_score", validate_confidence_score)
            ccv.add_validator("suggested_tier", validate_suggested_tier)
            
        except ImportError:
            # Validators not yet implemented - return empty CCV
            pass
        
        return ccv
    
    @classmethod
    def empty(cls) -> "CCV":
        """Create empty CCV with no validators (for testing or manual setup)."""
        return cls()


# ============================================================================
# Utility Functions
# ============================================================================

def create_ccv_for_tier(tier: str) -> CCV:
    """
    Factory function to create CCV instance for specific tier.
    
    Args:
        tier: Tier identifier ("A", "B", "C", "D", "E", "F")
    
    Returns:
        CCV instance configured for the specified tier
    
    Raises:
        ValueError: If tier is not recognized
    """
    tier = tier.upper()
    
    factory_map = {
        "A": CCV.for_tier_a,
        "B": CCV.for_tier_b,
        "C": CCV.for_tier_c,
        "D": CCV.for_tier_d,
        "E": CCV.for_tier_e,
        "F": CCV.for_tier_f
    }
    
    factory = factory_map.get(tier)
    if factory is None:
        raise ValueError(f"Unknown tier: {tier}. Must be one of A, B, C, D, E, F")
    
    return factory()


__all__ = [
    "CCV",
    "create_ccv_for_tier"
]
