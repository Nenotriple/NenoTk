
# Define __all__
__all__ = ["number_commas"]

import numbers
import math


def number_commas(value):
    """
    Minimal formatter that inserts commas into the integer part of a number.

    Accepts `int`, `float`, or numeric `str` (strings may include commas).
    Raises `ValueError` for non-numeric input or non-finite floats (NaN/Inf).

    Examples:
      3555677        -> "3,555,677"
      3555677.4      -> "3,555,677.4"
      "1,234,567.00" -> "1,234,567"
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


# Demo / quick self-test
if __name__ == "__main__":
    tests = [
        (3555677.4, "3,555,677.4"),
        ("1234567890", "1,234,567,890"),
        ("1,234,567.00", "1,234,567"),
        ("-12345", "-12,345"),
    ]
    for inp, expect in tests:
        out = number_commas(inp)
        print(f"{inp!r} -> {out}  expected: {expect}")
        assert out == expect