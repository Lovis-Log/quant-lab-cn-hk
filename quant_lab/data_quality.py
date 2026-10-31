"""Historical coverage and calendar checks; no UI and no network access.

Calendar gaps are observations, never proof of suspension, listing age, or a
provider outage. The calendar version and its research scope stay visible.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from importlib.metadata import version
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from quant_lab.processing import COLUMNS, DataValidationError, clean_stock_history


CALENDARS = {"A 股": "XSHG", "港股": "XHKG", "美股": "XNYS"}


def require_completed_close(bundle):
    report = getattr(bundle, "quality", None)
    if report is not None and (not report.structural_valid or report.unfinished_sessions):
        raise DataValidationError("存在未校验或尚未收市的日线；请使用已结束交易日并重新获取研究输入。")
    if report is not None and not report.calendar_available and bundle.received_at is not None:
        teaching = any(word in report.source.casefold() for word in ("教学", "模拟", "demo", "simulation", "teaching"))
        zone = {"A 股":"Asia/Shanghai", "港股":"Asia/Hong_Kong", "美股":"America/New_York"}.get(bundle.market, "UTC")
        local_day = bundle.received_at.astimezone(ZoneInfo(zone)).date()
        if not teaching and report.actual_end is not None and report.actual_end >= local_day:
            raise DataValidationError("末日日线是否收市无法核验，请缩短至已结束交易日后重新获取。")


@dataclass(frozen=True)
class CalendarReference:
    name: str
    version: str
    sessions: tuple[tuple[date, datetime], ...]
    available: bool
    note: str


@lru_cache(maxsize=64)
def calendar_reference(market: str, start: date, end: date) -> CalendarReference:
    name = CALENDARS.get(market)
    if name is None:
        return CalendarReference("", "", (), False, "该市场没有已配置的参考交易日历。")
    calendar_version = ""
    try:
        import exchange_calendars as xcals
        calendar_version = version("exchange_calendars")
        # Padding supports ranges that contain only holidays/weekends.
        cal = xcals.get_calendar(name, start=start-timedelta(days=14), end=end+timedelta(days=14))
        schedule = cal.schedule.loc[str(start):str(end)]
        sessions = tuple((day.date(), row["close"].to_pydatetime()) for day, row in schedule.iterrows())
        note = "参考交易日历，不能判定个股停牌或证券身份。"
        if market == "A 股":
            note += "A股使用XSHG参考，深北及特殊交易安排需另行核对。"
        return CalendarReference(name, calendar_version, sessions, True, note)
    except Exception:
        return CalendarReference(name, calendar_version, (), False, "参考日历不可用或不覆盖该区间；不能核验交易日缺口。")


@dataclass(frozen=True)
class HistoryQuality:
    requested_start: date
    requested_end: date
    actual_start: date | None
    actual_end: date | None
    observations: int
    source: str
    currency: str
    adjustment: str
    structural_valid: bool
    errors: tuple[str, ...]
    calendar_name: str
    calendar_version: str
    calendar_available: bool
    calendar_note: str
    asof_known: bool
    expected_completed_sessions: int | None
    missing_sessions: tuple[date, ...]
    off_calendar_sessions: tuple[date, ...]
    unfinished_sessions: tuple[date, ...]
    zero_volume_sessions: tuple[date, ...]
    large_move_sessions: tuple[date, ...]
    notes: tuple[str, ...]

    @property
    def coverage_label(self):
        if not self.structural_valid:
            return "结构校验失败"
        if self.observations == 0:
            return "所选区间没有返回记录；证券身份与原因未核验"
        if not self.calendar_available:
            return "实际区间已记录，交易日覆盖尚未核验"
        if not self.asof_known:
            return "参考日历可用，获取时点未记录，完整性未核验"
        if self.unfinished_sessions:
            return "含尚未结束日线，不能作为完整收盘输入"
        if self.missing_sessions or self.off_calendar_sessions:
            return "与参考日历存在差异，原因未核验"
        return "按参考日历未见已结束交易日缺口"

    def to_dict(self):
        def convert(value):
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            if isinstance(value, (tuple, list)):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            return value
        return {**convert(asdict(self)), "coverage_label": self.coverage_label}


def assess_history(frame: pd.DataFrame, market: str, start: date, end: date, *,
                   source="", currency="", adjustment="", received_at: datetime | None = None) -> HistoryQuality:
    if start > end:
        raise ValueError("开始日期不能晚于结束日期。")
    errors = []
    try:
        data = clean_stock_history(frame, start, end)
    except (DataValidationError, TypeError, ValueError) as error:
        errors.append(str(error))
        data = pd.DataFrame(columns=COLUMNS)
    observations = len(data)
    actual_start = data.date.iloc[0].date() if observations else None
    actual_end = data.date.iloc[-1].date() if observations else None
    observed = set(data.date.dt.date) if observations else set()
    notes = []
    teaching = any(token in source.casefold() for token in ("教学", "模拟", "demo", "simulation", "teaching"))
    if errors:
        reference = CalendarReference("", "", (), False, "结构校验失败，未进行日历完整性核验。")
    elif teaching:
        reference = CalendarReference("", "", (), False, "固定教学样本，不按真实市场日历判定覆盖。")
    else:
        reference = calendar_reference(market, start, end)
    if received_at is not None and received_at.tzinfo is None:
        errors.append("接收时间缺少时区，不能作为上游成功时间。")
        received_at = None
    if received_at is None:
        notes.append("成功接收时间未记录，无法据此核对末日是否结束；不以页面读取时间替代。")
    completed = {day for day, close in reference.sessions if received_at is None or close <= received_at.astimezone(timezone.utc)}
    unfinished = {day for day, close in reference.sessions if received_at is not None and close > received_at.astimezone(timezone.utc)} & observed
    missing = completed-observed if reference.available else set()
    off_calendar = observed-{day for day, _ in reference.sessions} if reference.available else set()
    zero_volume = tuple(data.loc[data.volume.eq(0), "date"].dt.date) if observations else ()
    large_moves = ()
    if observations >= 2:
        returns = data.close.pct_change()
        large_moves = tuple(data.loc[(returns.abs() > .5) | ~np.isfinite(returns.fillna(0)), "date"].dt.date)
    first_expected = min((day for day, _ in reference.sessions), default=start)
    if not teaching and actual_start is not None and actual_start > first_expected:
        notes.append("返回起点晚于请求起点；可能涉及上市时间或源端截断，尚未核验原因。")
    if teaching:
        notes.append("教学样本长度固定，其实际区间不代表真实数据源的历史覆盖。")
    if missing:
        notes.append("参考应交易日没有对应记录；不能据此认定停牌或数据源错误。")
    if zero_volume:
        notes.append("存在零成交量记录；不能单凭此字段断言停牌。")
    if large_moves:
        notes.append("存在绝对日价格变化超过50%的记录，需核对公司行动或源端异常；不是涨跌停判断。")
    if adjustment:
        notes.append("复权为所请求口径，源端复权效果未由本报告独立认证。")
    if unfinished:
        notes.append("包含参考收市时刻尚未到达的日线，不能把它当作已完成收盘数据用于回测。")
    return HistoryQuality(start, end, actual_start, actual_end, observations, source, currency, adjustment,
        not errors, tuple(errors), reference.name, reference.version, reference.available, reference.note, received_at is not None,
        len(completed) if reference.available and received_at is not None else None, tuple(sorted(missing)), tuple(sorted(off_calendar)),
        tuple(sorted(unfinished)), zero_volume, large_moves, tuple(notes))
