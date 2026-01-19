
import carla
import os
import pygame
import math
from io import BytesIO
import base64
from PIL import Image, ImageDraw
# 颜色定义
COLOR_LIGHT_GRAY = pygame.Color(84, 84, 84)
COLOR_DARK_GRAY = pygame.Color(50, 50, 50)
COLOR_WHITE = pygame.Color(255, 255, 255)
COLOR_YELLOW = pygame.Color(255, 255, 0)

PIXELS_PER_METER = 5 

class MapGenerator(object):
    def __init__(self, carla_world, pixels_per_meter=PIXELS_PER_METER):
        self._pixels_per_meter = pixels_per_meter
        self.scale = 1.0
        self.world = carla_world
        self.map = self.world.get_map()

        pygame.init()
        '''
        它的主要作用是 计算当前 CARLA 地图的物理边界（Bounding Box），并确定生成的 2D 地图图片所需的像素尺寸 。
        '''
        #通过这些密集的点来覆盖地图的所有可通行区域，以便后续计算地图的最边缘坐标。
        waypoints = self.map.generate_waypoints(2)
        #遍历所有生成的路点，找出 X 轴和 Y 轴的最大值和最小值。
        #在计算出的边界外额外预留 5 米的边距，防止地图边缘紧贴画布边缘，更加美观。
        margin = 5
        max_x = max(waypoints, key=lambda x: x.transform.location.x).transform.location.x + margin
        max_y = max(waypoints, key=lambda x: x.transform.location.y).transform.location.y + margin
        min_x = min(waypoints, key=lambda x: x.transform.location.x).transform.location.x - margin
        min_y = min(waypoints, key=lambda x: x.transform.location.y).transform.location.y - margin

        self.world_width = max_x - min_x
        self.world_height = max_y - min_y
        self._world_offset = (min_x, min_y)
        #根据预设的比例尺 self._pixels_per_meter （代码中定义为 5，即 1 米对应 5 像素），将物理尺寸转换为屏幕上的像素尺寸。
        self.pixel_width = int(self._pixels_per_meter * self.world_width)
        self.pixel_height = int(self._pixels_per_meter * self.world_height)
        
        self.big_map_surface = pygame.Surface((self.pixel_width, self.pixel_height))
        
        self._draw_road()

    def _draw_road(self):
        self.big_map_surface.fill(COLOR_LIGHT_GRAY)
        topology = self.map.get_topology()
        self._draw_topology(topology)

    def _draw_topology(self, carla_topology, index=0):
        # 1. 提取拓扑中的路点，并按 Z 轴高度排序，确保渲染顺序（处理立交桥遮挡）
        topology = [x[index] for x in carla_topology]
        topology = sorted(topology, key=lambda w: w.transform.location.z)
        
        for waypoint in topology:
            # 2. 构建连续车道段：从当前路点向前搜索，直到路段 ID 变化
            waypoints = [waypoint]
            nxt = waypoint.next(2.0)
            if len(nxt) > 0:
                nxt = nxt[0]
                while nxt.road_id == waypoint.road_id:
                    waypoints.append(nxt)
                    nxt = nxt.next(2.0)
                    if len(nxt) > 0:
                        nxt = nxt[0]
                    else:
                        break

            # 3. 计算车道多边形边界：分别计算左右两侧的边界点
            # _lateral_shift 用于根据车道宽度向左/右平移坐标
            road_left_side = [self._lateral_shift(w.transform, -w.lane_width * 0.5) for w in waypoints]
            road_right_side = [self._lateral_shift(w.transform, w.lane_width * 0.5) for w in waypoints]

            # 4. 闭合多边形：左侧点序 + 右侧点序（逆序），形成封闭区域
            polygon = road_left_side + [x for x in reversed(road_right_side)]
            # 将世界坐标转换为像素坐标
            polygon = [self.world_to_pixel(x) for x in polygon]

            # 5. 绘制车道表面
            if len(polygon) > 2:
                # 绘制边缘（宽度5），抗锯齿或加粗效果
                pygame.draw.polygon(self.big_map_surface, COLOR_DARK_GRAY, polygon, 5)
                # 绘制填充（默认宽度0），填充车道颜色
                pygame.draw.polygon(self.big_map_surface, COLOR_DARK_GRAY, polygon)

            # 6. 绘制车道线（非路口区域）
            if not waypoint.is_junction:
                self._draw_lane_marking_single_side(waypoints, -1) #左侧
                self._draw_lane_marking_single_side(waypoints, 1)  #右侧

    def _draw_lane_marking_single_side(self, waypoints, sign):
        """ 绘制单侧车道线逻辑 """
        lane_marking = None
        previous_marking_type = carla.LaneMarkingType.NONE
        previous_marking_color = carla.LaneMarkingColor.Other
        temp_waypoints = []
        current_lane_marking = carla.LaneMarkingType.NONE

        for sample in waypoints:
            # 根据 sign (-1 或 1) 获取左侧或右侧的车道线属性
            lane_marking = sample.left_lane_marking if sign < 0 else sample.right_lane_marking
            if lane_marking is None: continue

            # 检测车道线类型是否发生变化（例如从实线变为虚线）
            if current_lane_marking != lane_marking.type:
                # 如果变化，先绘制之前积攒的那一段同类型车道线
                self._draw_line_segment(previous_marking_type, previous_marking_color, temp_waypoints, sign)
                
                # 更新当前状态为新的车道线类型，并重新开始积攒点
                current_lane_marking = lane_marking.type
                temp_waypoints = [sample] # 新段的起点
                previous_marking_type = lane_marking.type
                previous_marking_color = lane_marking.color
            else:
                # 如果类型没变，继续将当前点加入到当前段中
                temp_waypoints.append(sample)

        # 循环结束后，绘制最后剩余的一段车道线
        self._draw_line_segment(previous_marking_type, previous_marking_color, temp_waypoints, sign)

    def _draw_line_segment(self, marking_type, marking_color, waypoints, sign):
        if len(waypoints) < 2: return

        # 1. 确定车道线颜色
        color = COLOR_WHITE
        if marking_color == carla.LaneMarkingColor.Yellow:
            color = COLOR_YELLOW
        
        # 2. 计算绘制点坐标：基于路点位置向左/右平移半个车道宽，并转为像素坐标
        points = [self.world_to_pixel(self._lateral_shift(w.transform, sign * w.lane_width * 0.5)) for w in waypoints]
        
        line_width = 2

        # 3. 绘制实线 (Solid)
        if marking_type == carla.LaneMarkingType.Solid or marking_type == carla.LaneMarkingType.SolidSolid:
            pygame.draw.lines(self.big_map_surface, color, False, points, line_width)

        # 4. 绘制虚线 (Broken)
        elif marking_type == carla.LaneMarkingType.Broken or marking_type == carla.LaneMarkingType.BrokenBroken:
            # 这里的切片技巧用于模拟虚线效果：
            # zip(*(iter(points),) * 4) 将点列表按每4个点分为一组
            # if n % 2 == 0 隔一组取一组，实现“画一段、空一段”的效果
            broken_lines = [x for n, x in enumerate(zip(*(iter(points),) * 4)) if n % 2 == 0]
            for line in broken_lines:
                pygame.draw.lines(self.big_map_surface, color, False, line, line_width)

    def _lateral_shift(self, transform, shift):
        # 1. 旋转方向：将当前朝向（yaw）顺时针旋转 90 度，得到垂直于前进方向的“右侧”方向
        transform.rotation.yaw += 90
        # 2. 向量计算：
        # transform.get_forward_vector() 现在返回的是侧向向量
        # location + shift * vector 实现沿侧向移动指定距离
        # shift 为正向右平移，为负向左平移
        return transform.location + shift * transform.get_forward_vector()

    def world_to_pixel(self, location):
        x = self.scale * self._pixels_per_meter * (location.x - self._world_offset[0])
        y = self.scale * self._pixels_per_meter * (location.y - self._world_offset[1])
        return [int(x), int(y)]

    def get_pil_image(self):
        image_str = pygame.image.tostring(self.big_map_surface, "RGB")
        pil_image = Image.frombytes("RGB", self.big_map_surface.get_size(), image_str)
        return pil_image



