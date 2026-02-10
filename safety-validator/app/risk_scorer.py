"""Risk scoring algorithm for tool execution."""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import yaml
from pathlib import Path


class RiskLevel(str, Enum):
    """Risk levels for tool execution."""

    LOW = "LOW"  # Safe, no confirmation needed
    MEDIUM = "MEDIUM"  # Log but allow
    HIGH = "HIGH"  # Require confirmation
    CRITICAL = "CRITICAL"  # Block or require explicit authorization


@dataclass
class RiskScore:
    """Risk score with breakdown."""

    level: RiskLevel
    score: float  # 0.0 - 1.0
    factors: Dict[str, float]  # Contributing factors
    reasoning: str  # Human-readable explanation


class RiskScorer:
    """Calculate risk scores for tool execution plans."""

    def __init__(self, config_path: str = "config/policies.yaml"):
        """Initialize risk scorer.

        Args:
            config_path: Path to policies configuration
        """
        self.config_path = Path(config_path)
        self.policies = self._load_policies()

        # Load risk level mappings
        self.risk_mappings = self.policies.get("risk_levels", {})

        # Risk score thresholds (adjusted for 70% tool weight)
        # HIGH tools: 0.7 base * 0.7 weight = 0.49 should be HIGH
        # CRITICAL tools: 1.0 base * 0.7 weight = 0.70 should be CRITICAL
        # Thresholds are minimum scores, checked from top down
        self.thresholds = {
            RiskLevel.CRITICAL: 0.70,  # >= 0.70
            RiskLevel.HIGH: 0.45,  # >= 0.45, < 0.70
            RiskLevel.MEDIUM: 0.15,  # >= 0.15, < 0.45
            RiskLevel.LOW: 0.0,  # < 0.15
        }

    def _load_policies(self) -> Dict[str, Any]:
        """Load policies from YAML file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    return yaml.safe_load(f)

            module_dir = Path(__file__).parent.parent
            config_file = module_dir / self.config_path

            if config_file.exists():
                with open(config_file, "r") as f:
                    return yaml.safe_load(f)

            return {}

        except Exception as e:
            print(f"Warning: Failed to load policies: {e}")
            return {}

    def calculate_risk(
        self, tool: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> RiskScore:
        """Calculate risk score for a tool execution.

        Args:
            tool: Tool name
            parameters: Tool parameters
            context: Optional context (user history, time of day, etc.)

        Returns:
            RiskScore with level and breakdown
        """
        factors = {}

        # Factor 1: Base risk from tool type (70% weight - primary factor)
        base_risk = self._get_base_risk(tool)
        factors["tool_type"] = base_risk * 0.7

        # Factor 2: Parameter risk (20% weight)
        param_risk = self._assess_parameter_risk(tool, parameters)
        factors["parameters"] = param_risk * 0.2

        # Factor 3: Contextual risk (10% weight)
        context_risk = self._assess_contextual_risk(tool, parameters, context or {})
        factors["context"] = context_risk * 0.1

        # Calculate total score
        total_score = sum(factors.values())

        # Determine risk level
        risk_level = self._score_to_level(total_score)

        # Generate reasoning
        reasoning = self._generate_reasoning(tool, risk_level, factors)

        return RiskScore(level=risk_level, score=total_score, factors=factors, reasoning=reasoning)

    def _get_base_risk(self, tool: str) -> float:
        """Get base risk score for a tool.

        Args:
            tool: Tool name

        Returns:
            Risk score 0.0 - 1.0
        """
        tool_upper = tool.upper()

        # Check each risk level
        if tool_upper in self.risk_mappings.get("low", []):
            return 0.1
        elif tool_upper in self.risk_mappings.get("medium", []):
            return 0.4
        elif tool_upper in self.risk_mappings.get("high", []):
            return 0.7
        elif tool_upper in self.risk_mappings.get("critical", []):
            return 1.0
        else:
            # Unknown tool - treat as medium risk
            return 0.5

    def _assess_parameter_risk(self, tool: str, parameters: Dict[str, Any]) -> float:
        """Assess risk from parameters.

        Args:
            tool: Tool name
            parameters: Tool parameters

        Returns:
            Risk score 0.0 - 1.0
        """
        risk = 0.0
        risk_factors = []

        # Check for sensitive data in parameters
        for key, value in parameters.items():
            if not isinstance(value, str):
                continue

            value_lower = value.lower()

            # Check for file paths
            if key in ["path", "file_path", "directory"]:
                if any(
                    pattern in value_lower for pattern in ["..", "~", "/etc", "/var", "c:\\windows"]
                ):
                    risk_factors.append(0.5)

            # Check for commands
            if key in ["command", "cmd", "script"]:
                dangerous_chars = [";", "|", "&", "`", "$"]
                if any(char in value for char in dangerous_chars):
                    risk_factors.append(0.6)

            # Check for URLs
            if key in ["url", "link", "website"]:
                if "localhost" in value_lower or "127.0.0.1" in value:
                    risk_factors.append(0.4)

            # Check for database queries
            if key in ["query", "sql"]:
                sql_keywords = ["drop", "delete", "insert", "update", "exec"]
                if any(kw in value_lower for kw in sql_keywords):
                    risk_factors.append(0.7)

        # Check for large numbers (potential DoS)
        for key, value in parameters.items():
            if isinstance(value, (int, float)):
                if value > 1_000_000:
                    risk_factors.append(0.3)

        # Check for long strings (potential buffer overflow)
        for key, value in parameters.items():
            if isinstance(value, str) and len(value) > 5000:
                risk_factors.append(0.3)

        # Return maximum risk factor or 0
        return max(risk_factors) if risk_factors else 0.0

    def _assess_contextual_risk(
        self, tool: str, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> float:
        """Assess risk based on context.

        Args:
            tool: Tool name
            parameters: Tool parameters
            context: Execution context

        Returns:
            Risk score 0.0 - 1.0
        """
        risk = 0.0

        # Check if user has history of failed validations
        failed_validations = context.get("failed_validations", 0)
        if failed_validations > 5:
            risk += 0.3

        # Check if executing multiple high-risk actions
        recent_high_risk = context.get("recent_high_risk_count", 0)
        if recent_high_risk > 3:
            risk += 0.2

        # Check time of day (unusual hours increase risk)
        hour = context.get("hour", 12)
        if hour < 6 or hour > 23:
            risk += 0.1

        # Check if action is unusual for user
        is_unusual = context.get("is_unusual_action", False)
        if is_unusual:
            risk += 0.2

        return min(risk, 1.0)

    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level.

        Args:
            score: Risk score 0.0 - 1.0

        Returns:
            RiskLevel enum
        """
        if score >= self.thresholds[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        elif score >= self.thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif score >= self.thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_reasoning(self, tool: str, level: RiskLevel, factors: Dict[str, float]) -> str:
        """Generate human-readable risk reasoning.

        Args:
            tool: Tool name
            level: Risk level
            factors: Risk factors breakdown

        Returns:
            Reasoning string
        """
        lines = [f"Tool '{tool}' assessed as {level.value} risk."]

        # Sort factors by contribution
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)

        for factor_name, factor_value in sorted_factors:
            if factor_value > 0.1:
                percentage = int(factor_value * 100)
                lines.append(f"  - {factor_name}: {percentage}% contribution")

        return "\n".join(lines)

    def requires_confirmation(self, risk_score: RiskScore) -> bool:
        """Check if risk level requires user confirmation.

        Args:
            risk_score: Risk score result

        Returns:
            True if confirmation required
        """
        return risk_score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def should_block(self, risk_score: RiskScore) -> bool:
        """Check if risk level should block execution.

        Args:
            risk_score: Risk score result

        Returns:
            True if should block
        """
        # Only CRITICAL should be blocked by default
        # HIGH requires confirmation but can proceed
        return risk_score.level == RiskLevel.CRITICAL
