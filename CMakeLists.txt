cmake_minimum_required(VERSION 3.12.0)

project(fuzzcover VERSION 0.3.0 LANGUAGES CXX)

# compiler checks
if (NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    message(WARNING "Fuzzcover requires Clang as compiler and assumes libFuzzer is available.")
endif()
if (CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang")
    message(WARNING "The compiler provided by Xcode (AppleClang ${CMAKE_CXX_COMPILER_VERSION}) cannot compile Fuzzcover, because it does not contain libFuzzer. Please install Clang via Homebrew calling 'brew install llvm' and re-run CMake after setting 'CXX=$(brew --prefix llvm)/bin/clang'.")
endif()

# required headers
include(CheckIncludeFileCXX)
check_include_file_cxx(dirent.h FUZZCOVER_HAS_DIRENT_H)
if (NOT FUZZCOVER_HAS_DIRENT_H)
    message(WARNING "Header <dirent.h> is required by Fuzzcover, but not found.")
endif()

# Fuzzcover interface library
add_library(libfuzzcover INTERFACE)
target_include_directories(libfuzzcover INTERFACE include)
target_compile_features(libfuzzcover INTERFACE cxx_std_11)
target_link_libraries(libfuzzcover INTERFACE -fsanitize=fuzzer -fprofile-instr-generate -fcoverage-mapping)
target_compile_options(libfuzzcover INTERFACE -fsanitize=fuzzer-no-link -fprofile-instr-generate -fcoverage-mapping)

# interactive Fuzzcover suite
configure_file(tools/fuzzcover.py fuzzcover.py)

# target to create virtual environment
include(FindPython3)
find_package(Python3 COMPONENTS Interpreter)

add_custom_target(fuzzcover_suite
    COMMAND ${Python3_EXECUTABLE} -mvenv venv
    COMMAND venv/bin/pip3 install -r ${CMAKE_SOURCE_DIR}/tools/requirements.txt
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Installing virtual environment"
)

# examples
add_subdirectory(examples EXCLUDE_FROM_ALL)
