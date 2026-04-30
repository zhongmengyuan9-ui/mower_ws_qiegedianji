# 启动仿真（rviz和gazebo一键启动）
ros2 launch mower_description mower_gazebo.launch.py 2>&1 | grep -v "blade_trajectory_controller"

# 传感器支持列表
	传感器 			topic			
	深度相机 RGB		/mower/camera/image_raw
	深度相机 Depth		/mower/camera/depth/image_raw
	深度相机 点云		/mower/camera/points		
	雷达			/scan
	超声波			/mower/ultrasonic/scan
	IMU			/mower/imu/data

# 机器人状态
	状态名			topic
	里程计			/odom
	关节状态		/joint_states
	坐标变换		/tf /tf_static
	速度			/cmd_vel
	刀盘轨迹控制		/mower/blade/set_joint_trajectory
	电机状态		/mower/cutting_motor/status
	档位可视化		/mower/gear_marker


# 切割电机档位开启与关闭
## 启动一档
ros2 service call /gmower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 1}"

## 启动二档
ros2 service call /gmower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 2}"

## 启动三档
ros2 service call /gmower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 3}"

## 关闭电机
ros2 service call /gmower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 0}"


# 机器人移动控制
ros2 run teleop_twist_keyboard teleop_twist_keyboard 
