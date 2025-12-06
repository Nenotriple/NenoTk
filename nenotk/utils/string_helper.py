"""Utility helpers for string and numeric formatting.

This module provides small helpers for formatting numeric values as
strings (inserting thousands separators) and simple time unit
conversions. Public helpers exported by this module are:

- `number_commas`: Format ints/floats/numeric-strings with commas.
- `time_convert`: Convert seconds to days/hours/minutes/seconds.

The implementations are intentionally minimal and designed for use in
UI displays and demos included in the module's `__main__` section.
"""

#region Imports


import math
import numbers
from typing import Literal, Union, Any

__all__ = [
    "number_commas",
    "time_convert",
    "format_time",
]


#endregion
#region Numbers


def number_commas(value: Union[int, float, str, Any]) -> str:
    """Format a numeric value with commas in the integer part.

    Accepts an ``int``, ``float``, or numeric ``str`` (string input may
    already contain commas). The function returns a string with thousands
    separators inserted into the integer part. For floats, any trailing
    zeros after the decimal point are trimmed; an integer-valued float
    will be returned without a decimal point.

    Args:
        value (int | float | str | Any): Value to format. ``bool`` is
            explicitly rejected because it is a subclass of ``int``.

    Returns:
        str: The formatted number (e.g. "1,234,567" or "3,555,677.4").

    Raises:
        ValueError: If ``value`` is a boolean, an empty string, a
            non-numeric string, or a non-finite float (NaN/Infinity).

    Examples:
        >>> number_commas(3555677)
        '3,555,677'
        >>> number_commas(3555677.4)
        '3,555,677.4'
        >>> number_commas('1,234,567.00')
        '1,234,567'
    """
    # Reject bool explicitly (bool is subclass of int)
    if isinstance(value, bool):
        raise ValueError("Value must be an int, float, or numeric string (not bool).")
    # Integers
    if isinstance(value, numbers.Integral):
        return f"{int(value):,}"
    # Strings: strip and accept existing commas
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError("Empty string is not a valid number.")
        s = s.replace(",", "")
        try:
            f = float(s)
        except (ValueError, TypeError):
            raise ValueError("Value must be an int, float, or numeric string.")
        return number_commas(f)
    # Float
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite float (NaN or Infinity) is not supported.")
        # Use fixed-point representation to avoid scientific notation
        s = format(value, "f")
        sign = ""
        if s.startswith(("+", "-")):
            sign, s = s[0], s[1:]
        if "." in s:
            integer_part, decimal_part = s.split(".", 1)
            decimal_part = decimal_part.rstrip("0")
        else:
            integer_part, decimal_part = s, ""
        if integer_part == "":
            integer_part = "0"
        if decimal_part:
            return f"{sign}{int(integer_part):,}.{decimal_part}"
        return f"{sign}{int(integer_part):,}"
    # Fallback: try float coercion for other numeric-like types
    try:
        f = float(value)
    except Exception:
        raise ValueError("Value must be an int, float, or numeric string.")
    return number_commas(f)


#endregion
#region Time


TIME_UNITS = [("day", 86400), ("hour", 3600), ("minute", 60), ("second", 1)]


def time_convert(
        seconds: float,
        to_unit: Literal[
            "day",
            "hour",
            "minute",
            "second"
        ]
) -> float:
    """Convert a duration given in seconds to the requested time unit.

    Args:
        seconds (float): Duration in seconds.
        to_unit (Literal['day','hour','minute','second']): Target unit to
            convert the input seconds into.

    Returns:
        float: The converted duration expressed in the requested unit.

    Raises:
        ValueError: If ``to_unit`` is not one of the supported units.
    """
    unit_dict = dict(TIME_UNITS)
    if not isinstance(to_unit, str):
        raise ValueError(f"Invalid time unit: {to_unit}")
    to_unit_norm = to_unit.strip().lower()
    if to_unit_norm not in unit_dict:
        raise ValueError(f"Invalid time unit: {to_unit}")
    return seconds / unit_dict[to_unit_norm]


