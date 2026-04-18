from __future__ import annotations

from domain.enums.due_state import DueState

TASK_LABEL_COLORS = [
    {"id": "red", "bg": "#FEE2E2", "fg": "#991B1B"},
    {"id": "orange", "bg": "#FFEDD5", "fg": "#9A3412"},
    {"id": "yellow", "bg": "#FEF3C7", "fg": "#92400E"},
    {"id": "green", "bg": "#DCFCE7", "fg": "#166534"},
    {"id": "blue", "bg": "#DBEAFE", "fg": "#1D4ED8"},
    {"id": "cyan", "bg": "#CFFAFE", "fg": "#155E75"},
    {"id": "brown", "bg": "#E7D3C8", "fg": "#7C2D12"},
    {"id": "gray", "bg": "#E5E7EB", "fg": "#374151"},
]

STATUS_COLORS = [
    {"id": "gray", "main": "#6B7280"},
    {"id": "blue", "main": "#2563EB"},
    {"id": "green", "main": "#059669"},
    {"id": "yellow", "main": "#D97706"},
    {"id": "red", "main": "#DC2626"},
    {"id": "purple", "main": "#7C3AED"},
]

DUE_DATE_COLORS = {
    "overdue": "#DC2626",
    "today": "#EA580C",
    "future": "#6B7280",
    "none": "#9CA3AF",
}


def normalize_hex_color(value: str, default: str = "#E5E7EB") -> str:
    raw = value.strip()
    if not raw:
        return default
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) != 6:
        return default
    try:
        int(raw, 16)
    except ValueError:
        return default
    return f"#{raw.upper()}"


def darken_hex_color(value: str, ratio: float = 0.75) -> str:
    color = normalize_hex_color(value)
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    r = max(0, min(255, int(r * ratio)))
    g = max(0, min(255, int(g * ratio)))
    b = max(0, min(255, int(b * ratio)))
    return f"#{r:02X}{g:02X}{b:02X}"


def contrast_text_color(
    background: str,
    light: str = "#FFFFFF",
    dark: str = "#111827",
) -> str:
    color = normalize_hex_color(background)
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    return dark if yiq >= 140 else light


def due_state_color(due_state: DueState) -> str:
    if due_state == DueState.OVERDUE:
        return DUE_DATE_COLORS["overdue"]
    if due_state == DueState.TODAY:
        return DUE_DATE_COLORS["today"]
    if due_state == DueState.UPCOMING:
        return DUE_DATE_COLORS["future"]
    return DUE_DATE_COLORS["none"]
