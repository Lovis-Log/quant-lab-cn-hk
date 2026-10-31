"""Declared version routes; legacy prices and their repr/CSV audit stay intact."""

LEGACY_VERSIONS={"algorithm":"ah-single-v1","rules":"ah-research-assumptions-v1",
    "fingerprint":"legacy-csv-repr-v1","data":"ohlcv-snapshot-v1"}
VALIDATION_VERSIONS={"algorithm":"research-validation-v1","execution":"ah-single-v1",
    "rules":"ah-research-assumptions-v1","fingerprint":"validation-manifest-sha256-v1","data":"ohlcv-snapshot-v1"}


def legacy_versions(manifest):
    declared=(manifest or {}).get("experiment_versions")
    present="experiment_versions" in (manifest or {})
    if present and declared!=LEGACY_VERSIONS:
        raise ValueError("该实验算法/规则/指纹版本尚无对应复算实现，不能用当前版本重新解释。")
    return dict(LEGACY_VERSIONS),present
