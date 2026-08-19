cmake_minimum_required(VERSION 3.16)
project(legion_service LANGUAGES CXX)

find_package(nlohmann_json 3.10 REQUIRED)
find_package(yaml-cpp REQUIRED)

if(TARGET yaml-cpp::yaml-cpp)
  set(YAML_CPP_TARGET yaml-cpp::yaml-cpp)
elseif(TARGET yaml-cpp)
  set(YAML_CPP_TARGET yaml-cpp)
else()
  message(FATAL_ERROR "yaml-cpp did not provide a supported CMake target")
endif()

add_executable(legion_service legion_service.cpp)
target_compile_features(legion_service PRIVATE cxx_std_20)
target_compile_options(legion_service PRIVATE -Wall -Wextra -Wpedantic -Wconversion)
target_link_libraries(legion_service PRIVATE nlohmann_json::nlohmann_json ${YAML_CPP_TARGET})
install(TARGETS legion_service RUNTIME DESTINATION bin)
