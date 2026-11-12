import sys
from pathlib import Path

# Make the package importable when pytest runs from the source tree (no colcon
# install needed for the ROS-free unit tests).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
