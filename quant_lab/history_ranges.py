"""Calendar-year shortcuts for explicit historical research windows."""

from datetime import date


HISTORY_PRESETS = {"1 年": 1, "3 年": 3, "5 年": 5, "10 年": 10, "自定义": None}


def history_window(end: date, years: int) -> tuple[date, date]:
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 100:
        raise ValueError("历史年数必须为1到100之间的整数。")
    try:
        start = end.replace(year=end.year-years)
    except ValueError:
        if end.month != 2 or end.day != 29:
            raise ValueError("历史起点超出日期范围。") from None
        start = date(end.year-years, 2, 28)
    return start, end
