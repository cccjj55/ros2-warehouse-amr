import os
from glob import glob

from setuptools import setup

package_name = 'warehouse_amr_mission'

setup(
    name=package_name,
    version='0.2.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Chen Zeyi',
    maintainer_email='cccjj55@users.noreply.github.com',
    description='Mission FSM, Nav2 action dispatch and benchmarks for the warehouse AMR.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mission_server = warehouse_amr_mission.mission_server:main',
            'bench_goals = warehouse_amr_mission.bench_goals:main',
        ],
    },
)
