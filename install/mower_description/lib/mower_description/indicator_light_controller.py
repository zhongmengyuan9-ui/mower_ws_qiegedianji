#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetLightProperties
from std_msgs.msg import ColorRGBA, String

class IndicatorLightController(Node):
    def __init__(self):
        super().__init__('indicator_light_controller')
        
        # 订阅切割电机控制服务的调用
        self.subscription = self.create_subscription(
            String,
            '/mower/cutting_motor/status',
            self.status_callback,
            10
        )
        
        # 记录当前的速度档位
        self.current_speed_level = 0
        self.desired_speed_level = 0
        self.applied_speed_level = None
        self._service_warned = False

        self.set_light_client = self.create_client(
            SetLightProperties,
            '/gazebo/set_light_properties'
        )

        # 兼容 Gazebo 中可能出现的不同 light 名字（是否带 model/link 作用域）
        self.light_name_candidates = {
            1: [
                'indicator_light_1_glow',
                'mower::indicator_light_1_glow',
                'mower::indicator_light_1::indicator_light_1_glow',
            ],
            2: [
                'indicator_light_2_glow',
                'mower::indicator_light_2_glow',
                'mower::indicator_light_2::indicator_light_2_glow',
            ],
            3: [
                'indicator_light_3_glow',
                'mower::indicator_light_3_glow',
                'mower::indicator_light_3::indicator_light_3_glow',
            ],
        }
        self.resolved_light_names = {}

        # 周期重试，避免 Gazebo 服务/实体发现晚于状态消息导致丢更新
        self._retry_timer = self.create_timer(0.5, self._retry_apply)
        
        # 延迟初始化，等待Gazebo服务就绪
        self._init_timer = self.create_timer(3.0, self._delayed_init)
        self.get_logger().info('Indicator light controller started')

    def _retry_apply(self):
        if self.applied_speed_level != self.desired_speed_level:
            self.update_lights(self.desired_speed_level)

    def status_callback(self, msg):
        try:
            # 解析消息内容，获取速度档位
            speed_level = int(msg.data)
            self.current_speed_level = speed_level
            self.desired_speed_level = speed_level
            self.update_lights(speed_level)
        except ValueError:
            self.get_logger().error(f'Invalid status message: {msg.data}')

    def _color(self, r, g, b, a=1.0):
        return ColorRGBA(r=float(r), g=float(g), b=float(b), a=float(a))

    def _set_single_light(self, light_index, color):
        if not self.set_light_client.wait_for_service(timeout_sec=2.0):
            if not self._service_warned:
                self.get_logger().warning(
                    'Gazebo /gazebo/set_light_properties not ready, indicator colors are pending.'
                )
                self._service_warned = True
            return False

        self._service_warned = False
        candidate_names = []
        if light_index in self.resolved_light_names:
            candidate_names.append(self.resolved_light_names[light_index])
        candidate_names.extend(self.light_name_candidates[light_index])

        self.get_logger().debug(f'设置指示灯 {light_index} 颜色: R={color.r:.2f}, G={color.g:.2f}, B={color.b:.2f}')
        
        for light_name in candidate_names:
            self.get_logger().debug(f'尝试灯光名称: {light_name}')
            
            req = SetLightProperties.Request()
            req.light_name = light_name
            req.diffuse = color
            req.attenuation_constant = 0.8
            req.attenuation_linear = 0.02
            req.attenuation_quadratic = 0.01

            future = self.set_light_client.call_async(req)
            rclpy.spin_until_future_complete(self, future, timeout_sec=0.4)

            if not future.done():
                self.get_logger().warning(f'灯光 {light_name} 服务调用超时')
                continue

            result = future.result()
            if result is not None and result.success:
                self.resolved_light_names[light_index] = light_name
                self.get_logger().info(f'成功设置指示灯 {light_index} 使用灯光名称: {light_name}')
                return True
            else:
                self.get_logger().warning(f'灯光 {light_name} 设置失败: {result}')

        self.get_logger().warning(
            f'所有灯光名称尝试失败 for indicator light {light_index}; check Gazebo light names.'
        )
        return False

    def _delayed_init(self):
        """延迟初始化，确保Gazebo服务就绪后尝试连接"""
        self._init_timer.cancel()
        if self.set_light_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().info('Gazebo light service is ready')
            # 应用当前档位的指示灯状态
            self.update_lights(self.current_speed_level)
        else:
            self.get_logger().warning('Gazebo light service still not available after delay')

    def update_lights(self, speed_level):
        """根据速度档位更新指示灯颜色。默认全白，档位升高后按序亮红/黄/绿。"""
        level_to_colors = {
            0: [self._color(1.0, 1.0, 1.0), self._color(1.0, 1.0, 1.0), self._color(1.0, 1.0, 1.0)],
            1: [self._color(0.9, 0.1, 0.1), self._color(1.0, 1.0, 1.0), self._color(1.0, 1.0, 1.0)],
            2: [self._color(0.9, 0.1, 0.1), self._color(0.95, 0.85, 0.1), self._color(1.0, 1.0, 1.0)],
            3: [self._color(0.9, 0.1, 0.1), self._color(0.95, 0.85, 0.1), self._color(0.1, 0.9, 0.1)],
        }

        if speed_level not in level_to_colors:
            self.get_logger().warning(f'Unknown speed level: {speed_level}')
            return

        colors = level_to_colors[speed_level]
        ok1 = self._set_single_light(1, colors[0])
        ok2 = self._set_single_light(2, colors[1])
        ok3 = self._set_single_light(3, colors[2])
        if ok1 and ok2 and ok3:
            self.applied_speed_level = speed_level
            self.get_logger().info(f'Indicator lights updated for speed level: {speed_level}')

def main(args=None):
    rclpy.init(args=args)
    indicator_light_controller = IndicatorLightController()
    rclpy.spin(indicator_light_controller)
    indicator_light_controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()