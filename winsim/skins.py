"""WinSim — Theme definitions."""

WIN10 = {
    "name": "Windows 10",
    # Desktop
    "desktop_bg_top":    "#0078D7",
    "desktop_bg_bottom": "#004e8c",
    # Taskbar
    "taskbar_bg":    "#1a1a2e",
    "taskbar_text":  "#ffffff",
    "taskbar_hover": "#2d2d44",
    "taskbar_active":"#3d3d5c",
    "start_btn":     "#0078d4",
    # Window chrome
    "win_title_bg":      "#ffffff",
    "win_title_text":    "#000000",
    "win_title_btn":     "#e0e0e0",
    "win_close_hover":   "#e81123",
    "win_close_text":    "#ffffff",
    "win_border":        "#d1d1d1",
    "win_bg":            "#f3f3f3",
    # Start menu
    "start_menu_bg":     "#2d2d30",
    "start_menu_text":   "#ffffff",
    "start_menu_hover":  "#3e3e42",
    "start_menu_accent": "#0078d4",
    # General
    "accent":        "#0078d4",
    "accent_hover":  "#1a86d9",
    "text":          "#1d1d1f",
    "text2":         "#666666",
    "text3":         "#999999",
    "danger":        "#e81123",
    "success":       "#107c10",
    "warning":       "#ff8c00",
    "bg":            "#f3f3f3",
    "card":          "#ffffff",
    "border":        "#d1d1d1",
    "select":        "#cce4f7",
    "font":          "Segoe UI",
    "font_mono":     "Consolas",
    # Toast
    "toast_bg":      "#2d2d30",
    "toast_text":    "#ffffff",
    "toast_accent":  "#0078d4",
    # Icon colours for desktop
    "icon_text":     "#ffffff",
    "icon_shadow":   "#00000088",
}

# Active theme (can be swapped at runtime)
THEME = dict(WIN10)

def get(key: str) -> str:
    return THEME.get(key, "#ff00ff")
