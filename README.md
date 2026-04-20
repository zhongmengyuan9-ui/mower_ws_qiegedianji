
# 启动 Gazebo 模拟环境
ros2 launch mower_description mower_gazebo.launch.py




# 启动一档（红色指示灯亮）
ros2 service call /mower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 1}"

# 启动二档（红色和黄色指示灯亮）
ros2 service call /mower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 2}"

# 启动三档（所有指示灯亮）
ros2 service call /mower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 3}"

# 关闭电机（所有指示灯灭）
ros2 service call /mower/cutting_motor/control mower_description/srv/CuttingMotorControl "{speed_level: 0}"