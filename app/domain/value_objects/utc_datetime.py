from datetime import datetime, timezone


def to_naive_utc(value: datetime) -> datetime:
    """Convertit en UTC naïf, la convention de stockage, pour comparer toutes les dates entre elles."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)
