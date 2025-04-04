from decimal import Decimal


def format_number(value: Decimal) -> Decimal:
    value_str = format(value, "f")
    if "." in value_str:
        int_part, frac_part = value_str.split(".", 1)
        frac_part = frac_part.rstrip("0")
        if frac_part:
            formatted_str = f"{int_part}.{frac_part}"
        else:
            formatted_str = int_part
    else:
        formatted_str = value_str
    return Decimal(formatted_str)


def round_to_2(value: Decimal) -> Decimal:
    """Округление числа до 2 знаков после запятой"""
    return value.quantize(Decimal("0.01"))
