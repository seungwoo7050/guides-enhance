cmake_minimum_required(VERSION 3.20)
project(local_job_runner LANGUAGES CXX)

find_package(Threads REQUIRED)

# [Implementation 0] Build one reusable library for the app and tests
add_library(local_job_runner src/job_runner.cpp)
target_include_directories(local_job_runner PUBLIC include)
target_compile_features(local_job_runner PUBLIC cxx_std_20)
target_compile_options(local_job_runner PRIVATE -Wall -Wextra -Wpedantic -Werror)
target_link_libraries(local_job_runner PUBLIC Threads::Threads)

add_executable(local_job_runner_app app/main.cpp)
target_link_libraries(local_job_runner_app PRIVATE local_job_runner)
target_compile_options(local_job_runner_app PRIVATE -Wall -Wextra -Wpedantic -Werror)

add_executable(local_job_runner_tests tests/job_runner_tests.cpp)
target_link_libraries(local_job_runner_tests PRIVATE local_job_runner)
target_compile_options(local_job_runner_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)

enable_testing()
add_test(NAME local_job_runner_tests COMMAND local_job_runner_tests)
