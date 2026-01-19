from bottle import thread
import carla
from typing import Optional
import random
import math


class CarlaClientManager:
    _instance: Optional["CarlaClientManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.client: Optional[carla.Client] = None
        self.world: Optional[carla.World] = None
        self._is_connected = False
        self._status_message = "未连接"
        self._maps = []
        self._initialized = True
        self.ego_vehicle = None
        self._show_speed = False
        self._show_pose = False
        self._display_info_thread_running = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def status_message(self) -> str:
        return self._status_message

    def connect(self, ip: str, port: int, timeout: float = 10.0) -> None:
        """尝试连接到 CARLA 服务器"""
        try:
            self._status_message = f"正在连接到 {ip}:{port}..."
            # 创建 Client 实例
            client = carla.Client(ip, port)
            client.set_timeout(timeout)

            # 尝试获取 World 来验证连接
            self.world = client.get_world()
            self.client = client
            self.ip = ip
            self.port = port

            self._is_connected = True

            self.get_status()

        except Exception as e:
            self._is_connected = False
            self.client = None
            self.world = None
            self._status_message = f"连接失败: {str(e)}"
            raise e

    def disconnect(self) -> None:
        """断开连接（清理资源）"""
        self.client = None
        self.world = None
        self._is_connected = False
        self._status_message = "已断开连接"

    def get_status(self) -> str:
        if self._is_connected:
            self.mode_info = (
                "同步模式" if self.world.get_settings().synchronous_mode else "异步模式"
            )
            self.current_map_name = self.world.get_map().name.split("/")[-1]
            spectator_info = self.get_spectator_info()
            self._status_message = f"成功连接到 CARLA ({self.ip}:{self.port})\nServer Version: {self.client.get_server_version()}\n{self.mode_info}\n当前地图: {self.current_map_name}\nSpectator Info: {spectator_info}"
        return self._status_message

    def get_spectator_info(self):
        if self.world:
            spectator = self.world.get_spectator()
            if spectator:
                transform = spectator.get_transform()
                location = transform.location
                rotation = transform.rotation
                spectator_info = f"{location.x:.2f}, {location.y:.2f}, {location.z:.2f}\nYaw: {rotation.yaw:.2f}"
                return spectator_info
        return None

    def get_maps(self):
        if self.client and self._is_connected:
            try:
                self._maps = self.client.get_available_maps()
            except Exception:
                self._maps = []
        return self._maps

    def get_maps(self):
        """获取可用地图列表"""
        if self.client:
            maps = self.client.get_available_maps()
            return [map.split("/")[-1] for map in maps]
        return []

    def change_map(self, map_name: str) -> None:
        """切换到指定地图"""
        if self.client and self._is_connected:
            try:
                self.client.load_world(map_name)
                self._status_message = f"已切换到地图: {map_name}"
            except Exception as e:
                self._status_message = f"切换地图失败: {str(e)}"
                raise e

    def get_weathers(self):
        return {
            "晴朗-中午": carla.WeatherParameters.ClearNoon,
            "多云-中午": carla.WeatherParameters.CloudyNoon,
            "湿润-中午": carla.WeatherParameters.WetNoon,
            "湿润多云-中午": carla.WeatherParameters.WetCloudyNoon,
            "小雨-中午": carla.WeatherParameters.SoftRainNoon,
            "中雨-中午": carla.WeatherParameters.MidRainyNoon,
            "大雨-中午": carla.WeatherParameters.HardRainNoon,
            "晴朗-日出": carla.WeatherParameters.ClearSunset,
            "多云-日出": carla.WeatherParameters.CloudySunset,
            "湿润-日出": carla.WeatherParameters.WetSunset,
            "湿润多云-日出": carla.WeatherParameters.WetCloudySunset,
            "小雨-日出": carla.WeatherParameters.SoftRainSunset,
            "中雨-日出": carla.WeatherParameters.MidRainSunset,
            "大雨-日出": carla.WeatherParameters.HardRainSunset,
            "晴朗-夜晚": carla.WeatherParameters.ClearNight,
            "多云-夜晚": carla.WeatherParameters.CloudyNight,
            "湿润-夜晚": carla.WeatherParameters.WetNight,
            "湿润多云-夜晚": carla.WeatherParameters.WetCloudyNight,
            "小雨-夜晚": carla.WeatherParameters.SoftRainNight,
            "中雨-夜晚": carla.WeatherParameters.MidRainyNight,
            "大雨-夜晚": carla.WeatherParameters.HardRainNight,
        }

    def set_weather(self, weather_name: str) -> None:
        if not self.world:
            return
        weather_dict = self.get_weathers()
        if weather_name not in weather_dict:
            return
        try:
            self.world.set_weather(weather_dict[weather_name])
            self._status_message = f"已设置天气: {weather_name}"
        except Exception as e:
            self._status_message = f"设置天气失败: {str(e)}"
            raise e

    def delete_all_vehicles(self) -> None:
        """删除所有车辆"""
        if self.world:
            count = 0
            for actor in self.world.get_actors():
                if actor.type_id.find("vehicle.") != -1:
                    actor.destroy()
                    count += 1
            self._status_message = f"已删除所有车辆, 共{count}个"

    def get_auto_vehicle_spawnpoint(self):
        """获取自动生成车辆的出生点"""
        if self.world:
            # 1. 获取当前 Spectator (上帝视角相机) 的位置
            # 这个位置通常由用户在模拟器窗口中漫游时决定
            spectator = self.world.get_spectator()
            spec_transform = spectator.get_transform()
            spec_location = spec_transform.location

            # 2. 在地图上查找最近的“可驾驶”路点 (Waypoint)
            carla_map = self.world.get_map()
            waypoint = carla_map.get_waypoint(
                spec_location, 
                project_to_road=True, # 强制投射到最近的道路中心线上
                lane_type=carla.LaneType.Driving # 仅限机动车道（排除人行道等）
            )

            if waypoint:
                # 3. 如果找到了路点，将生成点设置为该路点的位姿
                target_transform = waypoint.transform
                target_transform.location.z += 0.3 # 稍微抬高一点，防止车辆轮胎陷入地下
                print(
                    f"✅ 已自动吸附到最近道路: (X:{target_transform.location.x:.1f}, Y:{target_transform.location.y:.1f})"
                )
            else:
                # 4. 如果附近没有路（例如在荒野），则无法吸附
                print("⚠️ 当前位置附近未检测到可行驶道路。")
            return target_transform
        return None


    def spawn_vehicle(self, role="hero", transform=None, blueprint_id: str | None = None):
        if not self.world:
            print("❌ 请先连接到 CARLA")
            return
        blueprint_library = self.world.get_blueprint_library()
        if blueprint_id:
            car_bp = blueprint_library.find(blueprint_id)
        else:
            car_bp = blueprint_library.find("vehicle.tesla.model3")
        car_bp.set_attribute("role_name", role)

        try:
            if transform:
                vehicle = self.world.spawn_actor(car_bp, transform)
                print(f"✅ 成功生成车辆: {vehicle.attributes.get('role_name', '')}")
                return vehicle
            else:
                print("⚠️ 未提供车辆生成位置 transform")
        except Exception as e:
            print(f"❌ 生成车辆失败: {e}")
        return None

    def set_vehicle_pose(self, transform,rolename='hero'):
        """设置车辆位置"""
        hero_vehicles = [actor for actor in self.world.get_actors()
                            if 'vehicle' in actor.type_id and actor.attributes['role_name'] == rolename]
        self.ego_vehicle = None
        print(f"发现{len(hero_vehicles)}辆车辆")
        if len(hero_vehicles) > 0:
            self.ego_vehicle = hero_vehicles[-1]
            if transform:
                self.ego_vehicle.set_transform(transform)
                print(f"✅ 已设置车辆 {self.ego_vehicle.attributes.get('role_name', '')} 位置")
            else:
                print("⚠️ 未提供车辆或位置 transform")

    def set_autopilot(self, enabled: bool,rolename="hero") -> None:
        """设置是否启用自动驾驶"""
        if not self.world:
            return

        hero_vehicles = [actor for actor in self.world.get_actors()
                            if 'vehicle' in actor.type_id and actor.attributes['role_name'] == rolename]
        self.ego_vehicle = None
        print(f"发现{len(hero_vehicles)}辆车辆")
        for vehicle in hero_vehicles:
            vehicle.set_autopilot(enabled)
        # if len(hero_vehicles) > 0:
        #     self.ego_vehicle = random.choice(hero_vehicles)
        #     self.ego_vehicle.set_autopilot(enabled)
        #     print(f"✅ 已{'启用' if enabled else '禁用'}自动驾驶")
    
    def get_ego_vehicle(self,rolename="hero"):
        """获取当前自动驾驶车辆"""
        hero_vehicles = [actor for actor in self.world.get_actors()
                            if 'vehicle' in actor.type_id and actor.attributes['role_name'] == rolename]
        self.ego_vehicle = None
        print(f"发现{len(hero_vehicles)}辆车辆")
        if len(hero_vehicles) > 0:
            self.ego_vehicle = hero_vehicles[-1]
        return self.ego_vehicle

    def get_vehicles(self):
        """获取所有车辆"""
        hero_vehicles = self.world.get_actors().filter("vehicle.*")
        print(f"发现{len(hero_vehicles)}辆车辆")
        return hero_vehicles

    def get_available_vehicle_blueprints(self):
        """获取所有可用的车辆蓝图"""
        vehicle_blueprints = self.world.get_blueprint_library().filter('vehicle')
        return vehicle_blueprints

    def run_display_info(self):
        """
        统一的车辆信息显示线程。
        只要 _show_speed 或 _show_pose 为 True，就持续更新车辆信息显示。
        """
        self._display_info_thread_running = True
        while self._show_speed or self._show_pose:
            try:
                vehicle_list = self.world.get_actors().filter('vehicle.*')

                if not vehicle_list:
                    self.world.wait_for_tick()
                    continue

                for vehicle in vehicle_list:
                    if not vehicle.is_alive:
                        continue

                    lines = []
                    
                    # 收集速度信息
                    if self._show_speed:
                        velocity = vehicle.get_velocity()
                        speed_kmh = 3.6 * math.sqrt(velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2)
                        lines.append((f"{speed_kmh:.1f} km/h", carla.Color(r=255, g=0, b=0)))

                    # 收集坐标信息
                    if self._show_pose:
                        transform = vehicle.get_transform()
                        loc = transform.location
                        rot = transform.rotation
                        lines.append((f"X:{loc.x:.1f} Y:{loc.y:.1f} Yaw:{rot.yaw:.1f}", carla.Color(r=0, g=255, b=0)))

                    # 统一显示
                    if lines:
                        base_location = vehicle.get_location()
                        # 基础高度，从车辆上方开始
                        current_z = 2.5
                        
                        for text, color in lines:
                            text_location = base_location + carla.Location(y=1.0, z=current_z)
                            self.world.debug.draw_string(
                                location=text_location,
                                text=text,
                                draw_shadow=True,
                                color=color,
                                persistent_lines=True
                            )
                            # 每行增加高度偏移，避免重叠
                            current_z += 1.2

                self.world.wait_for_tick()

            except RuntimeError as e:
                print(f"线程运行时发生错误 (可能CARLA已关闭): {e}")
                break
            except Exception as e:
                print(f"多车信息显示线程发生未知异常: {e}")
                break
        
        self._display_info_thread_running = False
        print("多车信息显示线程已退出。")

    def _ensure_display_thread_running(self):
        if (self._show_speed or self._show_pose) and not self._display_info_thread_running:
            thread.start_new_thread(self.run_display_info, ())

    def set_display_speed(self, enabled: bool) -> None:
        """设置是否显示车速"""
        if not self.world:
            return
        self._show_speed = enabled
        self._ensure_display_thread_running()

    def set_display_pose(self, enabled: bool) -> None:
        """设置是否显示车坐标"""
        if not self.world:
            return
        self._show_pose = enabled
        self._ensure_display_thread_running()

    def set_spectator_pose(self, transform):
        """设置 spectator 位置"""
        if not self.world:
            return False
        spectator = self.world.get_spectator()
        spectator.set_transform(transform)

    def set_spectator_to_vehicle(self, rolename="hero") -> bool:
        if not self.world:
            return False
        hero_vehicles = [
            actor
            for actor in self.world.get_actors()
            if "vehicle" in actor.type_id and actor.attributes.get("role_name") == rolename
        ]
        self.ego_vehicle = None
        print(f"发现{len(hero_vehicles)}辆车辆")
        if not hero_vehicles:
            return False
        self.ego_vehicle = random.choice(hero_vehicles)
        spectator = self.world.get_spectator()
        transform = self.ego_vehicle.get_transform()
        location = transform.location
        rotation = transform.rotation
        spectator_location = location + carla.Location(
            x=-6 * math.cos(math.radians(rotation.yaw)),
            y=-6 * math.sin(math.radians(rotation.yaw)),
            z=3,
        )
        spectator_rotation = carla.Rotation(pitch=-15, yaw=rotation.yaw, roll=0)
        spectator_transform = carla.Transform(spectator_location, spectator_rotation)
        spectator.set_transform(spectator_transform)
        print("已将 spectator 位置设置到当前车辆")
        return True

    def set_spectator_to_vehicle_shoudler_view(self,  x_offset=-20, z_offset=15, look_at_offset=5,rolename="hero") -> bool:
        if not self.world:
            return False

        if self.ego_vehicle is None:
            self.ego_vehicle = self.get_ego_vehicle(rolename)
        # hero_vehicles = [
        #     actor
        #     for actor in self.world.get_actors()
        #     if "vehicle" in actor.type_id and actor.attributes.get("role_name") == rolename
        # ]
        
        # print(f"发现{len(hero_vehicles)}辆车辆")
        # if not hero_vehicles:
        #     return False
        # self.ego_vehicle = random.choice(hero_vehicles)
        spectator = self.world.get_spectator()

        # 1. 获取车辆当前的位姿信息
        vehicle_transform = self.ego_vehicle.get_transform()
        vehicle_location = self.ego_vehicle.get_transform().location
        vehicle_forward_vector = vehicle_transform.get_forward_vector() # 获取车辆正前方方向向量

        # 2. 计算摄像机（Spectator）的放置位置：
        # 基于车辆位置，沿着车辆后方（x_offset 为负值）和上方（z_offset）偏移
        spectator_location = carla.Location(
            x=vehicle_location.x + vehicle_forward_vector.x * x_offset,
            y=vehicle_location.y + vehicle_forward_vector.y * x_offset,
            z=vehicle_location.z + z_offset
        )

        # 3. 计算“注视点”（Look-at Point）：
        # 设定摄像机应该看向的目标点，通常是车辆前方的一点（look_at_offset 为正值）
        look_at_point = carla.Location(
            x=vehicle_location.x + vehicle_forward_vector.x * look_at_offset,
            y=vehicle_location.y + vehicle_forward_vector.y * look_at_offset,
            z=vehicle_location.z
        )

        # 4. 计算方向向量：从摄像机位置指向注视点
        direction_vector = look_at_point - spectator_location

        # 5. 计算摄像机的旋转角度（俯仰角 Pitch 和 偏航角 Yaw），使其对准注视点
        horizontal_dist = math.sqrt(direction_vector.x**2 + direction_vector.y**2)
        pitch = math.degrees(math.atan2(direction_vector.z, horizontal_dist)) if horizontal_dist != 0 else 0
        yaw = math.degrees(math.atan2(direction_vector.y, direction_vector.x))
        roll = 0.0 # 保持水平，无侧倾
        spectator_rotation = carla.Rotation(pitch=pitch, yaw=yaw, roll=roll)

        # 6. 应用新的变换：移动摄像机到计算出的位置并旋转朝向
        new_spectator_transform = carla.Transform(spectator_location, spectator_rotation)
        spectator.set_transform(new_spectator_transform)
        print("已将 spectator 位置设置到当前车辆")
        return True

    def run_spectator_follow_vehicle_shoulder_view(self):
        while self._is_running_follow_vehicle_shoulder_view:
            try:
                self.set_spectator_to_vehicle_shoudler_view()
            except:
                pass
            self.world.wait_for_tick()


    def set_spectator_follow_vehicle_shoulder_view(self,enabled: bool) -> None:
        if not self.world:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        if enabled:
            self._is_running_follow_vehicle_shoulder_view = True
            thread.start_new_thread(self.run_spectator_follow_vehicle_shoulder_view, ())
        else:
            self._is_running_follow_vehicle_shoulder_view = False

    def set_spectator_to_vehicle_monitor_view(self,  x_offset=110, y_offset=60, z_offset=40, tolerance=2,rolename="hero") -> bool:
        if not self.world:
            return False
        if self.ego_vehicle is None:
            self.ego_vehicle = self.get_ego_vehicle(rolename)
        spectator = self.world.get_spectator()

        # 1. 获取车辆和摄像机当前位置
        vehicle_transform = self.ego_vehicle.get_transform()
        vehicle_location = self.ego_vehicle.get_transform().location
        spectator_transform = spectator.get_transform()
        spectator_location = spectator_transform.location

        # 2. 定义距离约束区间
        # min_distance: 最小距离限制（防止相机穿模进入车内或离得太近）
        # max_distance: 最大距离限制（防止车跑太远看不清）
        # tolerance: 容差缓冲，避免在临界点频繁跳动
        min_distance = math.sqrt(z_offset**2) - tolerance
        max_distance = math.sqrt(x_offset**2 + y_offset**2 + z_offset**2) + tolerance

        # 3. 计算实际距离
        distance = vehicle_location.distance(spectator_location)

        # 4. 根据距离动态调整相机
        if distance < min_distance or distance > max_distance:
            # Case A: 距离超出范围（太远或太近）
            # 强制重置相机位置到理想的跟随位置 (get_spectator_transform 会计算最佳位置)
            # 这种“瞬移”机制保证了车辆永远不会跑出视野
            new_transform = self.get_spectator_transform(self.ego_vehicle,x_offset,y_offset,z_offset)
            spectator.set_transform(new_transform)
        else:
            # Case B: 距离在合理范围内
            # 此时保持相机位置不变，只旋转镜头跟踪车辆
            # 这种“平滑跟踪”机制让视角更稳定，不会一直死板地吸附在车辆后方，
            # 允许车辆在画面中自由移动一段距离，增加临场感
            new_rotation = self.get_rotation_towards(vehicle_transform, spectator_location)
            new_transform = carla.Transform(spectator_location, new_rotation)
            spectator.set_transform(new_transform)

        return True

    def get_spectator_transform(self,vehicle,x_offset,y_offset,z_offset):
        transform = vehicle.get_transform()
        location = transform.location
        forward = transform.get_forward_vector()
        right = transform.get_right_vector()

        # 1. 获取车辆角速度，判断转向趋势
        angular_velocity = vehicle.get_angular_velocity()
        yaw_rate = angular_velocity.z # z轴角速度代表车辆的转向快慢（Yaw Rate）
        threshold = 0.05 

        # 2. 动态决定相机侧向偏移方向
        if abs(yaw_rate) < threshold:
            # 如果车辆基本直行（转向率低），随机选择左侧或右侧视角，增加观赏趣味性
            tmp_y_offset = y_offset if random.random() > 0.5 else -y_offset
        else:
            # 如果车辆正在转弯，将相机放置在转弯的“外侧”，以获得更好的视野覆盖
            if yaw_rate < 0:
                tmp_y_offset = y_offset # 左转（Yaw Rate < 0），相机放右侧
            else:
                tmp_y_offset = -y_offset # 右转（Yaw Rate > 0），相机放左侧

        # 3. 计算相机最终位置：基于车辆位置，叠加前后、左右（动态）、高度偏移
        cam_location = location + forward * x_offset + right * tmp_y_offset 
        cam_location.z += z_offset

        # 4. 计算相机旋转角度，使其始终注视车辆
        rotation = self.get_rotation_towards(transform, cam_location)
        return carla.Transform(cam_location, rotation)

    def get_rotation_towards(self, vehicle_transform, from_location):
        # 1. 确定注视目标点
        vehicle_location = vehicle_transform.location
        forward = vehicle_transform.get_forward_vector()
        
        # 目标点不仅是车辆本身，而是车辆前方 30 米处
        # 这样摄像机视线会具有“前瞻性”，符合驾驶或观战习惯
        look_at_location = vehicle_location + forward * 30

        # 2. 计算方向向量：从相机位置指向目标点
        direction = look_at_location - from_location

        # 3. 计算偏航角 (Yaw)：在水平面(XY)上的旋转角度
        yaw = math.degrees(math.atan2(direction.y, direction.x))

        # 4. 计算俯仰角 (Pitch)：垂直方向的旋转角度
        # hypot 计算水平投影距离 sqrt(x^2 + y^2)
        horizontal_dist = math.hypot(direction.x, direction.y)
        pitch = math.degrees(math.atan2(direction.z, horizontal_dist))

        # 5. 返回旋转对象 (Roll 保持为 0，防止画面倾斜)
        return carla.Rotation(pitch=pitch, yaw=yaw, roll=0)


    def run_spectator_follow_vehicle_monitor_view(self):
        while self._is_running_follow_vehicle_monitor_view:
            self.set_spectator_to_vehicle_monitor_view()
            self.world.wait_for_tick()


    def set_spectator_follow_vehicle_monitor_view(self,enabled: bool) -> None:
        if not self.world:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        if enabled:
            self._is_running_follow_vehicle_monitor_view = True
            thread.start_new_thread(self.run_spectator_follow_vehicle_monitor_view, ())
        else:
            self._is_running_follow_vehicle_monitor_view = False

    def set_spectator_to_vehicle_bev_view(self, z_offset=50, rolename="hero") -> bool:
        if not self.world:
            return False
        if self.ego_vehicle is None:
            self.ego_vehicle = self.get_ego_vehicle(rolename)
        spectator = self.world.get_spectator()
        # 车辆位置
        vehicle_transform = self.ego_vehicle.get_transform()
        vehicle_location = self.ego_vehicle.get_transform().location
         # 计算旁观者的新位置
        spectator_location = carla.Location(
            x=vehicle_location.x,
            y=vehicle_location.y,
            z=vehicle_location.z + z_offset
        )

        spectator_rotation = carla.Rotation(pitch=-92, yaw=0, roll=0)
        # 更新旁观者的变换
        new_spectator_transform = carla.Transform(spectator_location, spectator_rotation)
        spectator.set_transform(new_spectator_transform)
        print("已将 spectator 位置设置到当前BEV")
        return True

    def run_spectator_follow_vehicle_bev_view(self):
        while self._is_running_follow_vehicle_bev_view:
            self.set_spectator_to_vehicle_bev_view()
            self.world.wait_for_tick()


    def set_spectator_follow_vehicle_bev_view(self,enabled: bool) -> None:
        if not self.world:
            ui.notify("请先连接到 CARLA 服务器", type="warning")
            return
        if enabled:
            self._is_running_follow_vehicle_bev_view = True
            thread.start_new_thread(self.run_spectator_follow_vehicle_bev_view, ())
        else:
            self._is_running_follow_vehicle_bev_view = False
