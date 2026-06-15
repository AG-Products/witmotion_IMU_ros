
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    ld = LaunchDescription()

    config = os.path.join(
        get_package_share_directory('witmotion_ros'),
        'config',
        'wt905.yml'
        )
        
    node=Node(
        name = 'witmotion_ros_node', # to match with watchdog restart stuff, must be the same as "executable"
        package = 'witmotion_ros',
        executable = 'witmotion_ros_node',
        parameters = [config]
    )

    ld.add_action(node)
    return ld
