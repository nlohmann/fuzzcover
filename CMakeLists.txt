cmake_minimum_required(VERSION 3.8.0)

project(fuzzcover VERSION 0.3.0 LANGUAGES CXX)

add_library(libfuzzcover INTERFACE)
target_include_directories(libfuzzcover INTERFACE include)
target_compile_features(libfuzzcover INTERFACE cxx_std_11)
target_link_libraries(libfuzzcover INTERFACE -fsanitize=fuzzer -fprofile-instr-generate -fcoverage-mapping)
target_compile_options(libfuzzcover INTERFACE -fsanitize=fuzzer-no-link -fprofile-instr-generate -fcoverage-mapping)

if (NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    message(WARNING "Fuzzcover requires Clang as compiler and assumes libFuzzer is available.")
endif()

if (CMAKE_CXX_COMPILER_ID STREQUAL "AppleClang")
    message(WARNING "The compiler provided by Xcode (AppleClang ${CMAKE_CXX_COMPILER_VERSION}) cannot compile Fuzzcover, because it does not contain libFuzzer. Please install Clang via Homebrew calling 'brew install llvm' and re-run CMake after setting 'CXX=$(brew --prefix llvm)/bin/clang'.")
endif()

add_subdirectory(examples EXCLUDE_FROM_ALL)
