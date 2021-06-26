cmake_minimum_required(VERSION 3.8.0)

project(fuzzcover VERSION 0.3.0 LANGUAGES CXX)

add_library(libfuzzcover INTERFACE)
target_include_directories(libfuzzcover INTERFACE include)
target_compile_features(libfuzzcover INTERFACE cxx_std_11)
target_link_libraries(libfuzzcover INTERFACE -fsanitize=fuzzer -fprofile-instr-generate -fcoverage-mapping)
target_compile_options(libfuzzcover INTERFACE -fsanitize=fuzzer-no-link -fprofile-instr-generate -fcoverage-mapping)

add_subdirectory(examples EXCLUDE_FROM_ALL)
