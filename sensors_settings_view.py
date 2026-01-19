from nicegui import ui
from carla_client import CarlaClientManager
from msf_viewer import MSFViewer
from i18n import t, add_language_listener


def build_sensors_settings_tab():
    client_manager = CarlaClientManager()
    msf_viewer = None
    has_started_msf = False
    img_sensor = None
    scale_label = None
    lidar_range_label = None
    lidar_points_label = None
    lidar_rotation_label = None
    fov_label = None
    depth_fov_label = None
    depth_yaw_label = None
    depth_pitch_label = None
    dvs_fov_label = None
    dvs_yaw_label = None
    dvs_pitch_label = None
    semantic_fov_label = None
    semantic_yaw_label = None
    semantic_pitch_label = None
    lidar_config = {
        "channels": "64",
        "range": "100",
        "points_per_second": "250000",
        "rotation_frequency": "20",
    }
    camera_configs = {
        "depth": {"yaw": 0, "pitch": 0, "fov": 90},
        "dvs": {"yaw": 0, "pitch": 0, "fov": 90},
        "semantic": {"yaw": 0, "pitch": 0, "fov": 90},
        "wide": {"yaw": 0, "pitch": 0, "fov": 120},
    }
    bev_height = 10.0
    bev_height_label = None

    def on_start_msf():
        nonlocal msf_viewer, has_started_msf
        if not client_manager.is_connected or client_manager.world is None:
            ui.notify("请先连接到 CARLA 并加载地图", type="warning")
            return
        vehicle = client_manager.get_ego_vehicle()
        if vehicle is None:
            ui.notify("未找到 hero 车辆，请先生成车辆", type="warning")
            return
        if msf_viewer is not None:
            msf_viewer.destroy()
        msf_viewer = MSFViewer(
            client_manager.world,
            vehicle,
            width=960,
            height=540,
            lidar_config=lidar_config,
            camera_configs=camera_configs,
            bev_height=bev_height,
        )
        has_started_msf = True
        b64_img = msf_viewer.update()
        if b64_img:
            img_sensor.set_source(f"data:image/png;base64,{b64_img}")

    def refresh_msf():
        nonlocal msf_viewer
        if not has_started_msf:
            return
        if not client_manager.is_connected or client_manager.world is None:
            return
        if msf_viewer is None:
            return
        try:
            b64_img = msf_viewer.update()
            if not b64_img:
                return
            img_sensor.set_source(f"data:image/png;base64,{b64_img}")
        except Exception:
            return

    def on_stop_msf():
        nonlocal msf_viewer, has_started_msf
        has_started_msf = False
        if msf_viewer is not None:
            msf_viewer.destroy()
            msf_viewer = None
        img_sensor.set_source("")

    def on_scale_change(e):
        nonlocal img_sensor, scale_label
        if img_sensor is None:
            return
        value = float(e.value)
        scale = value / 100.0
        img_sensor.style(
            f"width:100%; transform: scale({scale}); transform-origin: center center;"
        )
        if scale_label is not None:
            scale_label.text = f"{int(value)}%"

    def restart_msf():
        nonlocal msf_viewer, has_started_msf
        if not has_started_msf:
            return
        if not client_manager.is_connected or client_manager.world is None:
            return
        vehicle = client_manager.get_ego_vehicle()
        if vehicle is None:
            return
        if msf_viewer is not None:
            msf_viewer.destroy()
        msf_viewer = MSFViewer(
            client_manager.world,
            vehicle,
            width=960,
            height=540,
            lidar_config=lidar_config,
            camera_configs=camera_configs,
            bev_height=bev_height,
        )

    def on_lidar_range_change(e):
        nonlocal lidar_range_label
        value = int(e.value)
        lidar_config["range"] = str(value)
        if lidar_range_label is not None:
            lidar_range_label.text = f"{value} m"

    def on_lidar_points_change(e):
        nonlocal lidar_points_label
        value = int(e.value)
        lidar_config["points_per_second"] = str(value)
        if lidar_points_label is not None:
            lidar_points_label.text = f"{value}"

    def on_lidar_rotation_change(e):
        nonlocal lidar_rotation_label
        value = int(e.value)
        lidar_config["rotation_frequency"] = str(value)
        if lidar_rotation_label is not None:
            lidar_rotation_label.text = f"{value} Hz"

    def on_wide_fov_change(e):
        nonlocal fov_label
        value = int(e.value)
        camera_configs["wide"]["fov"] = value
        if fov_label is not None:
            fov_label.text = f"{value}°"

    def on_apply_sensor_config():
        restart_msf()

    def on_bev_height_change(e):
        nonlocal bev_height, bev_height_label
        value = float(e.value)
        bev_height = value
        if bev_height_label is not None:
            bev_height_label.text = f"{value:.1f} m"

    def on_depth_fov_change(e):
        nonlocal depth_fov_label
        value = int(e.value)
        camera_configs["depth"]["fov"] = value
        if depth_fov_label is not None:
            depth_fov_label.text = f"{value}°"

    def on_depth_yaw_change(e):
        nonlocal depth_yaw_label
        value = int(e.value)
        camera_configs["depth"]["yaw"] = value
        if depth_yaw_label is not None:
            depth_yaw_label.text = f"{value}°"

    def on_depth_pitch_change(e):
        nonlocal depth_pitch_label
        value = int(e.value)
        camera_configs["depth"]["pitch"] = value
        if depth_pitch_label is not None:
            depth_pitch_label.text = f"{value}°"

    def on_dvs_fov_change(e):
        nonlocal dvs_fov_label
        value = int(e.value)
        camera_configs["dvs"]["fov"] = value
        if dvs_fov_label is not None:
            dvs_fov_label.text = f"{value}°"

    def on_dvs_yaw_change(e):
        nonlocal dvs_yaw_label
        value = int(e.value)
        camera_configs["dvs"]["yaw"] = value
        if dvs_yaw_label is not None:
            dvs_yaw_label.text = f"{value}°"

    def on_dvs_pitch_change(e):
        nonlocal dvs_pitch_label
        value = int(e.value)
        camera_configs["dvs"]["pitch"] = value
        if dvs_pitch_label is not None:
            dvs_pitch_label.text = f"{value}°"

    def on_semantic_fov_change(e):
        nonlocal semantic_fov_label
        value = int(e.value)
        camera_configs["semantic"]["fov"] = value
        if semantic_fov_label is not None:
            semantic_fov_label.text = f"{value}°"

    def on_semantic_yaw_change(e):
        nonlocal semantic_yaw_label
        value = int(e.value)
        camera_configs["semantic"]["yaw"] = value
        if semantic_yaw_label is not None:
            semantic_yaw_label.text = f"{value}°"

    def on_semantic_pitch_change(e):
        nonlocal semantic_pitch_label
        value = int(e.value)
        camera_configs["semantic"]["pitch"] = value
        if semantic_pitch_label is not None:
            semantic_pitch_label.text = f"{value}°"

    with ui.grid(rows=1, columns='3fr 1fr'):
        with ui.card().classes("w-full"):
            view_title_label = ui.label(t("sensors.card_view_title"))
            with ui.row():
                btn_start = ui.button(
                    t("sensors.btn_start"),
                    color="blue-100",
                    on_click=on_start_msf,
                )
                btn_stop = ui.button(
                    t("sensors.btn_stop"),
                    color="red-100",
                    on_click=on_stop_msf,
                )
            with ui.row():
                img_sensor = ui.interactive_image("").style("width:100%")
            with ui.row():
                scale_label_title = ui.label(t("sensors.label_scale"))
                scale_slider = ui.slider(
                    min=30, max=200, value=100, on_change=on_scale_change
                ).classes("w-128")
                scale_label = ui.label(f"{int(scale_slider.value)}%")
        with ui.card():
            config_title_label = ui.label(t("sensors.card_config_title"))
            depth_title_label = ui.label(t("sensors.depth_title"))
            with ui.row():
                depth_fov_title = ui.label(t("sensors.label_fov"))
                depth_fov_slider = ui.slider(
                    min=30,
                    max=150,
                    value=int(camera_configs["depth"]["fov"]),
                    step=5,
                    on_change=on_depth_fov_change,
                ).classes("w-64")
                depth_fov_label = ui.label(f"{int(depth_fov_slider.value)}°")
            with ui.row():
                depth_yaw_title = ui.label(t("sensors.label_yaw"))
                depth_yaw_slider = ui.slider(
                    min=-180,
                    max=180,
                    value=int(camera_configs["depth"]["yaw"]),
                    step=5,
                    on_change=on_depth_yaw_change,
                ).classes("w-64")
                depth_yaw_label = ui.label(f"{int(depth_yaw_slider.value)}°")
            with ui.row():
                depth_pitch_title = ui.label(t("sensors.label_pitch"))
                depth_pitch_slider = ui.slider(
                    min=-90,
                    max=90,
                    value=int(camera_configs["depth"]["pitch"]),
                    step=5,
                    on_change=on_depth_pitch_change,
                ).classes("w-64")
                depth_pitch_label = ui.label(f"{int(depth_pitch_slider.value)}°")
            dvs_title_label = ui.label(t("sensors.dvs_title"))
            with ui.row():
                dvs_fov_title = ui.label(t("sensors.label_fov"))
                dvs_fov_slider = ui.slider(
                    min=30,
                    max=150,
                    value=int(camera_configs["dvs"]["fov"]),
                    step=5,
                    on_change=on_dvs_fov_change,
                ).classes("w-64")
                dvs_fov_label = ui.label(f"{int(dvs_fov_slider.value)}°")
            with ui.row():
                dvs_yaw_title = ui.label(t("sensors.label_yaw"))
                dvs_yaw_slider = ui.slider(
                    min=-180,
                    max=180,
                    value=int(camera_configs["dvs"]["yaw"]),
                    step=5,
                    on_change=on_dvs_yaw_change,
                ).classes("w-64")
                dvs_yaw_label = ui.label(f"{int(dvs_yaw_slider.value)}°")
            with ui.row():
                dvs_pitch_title = ui.label(t("sensors.label_pitch"))
                dvs_pitch_slider = ui.slider(
                    min=-90,
                    max=90,
                    value=int(camera_configs["dvs"]["pitch"]),
                    step=5,
                    on_change=on_dvs_pitch_change,
                ).classes("w-64")
                dvs_pitch_label = ui.label(f"{int(dvs_pitch_slider.value)}°")
            semantic_title_label = ui.label(t("sensors.semantic_title"))
            with ui.row():
                semantic_fov_title = ui.label(t("sensors.label_fov"))
                semantic_fov_slider = ui.slider(
                    min=30,
                    max=150,
                    value=int(camera_configs["semantic"]["fov"]),
                    step=5,
                    on_change=on_semantic_fov_change,
                ).classes("w-64")
                semantic_fov_label = ui.label(f"{int(semantic_fov_slider.value)}°")
            with ui.row():
                semantic_yaw_title = ui.label(t("sensors.label_yaw"))
                semantic_yaw_slider = ui.slider(
                    min=-180,
                    max=180,
                    value=int(camera_configs["semantic"]["yaw"]),
                    step=5,
                    on_change=on_semantic_yaw_change,
                ).classes("w-64")
                semantic_yaw_label = ui.label(f"{int(semantic_yaw_slider.value)}°")
            with ui.row():
                semantic_pitch_title = ui.label(t("sensors.label_pitch"))
                semantic_pitch_slider = ui.slider(
                    min=-90,
                    max=90,
                    value=int(camera_configs["semantic"]["pitch"]),
                    step=5,
                    on_change=on_semantic_pitch_change,
                ).classes("w-64")
                semantic_pitch_label = ui.label(f"{int(semantic_pitch_slider.value)}°")
            with ui.row():
                lidar_range_title = ui.label(t("sensors.lidar_range"))
                lidar_range_slider = ui.slider(
                    min=10,
                    max=200,
                    value=int(lidar_config["range"]),
                    step=10,
                    on_change=on_lidar_range_change,
                ).classes("w-64")
                lidar_range_label = ui.label(f"{lidar_range_slider.value} m")
            with ui.row():
                lidar_points_title = ui.label(t("sensors.lidar_points"))
                lidar_points_slider = ui.slider(
                    min=100000,
                    max=1000000,
                    value=int(lidar_config["points_per_second"]),
                    step=50000,
                    on_change=on_lidar_points_change,
                ).classes("w-64")
                lidar_points_label = ui.label(f"{int(lidar_points_slider.value)}")
            with ui.row():
                lidar_rotation_title = ui.label(t("sensors.lidar_rotation"))
                lidar_rotation_slider = ui.slider(
                    min=5,
                    max=30,
                    value=int(lidar_config["rotation_frequency"]),
                    step=1,
                    on_change=on_lidar_rotation_change,
                ).classes("w-64")
                lidar_rotation_label = ui.label(f"{int(lidar_rotation_slider.value)} Hz")
            bev_title_label = ui.label(t("sensors.bev_title"))
            with ui.row():
                bev_height_title = ui.label(t("sensors.bev_height"))
                bev_height_slider = ui.slider(
                    min=5.0,
                    max=50.0,
                    value=bev_height,
                    step=1.0,
                    on_change=on_bev_height_change,
                ).classes("w-64")
                bev_height_label = ui.label(f"{bev_height_slider.value:.1f} m")
            with ui.row():
                wide_fov_title = ui.label(t("sensors.wide_fov"))
                fov_slider = ui.slider(
                    min=60,
                    max=150,
                    value=int(camera_configs["wide"]["fov"]),
                    step=5,
                    on_change=on_wide_fov_change,
                ).classes("w-64")
                fov_label = ui.label(f"{int(fov_slider.value)}°")
            with ui.row():
                btn_apply = ui.button(t("sensors.btn_apply"), color="green-100", on_click=on_apply_sensor_config)

    def apply_language(lang):
        view_title_label.text = t("sensors.card_view_title")
        btn_start.text = t("sensors.btn_start")
        btn_stop.text = t("sensors.btn_stop")
        scale_label_title.text = t("sensors.label_scale")
        config_title_label.text = t("sensors.card_config_title")
        depth_title_label.text = t("sensors.depth_title")
        depth_fov_title.text = t("sensors.label_fov")
        depth_yaw_title.text = t("sensors.label_yaw")
        depth_pitch_title.text = t("sensors.label_pitch")
        dvs_title_label.text = t("sensors.dvs_title")
        dvs_fov_title.text = t("sensors.label_fov")
        dvs_yaw_title.text = t("sensors.label_yaw")
        dvs_pitch_title.text = t("sensors.label_pitch")
        semantic_title_label.text = t("sensors.semantic_title")
        semantic_fov_title.text = t("sensors.label_fov")
        semantic_yaw_title.text = t("sensors.label_yaw")
        semantic_pitch_title.text = t("sensors.label_pitch")
        lidar_range_title.text = t("sensors.lidar_range")
        lidar_points_title.text = t("sensors.lidar_points")
        lidar_rotation_title.text = t("sensors.lidar_rotation")
        bev_title_label.text = t("sensors.bev_title")
        bev_height_title.text = t("sensors.bev_height")
        wide_fov_title.text = t("sensors.wide_fov")
        btn_apply.text = t("sensors.btn_apply")

    add_language_listener(apply_language)

    ui.timer(0.1, refresh_msf)
