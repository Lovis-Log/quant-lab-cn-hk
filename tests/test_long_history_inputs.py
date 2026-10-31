"""Atomic segments, retained snapshots, and paired research-input regressions."""

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pandas as pd
import pytest

from quant_lab.data import AKShareProvider, HistoryBundle, HistoryCache
from quant_lab.history_snapshots import HistorySnapshotStore, frame_sha
from quant_lab.paths import database_path
from quant_lab.processing import DataValidationError
from quant_lab.research_inputs import prepare_inputs
from quant_lab.source_rights import TEACHING_RETENTION, UNVERIFIED_RETENTION


START, END = date(2020, 1, 1), date(2020, 1, 6)


def bundle(start=START, end=END, adjustment="", *, retained=True, price=10.):
    days = pd.bdate_range(start, end)
    frame = pd.DataFrame({"date": days, "open": price, "high": price+1, "low": price-1,
                          "close": price, "volume": 100., "amount": price*100})
    return HistoryBundle(frame, "A 股", "600519", "固定教学样本", "CNY", adjustment,
                         datetime.now(timezone.utc), retention=TEACHING_RETENTION if retained else UNVERIFIED_RETENTION)


def test_raw_segmentation_overlap_and_adjusted_history_is_atomic(monkeypatch):
    provider, calls = AKShareProvider(), []
    def once(market, symbol, start, end, adjustment):
        calls.append((start, end, adjustment))
        return bundle(start, end, adjustment)
    monkeypatch.setattr(provider, "_history_once", once)
    start, end = date(2016, 10, 27), date(2026, 10, 27)
    result = provider.history("A 股", "600519", start, end)
    assert len(calls) == len(result.segments) == 4
    assert not result.frame.date.duplicated().any()
    assert result.frame.date.iloc[0].date() == start and result.frame.date.iloc[-1].date() == end
    assert all(calls[i][0] < calls[i-1][1] for i in range(1, len(calls)))
    calls.clear()
    provider.history("A 股", "600519", start, end, "qfq")
    assert calls == [(start, end, "qfq")]


@pytest.mark.parametrize("changed", ["price", "source"])
def test_segment_revision_or_source_switch_rejects_entire_result(monkeypatch, changed):
    provider, calls = AKShareProvider(), []
    def once(market, symbol, start, end, adjustment):
        calls.append(start)
        result = bundle(start, end, price=11. if changed == "price" and len(calls)>1 else 10.)
        return replace(result, source="changed") if changed == "source" and len(calls)>1 else result
    monkeypatch.setattr(provider, "_history_once", once)
    with pytest.raises(DataValidationError, match="来源|不一致"):
        provider.history("A 股", "600519", date(2016,1,1), END)


def test_unverified_rights_never_write_new_snapshot(tmp_path):
    target = tmp_path/"research.sqlite3"
    with pytest.raises(ValueError, match="留存许可"):
        HistorySnapshotStore(target).save(bundle(retained=False), START, END)
    assert not target.exists()


def test_immutable_versions_checksum_and_previous_good_head(tmp_path):
    target = tmp_path/"research.sqlite3"
    store = HistorySnapshotStore(target)
    first = bundle()
    old_id = store.save(first, START, END)
    new_id = store.save(bundle(price=20), START, END)
    assert old_id != new_id
    broken = bundle(price=-1)
    with pytest.raises(ValueError):
        store.save(broken, START, END)
    loaded = store.load("A 股", "600519", START, END, "", policy=TEACHING_RETENTION)
    assert loaded.snapshot_id == new_id and loaded.frame.close.eq(20).all()
    assert loaded.received_at == datetime.fromisoformat(loaded.received_at.isoformat())
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM history_snapshots").fetchone()[0] == 2
        db.execute("UPDATE history_snapshots SET frame_csv=? WHERE id=?", (b"corrupt", new_id))
    with pytest.raises(DataValidationError, match="快照校验失败"):
        store.load("A 股", "600519", START, END, "", policy=TEACHING_RETENTION)


def test_durable_cache_restart_force_refresh_and_failure_keep_time():
    class Provider:
        retention_policy = TEACHING_RETENTION
        calls = 0
        fail = False
        def history(self, *args):
            self.calls += 1
            if self.fail:
                raise ConnectionError("offline")
            return bundle()
    provider = Provider()
    first = HistoryCache(provider).get("A 股", "600519", START, END)
    assert first.snapshot_id and not first.cached
    restarted = HistoryCache(provider)
    restored = restarted.get("A 股", "600519", START, END)
    assert restored.cached and restored.received_at == first.received_at and provider.calls == 1
    provider.fail = True
    failed = restarted.get("A 股", "600519", START, END, force=True)
    assert provider.calls == 2 and failed.update_error and failed.frame.equals(first.frame)
    assert failed.received_at == first.received_at and failed.snapshot_id == first.snapshot_id


def test_same_query_force_requests_single_flight():
    entered, release = Event(), Event()
    class Provider:
        calls = 0
        def history(self, *args):
            self.calls += 1
            entered.set()
            assert release.wait(5)
            return bundle(retained=False)
    provider = Provider()
    cache = HistoryCache(provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one = pool.submit(cache.get, "A 股", "600519", START, END, force=True)
        assert entered.wait(3)
        two = pool.submit(cache.get, "A 股", "600519", START, END, force=True)
        # Observe the second worker has entered RefreshCache.get before releasing
        # the provider; avoid making a timing assertion on a fast HTTP surrogate.
        import time
        time.sleep(.05)
        release.set()
        assert one.result().frame.equals(two.result().frame)
    assert provider.calls == 1


def test_adjusted_pair_uses_three_fresh_requests_and_exact_days():
    shown = bundle(adjustment="qfq")
    calls = []
    def fetch(market, symbol, start, end, adjustment, **kwargs):
        calls.append((adjustment, kwargs))
        return bundle(start, end, adjustment)
    inputs = prepare_inputs(shown, fetch=fetch)
    assert [call[0] for call in calls] == ["qfq", "", "qfq"]
    assert all(call[1] == {"force": True} for call in calls)
    assert inputs.manifest["raw"]["sha256"] == frame_sha(inputs.raw)
    assert inputs.manifest["signal"]["sha256"] == frame_sha(inputs.signal)
    inputs.raw.iloc[0,1] = 999
    assert shown.frame.open.iloc[0] == 10


@pytest.mark.parametrize("failure", ["revised", "cached", "error", "dates", "source", "currency"])
def test_pair_never_silently_mixes_changed_or_old_inputs(failure):
    calls = []
    def fetch(market, symbol, start, end, adjustment, **kwargs):
        calls.append(adjustment)
        result = bundle(adjustment=adjustment)
        if failure == "revised" and len(calls)==3:
            return bundle(adjustment=adjustment, price=20)
        if len(calls)==2:
            if failure == "cached": return replace(result, cached=True)
            if failure == "error": return replace(result, update_error="failed")
            if failure == "dates": return replace(result, frame=result.frame.iloc[1:].reset_index(drop=True))
            if failure == "source": return replace(result, source="different")
            if failure == "currency": return replace(result, currency="USD")
        return result
    with pytest.raises(DataValidationError):
        prepare_inputs(bundle(adjustment="qfq"), fetch=fetch)


def test_unadjusted_pair_is_offline_and_keeps_legacy_algorithm():
    inputs = prepare_inputs(bundle())
    assert inputs.raw.equals(inputs.signal)
    assert inputs.manifest["revision_check"] == "same-unadjusted-input"
