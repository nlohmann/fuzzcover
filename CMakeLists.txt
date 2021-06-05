cmake_minimum_required(VERSION 3.15)

project(fuzzcover VERSION 0.3.0 LANGUAGES CXX)

# the actual library
add_library(libfuzzcover INTERFACE)
target_include_directories(libfuzzcover INTERFACE include)
target_compile_features(libfuzzcover INTERFACE cxx_std_11)
target_link_libraries(libfuzzcover INTERFACE -fsanitize=fuzzer -fprofile-instr-generate -fcoverage-mapping)
target_compile_options(libfuzzcover INTERFACE -fsanitize=fuzzer-no-link -fprofile-instr-generate -fcoverage-mapping)

add_subdirectory(examples)

##############################################################################

## the path where the fuzzer generates the corpus
#set(CORPUS_DIRECTORY ${CMAKE_BINARY_DIR}/corpus)
#
#find_program(LLVM_PROFDATA NAMES llvm-profdata REQUIRED)
#find_program(LLVM_COV NAMES llvm-cov REQUIRED)
#find_program(LCOV NAMES lcov REQUIRED)
#find_program(GENHTML NAMES genhtml REQUIRED)
#
#add_custom_target(run_fuzzer
#    COMMAND ${CMAKE_COMMAND} -E make_directory ${CORPUS_DIRECTORY}
#    COMMAND ${CMAKE_CURRENT_BINARY_DIR}/fuzzer ${CORPUS_DIRECTORY}
#    COMMENT "running fuzzer"
#)
#add_dependencies(run_fuzzer fuzzer)
#
#add_custom_target(run_fuzzer_parallel
#    COMMAND ${CMAKE_COMMAND} -E make_directory ${CORPUS_DIRECTORY}
#    COMMAND ${CMAKE_CURRENT_BINARY_DIR}/fuzzer -jobs=64 -workers=8 ${CORPUS_DIRECTORY}
#    COMMENT "running fuzzer"
#)
#add_dependencies(run_fuzzer_parallel fuzzer)
#
#add_custom_target(minimize_corpus_files
#    COMMAND ${CMAKE_COMMAND} -E make_directory new_corpus
#    COMMAND fuzzer new_corpus ${CORPUS_DIRECTORY} -merge=1
#    COMMAND ${CMAKE_COMMAND} -E remove_directory ${CORPUS_DIRECTORY}
#    COMMAND ${CMAKE_COMMAND} -E rename new_corpus ${CORPUS_DIRECTORY}
#    COMMAND ${CMAKE_SOURCE_DIR}/tools/minimize_corpus_files.py ${CORPUS_DIRECTORY}
#    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
#    COMMENT "minimizing corpus files"
#)
#
#add_custom_target(minimize_corpus_length
#    COMMAND ${CMAKE_SOURCE_DIR}/tools//minimize_corpus_length.py ${CORPUS_DIRECTORY}
#    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
#    COMMENT "minimizing corpus length"
#)
#
#add_custom_target(check_coverage
#    COMMAND tester ${CORPUS_DIRECTORY}/*
#    COMMAND ${LLVM_PROFDATA} merge -sparse default.profraw -o default.profdata
#    COMMAND ${LLVM_COV} report ./tester -instr-profile=default.profdata
#    COMMAND ${LLVM_COV} show ./tester -instr-profile=default.profdata --format=html > coverage.html
#
#    COMMAND ${LLVM_COV} export ./tester -instr-profile=default.profdata --format=lcov > coverage.info
#    COMMAND ${LCOV} --summary coverage.info
#    COMMAND ${GENHTML} --branch-coverage coverage.info --output-directory html
#
#    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
#    COMMENT "collect coverage"
#)
#add_dependencies(check_coverage tester)
#
#add_custom_target(check_coverage_fast
#    COMMAND tester ${CORPUS_DIRECTORY}/*
#    COMMAND ${LLVM_PROFDATA} merge -sparse default.profraw -o default.profdata
#    COMMAND ${LLVM_COV} report ./tester -instr-profile=default.profdata
#    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
#    COMMENT "collect coverage"
#)
#add_dependencies(check_coverage_fast tester)
#
#add_custom_target(dump_corpus
#    COMMAND dumper ${CORPUS_DIRECTORY}/*
#    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
#    COMMENT "dump corpus"
#)
#add_dependencies(dump_corpus dumper)
#