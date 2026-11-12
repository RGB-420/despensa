from decimal import Decimal, localcontext

UNIT_DEFINITIONS = {
    "g": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "l": ("ml", Decimal("1000")),
    "unit": ("unit", Decimal("1")),
}


def normalize_unit(unit: str) -> str:
    if not isinstance(unit, str):
        raise ValueError("Unit must be a supported unit name.")
    normalized = unit.strip().casefold()
    if normalized == "units":
        normalized = "unit"
    if normalized not in UNIT_DEFINITIONS:
        raise ValueError("Unsupported measurement unit.")
    return normalized


def to_base_quantity(quantity: Decimal, unit: str) -> tuple[Decimal, str]:
    base_unit, factor = UNIT_DEFINITIONS[normalize_unit(unit)]
    with localcontext() as context:
        context.prec = 700
        return quantity * factor, base_unit


def convert_quantity(quantity: Decimal, source_unit: str, target_unit: str) -> Decimal:
    value, source_base = to_base_quantity(quantity, source_unit)
    target_base, factor = UNIT_DEFINITIONS[normalize_unit(target_unit)]
    if source_base != target_base:
        raise ValueError("Cannot convert between weight, volume, and individual units.")
    with localcontext() as context:
        context.prec = 700
        return value / factor
