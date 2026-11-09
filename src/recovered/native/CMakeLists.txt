cmake_minimum_required(VERSION 3.16)
project(iris_native_recovered LANGUAGES CXX)

add_library(iris_native_recovered STATIC touch_event.cpp)
target_compile_features(iris_native_recovered PUBLIC cxx_std_17)
target_include_directories(iris_native_recovered PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
