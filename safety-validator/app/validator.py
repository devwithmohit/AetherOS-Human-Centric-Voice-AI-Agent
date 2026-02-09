"""Main safety validator for execution plans."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .risk_scorer import RiskScorer, RiskLevel, RiskScore
from .sanitizers import InputSanitizer, SanitizationError
from .allow_lists import AllowListManager


class ValidationStatus(str, Enum):
    """Validation result status."""

    APPROVED = "APPROVED"  # Safe to execute
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"  # Needs user confirmation
    BLOCKED = "BLOCKED"  # Blocked, cannot execute
    SANITIZED = "SANITIZED"  # Approved with sanitized parameters


@dataclass
class ValidationResult:
    """Result of safety validation."""

    status: ValidationStatus
    risk_score: RiskScore
    sanitized_parameters: Dict[str, Any]
    warnings: List[str]
    blocked_reason: Optional[str] = None
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def is_safe(self) -> bool:
        """Check if execution is safe to proceed.

        Returns:
            True if APPROVED or SANITIZED, False otherwise
        """
        return self.status in [ValidationStatus.APPROVED, ValidationStatus.SANITIZED]

    def needs_confirmation(self) -> bool:
        """Check if user confirmation is needed.

        Returns:
            True if REQUIRES_CONFIRMATION
        """
        return self.status == ValidationStatus.REQUIRES_CONFIRMATION


class SafetyValidator:
    """Main safety validator for execution plans.

    Validates execution plans from Module 5 (Reasoning Engine) before
    they are sent to Module 7 (Action Executor).
    """

    def __init__(self, config_path: str = "config/policies.yaml", strict_mode: bool = False):
        """Initialize safety validator.

        Args:
            config_path: Path to policies configuration
            strict_mode: If True, block instead of warn on sanitization issues
        """
        self.risk_scorer = RiskScorer(config_path)
        self.sanitizer = InputSanitizer(config_path)
        self.allow_list = AllowListManager(config_path)
        self.strict_mode = strict_mode

        # Validation history for rate limiting
        self.validation_history: Dict[str, List[ValidationResult]] = {}

    def validate(
        self,
        user_id: str,
        tool: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """Validate a tool execution request.

        Args:
            user_id: User identifier
            tool: Tool name to execute
            parameters: Tool parameters
            context: Optional execution context

        Returns:
            ValidationResult with status and details
        """
        warnings = []

        # Step 1: Check if tool is on allow list
        if not self.allow_list.is_tool_allowed(tool):
            if self.allow_list.is_tool_blocked(tool):
                return ValidationResult(
                    status=ValidationStatus.BLOCKED,
                    risk_score=RiskScore(
                        level=RiskLevel.CRITICAL,
                        score=1.0,
                        factors={"tool_blocked": 1.0},
                        reasoning=f"Tool '{tool}' is explicitly blocked",
                    ),
                    sanitized_parameters={},
                    warnings=[],
                    blocked_reason=f"Tool '{tool}' is on the blocked list",
                )
            else:
                warnings.append(f"Tool '{tool}' not on allow list")
                if self.strict_mode:
                    return ValidationResult(
                        status=ValidationStatus.BLOCKED,
                        risk_score=RiskScore(
                            level=RiskLevel.HIGH,
                            score=0.8,
                            factors={"tool_not_allowed": 0.8},
                            reasoning=f"Tool '{tool}' not on allow list",
                        ),
                        sanitized_parameters={},
                        warnings=warnings,
                        blocked_reason=f"Tool '{tool}' not on allow list",
                    )

        # Step 2: Sanitize parameters
        try:
            sanitized_params, sanitization_warnings = self.sanitizer.sanitize_parameters(
                tool, parameters
            )
            warnings.extend(sanitization_warnings)
        except SanitizationError as e:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                risk_score=RiskScore(
                    level=RiskLevel.CRITICAL,
                    score=1.0,
                    factors={"sanitization_failed": 1.0},
                    reasoning=f"Sanitization failed: {e}",
                ),
                sanitized_parameters={},
                warnings=warnings,
                blocked_reason=f"Sanitization failed: {e}",
            )

        # Step 3: Validate specific parameter types
        param_validation_warnings = self._validate_parameter_types(sanitized_params)
        warnings.extend(param_validation_warnings)

        # Step 4: Calculate risk score
        enriched_context = self._enrich_context(user_id, context or {})
        risk_score = self.risk_scorer.calculate_risk(tool, sanitized_params, enriched_context)

        # Step 5: Check for PII in parameters
        pii_warnings = self._check_pii(sanitized_params)
        warnings.extend(pii_warnings)

        # Step 6: Check rate limits
        rate_limit_exceeded, rate_msg = self._check_rate_limits(user_id, risk_score.level)
        if rate_limit_exceeded:
            return ValidationResult(
                status=ValidationStatus.BLOCKED,
                risk_score=risk_score,
                sanitized_parameters=sanitized_params,
                warnings=warnings,
                blocked_reason=rate_msg,
            )

        # Step 7: Determine final status based on risk level
        status, requires_confirmation, confirmation_msg = self._determine_status(
            tool, risk_score, warnings
        )

        result = ValidationResult(
            status=status,
            risk_score=risk_score,
            sanitized_parameters=sanitized_params,
            warnings=warnings,
            requires_confirmation=requires_confirmation,
            confirmation_message=confirmation_msg,
        )

        # Record validation for rate limiting
        self._record_validation(user_id, result)

        return result

    def validate_batch(
        self,
        user_id: str,
        tool_calls: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ValidationResult]:
        """Validate multiple tool calls in a batch.

        Args:
            user_id: User identifier
            tool_calls: List of tool calls with 'tool' and 'parameters'
            context: Optional execution context

        Returns:
            List of ValidationResult objects
        """
        results = []

        for tool_call in tool_calls:
            tool = tool_call.get("tool")
            parameters = tool_call.get("parameters", {})

            result = self.validate(user_id, tool, parameters, context)
            results.append(result)

            # If any high-risk action is blocked, stop validation
            if (
                result.status == ValidationStatus.BLOCKED
                and result.risk_score.level == RiskLevel.CRITICAL
            ):
                break

        return results

    def _validate_parameter_types(self, parameters: Dict[str, Any]) -> List[str]:
        """Validate specific parameter types.

        Args:
            parameters: Sanitized parameters

        Returns:
            List of warnings
        """
        warnings = []

        for key, value in parameters.items():
            if not isinstance(value, str):
                continue

            # Validate URLs
            if key.lower() in ["url", "link", "website"]:
                if not self.allow_list.validate_url(value):
                    warnings.append(f"URL validation failed for: {value[:50]}")

            # Validate file paths
            elif key.lower() in ["path", "file_path", "directory"]:
                if not self.allow_list.validate_file_path(value):
                    warnings.append(f"File path validation failed for: {value[:50]}")

            # Validate application names
            elif key.lower() in ["app_name", "application"]:
                if not self.allow_list.is_application_allowed(value):
                    warnings.append(f"Application '{value}' not on allow list")

        return warnings

    def _enrich_context(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich context with validation history.

        Args:
            user_id: User identifier
            context: Base context

        Returns:
            Enriched context
        """
        enriched = context.copy()

        # Add validation history
        history = self.validation_history.get(user_id, [])

        # Count recent failed validations
        recent_failed = sum(1 for v in history[-10:] if v.status == ValidationStatus.BLOCKED)
        enriched["failed_validations"] = recent_failed

        # Count recent high-risk actions
        recent_high_risk = sum(
            1 for v in history[-20:] if v.risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        enriched["recent_high_risk_count"] = recent_high_risk

        return enriched

    def _check_pii(self, parameters: Dict[str, Any]) -> List[str]:
        """Check for PII in parameters.

        Args:
            parameters: Parameters to check

        Returns:
            List of warnings
        """
        warnings = []

        for key, value in parameters.items():
            if isinstance(value, str):
                pii_found = self.sanitizer.detect_pii(value)

                if pii_found:
                    pii_types = [pii_type for pii_type, _ in pii_found]
                    warnings.append(f"PII detected in parameter '{key}': {', '.join(pii_types)}")

        return warnings

    def _check_rate_limits(self, user_id: str, risk_level: RiskLevel) -> tuple[bool, Optional[str]]:
        """Check if user has exceeded rate limits.

        Args:
            user_id: User identifier
            risk_level: Risk level of current action

        Returns:
            Tuple of (exceeded, message)
        """
        history = self.validation_history.get(user_id, [])

        # Get rate limits from policies
        rate_limits = self.allow_list.get_policy("rate_limits.actions_per_minute", {})

        # Check recent actions (last minute)
        cutoff_time = datetime.utcnow()
        recent_actions = [v for v in history if (cutoff_time - v.timestamp).total_seconds() < 60]

        # Get limit for this risk level
        limit_key = f"{risk_level.value.lower()}_risk"
        limit = rate_limits.get(limit_key, 30)

        if len(recent_actions) >= limit:
            return (
                True,
                f"Rate limit exceeded: {len(recent_actions)} actions in last minute (limit: {limit})",
            )

        return False, None

    def _determine_status(
        self, tool: str, risk_score: RiskScore, warnings: List[str]
    ) -> tuple[ValidationStatus, bool, Optional[str]]:
        """Determine final validation status.

        Args:
            tool: Tool name
            risk_score: Calculated risk score
            warnings: Accumulated warnings

        Returns:
            Tuple of (status, requires_confirmation, confirmation_message)
        """
        # CRITICAL risk -> Block
        if risk_score.level == RiskLevel.CRITICAL:
            return ValidationStatus.BLOCKED, False, None

        # HIGH risk -> Require confirmation
        elif risk_score.level == RiskLevel.HIGH:
            msg = self._generate_confirmation_message(tool, risk_score)
            return ValidationStatus.REQUIRES_CONFIRMATION, True, msg

        # MEDIUM/LOW risk with warnings -> Sanitized
        elif warnings:
            return ValidationStatus.SANITIZED, False, None

        # LOW risk, no issues -> Approved
        else:
            return ValidationStatus.APPROVED, False, None

    def _generate_confirmation_message(self, tool: str, risk_score: RiskScore) -> str:
        """Generate confirmation message for high-risk actions.

        Args:
            tool: Tool name
            risk_score: Risk score

        Returns:
            Confirmation message
        """
        return (
            f"This action '{tool}' is classified as {risk_score.level.value} risk. "
            f"Do you want to proceed?\n\n"
            f"Risk assessment:\n{risk_score.reasoning}"
        )

    def _record_validation(self, user_id: str, result: ValidationResult):
        """Record validation result for rate limiting and history.

        Args:
            user_id: User identifier
            result: Validation result
        """
        if user_id not in self.validation_history:
            self.validation_history[user_id] = []

        self.validation_history[user_id].append(result)

        # Keep only last 100 validations per user
        if len(self.validation_history[user_id]) > 100:
            self.validation_history[user_id] = self.validation_history[user_id][-100:]

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get validation statistics for a user.

        Args:
            user_id: User identifier

        Returns:
            Dictionary of statistics
        """
        history = self.validation_history.get(user_id, [])

        if not history:
            return {
                "total_validations": 0,
                "approved": 0,
                "blocked": 0,
                "requires_confirmation": 0,
                "average_risk_score": 0.0,
            }

        return {
            "total_validations": len(history),
            "approved": sum(1 for v in history if v.status == ValidationStatus.APPROVED),
            "blocked": sum(1 for v in history if v.status == ValidationStatus.BLOCKED),
            "requires_confirmation": sum(
                1 for v in history if v.status == ValidationStatus.REQUIRES_CONFIRMATION
            ),
            "sanitized": sum(1 for v in history if v.status == ValidationStatus.SANITIZED),
            "average_risk_score": sum(v.risk_score.score for v in history) / len(history),
            "recent_actions": len(
                [v for v in history if (datetime.utcnow() - v.timestamp).total_seconds() < 60]
            ),
        }
