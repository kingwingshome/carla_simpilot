import threading
from nicegui import ui
from tkinter import Tk, filedialog
from carla_manager import CarlaSimulatorManager
from carla_client import CarlaClientManager
from i18n import t, add_language_listener
import os
import subprocess
import sys


def build_home_tab():
    manager = CarlaSimulatorManager()
    client_manager = CarlaClientManager()
    map_select = None

    def run_script():
        root = Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="选择要运行的 Python 脚本",
            filetypes=[("Python 脚本", "*.py"), ("所有文件", "*.*")],
        )
        root.destroy()
        if not path:
            return

        script_path = path
        dialog = ui.dialog()

        def on_confirm():
            dialog.close()
            try:
                script_dir = os.path.dirname(script_path)
                script_name = os.path.basename(script_path)
                if os.name == "nt":
                    # 使用外部命令行窗口启动脚本，便于查看输出
                    # 生成临时批处理文件来运行，规避复杂的命令行转义问题
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".bat", delete=False) as tf:
                        tf.write("@echo off\n")
                        tf.write(f'cd /d "{script_dir}"\n')
                        tf.write(f'"{sys.executable}" "{script_name}"\n')
                        tf.write("pause\n")
                        tf.write('del "%~f0"\n')
                    print(f"Running script via temporary batch file: {tf.name}")
                    subprocess.Popen(f'start "" "{tf.name}"', shell=True)
                else:
                    subprocess.Popen([sys.executable, script_name], cwd=script_dir)
                ui.notify("脚本已启动运行", type="positive")
            except Exception as e:
                ui.notify(f"运行脚本失败: {e}", type="negative")

        with dialog:
            with ui.card():
                ui.label(t("home.script_confirm_title"))
                ui.label(script_path).classes("text-xs break-all")
                with ui.row():
                    ui.button(t("home.script_confirm_button_ok"), color="green", on_click=on_confirm)
                    ui.button(t("home.script_confirm_button_cancel"), on_click=dialog.close)

        dialog.open()


    def on_connection_toggle(e):
        nonlocal map_select
        if e.value:
            try:
                status_text.value = f"正在连接到 {ip_input.value}:{int(port_input.value)}..."
                client_manager.connect(ip_input.value, int(port_input.value))
                status_text.value = client_manager.status_message
                if map_select is not None:
                    map_select.options = client_manager.get_maps()
                    if map_select.options:
                        map_select.value = map_select.options[0]
                ui.notify("已连接到 CARLA", type="positive")
            except Exception:
                conn_switch.value = False
                status_text.value = client_manager.status_message
                ui.notify("连接失败", type="negative")
        else:
            if client_manager.is_connected:
                client_manager.disconnect()
                status_text.value = client_manager.status_message
                ui.notify("已断开连接", type="info")

    def on_change_map():
        if not client_manager.is_connected:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        if not map_select.value:
            ui.notify("请选择要切换的地图", type="warning")
            return
        try:
            client_manager.change_map(map_select.value)
            status_text.value = client_manager.get_status()
            ui.notify(f"已切换到地图: {map_select.value}", type="positive")
        except Exception as e:
            ui.notify(f"切换地图失败: {e}", type="negative")



    with ui.grid(columns=2):
        with ui.column():
            with ui.card():
                carla_control_title = ui.label(t("home.carla_control_title"))
                carla_path_input = ui.input(
                    t("home.carla_path_label"),
                    value=manager.carla_executable or "",
                ).classes("w-full")
                status_label = ui.label(
                    "状态: 运行中" if manager.is_running() else "状态: 未运行"
                )

                def refresh_status():
                    status_label.text = (
                        "状态: 运行中" if manager.is_running() else "状态: 未运行"
                    )

                def on_choose_path():
                    root = Tk()
                    root.withdraw()
                    path = filedialog.askopenfilename(
                        title="选择 CARLA 可执行文件",
                        filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
                    )
                    root.destroy()
                    if not path:
                        return
                    carla_path_input.value = path
                    try:
                        manager.set_carla_executable(path, save=True)
                        ui.notify("CARLA 路径已选择并保存", type="positive")
                    except FileNotFoundError:
                        ui.notify("选择的路径不存在，请确认后再试", type="negative")

                def on_start():
                    try:
                        args = f"-quality-level={manager.render_quality}"
                        manager.start(args)
                        ui.notify("CARLA 仿真器已启动", type="positive")
                    except Exception as e:
                        ui.notify(f"启动失败: {e}", type="negative")
                    refresh_status()

                def on_stop():
                    manager.stop()
                    ui.notify("CARLA 仿真器已停止", type="positive")
                    refresh_status()

                with ui.row():
                    ui.select(
                        ["Low", "Epic"],
                        value=manager.render_quality,
                        on_change=lambda e: setattr(manager, "render_quality", e.value),
                    ).classes("w-24")
                    btn_choose_carla = ui.button(t("home.btn_choose_carla"), on_click=on_choose_path, color="primary")
                    btn_start_carla = ui.button(t("home.btn_start_carla"), on_click=on_start, color="green")
                    btn_stop_carla = ui.button(t("home.btn_stop_carla"), on_click=on_stop, color="red")
                    btn_run_script = ui.button(t("home.btn_run_script"), color="purple", on_click=run_script)

            with ui.card():
                client_title_label = ui.label(t("home.client_title"))
                with ui.row().classes("w-full items-center"):
                    ip_input = ui.input(t("home.ip_label"), value="127.0.0.1").classes("w-1/5")
                    port_input = ui.number(t("home.port_label"), value=2000, format="%.0f").classes("w-1/5")
                    conn_switch = ui.switch(t("home.conn_switch"), on_change=on_connection_toggle)
                status_text = ui.textarea(value="状态: 未连接").props("readonly rows=3").classes("w-full")

                def refresh_client_status():
                    status_text.value = client_manager.get_status()

                ui.timer(3.0, refresh_client_status)

        with ui.column():
            with ui.card():
                env_title_label = ui.label(t("home.env_title"))
                with ui.row():
                    map_select = ui.select(
                        [],
                        label=t("home.map_label"),
                    ).classes("w-full")
                    btn_change_map = ui.button(t("home.btn_change_map"), on_click=on_change_map, color="primary")
                with ui.row():
                    weather_options = list(client_manager.get_weathers().keys())
                    weather_select = ui.select(
                        weather_options,
                        label=t("home.weather_label"),
                    ).classes("w-full")

                    def on_change_weather():
                        if not client_manager.is_connected:
                            ui.notify("请先连接到 CARLA 服务器", type="warning")
                            return
                        if not weather_select.value:
                            ui.notify("请选择要切换的天气", type="warning")
                            return
                        try:
                            client_manager.set_weather(weather_select.value)
                            status_text.value = client_manager.get_status()
                            ui.notify(f"已设置天气: {weather_select.value}", type="positive")
                        except Exception as e:
                            ui.notify(f"设置天气失败: {e}", type="negative")

                    btn_change_weather = ui.button(t("home.btn_change_weather"), on_click=on_change_weather, color="primary")

    def apply_language(lang):
        carla_control_title.text = t("home.carla_control_title")
        carla_path_input.label = t("home.carla_path_label")
        btn_choose_carla.text = t("home.btn_choose_carla")
        btn_start_carla.text = t("home.btn_start_carla")
        btn_stop_carla.text = t("home.btn_stop_carla")
        btn_run_script.text = t("home.btn_run_script")
        client_title_label.text = t("home.client_title")
        ip_input.label = t("home.ip_label")
        port_input.label = t("home.port_label")
        conn_switch.label = t("home.conn_switch")
        env_title_label.text = t("home.env_title")
        map_select.label = t("home.map_label")
        btn_change_map.text = t("home.btn_change_map")
        weather_select.label = t("home.weather_label")
        btn_change_weather.text = t("home.btn_change_weather")

    add_language_listener(apply_language)
