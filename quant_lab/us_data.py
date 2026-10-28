"""US price/action contracts. Unknown actions are never an empty event ledger."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Protocol

import numpy as np
import pandas as pd

from quant_lab.source_rights import RetentionPolicy, UNVERIFIED_RETENTION
from quant_lab.us_market import USInstrument, SettlementCalendar, us_schedule, NY


def money(value):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("美元金额必须是有效数值。") from exc
    if not number.is_finite():
        raise ValueError("美元金额必须为有限值。")
    return number


@dataclass(frozen=True)
class USAction:
    event_id: str
    symbol: str
    kind: str
    effective_date: date
    evidence: str
    known_at: datetime
    numerator: int = 1
    denominator: int = 1
    amount_per_share: Decimal = Decimal("0")
    pay_at: datetime | None = None
    verified: bool = True
    payment_date: date | None = None
    availability_assumption: str = "verified-timestamp"

    def __post_init__(self):
        if not self.event_id or self.known_at.tzinfo is None:
            raise ValueError("公司行动需稳定事件ID和带时区的信息可得时间。")
        if self.kind == "split" and (isinstance(self.numerator,bool) or isinstance(self.denominator,bool) or
                not isinstance(self.numerator,int) or not isinstance(self.denominator,int) or
                self.numerator <= 0 or self.denominator <= 0):
            raise ValueError("拆股比例须为正整数之比。")
        if self.kind == "dividend":
            if self.pay_at is None and self.payment_date is not None:
                object.__setattr__(self,"pay_at",datetime.combine(self.payment_date+timedelta(days=1),time.min,NY))
                object.__setattr__(self,"availability_assumption","after-payment-date")
            if money(self.amount_per_share) <= 0 or self.pay_at is None or self.pay_at.tzinfo is None:
                raise ValueError("普通现金股息需正的每股金额和已核验的支付时刻；未知支付时间不能当作可用现金。")
            if self.payment_date is None:
                object.__setattr__(self,"payment_date",self.pay_at.astimezone(NY).date())
            if self.payment_date < self.effective_date or self.availability_assumption not in {"verified-timestamp","after-payment-date"}:
                raise ValueError("股息支付不得早于除息日期。")
            earliest=datetime.combine(self.payment_date+timedelta(days=1),time.min,NY)
            if (self.availability_assumption=="verified-timestamp" and self.pay_at.astimezone(NY).date()!=self.payment_date) or (
                    self.availability_assumption=="after-payment-date" and self.pay_at<earliest):
                raise ValueError("股息可用时刻与已核验支付日期或保守可用假设不一致。")

    @property
    def split_ratio(self):
        return Fraction(self.numerator, self.denominator)


@dataclass(frozen=True)
class USActionBook:
    symbol: str
    start: date
    end: date
    known: bool
    evidence: str
    events: tuple[USAction, ...] = ()


@dataclass(frozen=True)
class USDataset:
    instrument: USInstrument
    raw: pd.DataFrame
    source: str
    received_at: datetime
    actions: USActionBook
    raw_price_evidence: str = ""
    price_basis: str = "unverified"
    retention: RetentionPolicy = UNVERIFIED_RETENTION
    synthetic: bool = False
    input_version: str = "us-input-v1"


class USMarketDataProvider(Protocol):
    name: str

    def history(self, instrument: USInstrument, start: date, end: date) -> USDataset: ...


def validate_us_prices(raw):
    required = ("date", "open", "high", "low", "close", "volume")
    if not isinstance(raw,pd.DataFrame) or raw.columns.duplicated().any() or not set(required).issubset(raw.columns):
        raise ValueError("美股原始日线缺少唯一的OHLCV字段。")
    data = raw.loc[:,list(required)].copy()
    data["date"] = pd.to_datetime(data.date,errors="coerce")
    if data.empty or data.date.isna().any() or not pd.api.types.is_datetime64_dtype(data.date.dtype):
        raise ValueError("日线需非空、无时区的市场交易日期，不能混用报价时刻。")
    if (data.date != data.date.dt.normalize()).any() or data.date.duplicated().any() or not data.date.is_monotonic_increasing:
        raise ValueError("日线交易日期须为唯一升序的完整日期。")
    for field in required[1:]:
        if data[field].map(lambda value:isinstance(value,(bool,np.bool_))).any():
            raise ValueError("价格和成交量不能是布尔值。")
        data[field]=pd.to_numeric(data[field],errors="coerce")
    if not np.isfinite(data.loc[:,list(required[1:])].to_numpy(dtype=float)).all():
        raise ValueError("美股价格或成交量包含无效数值。")
    if (data[["open","high","low","close"]]<=0).any().any() or (data.volume<0).any():
        raise ValueError("美股价格须为正、成交量须非负。")
    if (data.high < data[["open","low","close"]].max(axis=1)).any() or (data.low > data[["open","high","close"]].min(axis=1)).any():
        raise ValueError("美股OHLC高低价关系无效。")
    return data


def eligibility_issues(data: USDataset, settlement: SettlementCalendar, *, teaching=False):
    """Fail closed before any calculation; callers cannot turn unknown into zero."""
    issues=[]
    raw=validate_us_prices(data.raw)
    first,last=raw.date.iloc[0].date(),raw.date.iloc[-1].date()
    symbol=data.instrument.symbol
    if data.received_at.tzinfo is None:
        issues.append("接收时间未带时区")
    if data.input_version != "us-input-v1":
        issues.append("研究输入版本不受支持")
    if not data.instrument.identity_evidence:
        issues.append("证券身份尚未核验")
    if data.instrument.security_type not in {"common_stock","class_share"}:
        issues.append("首版仅核算普通股票及类别股，ADR/其他证券需专门事件和费用适配")
    if data.price_basis != "unadjusted-execution" or not data.raw_price_evidence:
        issues.append("原始执行价格口径尚未核验")
    book=data.actions
    if not book.known or not book.evidence or book.symbol!=symbol or book.start>first or book.end<last:
        issues.append("公司行动完整性或覆盖未知，不能视为没有事件")
    expected=us_schedule(first,last)
    if tuple(raw.date.dt.date) != tuple(expected.index.date):
        issues.append("交易日缺失或不在参考日历内；不能填充可成交价格")
    if not data.retention.allowed or not data.retention.evidence:
        issues.append("研究快照留存权限尚未通过")
    if not settlement.verified or not settlement.evidence or settlement.start>first or settlement.end<last:
        issues.append("独立结算日历尚未核验或覆盖不足")
    if data.synthetic and not teaching:
        issues.append("教学输入不能作为真实行情运行")
    if teaching and not data.synthetic:
        issues.append("教学模式不能绕过真实来源的验证关卡")
    if len({e.event_id for e in book.events}) != len(book.events):
        issues.append("公司行动事件ID重复")
    split_days={e.effective_date for e in book.events if e.kind=="split" and first<=e.effective_date<=last}
    dividend_days={e.effective_date for e in book.events if e.kind=="dividend" and first<=e.effective_date<=last}
    if split_days & dividend_days:
        issues.append("同日拆股与分红的份额基准首版不支持")
    for event in book.events:
        if not first<=event.effective_date<=last:
            continue
        if not event.verified or not event.evidence or event.symbol!=symbol:
            issues.append(f"{event.effective_date} 公司行动未核验或证券不匹配")
        elif event.kind not in {"split","dividend"}:
            issues.append(f"{event.effective_date} {event.kind}事件首版不支持")
        elif event.effective_date not in expected.index.date:
            issues.append(f"{event.effective_date} 公司行动不在交易日")
        elif event.known_at > expected.loc[str(event.effective_date),"open"].to_pydatetime():
            issues.append(f"{event.effective_date} 公司行动在开盘前不可得")
    if not expected.empty and data.received_at.tzinfo and data.received_at < expected.iloc[-1].close.to_pydatetime():
        issues.append("末日日线尚未收市")
    return tuple(dict.fromkeys(issues))
