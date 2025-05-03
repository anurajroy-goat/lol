# Project-level configuration.
cmake_minimum_required(VERSION 3.14)
project(space_time LANGUAGES CXX)

# The name of the executable created for the application.
set(BINARY_NAME "space_time")

# Explicitly opt-in to modern CMake behaviors to avoid warnings with recent
# versions of CMake.
cmake_policy(SET CMP0063 NEW)

# Define the application target.
add_executable(${BINARY_NAME}
  "flutter_window.cpp"
  "main.cpp"
  "Runner.rc"
  "utils.cpp"
  "win32_window.cpp"
  "floating_window_plugin.cpp"
)

# Apply the standard set of build settings.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Specify the location of Flutter's generated header and source files.
target_include_directories(${BINARY_NAME} PRIVATE
  "${CMAKE_SOURCE_DIR}/flutter/generated"
)

# Link against the Flutter library and other required dependencies.
target_link_libraries(${BINARY_NAME} PRIVATE
  flutter
  flutter_wrapper_app
  dwmapi
)

# Specify that this is a Windows GUI application (not a console application).
if(WIN32)
  set_target_properties(${BINARY_NAME} PROPERTIES
    LINK_FLAGS "/SUBSYSTEM:WINDOWS"
  )
endif()

# Ensure the executable is placed in the correct output directory.
set_target_properties(${BINARY_NAME} PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Copy the Flutter runtime dependencies to the output directory.
add_custom_command(TARGET ${BINARY_NAME} POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_directory
  "${CMAKE_SOURCE_DIR}/flutter/ephemeral"
  "$<TARGET_FILE_DIR:${BINARY_NAME}>"
)