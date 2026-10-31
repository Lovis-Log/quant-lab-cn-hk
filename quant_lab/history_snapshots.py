"""Immutable, checksum-verified snapshots, only for reviewed retention rights."""

from datetime import datetime, timezone
import hashlib
import io
import json
import zlib

import pandas as pd

from quant_lab.processing import clean_stock_history, DataValidationError
from quant_lab.source_rights import require_retention
from quant_lab.storage import _connect, database_path
from quant_lab.market_data import normalize_symbol


def query_key(market, symbol, start, end, adjustment):
    return json.dumps([market, symbol, str(start), str(end), adjustment], ensure_ascii=False)


def frame_sha(frame):
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


class HistorySnapshotStore:
    """The head moves only after an entire validated response is committed."""

    def __init__(self, path=None):
        self.path = path

    def save(self, bundle, start, end):
        require_retention(bundle.retention)
        if bundle.symbol != normalize_symbol(bundle.market, bundle.symbol) or bundle.currency != {"A 股": "CNY", "港股": "HKD"}.get(bundle.market):
            raise DataValidationError("快照的证券代码或市场币种不匹配。")
        if bundle.update_error or bundle.received_at is None or bundle.received_at.tzinfo is None:
            raise DataValidationError("失败或未知接收时间的行情不能形成有效快照。")
        frame = clean_stock_history(bundle.frame, start, end)
        if frame.empty or not frame.equals(bundle.frame):
            raise DataValidationError("快照必须是完整、已规范化且非空的查询结果。")
        from quant_lab.data_quality import assess_history
        quality = assess_history(frame, bundle.market, start, end, source=bundle.source,
            currency=bundle.currency, adjustment=bundle.adjustment, received_at=bundle.received_at)
        if not quality.structural_valid or quality.unfinished_sessions:
            raise DataValidationError("未校验或未结束日线不能持久化为已校验快照。")
        raw = frame.to_csv(index=False).encode("utf-8")
        sha = hashlib.sha256(raw).hexdigest()
        metadata = {"format": 1, "market": bundle.market, "symbol": bundle.symbol,
            "source": bundle.source, "currency": bundle.currency, "adjustment": bundle.adjustment,
            "received_at": bundle.received_at.isoformat(), "company_name": bundle.company_name,
            "requested_start": str(start), "requested_end": str(end), "raw_sha256": sha,
            "batch_id": bundle.batch_id, "quality": quality.to_dict(), "retention": bundle.retention.to_dict()}
        encoded = json.dumps(metadata, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        snapshot_id = hashlib.sha256(encoded.encode("utf-8") + raw).hexdigest()
        key = query_key(bundle.market, bundle.symbol, start, end, bundle.adjustment)
        with _connect(self.path) as db:
            db.execute("INSERT OR IGNORE INTO history_snapshots VALUES (?,?,?,?,?)",
                       (snapshot_id, encoded, sha, zlib.compress(raw), datetime.now(timezone.utc).isoformat()))
            db.execute("INSERT INTO history_snapshot_heads VALUES (?,?) ON CONFLICT(query_key) "
                       "DO UPDATE SET snapshot_id=excluded.snapshot_id", (key, snapshot_id))
        return snapshot_id

    def load(self, market, symbol, start, end, adjustment, *, policy):
        # Recheck the current policy; an old stored grant is not sufficient.
        require_retention(policy)
        if not (self.path or database_path()).exists():
            return None
        key = query_key(market, symbol, start, end, adjustment)
        with _connect(self.path) as db:
            row = db.execute("SELECT s.* FROM history_snapshot_heads h JOIN history_snapshots s "
                             "ON s.id=h.snapshot_id WHERE h.query_key=?", (key,)).fetchone()
        if row is None:
            return None
        try:
            encoded = row["metadata_json"]
            raw = zlib.decompress(row["frame_csv"])
            metadata = json.loads(encoded)
            if hashlib.sha256(raw).hexdigest() != row["raw_sha256"] or metadata["raw_sha256"] != row["raw_sha256"]:
                raise ValueError("checksum")
            if hashlib.sha256(encoded.encode("utf-8") + raw).hexdigest() != row["id"]:
                raise ValueError("metadata checksum")
            if query_key(metadata["market"], metadata["symbol"], metadata["requested_start"],
                         metadata["requested_end"], metadata["adjustment"]) != key:
                raise ValueError("query")
            if metadata["format"] != 1 or metadata["retention"] != policy.to_dict():
                return None
            if metadata["currency"] != {"A 股": "CNY", "港股": "HKD"}.get(market):
                raise ValueError("currency")
            frame = pd.read_csv(io.BytesIO(raw), parse_dates=["date"], float_precision="round_trip")
            frame = clean_stock_history(frame, start, end)
            from quant_lab.data import HistoryBundle
            from quant_lab.data_quality import assess_history
            received = datetime.fromisoformat(metadata["received_at"])
            quality = assess_history(frame, market, start, end, source=metadata["source"],
                currency=metadata["currency"], adjustment=adjustment, received_at=received)
            if not quality.structural_valid or frame.empty:
                raise ValueError("structure")
            return HistoryBundle(frame, market, symbol, metadata["source"], metadata["currency"], adjustment,
                received_at=received, cached=True, quality=quality, company_name=metadata["company_name"],
                batch_id=metadata["batch_id"], retention=policy, snapshot_id=row["id"],
                update_result="读取已校验磁盘快照；不是新获取")
        except (KeyError, TypeError, ValueError, zlib.error) as exc:
            raise DataValidationError("本地行情快照校验失败；未删除或替换原快照。") from exc
