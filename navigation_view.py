from nicegui import ui
from tkinter import Tk, filedialog
import os
import sys
import subprocess
import carla
from carla_manager import CarlaSimulatorManager
from carla_client import CarlaClientManager
from map_2d_viewer import Map2dViewer
from i18n import t, add_language_listener


def build_navigation_tab():
    client_manager = CarlaClientManager()
    map_viewer = Map2dViewer()
    has_shown_map = False
    view_switch_updating = False
    shoulder_switch = None
    monitor_switch = None
    bev_switch = None

    def on_show_map():
        nonlocal has_shown_map
        has_shown_map = True
        if not client_manager.is_connected or client_manager.world is None:
            ui.notify("请先连接到 CARLA 并加载地图", type="warning")
            return
        try:
            ego_vehicle = client_manager.get_ego_vehicle()
            b64_img = None
            if ego_vehicle is None:
                b64_img = map_viewer.update(client_manager.world)
            if ego_vehicle is not None:
                b64_img = map_viewer.update_with_ego(client_manager.world, ego_vehicle)
            if not b64_img:
                ui.notify("生成地图失败", type="negative")
                return
            img_map.set_source(f"data:image/png;base64,{b64_img}")
        except Exception as e:
            ui.notify(f"显示地图失败: {e}", type="negative")

    def refresh_map_periodically():
        if not has_shown_map:
            return
        if not client_manager.is_connected or client_manager.world is None:
            return
        try:
            ego_vehicle = client_manager.get_ego_vehicle()
            b64_img = None
            if ego_vehicle is None:
                b64_img = map_viewer.update(client_manager.world)
            if ego_vehicle is not None:
                b64_img = map_viewer.update_with_ego(client_manager.world, ego_vehicle)
            if not b64_img:
                return
            img_map.set_source(f"data:image/png;base64,{b64_img}")
        except Exception:
            return

    def on_set_spectator_pose():
        if not client_manager.is_connected:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        try:
            transform = carla.Transform(
                carla.Location(
                    x=float(move_x.value), y=float(move_y.value), z=float(move_z.value)
                ),
                carla.Rotation(
                    pitch=float(move_pitch.value),
                    yaw=float(move_yaw.value),
                    roll=float(move_roll.value),
                ),
            )
            client_manager.set_spectator_pose(transform)
            ui.notify("已将观察者视角设置到指定位置", type="positive")
        except Exception as e:
            ui.notify(f"设置观察者视角失败: {e}", type="negative")

    def on_set_spectator_to_vehicle():
        if not client_manager.is_connected:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        try:
            client_manager.set_spectator_to_vehicle()
        except Exception as e:
            ui.notify(f"设置观察者视角失败: {e}", type="negative")

    with ui.row().classes("items-stretch"):
        with ui.card():
            dynamic_title_label = ui.label(t("nav.card_dynamic_title"))
            with ui.row():
                btn_set_spectator_to_vehicle = ui.button(
                    t("nav.btn_set_spectator_to_vehicle"),
                    color="blue",
                    on_click=on_set_spectator_to_vehicle,
                )
                def on_shoulder_change(e):
                    nonlocal view_switch_updating
                    if view_switch_updating:
                        return
                    enabled = e.value
                    client_manager.set_spectator_follow_vehicle_shoulder_view(enabled)
                    if enabled:
                        view_switch_updating = True
                        try:
                            if monitor_switch and monitor_switch.value:
                                monitor_switch.value = False
                                client_manager.set_spectator_follow_vehicle_monitor_view(
                                    False
                                )
                            if bev_switch and bev_switch.value:
                                bev_switch.value = False
                                client_manager.set_spectator_follow_vehicle_bev_view(
                                    False
                                )
                        finally:
                            view_switch_updating = False

                shoulder_switch = ui.switch(t("nav.switch_shoulder"), on_change=on_shoulder_change)
            with ui.row():
                def on_monitor_change(e):
                    nonlocal view_switch_updating
                    if view_switch_updating:
                        return
                    enabled = e.value
                    client_manager.set_spectator_follow_vehicle_monitor_view(enabled)
                    if enabled:
                        view_switch_updating = True
                        try:
                            if shoulder_switch and shoulder_switch.value:
                                shoulder_switch.value = False
                                client_manager.set_spectator_follow_vehicle_shoulder_view(
                                    False
                                )
                            if bev_switch and bev_switch.value:
                                bev_switch.value = False
                                client_manager.set_spectator_follow_vehicle_bev_view(
                                    False
                                )
                        finally:
                            view_switch_updating = False

                monitor_switch = ui.switch(t("nav.switch_monitor"), on_change=on_monitor_change)

                def on_bev_change(e):
                    nonlocal view_switch_updating
                    if view_switch_updating:
                        return
                    enabled = e.value
                    client_manager.set_spectator_follow_vehicle_bev_view(enabled)
                    if enabled:
                        view_switch_updating = True
                        try:
                            if shoulder_switch and shoulder_switch.value:
                                shoulder_switch.value = False
                                client_manager.set_spectator_follow_vehicle_shoulder_view(
                                    False
                                )
                            if monitor_switch and monitor_switch.value:
                                monitor_switch.value = False
                                client_manager.set_spectator_follow_vehicle_monitor_view(
                                    False
                                )
                        finally:
                            view_switch_updating = False

                bev_switch = ui.switch(t("nav.switch_bev"), on_change=on_bev_change)
        with ui.card():
            pose_title_label = ui.label(t("nav.card_pose_title"))
            with ui.row():
                move_x = (
                    ui.input("X:", value="-114.47")
                    .props("type=number")
                    .classes("w-1/4")
                )
                move_y = (
                    ui.input("Y:", value="65.08").props("type=number").classes("w-1/4")
                )
                move_z = (
                    ui.input("Z:", value="0.30").props("type=number").classes("w-1/4")
                )
            with ui.row():

                move_pitch = (
                    ui.input("Pitch:", value="0").props("type=number").classes("w-1/4")
                )
                move_yaw = (
                    ui.input("Yaw:", value="90.64")
                    .props("type=number")
                    .classes("w-1/4")
                )
                move_roll = (
                    ui.input("Roll:", value="0").props("type=number").classes("w-1/4")
                )
            with ui.row():
                btn_set_pose = ui.button(
                    t("nav.btn_set_pose"),
                    color="green-100",
                    on_click=on_set_spectator_pose,
                )
        with ui.grid(rows=1, columns='1fr 3fr'):
            def locate_vehicle_by_id(vehicle_id: str):
                if not client_manager.is_connected or client_manager.world is None:
                    ui.notify("请先连接到 CARLA 并加载地图", type="warning")
                    return
                try:
                    vehicle = client_manager.world.get_actor(int(vehicle_id))
                    if vehicle is None:
                        ui.notify(f"未找到ID为 {vehicle_id} 的车辆", type="negative")
                        return
                    spectator = client_manager.world.get_spectator()
                    transform = vehicle.get_transform()
                    spectator.set_transform(transform)
                    ui.notify(f"已将视角定位到车辆 {vehicle_id}", type="positive")
                except Exception as e:
                    ui.notify(f"定位车辆失败: {e}", type="negative")

            def delete_vehicle_by_id(vehicle_id: str):
                if not client_manager.is_connected or client_manager.world is None:
                    ui.notify("请先连接到 CARLA 并加载地图", type="warning")
                    return
                try:
                    vehicle = client_manager.world.get_actor(int(vehicle_id))
                    if vehicle is None:
                        ui.notify(f"未找到ID为 {vehicle_id} 的车辆", type="negative")
                        return
                    vehicle.destroy()
                    ui.notify(f"已删除车辆 {vehicle_id}", type="positive")
                    on_list_all_vehicles()
                except Exception as e:
                    ui.notify(f"删除车辆失败: {e}", type="negative")

            def on_list_all_vehicles():
                nonlocal row_vehicles
                if not client_manager.is_connected:
                    ui.notify("请先连接到 CARLA 服务器", type="warning")
                    return
                vehicles = client_manager.get_vehicles()
                row_vehicles.clear()
                with row_vehicles:
                    with ui.grid(columns='64px auto auto auto').classes("gap-0 items-center w-full"):
                        for vehicle in vehicles:
                            v_id = f"{vehicle.id}"
                            ui.label(v_id).classes('border p-1')
                            ui.label(vehicle.type_id).classes('border p-1')
                            ui.button("定位", on_click=lambda e, vid=v_id: locate_vehicle_by_id(vid)).props("flat").classes('border p-1')
                            ui.button("删除", on_click=lambda e, vid=v_id: delete_vehicle_by_id(vid)).props("flat").classes('border p-1')
                ui.notify(f"发现{len(vehicles)}辆车辆", type="positive")
  
            with ui.card():
                vehicles_title_label = ui.label(t("nav.card_vehicles_title"))
                btn_list_vehicles = ui.button(
                    t("nav.btn_list_vehicles"),
                    color="blue-100",
                    on_click=on_list_all_vehicles,  
                )
                row_vehicles = ui.row().classes("w-full")

            with ui.card().classes("w-full"):
                map_title_label = ui.label(t("nav.card_map_title"))
                btn_show_map = ui.button(
                    t("nav.btn_show_map"),
                    color="blue-100",
                    on_click=on_show_map,
                )
                with ui.row():
                    img_map = ui.interactive_image(
                        f"data:image/png;base64,{map_viewer.placeholder}"
                    ).classes("w-128")

    def apply_language(lang):
        dynamic_title_label.text = t("nav.card_dynamic_title")
        btn_set_spectator_to_vehicle.text = t("nav.btn_set_spectator_to_vehicle")
        shoulder_switch.label = t("nav.switch_shoulder")
        monitor_switch.label = t("nav.switch_monitor")
        bev_switch.label = t("nav.switch_bev")
        pose_title_label.text = t("nav.card_pose_title")
        btn_set_pose.text = t("nav.btn_set_pose")
        vehicles_title_label.text = t("nav.card_vehicles_title")
        btn_list_vehicles.text = t("nav.btn_list_vehicles")
        map_title_label.text = t("nav.card_map_title")
        btn_show_map.text = t("nav.btn_show_map")

    add_language_listener(apply_language)

    ui.timer(1.0, refresh_map_periodically)
