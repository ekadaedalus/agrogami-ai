"""Presentation preserves unknowns."""
def display(value: object, reasons: tuple[str, ...] = ()) -> str:
    if value is None:
        return "Unavailable — " + (", ".join(reasons) if reasons else "insufficient supporting evidence")
    return str(value)
