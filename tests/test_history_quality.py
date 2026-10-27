"""Coverage checks use explicit dates, close times and structural failures."""

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from quant_lab.data_quality import CalendarReference, assess_history, calendar_reference, require_completed_close
from quant_lab.history_ranges import history_window
from quant_lab.processing import DataValidationError


def frame(days=("2026-10-08", "2026-10-12")):
    count = len(days)
    return pd.DataFrame({"date": pd.to_datetime(days), "open": [10.]*count,
        "high": [21.]*count, "low": [9.]*count, "close": [10.,20.][:count],
        "volume": [100.,0.][:count], "amount": [1000.,0.][:count]})


def reference(*args):
    return CalendarReference("TEST", "1", tuple((date(2026,10,day),datetime(2026,10,day,7,tzinfo=timezone.utc))
        for day in (8,9,12)), True, "确定性测试日历")


def test_year_shortcuts_leap_day_and_ten_calendar_years():
    assert history_window(date(2024,2,29),1) == (date(2023,2,28),date(2024,2,29))
    assert history_window(date(2026,10,27),10) == (date(2016,10,27),date(2026,10,27))
    with pytest.raises(ValueError):
        history_window(date(2026,10,27),0)


def test_missing_unfinished_zero_volume_and_large_move_are_distinct(monkeypatch):
    monkeypatch.setattr("quant_lab.data_quality.calendar_reference", reference)
    report = assess_history(frame(), "A 股", date(2026,10,1), date(2026,10,12),
        source="test", currency="CNY", received_at=datetime(2026,10,12,6,tzinfo=timezone.utc))
    assert report.structural_valid
    assert report.expected_completed_sessions == 2
    assert report.missing_sessions == (date(2026,10,9),)
    assert report.unfinished_sessions == (date(2026,10,12),)
    assert report.zero_volume_sessions == report.large_move_sessions == (date(2026,10,12),)
    assert report.actual_start == date(2026,10,8)
    assert not any("上市时间" in note for note in report.notes)  # First expected day is Oct 8, not the holiday start.
    assert "尚未结束" in report.coverage_label
    assert report.to_dict()["actual_start"] == "2026-10-08"
    with pytest.raises(DataValidationError, match="尚未收市"):
        require_completed_close(SimpleNamespace(quality=report))


def test_no_receive_time_does_not_invent_a_success_time(monkeypatch):
    monkeypatch.setattr("quant_lab.data_quality.calendar_reference", reference)
    report = assess_history(frame(),"A 股",date(2026,10,8),date(2026,10,12),source="test")
    assert not report.asof_known and report.expected_completed_sessions is None
    assert "获取时点未记录" in report.coverage_label


def test_teaching_and_unknown_calendar_never_imply_missing_trading_days(monkeypatch):
    report = assess_history(frame(),"A 股",date(2016,1,1),date(2026,10,12),source="固定教学样本")
    assert not report.calendar_available and not report.missing_sessions
    unavailable = CalendarReference("XSHG","",(),False,"无法核验")
    monkeypatch.setattr("quant_lab.data_quality.calendar_reference",lambda *args: unavailable)
    report = assess_history(frame(),"A 股",date(2016,1,1),date(2026,10,12),source="test")
    assert not report.calendar_available and report.expected_completed_sessions is None
    assert "尚未核验" in report.coverage_label
    assert any("尚未核验原因" in note for note in report.notes)


def test_duplicate_columns_invalid_prices_and_times_are_visible():
    original = frame()
    duplicate = pd.concat([original, original[["close"]]],axis=1)
    report = assess_history(duplicate,"A 股",date(2026,1,1),date(2026,12,31))
    assert not report.structural_valid and "重复列" in report.errors[0]
    invalid = original.copy()
    invalid.loc[0,"close"] = -1
    assert not assess_history(invalid,"A 股",date(2026,1,1),date(2026,12,31)).structural_valid
    intraday = original.copy()
    intraday["date"] = pd.to_datetime(["2026-10-08 15:00", "2026-10-12 15:00"])
    assert "盘中时间" in assess_history(intraday,"A 股",date(2026,1,1),date(2026,12,31)).errors[0]
    boolean = original.astype({name: bool for name in ("open", "high", "low", "close")})
    assert "布尔类型" in assess_history(boolean,"A 股",date(2026,1,1),date(2026,12,31)).errors[0]


def test_offline_exchange_calendar_holiday_and_ten_year_window():
    calendar = calendar_reference("A 股",date(2016,10,27),date(2026,10,27))
    assert calendar.available and calendar.version == "4.13.2"
    sessions = {day for day,_ in calendar.sessions}
    assert date(2026,10,1) not in sessions
    assert date(2026,10,8) in sessions
    assert len(sessions) > 2000
    holiday = calendar_reference("A 股",date(2026,10,1),date(2026,10,7))
    assert holiday.available and not holiday.sessions
