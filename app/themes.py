from __future__ import annotations

THEMES: dict[str, dict] = {
    "champagne": {
        "title": "Шампань",
        "bg": "#050506",
        "surface": "#0f0f12",
        "accent": "#e9c77e",
        "accent2": "#c8a052",
        "text": "#f4f1ea",
        "muted": "#8b887f",
    },
    "nord": {
        "title": "Nord",
        "bg": "#242933",
        "surface": "#2e3440",
        "accent": "#88c0d0",
        "accent2": "#5e81ac",
        "text": "#eceff4",
        "muted": "#8f9bab",
    },
    "dracula": {
        "title": "Dracula",
        "bg": "#21222c",
        "surface": "#282a36",
        "accent": "#bd93f9",
        "accent2": "#ff79c6",
        "text": "#f8f8f2",
        "muted": "#8b8fa8",
    },
    "tokyo": {
        "title": "Tokyo Night",
        "bg": "#16161e",
        "surface": "#1a1b26",
        "accent": "#7aa2f7",
        "accent2": "#bb9af7",
        "text": "#c0caf5",
        "muted": "#7a82a8",
    },
    "catppuccin": {
        "title": "Catppuccin",
        "bg": "#181825",
        "surface": "#1e1e2e",
        "accent": "#cba6f7",
        "accent2": "#f5c2e7",
        "text": "#cdd6f4",
        "muted": "#8b90a8",
    },
    "gruvbox": {
        "title": "Gruvbox",
        "bg": "#1d2021",
        "surface": "#282828",
        "accent": "#fabd2f",
        "accent2": "#fe8019",
        "text": "#ebdbb2",
        "muted": "#a89984",
    },
    "solarized": {
        "title": "Solarized",
        "bg": "#00212b",
        "surface": "#002b36",
        "accent": "#b58900",
        "accent2": "#268bd2",
        "text": "#eee8d5",
        "muted": "#93a1a1",
    },
    "onedark": {
        "title": "One Dark",
        "bg": "#21252b",
        "surface": "#282c34",
        "accent": "#61afef",
        "accent2": "#c678dd",
        "text": "#abb2bf",
        "muted": "#7f8697",
    },
    "rosepine": {
        "title": "Rosé Pine",
        "bg": "#191724",
        "surface": "#1f1d2e",
        "accent": "#ebbcba",
        "accent2": "#c4a7e7",
        "text": "#e0def4",
        "muted": "#908caa",
    },
    "everforest": {
        "title": "Everforest",
        "bg": "#272e33",
        "surface": "#2d353b",
        "accent": "#a7c080",
        "accent2": "#dbbc7f",
        "text": "#d3c6aa",
        "muted": "#9da9a0",
    },
}

DEFAULT_THEME = "champagne"


def catalog() -> list[dict]:
    return [{"code": code, **data} for code, data in THEMES.items()]


def is_valid(code: str) -> bool:
    return code in THEMES
