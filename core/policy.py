"""
Strict AWS Free Credits and Spending-Limit Policy Engine
Enforces programmatic safety checks, cost guards, and approval gates.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class PolicyViolationError(Exception):
    """Raised when an operation attempts to bypass strict credit/budget controls."""
    pass

class AWSApprovalRequiredError(Exception):
    """Raised when an AWS cloud action is attempted without explicit user approval."""
    pass

class ResourceApprovalGateSpec(BaseModel):
    service_and_resource_type: str = Field(..., description="Service and resource type (e.g. S3 Standard Bucket, RDS db.t4g.micro)")
    aws_region: str = Field(..., description="Target AWS region")
    expected_runtime_and_storage: str = Field(..., description="Expected duration and storage capacity")
    estimated_cost_before_credits_usd: float = Field(..., description="Estimated cost before any promotional credits")
    credit_eligibility_status: str = Field(..., description="Confirmation whether promotional credits apply")
    possible_uncovered_costs: str = Field(..., description="Potential charges not covered by credits (data transfer, snapshots, etc.)")
    safe_shutdown_and_cleanup_steps: str = Field(..., description="Exact instructions to stop/delete resources cleanly")
    approved_by_user: bool = Field(default=False, description="Explicit approval flag granted by the user")

class AWSSpendingPolicy:
    """
    Programmatic enforcement of the 8 non-negotiable credit and spending rules.
    """
    
    def __init__(self, approved_budget_usd: float = 0.00, provisioning_locked: bool = True):
        self.approved_budget_usd = approved_budget_usd
        self.provisioning_locked = provisioning_locked
        self._approved_resources: Dict[str, ResourceApprovalGateSpec] = {}

    def is_locked(self) -> bool:
        return self.provisioning_locked

    def verify_action(self, action_name: str, estimated_cost: float, resource_id: Optional[str] = None) -> None:
        """
        Validates any cloud-related action against the strict policy.
        """
        # Rule 1 & 6: Never exceed approved budget
        if estimated_cost > self.approved_budget_usd:
            raise PolicyViolationError(
                f"Action '{action_name}' estimated cost (${estimated_cost:.2f}) exceeds approved budget (${self.approved_budget_usd:.2f}). "
                "Halted per Rule 1: Never exceed approved budget without explicit sign-off."
            )
        
        # Rule 8: Mandatory approval gate
        if self.provisioning_locked:
            raise AWSApprovalRequiredError(
                f"Action '{action_name}' blocked: Cloud provisioning is locked. "
                "Approval gate must be presented to the user and explicitly confirmed first."
            )
        
        if resource_id and resource_id not in self._approved_resources:
            raise AWSApprovalRequiredError(
                f"Resource '{resource_id}' is not in the explicitly approved list."
            )

    def register_approval(self, resource_id: str, spec: ResourceApprovalGateSpec) -> None:
        if not spec.approved_by_user:
            raise PolicyViolationError("Cannot register resource approval without user confirmation.")
        self._approved_resources[resource_id] = spec

    def get_approval_spec(self, resource_type: str, region: str = "us-east-1") -> ResourceApprovalGateSpec:
        """
        Prepares the required 7-point disclosure card for a proposed cloud resource.
        """
        if resource_type.lower() == "s3":
            return ResourceApprovalGateSpec(
                service_and_resource_type="Amazon S3 (Standard Storage Bucket)",
                aws_region=region,
                expected_runtime_and_storage="Temporary / 30-day lifecycle rule, < 1 GB synthetic backups",
                estimated_cost_before_credits_usd=0.03,  # ~$0.023/GB-month + PUT requests
                credit_eligibility_status="Subject to active AWS Free Tier (5 GB standard storage for 12 mos) or promotional credits.",
                possible_uncovered_costs="Data egress / API request charges if requests exceed free tier thresholds; cross-region data transfer if queried externally.",
                safe_shutdown_and_cleanup_steps=(
                    "1. Empty all versioned objects: `aws s3 rm s3://<bucket-name> --recursive`\n"
                    "2. Delete bucket: `aws s3 rb s3://<bucket-name>`\n"
                    "3. Ensure lifecycle expiration rules are purged."
                ),
                approved_by_user=False
            )
        elif resource_type.lower() == "rds":
            return ResourceApprovalGateSpec(
                service_and_resource_type="Amazon RDS (Single-AZ PostgreSQL db.t4g.micro or db.t3.micro, 20 GB gp3)",
                aws_region=region,
                expected_runtime_and_storage="Demo run only (< 2 hours), 20 GB allocated storage",
                estimated_cost_before_credits_usd=1.50,  # Pro-rated hourly compute + storage
                credit_eligibility_status="Subject to 750 hours/mo Free Tier (if in first 12 months) or Promotional Credits applicable to RDS compute.",
                possible_uncovered_costs="Allocated gp3 storage ($0.115/GB-mo) and automated snapshot retention charges accumulate EVEN WHEN THE INSTANCE IS STOPPED.",
                safe_shutdown_and_cleanup_steps=(
                    "1. Immediate stop during idle pauses (note: storage continues billing).\n"
                    "2. Complete teardown immediately after demonstration:\n"
                    "   `aws rds delete-db-instance --db-instance-identifier <id> --skip-final-snapshot`\n"
                    "3. Delete any manual snapshots or parameter groups."
                ),
                approved_by_user=False
            )
        else:
            return ResourceApprovalGateSpec(
                service_and_resource_type=f"Custom AWS Resource ({resource_type})",
                aws_region=region,
                expected_runtime_and_storage="TBD",
                estimated_cost_before_credits_usd=0.00,
                credit_eligibility_status="Unknown - verification required prior to provisioning.",
                possible_uncovered_costs="Uncertainty flagged per Rule 8. User confirmation required.",
                safe_shutdown_and_cleanup_steps="Resource-specific deletion procedure required before creation.",
                approved_by_user=False
            )

policy_engine = AWSSpendingPolicy()

