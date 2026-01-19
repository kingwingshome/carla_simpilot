from nicegui import ui, app
import time
import atexit
from home_view import build_home_tab
from vehicle_settings_view import build_vehicle_settings_tab
from navigation_view import build_navigation_tab
from sensors_settings_view import build_sensors_settings_tab
from about_view import build_about_tab
from i18n import t, set_language, get_language
from carla_manager import CarlaSimulatorManager


def run():
    manager = CarlaSimulatorManager()
    set_language(manager.language)
    current_language = get_language()

    language_items = ["中文（简体）", "中文（繁體）", "English"]
    code_by_label = {
        "中文（简体）": "zh-CN",
        "中文（繁體）": "zh-TW",
        "English": "en",
    }
    label_by_code = {v: k for k, v in code_by_label.items()}
    current_language_label = label_by_code.get(current_language, "中文（简体）")

    def update_time():
        label_time.text = time.strftime(
            "%b %d %Y %H:%M:%S", time.localtime(time.time())
        )

    def on_language_change(e):
        label = e.value
        lang = code_by_label.get(label, "zh-CN")
        set_language(lang)
        manager.language = lang
        ui.notify(f"语言已切换为：{label}，重启后生效")

    def on_shutdown():
        print("Application shutting down (NiceGUI hook)...")

    def on_cleanup():
        print("Python process exiting (atexit hook)...")

    app.on_shutdown(on_shutdown)
    atexit.register(on_cleanup)

    with ui.row().classes("items-stretch justify-between"):
        with ui.row().classes("items-center gap-2"):
            ui.chip(
                f" {t('app.title')}",
                selectable=True,
                icon="bookmark",
                color="blue-600",
                text_color="white",
            )
            ui.spinner("bars", size="lg", color="blue-600")
            label_time = ui.chip(
                "TIME",
                selectable=True,
                icon="update",
                color="blue-600",
                text_color="white",
            )
        ui.select(
            options=language_items,
            value=current_language_label,
            on_change=on_language_change,
        )

        ui.timer(1.0, update_time)

    with ui.tabs() as tabs:
        ui.tab("h", label=t("tabs.home"), icon="home")
        ui.tab("v", label=t("tabs.vehicle"), icon="launch")
        ui.tab("n", label=t("tabs.nav"), icon="navigation")
        ui.tab("s", label=t("tabs.sensors"), icon="settings")
        ui.tab("a", label=t("tabs.about"), icon="info")
    with ui.tab_panels(tabs, value="h").classes("w-full"):
        with ui.tab_panel("h"):
            build_home_tab()
        with ui.tab_panel("v"):
            build_vehicle_settings_tab()
        with ui.tab_panel("n"):
            build_navigation_tab()
        with ui.tab_panel("s"):
            build_sensors_settings_tab()
        with ui.tab_panel("a"):
            build_about_tab()

    ui.run(
        title="carla simpilot",
        native=True,
        host="0.0.0.0",
        port=9846,
        window_size=(800, 800),
    )


if __name__ in {"__main__", "__mp_main__"}:
    run()
