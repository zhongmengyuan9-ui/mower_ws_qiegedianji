#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from mower_description.srv import CuttingMotorControl
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class CuttingMotorController(Node):
    def __init__(self):
        super().__init__('cutting_motor_controller')
        
        # 速度档位映射
        self.speed_levels = {
            0: 0.0,    # 关闭
            1: 15.0,   # 一档
            2: 30.0,   # 二档
            3: 45.0    # 三档
        }

        self.current_speed = 0.0
        self.blade_position = 0.0
        self.command_period = 0.05  # 20 Hz trajectory update

        # 创建状态发布者
        self.status_publisher = self.create_publisher(
            String, 
            '/mower/cutting_motor/status', 
            10
        )

        # 使用 joint pose trajectory 插件的命令 topic
        self.traj_publisher = self.create_publisher(
            JointTrajectory,
            '/mower/blade/set_joint_trajectory',
            10
        )
        
        # 创建服务
        self.service = self.create_service(
            CuttingMotorControl, 
            '/mower/cutting_motor/control', 
            self.control_callback
        )

        self.timer = self.create_timer(self.command_period, self.publish_blade_trajectory)
        self.get_logger().info('Cutting motor controller started')

    def publish_blade_trajectory(self):
        # 按速度积分得到目标角度，形成连续旋转轨迹
        self.blade_position += self.current_speed * self.command_period

        traj = JointTrajectory()
        traj.header.frame_id = 'base_link'
        traj.joint_names = ['blade_joint']

        point = JointTrajectoryPoint()
        point.positions = [self.blade_position]
        point.time_from_start = Duration(sec=0, nanosec=int(self.command_period * 1e9))
        traj.points = [point]

        self.traj_publisher.publish(traj)

    def control_callback(self, request, response):
        speed_level = request.speed_level

        if speed_level not in self.speed_levels:
            response.success = False
            response.message = f'Invalid speed level: {speed_level}. Valid levels are 0-3.'
            response.actual_speed = 0.0
            return response

        # 获取对应档位的速度
        speed = self.speed_levels[speed_level]

        # 更新旋转速度（由定时器持续发布轨迹）
        self.current_speed = speed

        # 发布状态消息
        status_msg = String()
        status_msg.data = str(speed_level)
        self.status_publisher.publish(status_msg)

        # 构建响应
        response.success = True
        response.message = f'Successfully set cutting motor to level {speed_level} ({speed} rad/s)'
        response.actual_speed = speed

        self.get_logger().info(f'Cutting motor set to level {speed_level}, speed: {speed} rad/s')

        return response

def main(args=None):
    rclpy.init(args=args)
    cutting_motor_controller = CuttingMotorController()
    rclpy.spin(cutting_motor_controller)
    cutting_motor_controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
