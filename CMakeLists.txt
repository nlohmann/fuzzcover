cmake_minimum_required(VERSION 3.15)

project(fuzzcover VERSION 0.2.0 LANGUAGES CXX)

# the actual library
add_library(libfuzzcover INTERFACE)
target_include_directories(libfuzzcover INTERFACE include)
target_compile_features(libfuzzcover INTERFACE cxx_std_11)

##############################################################################

# binary that does the actual fuzzing
add_executable(fuzzer examples/fuzzer.cpp)
target_include_directories(fuzzer PRIVATE examples/json/include)
target_compile_options(fuzzer PRIVATE -fsanitize=fuzzer-no-link)
target_link_libraries(fuzzer PRIVATE -fsanitize=fuzzer libfuzzcover)

# binary that executes the test function with the corpus
add_executable(tester examples/tester.cpp)
target_include_directories(tester PRIVATE examples/json/include)
target_compile_options(tester PRIVATE -g -O1 -fprofile-instr-generate -fcoverage-mapping)
target_link_libraries(tester PRIVATE -fprofile-instr-generate -fcoverage-mapping libfuzzcover)

# binary that dumps the corpus in JSON format
add_executable(dumper examples/dumper.cpp)
target_include_directories(dumper PRIVATE examples/json/include)
target_link_libraries(dumper PRIVATE libfuzzcover)

##############################################################################

# the path where the fuzzer generates the corpus
set(CORPUS_DIRECTORY ${CMAKE_BINARY_DIR}/corpus)

add_custom_target(run_fuzzer
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CORPUS_DIRECTORY}
    #COMMAND ${CMAKE_CURRENT_BINARY_DIR}/fuzzer -jobs=64 -workers=8 ${CORPUS_DIRECTORY}
    COMMAND ${CMAKE_CURRENT_BINARY_DIR}/fuzzer ${CORPUS_DIRECTORY}
    COMMENT "running fuzzer"
)
add_dependencies(run_fuzzer fuzzer)

add_custom_target(minimize_corpus_files
    COMMAND ${CMAKE_COMMAND} -E make_directory new_corpus
    COMMAND fuzzer new_corpus ${CORPUS_DIRECTORY} -merge=1
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${CORPUS_DIRECTORY}
    COMMAND ${CMAKE_COMMAND} -E rename new_corpus ${CORPUS_DIRECTORY}
    COMMAND ${CMAKE_SOURCE_DIR}/tools/minimize_corpus_files.py ${CORPUS_DIRECTORY}
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "minimizing corpus files"
)

add_custom_target(minimize_corpus_length
    COMMAND ${CMAKE_SOURCE_DIR}/tools//minimize_corpus_length.py ${CORPUS_DIRECTORY}
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "minimizing corpus length"
)

add_custom_target(check_coverage
    COMMAND tester ${CORPUS_DIRECTORY}/*
    COMMAND llvm-profdata merge -sparse default.profraw -o default.profdata
    COMMAND llvm-cov report ./tester -instr-profile=default.profdata
    COMMAND llvm-cov show ./tester -instr-profile=default.profdata --format=html > coverage.html

    COMMAND llvm-cov export ./tester -instr-profile=default.profdata --format=lcov > coverage.info
    COMMAND lcov --summary coverage.info
    COMMAND genhtml coverage.info -o html

    COMMAND rm -f default.profdata default.profraw
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "collect coverage"
)
add_dependencies(check_coverage tester)

add_custom_target(check_coverage_fast
    COMMAND tester ${CORPUS_DIRECTORY}/*
    COMMAND llvm-profdata merge -sparse default.profraw -o default.profdata
    COMMAND llvm-cov report ./tester -instr-profile=default.profdata
    COMMAND rm -f default.profdata default.profraw
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "collect coverage"
)
add_dependencies(check_coverage_fast tester)

add_custom_target(dump_corpus
    COMMAND dumper ${CORPUS_DIRECTORY}/*
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "dump corpus"
)
add_dependencies(dump_corpus dumper)