class Map2dViewer:
    def __init__(self):
        self.placeholder = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBg+A8AAQQBAHAgZQsAAAAASUVORK5CYII="

    def update(self, world, map_gen=None, max_width=500, max_height=400):
        self.world = world
        self.map_gen = map_gen if map_gen is not None else MapGenerator(world)
        self.pil_image = self.map_gen.get_pil_image()
        self.map_w, self.map_h = self.pil_image.size
        
        self.raw_w, self.raw_h = self.pil_image.size
        scale_w = max_width / self.raw_w
        scale_h = max_height / self.raw_h
        self.render_scale = min(scale_w, scale_h)
        
        self.final_w = int(self.raw_w * self.render_scale)
        self.final_h = int(self.raw_h * self.render_scale)
        # 全局配置
        self.MAX_FPS = 30  # 根据实际需求调整
        self.FRAME_QUEUE_SIZE = 2  # 每个流的帧队列大小
        self.display_image = self.pil_image.resize((self.final_w, self.final_h), Image.Resampling.LANCZOS)
        return self.encode_image_to_base64(self.display_image)

    def update_with_ego(self, world, ego_vehicle, map_gen=None, max_width=500, max_height=400):
        self.world = world
        self.map_gen = map_gen if map_gen is not None else MapGenerator(world)
        self.pil_image = self.map_gen.get_pil_image()
        self.map_w, self.map_h = self.pil_image.size

        self.raw_w, self.raw_h = self.pil_image.size
        scale_w = max_width / self.raw_w
        scale_h = max_height / self.raw_h
        self.render_scale = min(scale_w, scale_h)

        self.final_w = int(self.raw_w * self.render_scale)
        self.final_h = int(self.raw_h * self.render_scale)
        base_image = self.pil_image.resize((self.final_w, self.final_h), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(base_image)

        try:
            vehicles = None
            if self.world is not None:
                vehicles = list(self.world.get_actors().filter("vehicle.*"))

            if ego_vehicle is not None:
                transform = ego_vehicle.get_transform()
                loc = transform.location
                raw_pixel = self.map_gen.world_to_pixel(loc)
                screen_x = raw_pixel[0] * self.render_scale
                screen_y = raw_pixel[1] * self.render_scale

                arrow_len = 12
                yaw_rad = math.radians(transform.rotation.yaw)
                end_x = screen_x + arrow_len * math.cos(yaw_rad)
                end_y = screen_y + arrow_len * math.sin(yaw_rad)

                r = 5
                draw.ellipse(
                    (screen_x - r, screen_y - r, screen_x + r, screen_y + r),
                    fill=(255, 85, 85),
                    outline=(255, 255, 255),
                    width=2,
                )
                draw.line(
                    (screen_x, screen_y, end_x, end_y),
                    fill=(255, 255, 85),
                    width=2,
                )

            if vehicles:
                for v in vehicles:
                    if ego_vehicle is not None and v.id == ego_vehicle.id:
                        continue
                    t = v.get_transform()
                    loc = t.location
                    raw_pixel = self.map_gen.world_to_pixel(loc)
                    screen_x = raw_pixel[0] * self.render_scale
                    screen_y = raw_pixel[1] * self.render_scale
                    r_other = 4
                    draw.ellipse(
                        (screen_x - r_other, screen_y - r_other, screen_x + r_other, screen_y + r_other),
                        fill=(80, 160, 255),
                        outline=(255, 255, 255),
                        width=1,
                    )
        except Exception:
            pass

        return self.encode_image_to_base64(base_image)

    def encode_image_to_base64(self, image):
        try:
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            data = buffer.getvalue()
            return base64.b64encode(data).decode("utf-8")
        except Exception:
            return self.placeholder
