import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # 获取功能包的路径
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    pkg_mower_description = get_package_share_directory('mower_description')
    
    # 使用命名空间来避免参数冲突
    robot_namespace = LaunchConfiguration('namespace', default='mower')

    # Gazebo 启动参数：是否使用GUI，是否暂停，世界文件路径
    default_world_path = os.path.join(pkg_mower_description, 'worlds', 'room_world_open.world')
    default_rviz_config = os.path.join(pkg_mower_description, 'config', 'rviz', 'mower_gazebo.rviz')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    headless = LaunchConfiguration('headless', default='false')
    world = LaunchConfiguration('world', default=default_world_path)

    # 启动 Gazebo 服务器和客户端
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={
            'world': world,
            # SetLightProperties service is provided by gazebo_ros_api_plugin.
            # Without it, indicator_light_controller cannot control light on/off.
            'extra_gazebo_args': '-s libgazebo_ros_api_plugin.so',
        }.items()
    )

    gazebo_client = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gzclient.launch.py')
        ),
        condition=IfCondition(LaunchConfiguration('gui', default='true'))
    )

    # 从 URDF 加载机器人描述
    urdf_path = os.path.join(pkg_mower_description, 'urdf', 'mower.urdf')
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()

    # 启动 robot_state_publisher，发布 TF 和 joint states
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': use_sim_time}],
        #remappings=[('/robot_description', '/mower_robot_description')]
    )

    # 在 Gazebo 中生成机器人
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'mower', '-topic', 'robot_description', '-x', '0', '-y', '0', '-z', '0.1', '-b'],
        output='screen'
    )

    # Best effort cleanup for stale entities from previous runs.
    delete_stale_entity = ExecuteProcess(
        cmd=[
            'ros2', 'service', 'call',
            '/delete_entity',
            'gazebo_msgs/srv/DeleteEntity',
            '{name: mower}'
        ],
        output='screen'
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('mower_rvizconfig')],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(LaunchConfiguration('mower_rviz'))
    )

    # 切割电机控制器节点
    cutting_motor_controller = Node(
        package='mower_description',
        executable='cutting_motor_controller.py',
        name='cutting_motor_controller',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    # 指示灯控制器节点
    indicator_light_controller = Node(
        package='mower_description',
        executable='indicator_light_controller.py',
        name='indicator_light_controller',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='Use simulation (Gazebo) clock if true'),
        DeclareLaunchArgument('headless', default_value='false',
                              description='Whether to run gzclient'),
        DeclareLaunchArgument('gui', default_value='true',
                              description='Whether to run gzclient'),
        DeclareLaunchArgument('world', default_value=default_world_path,
                              description='Gazebo world file'),
        # Backward-compatible RViz args for direct CLI usage
        DeclareLaunchArgument('rviz', default_value='true',
                              description='Whether to run RViz2'),
        DeclareLaunchArgument('rvizconfig', default_value=default_rviz_config,
                              description='Path to RViz2 config file'),
        # Namespaced RViz args to avoid collisions when included by other launches
        DeclareLaunchArgument('mower_rviz', default_value=LaunchConfiguration('rviz'),
                              description='(Internal) Whether to run RViz2 for mower_description'),
        DeclareLaunchArgument('mower_rvizconfig', default_value=LaunchConfiguration('rvizconfig'),
                              description='(Internal) RViz2 config path for mower_description'),
        gazebo,
        gazebo_client,
        robot_state_publisher,
        TimerAction(period=2.0, actions=[delete_stale_entity]),
        TimerAction(period=4.0, actions=[spawn_entity]),
        cutting_motor_controller,
        indicator_light_controller,
        rviz2,
    ])
