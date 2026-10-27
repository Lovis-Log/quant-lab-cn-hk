"""Audited local-retention decisions, separate from software licensing.

No live provider has been granted durable retention by this registry. Adding a
provider needs an explicit reviewed policy; a successful HTTP call is not one.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RetentionPolicy:
    policy_id: str = "unverified-v1"
    allowed: bool = False
    evidence: str = ""
    checked_on: str = "2026-10-27"
    note: str = "来源本地留存许可尚未核实；仅会话复用，不自动写入磁盘行情快照。"

    def to_dict(self):
        return asdict(self)


UNVERIFIED_RETENTION = RetentionPolicy()
TEACHING_RETENTION = RetentionPolicy(
    "quantlab-generated-v1", True, "repo:tools/performance_fixture.py", "2026-10-27",
    "平台生成的固定教学样本，可本地留存；不是市场行情。",
)


def require_retention(policy):
    if not isinstance(policy, RetentionPolicy) or not policy.allowed or not policy.evidence:
        raise ValueError("来源本地留存许可未核实，不能新增磁盘行情快照；已有档案保留可读。")
