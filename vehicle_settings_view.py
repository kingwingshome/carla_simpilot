from nicegui import ui
from tkinter import Tk, filedialog
import os
import sys
import subprocess
import carla
from carla_manager import CarlaSimulatorManager
from carla_client import CarlaClientManager
from i18n import t, add_language_listener


def build_vehicle_settings_tab():
    manager = CarlaSimulatorManager()
    client_manager = CarlaClientManager()

    def spawn_vehicle_from_spectator():
        # 1. 获取出生点
        transform = client_manager.get_auto_vehicle_spawnpoint()
        if not transform:
            ui.notify("无法获取出生点，请确认已连接 CARLA 并有地图", type="warning")
            return
            
        # 2. 填充UI显示
        loc = transform.location
        rot = transform.rotation
        spawn_x.value = f"{loc.x:.2f}"
        spawn_y.value = f"{loc.y:.2f}"
        spawn_z.value = f"{loc.z:.2f}"
        spawn_yaw.value = f"{rot.yaw:.2f}"
        
        # 3. 生成车辆
        role_name = role_input.value or "hero"
        blueprint_id = vehicle_blueprint_select.value or "vehicle.tesla.model3"
        try:
            vehicle = client_manager.spawn_vehicle(role_name, transform, blueprint_id=blueprint_id)
            if vehicle:
                ui.notify("车辆生成成功", type="positive")
            else:
                ui.notify("车辆生成失败", type="negative")
        except Exception as e:
            ui.notify(f"生成车辆失败: {e}", type="negative")

    def spawn_vehicle_manual():
        if not client_manager.is_connected:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        try:
            x = float(spawn_x.value)
            y = float(spawn_y.value)
            z = float(spawn_z.value)
            pitch = float(spawn_pitch.value)
            yaw = float(spawn_yaw.value)
            roll = float(spawn_roll.value)  
        except ValueError:
            ui.notify("坐标或朝向格式有误，请输入数字", type="negative")
            return
        transform = carla.Transform(
            carla.Location(x=x, y=y, z=z),
            carla.Rotation(pitch=pitch, yaw=yaw, roll=roll),
        )
        role_name = role_input.value or "hero"
        blueprint_id = vehicle_blueprint_select.value or "vehicle.tesla.model3"
        try:
            vehicle = client_manager.spawn_vehicle(role_name, transform, blueprint_id=blueprint_id)
            if vehicle:
                ui.notify("车辆生成成功", type="positive")
            else:
                ui.notify("车辆生成失败", type="negative")
        except Exception as e:
            ui.notify(f"生成车辆失败: {e}", type="negative")


    def move_vehicle_to_specified_pose():
        if not client_manager.is_connected:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        try:
            x = float(move_x.value)
            y = float(move_y.value)
            z = float(move_z.value)
            pitch = float(move_pitch.value)
            yaw = float(move_yaw.value)
            roll = float(move_roll.value)
        except ValueError:
            ui.notify("坐标或朝向格式有误，请输入数字", type="negative")
            return
        transform = carla.Transform(
            carla.Location(x=x, y=y, z=z),
            carla.Rotation(pitch=pitch, yaw=yaw, roll=roll),
        )
        try:
            client_manager.set_vehicle_pose(transform,rolename=role_input.value or "hero")
            ui.notify("已移动车辆到指定位置", type="positive")
        except Exception as e:
            ui.notify(f"移动车辆失败: {e}", type="negative")

    with ui.row().classes("items-stretch"):
        with ui.card():
            spawn_card_title = ui.label(t("vehicle.card_spawn_title"))
            with ui.row():
                role_input = ui.input("Role Name:", value="hero").classes("w-1/5")
                vehicle_blueprints = client_manager.get_available_vehicle_blueprints() if client_manager.is_connected else []
                vehicle_blueprint_options = [bp.id for bp in vehicle_blueprints]
                vehicle_blueprint_select = ui.select(
                    vehicle_blueprint_options,
                    label="车型",
                    value=vehicle_blueprint_options[0] if vehicle_blueprint_options else None,
                ).classes("w-2/5")
                
                def refresh_vehicle_blueprints():
                    if not client_manager.is_connected:
                        ui.notify("请先连接到 CARLA 服务器", type="warning")
                        return
                    blueprints = client_manager.get_available_vehicle_blueprints()
                    options = [bp.id for bp in blueprints]
                    vehicle_blueprint_select.options = options
                    vehicle_blueprint_select.value = options[0] if options else None
                    ui.notify(f"已获取 {len(options)} 种车型", type="positive")
                btn_refresh_blueprints = ui.button(t("vehicle.btn_refresh_blueprints"), color="green-200", on_click=refresh_vehicle_blueprints).classes("w-1/5")
                
                btn_spawn_at_view = ui.button(t("vehicle.btn_spawn_at_view"), color="green", on_click=spawn_vehicle_from_spectator).classes("w-1/5")
                btn_spawn_by_coord = ui.button(t("vehicle.btn_spawn_by_coord"), color="blue", on_click=spawn_vehicle_manual).classes("w-1/5")
                def on_delete_all_vehicles():
                    if not client_manager.is_connected:
                        ui.notify("请先连接到 CARLA 服务器", type="warning")
                        return
                    try:
                        client_manager.delete_all_vehicles()
                        ui.notify("已删除所有车辆", type="positive")
                    except Exception as e:
                        ui.notify(f"删除失败: {e}", type="negative")

                btn_delete_all = ui.button(t("vehicle.btn_delete_all"), on_click=on_delete_all_vehicles, color="red")
            with ui.row():
                spawn_x = ui.input("X:", value="-114.47").props("type=number").classes("w-1/4")
                spawn_y = ui.input("Y:", value="65.08").props("type=number").classes("w-1/4")
                spawn_z = ui.input("Z:", value="0.30").props("type=number").classes("w-1/4")
            with ui.row():
                spawn_pitch = ui.input("Pitch:", value="0.00").props("type=number").classes("w-1/4")
                spawn_yaw = ui.input("Yaw:", value="90.00").props("type=number").classes("w-1/4")
                spawn_roll = ui.input("Roll:", value="0.00").props("type=number").classes("w-1/4")
               
        with ui.card():
            move_card_title = ui.label(t("vehicle.card_move_title"))
            with ui.row():
                move_x = ui.input("X:", value="-114.47").props("type=number").classes("w-1/4")
                move_y = ui.input("Y:", value="65.08").props("type=number").classes("w-1/4")
                move_z = ui.input("Z:", value="0.30").props("type=number").classes("w-1/4")
            with ui.row():
                move_pitch = ui.input("Pitch:", value="0.00").props("type=number").classes("w-1/4")
                move_yaw = ui.input("Yaw:", value="90.00").props("type=number").classes("w-1/4")
                move_roll = ui.input("Roll:", value="0.00").props("type=number").classes("w-1/4")
            with ui.row():
                btn_move_to_pose = ui.button(t("vehicle.btn_move_to_pose"), color="green-100", on_click=move_vehicle_to_specified_pose)
                switch_autopilot = ui.switch(t("vehicle.switch_autopilot"),on_change=lambda e: client_manager.set_autopilot(e.value))
                switch_show_speed = ui.switch(t("vehicle.switch_show_speed"),on_change=lambda e: client_manager.set_display_speed(e.value))
                switch_show_pose = ui.switch(t("vehicle.switch_show_pose"),on_change=lambda e: client_manager.set_display_pose(e.value))

    def apply_language(lang):
        spawn_card_title.text = t("vehicle.card_spawn_title")
        btn_refresh_blueprints.text = t("vehicle.btn_refresh_blueprints")
        btn_spawn_at_view.text = t("vehicle.btn_spawn_at_view")
        btn_spawn_by_coord.text = t("vehicle.btn_spawn_by_coord")
        btn_delete_all.text = t("vehicle.btn_delete_all")
        move_card_title.text = t("vehicle.card_move_title")
        btn_move_to_pose.text = t("vehicle.btn_move_to_pose")
        switch_autopilot.label = t("vehicle.switch_autopilot")
        switch_show_speed.label = t("vehicle.switch_show_speed")
        switch_show_pose.label = t("vehicle.switch_show_pose")

    add_language_listener(apply_language)