def format_time(
    seconds: Union[int, float],
    pattern: Literal[
        "HH:MM:SS",
        "HH:MM:SS.MMM",
        "H:MM:SS",
        "M:SS",
        "#H #M #S",
        "#H#M#S",
        "ms",
        "H.hhhh",
        "M.mmmm",
    ] = "HH:MM:SS",
) -> str:
    """Format a duration given in seconds according to `pattern`.

    Supported patterns:
    - "HH:MM:SS": padded two-digit hours/minutes/seconds (hours may exceed 99)
    - "HH:MM:SS.MMM": padded with milliseconds (3 digits, rounded)
    - "H:MM:SS": hours unpadded, minutes/seconds padded
    - "M:SS": total minutes : padded seconds
    - "#H #M #S": verbose spaced units, only non-zero components
    - "#H#M#S": compact verbose units, no spaces
    - "ms": total milliseconds as integer with "ms" suffix
    - "H.hhhh": decimal hours with 4 fraction digits
    - "M.mmmm": decimal minutes with 4 fraction digits

    Notes:
    - Negative durations are prefixed with '-'.
    - Rounding is to nearest for milliseconds and decimal formats; carries are propagated.
    """
    if not isinstance(pattern, str):
        raise ValueError("Pattern must be a string literal describing the format.")
    pat_raw = pattern.strip()
    if not pat_raw:
        raise ValueError("Pattern must be a non-empty string.")
    # Normalize to an uppercase form for case-insensitive matching. This
    # preserves punctuation while making alphabetical components uniform.
    p = pat_raw.upper()
    sign, total_ms, h, m, s, ms = _split_ms(seconds)
    # Helper: obtain whole-second rounding and propagate carry
    def _rounded_hms_from_total_ms(total_ms_val: int) -> tuple[int, int, int]:
        total_seconds = (total_ms_val + 500) // 1000
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        return hh, mm, ss
    if p == "HH:MM:SS":
        hh, mm, ss = _rounded_hms_from_total_ms(total_ms)
        return f"{sign}{hh:02d}:{mm:02d}:{ss:02d}"
    if p == "HH:MM:SS.MMM":
        # ms is already rounded to nearest millisecond in _split_ms
        # but may cause seconds to roll over if ms == 1000 after rounding; handled by integer math above
        return f"{sign}{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    if p == "H:MM:SS":
        hh, mm, ss = _rounded_hms_from_total_ms(total_ms)
        return f"{sign}{hh}:{mm:02d}:{ss:02d}"
    if p == "M:SS":
        total_seconds = (total_ms + 500) // 1000
        minutes = total_seconds // 60
        seconds_only = total_seconds % 60
        return f"{sign}{minutes}:{seconds_only:02d}"
    if p in ("#H #M #S", "#H#M#S"):
        hh, mm, ss = _rounded_hms_from_total_ms(total_ms)
        parts: list[str] = []
        if hh:
            parts.append(f"{hh}h")
        if mm:
            parts.append(f"{mm}m")
        if ss:
            parts.append(f"{ss}s")
        if not parts:
            parts = ["0s"]
        if p == "#H #M #S":
            return sign + " ".join(parts)
        return sign + "".join(parts)
    if p == "MS":
        # Always render the suffix as lowercase 'ms' for readability
        return f"{sign}{total_ms}ms"
    if p == "H.HHHH":
        hours_decimal = total_ms / 3_600_000.0
        return f"{sign}{hours_decimal:.4f}"
    if p == "M.MMMM":
        minutes_decimal = total_ms / 60_000.0
        return f"{sign}{minutes_decimal:.4f}"
    # Should not reach here if typing is respected
    raise ValueError(f"Unsupported pattern: {pattern}")


def _split_ms(seconds: Union[int, float]) -> tuple[str, int, int, int, int, int]:
    """Helper to convert seconds -> integer milliseconds and split into h/m/s/ms

    Return (sign, total_ms, hours, minutes, seconds, ms).

    - Rounds the input seconds to nearest millisecond.
    - Preserves hours > 24 (no day wrapping).
    - Raises ValueError for NaN/Inf.
    """
    if isinstance(seconds, bool):
        raise ValueError("Value must be int/float representing seconds (not bool).")
    try:
        f = float(seconds)
    except Exception:
        raise ValueError("Value must be a numeric seconds value.")
    if not math.isfinite(f):
        raise ValueError("Non-finite float (NaN or Infinity) is not supported.")
    sign = "" if f >= 0 else "-"
    abs_ms = int(round(abs(f) * 1000.0))
    total_ms = abs_ms
    hours = total_ms // 3_600_000
    rem = total_ms % 3_600_000
    minutes = rem // 60_000
    rem2 = rem % 60_000
    secs = rem2 // 1000
    ms = rem2 % 1000
    return sign, total_ms, hours, minutes, secs, ms


#endregion
#region Tests


if __name__ == "__main__":
# Each major function has its own test function
# which runs a series of test cases and asserts expected output.
# A master `run_tests` function runs all test functions
# and reports any failures.

    import sys
    import traceback


# number_commas
    def test_number_commas():
        tests = [
            (3555677.4, "3,555,677.4"),
            ("1234567890", "1,234,567,890"),
            ("1,234,567.00", "1,234,567"),
            ("-12345", "-12,345"),
        ]
        print("\nTesting number_commas:")
        for inp, expect in tests:
            out = number_commas(inp)
            print(f"{inp!r} -> {out} -> Expected: {expect}")
            assert out == expect


# time_convert
    def test_time_convert():
        tests = [
            (86400, "day", 1),
            (7200, "hour", 2),
            (300, "minute", 5),
            (45, "second", 45),
        ]
        print("\nTesting time_convert:")
        for seconds, unit, expect in tests:
            out = time_convert(seconds, unit)
            print(f"{seconds}s -> {out} {unit} -> Expected: {expect}")
            assert out == expect


# format_time
    def test_format_time():
        print("\nTesting format_time:")
        cases = [
            (0, "HH:MM:SS", "00:00:00"),
            (3661, "HH:MM:SS", "01:01:01"),
            (12.3456, "HH:MM:SS.MMM", "00:00:12.346"),
            (3661, "H:MM:SS", "1:01:01"),
            (125.4, "M:SS", "2:05"),
            (3661, "#H #M #S", "1h 1m 1s"),
            (3661, "#H#M#S", "1h1m1s"),
            (1.234, "ms", "1234ms"),
            (3600, "H.hhhh", "1.0000"),
            (90, "M.mmmm", "1.5000"),
        ]
        for seconds, pattern, expect in cases:
            out = format_time(seconds, pattern)
            print(f"{seconds!r} -> {pattern!r} -> {out} -> Expected: {expect}")
            assert out == expect


# Run
    def run_tests():
        test_functions = [test_number_commas, test_time_convert, test_format_time]
        failures = []
        print("\nRunning demo tests...")
        for fn in test_functions:
            try:
                fn()
                print(f"{fn.__name__}: PASS")
            except AssertionError as ae:
                print(f"{fn.__name__}: FAIL - {ae}")
                traceback.print_exc()
                failures.append(fn.__name__)
            except Exception as ex:
                print(f"{fn.__name__}: ERROR - {ex}")
                traceback.print_exc()
                failures.append(fn.__name__)
        if failures:
            print(f"\nFAILED {len(failures)} test(s): {', '.join(failures)}")
            sys.exit(1)
        print("\nAll tests passed.")
        sys.exit(0)


    run_tests()


#endregion
