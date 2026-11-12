cmake_minimum_required(VERSION 3.8)
project(warehouse_amr_description)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)

# Everything in this package is data: xacro, yaml, launch, worlds, maps.
install(
  DIRECTORY config description launch worlds maps
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Upstream-derived files keep their own copyright headers; skip the blanket
  # copyright linter and rely on xmllint + cmake lint instead.
  set(ament_cmake_copyright_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
