"""Parse lệnh Telegram — thuần, không I/O (spec 002 FR-5, NFR-3)."""

# tên trong lệnh -> (key setting, hệ số nhân từ input, min, max)
SET_KEYS: dict[str, tuple[str, float, float, float]] = {
    "funding": ("funding_min_rate", 0.01, 0.0, 5.0),      # nhập %, lưu dạng tỉ lệ
    "basis": ("basis_min_pct", 0.01, 0.0, 50.0),
    "volume": ("min_quote_volume_usdt", 1.0, 0.0, 1e12),
    "cooldown": ("alert_cooldown_minutes", 1.0, 0.0, 1440.0),
}


def parse_command(text: str | None) -> tuple[str, list[str]] | None:
    """'/set@MyBot funding 0.05' -> ('set', ['funding', '0.05'])."""
    if not text or not text.startswith("/"):
        return None
    parts = text.strip().split()
    cmd = parts[0][1:].split("@", 1)[0].lower()
    return (cmd, parts[1:]) if cmd else None


def parse_set(args: list[str]) -> tuple[str, float]:
    """Trả (setting_key, value). Raise ValueError với thông báo tiếng Việt nếu sai."""
    if len(args) != 2:
        raise ValueError("Cú pháp: /set <funding|basis|volume|cooldown> <số>")
    name, raw = args[0].lower(), args[1].replace(",", ".").rstrip("%")
    if name not in SET_KEYS:
        raise ValueError(f"Không có tham số '{name}'. Chọn: {', '.join(SET_KEYS)}")
    key, mult, lo, hi = SET_KEYS[name]
    try:
        num = float(raw)
    except ValueError:
        raise ValueError(f"'{args[1]}' không phải là số") from None
    if not lo <= num <= hi:
        raise ValueError(f"{name} phải nằm trong [{lo:g}, {hi:g}]")
    return key, num * mult
