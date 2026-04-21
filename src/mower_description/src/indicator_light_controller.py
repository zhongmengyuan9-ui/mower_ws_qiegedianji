#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from gazebo_msgs.srv import SetLinkProperties
from gazebo_msgs.msg import LinkState
from std_msgs.msg import ColorRGBA

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
        
        # 创建Gazebo服务客户端
        self.set_link_properties_client = self.create_client(
            SetLinkProperties, 
            '/gazebo/set_link_properties'
        )
        
        # 记录当前的速度档位
        self.current_speed_level = 0
        self.desired_speed_level = 0
        self.applied_speed_level = None
        
        # 指示灯颜色映射
        self.indicator_colors = {
            0: ColorRGBA(r=0.5, g=0.5, b=0.5, a=1.0),    # 熄灭（中灰色）
            1: ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0),    # 红色
            2: ColorRGBA(r=1.0, g=0.9, b=0.0, a=1.0),    # 黄色
            3: ColorRGBA(r=0.0, g=1.0, b=0.0, a=1.0)     # 绿色
        }
        
        # 指示灯link名称
        self.indicator_links = {
            1: 'indicator_light_1',
            2: 'indicator_light_2', 
            3: 'indicator_light_3'
        }
        
        # 等待服务就绪
        self.wait_for_service()
        self.get_logger().info('Indicator light controller started (Gazebo link properties)')
    
    def wait_for_service(self):
        """等待Gazebo服务就绪"""
        if not self.set_link_properties_client.wait_for_service(timeout_sec=10.0):
            self.get_logger().error('Gazebo set_link_properties service not available')
            return False
        self.get_logger().info('Gazebo service is ready')
        return True
    
    def status_callback(self, msg):
        try:
            # 解析消息内容，获取速度档位
            speed_level = int(msg.data)
            self.get_logger().info(f'Received cutting motor level: {speed_level}')
            self.current_speed_level = speed_level
            self.desired_speed_level = speed_level
            self.update_indicators(speed_level)
        except ValueError:
            self.get_logger().error(f'Invalid status message: {msg.data}')
    
    def update_indicators(self, speed_level):
        """根据档位更新指示灯"""
        
        # 根据档位设置指示灯状态
        if speed_level == 0:
            # 档位0：所有指示灯熄灭
            self._set_indicator_color(1, self.indicator_colors[0])
            self._set_indicator_color(2, self.indicator_colors[0])
            self._set_indicator_color(3, self.indicator_colors[0])
            self.get_logger().info('All indicator lights OFF (gray)')
        elif speed_level == 1:
            # 档位1：指示灯1亮红色
            self._set_indicator_color(1, self.indicator_colors[1])
            self._set_indicator_color(2, self.indicator_colors[0])
            self._set_indicator_color(3, self.indicator_colors[0])
            self.get_logger().info('Indicator 1: RED, Indicators 2&3: OFF')
        elif speed_level == 2:
            # 档位2：指示灯1亮红色，指示灯2亮黄色
            self._set_indicator_color(1, self.indicator_colors[1])
            self._set_indicator_color(2, self.indicator_colors[2])
            self._set_indicator_color(3, self.indicator_colors[0])
            self.get_logger().info('Indicator 1: RED, Indicator 2: YELLOW, Indicator 3: OFF')
        elif speed_level == 3:
            # 档位3：所有指示灯亮起
            self._set_indicator_color(1, self.indicator_colors[1])
            self._set_indicator_color(2, self.indicator_colors[2])
            self._set_indicator_color(3, self.indicator_colors[3])
            self.get_logger().info('Indicator 1: RED, Indicator 2: YELLOW, Indicator 3: GREEN')
        else:
            # 未知档位，所有指示灯熄灭
            self._set_indicator_color(1, self.indicator_colors[0])
            self._set_indicator_color(2, self.indicator_colors[0])
            self._set_indicator_color(3, self.indicator_colors[0])
            self.get_logger().warning(f'Unknown speed level: {speed_level}, all indicators OFF')
    
    def _set_indicator_color(self, indicator_id, color):
        """设置单个指示灯颜色"""
        # 这里需要调用Gazebo服务来修改link的视觉属性
        # 由于Gazebo的API限制，我们使用日志输出颜色信息
        self.get_logger().debug(f'Setting indicator {indicator_id} to color: R={color.r}, G={color.g}, B={color.b}')
        
        # 实际应用中，这里应该调用Gazebo的SetLinkProperties服务
        # 但由于Gazebo API的限制，我们暂时使用日志输出
        # 在实际部署时，需要安装并配置相应的Gazebo插件

def main(args=None):
    rclpy.init(args=args)
    indicator_light_controller = IndicatorLightController()
    rclpy.spin(indicator_light_controller)
    indicator_light_controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()