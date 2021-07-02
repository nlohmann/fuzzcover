#pragma once

#include "FuzzedDataProvider.h" // (convenience to clients)
#include <cstddef>              // size_t
#include <cstdint>              // uint8_t
#include <cstdlib>              // EXIT_SUCCESS, EXIT_FAILURE, exit
#include <dirent.h>             // readdir, opendir
#include <fstream>              // istream_iterator
#include <iostream>             // cerr, endl
#include <string>               // string
#include <vector>               // vector
#include <nlohmann/json.hpp>    // nlohmann::json

#ifndef FUZZCOVER_NODOCTEST
#define DOCTEST_CONFIG_IMPLEMENT
#define DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#include <doctest/doctest.h> // TEST_CASE, CAPTURE, CHECK_EQ, CHECK_NOTHROW, doctest::Context
#else
// switch off doctest macros
#define TEST_CASE(f) void bogus_function1() { #f; } void bogus_function2()
#define CAPTURE(x)
#define CHECK_EQ(x)
#endif

#ifndef FUZZCOVER_NOFUZZER
// entry point for libfuzzer
extern "C" int LLVMFuzzerRunDriver(int* argc, char*** argv, int (*UserCb)(const uint8_t* Data, size_t Size));
#endif

namespace fuzzcover {

// function to be defined via MAKE_MAIN later to glue the client code with fuzzcover
int fuzz_wrapper(const std::uint8_t* data, std::size_t size);

// function to be defined via MAKE_MAIN later to glue doctest with fuzzcover
void doctest_wrapper();

/*!
 * @brief interface for fuzzcover
 * @tparam TestInput type of the test input
 */
template <class TestInput, class TestOutput = bool>
class fuzzcover_interface
{
  public:
    using test_input_t = TestInput;
    using test_output_t = TestOutput;

    ///////////////////////////////////////////////////////////////////////////

    /*!
     * @brief create a test input from some bytes
     * @param[in] data input bytes
     * @param[in] size number of bytes in @a data
     * @return test input
     */
    virtual test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) = 0;

    /*!
     * @brief execute a test with a given input
     * @param[in] value test input
     * @return test output (unless test_output_t is void)
     */
    virtual test_output_t test_function(const test_input_t& value) = 0;

    ///////////////////////////////////////////////////////////////////////////

    virtual ~fuzzcover_interface() = default;

    /*!
     * @brief function to call from libfuzzer
     * @param[in] data input bytes
     * @param[in] size number of bytes in @a data
     */
    void fuzz(const std::uint8_t* data, std::size_t size)
    {
        test_function(value_from_bytes(data, size));
    }

    /*!
     * @brief handle the command line arguments
     * @param argc the number of arguments
     * @param argv the arguments
     * @return 0 in case of success, any other value otherwise
     */
    int handle_arguments(int argc, char** argv)
    {
        if (argc >= 2)
        {
            std::string current = argv[1];

#ifndef FUZZCOVER_NOFUZZER
            if (current == "--fuzz")
            {
                return LLVMFuzzerRunDriver(&argc, &argv, fuzz_wrapper);
            }
#endif

            if (current == "--test" && argc >= 3)
            {
                test(get_files(argv[2]));
                return EXIT_SUCCESS;
            }

#ifndef FUZZCOVER_NODOCTEST
            if (current == "--check" && argc >= 3)
            {
                std::ifstream input_file(argv[2]);
                tests = nlohmann::json::parse(input_file);
                doctest::Context context;
                context.applyCommandLine(argc, argv);
                return context.run();
            }
#endif

            if (current == "--dump" && argc >= 3)
            {
                if (argc == 3)
                {
                    dump(get_files(argv[2]), std::cout);
                }
                else
                {
                    std::ofstream outfile(argv[3]);
                    dump(get_files(argv[2]), outfile);
                }
                return EXIT_SUCCESS;
            }

            if (current == "--help")
            {
                std::cerr << "usage: " << argv[0] << " ARGUMENTS\n\n";
                std::cerr << "Fuzzcover - test suite generation for C++\n\n"
                          << "arguments:\n"
                             "  --help                                   show this help message and exit\n"
#ifndef FUZZCOVER_NOFUZZER
                             "  --fuzz [LIBFUZZER_OPTION...]             perform fuzzing\n"
#endif
                             "  --dump CORPUS_DIRECTORY [CORPUS_FILE]    dump the corpus files as JSON\n"
                             "  --test CORPUS_DIRECTORY                  run the test function on the corpus\n"
#ifndef FUZZCOVER_NODOCTEST
                             "  --check CORPUS_FILE [DOCTEST_OPTION...]  execute test suite\n"
#endif
                             "\n"
                             "  CORPUS_DIRECTORY  a corpus directory\n"
                             "  CORPUS_FILE       a corpus file in JSON format as created by --dump\n"
#ifndef FUZZCOVER_NOFUZZER
                             "  LIBFUZZER_OPTION  an option for LibFuzzer (e.g., '-help=1')\n"
#endif
#ifndef FUZZCOVER_NODOCTEST
                             "  DOCTEST_OPTION    an option for doctest (e.g., '--help')"
#endif
                          << std::endl;
                return EXIT_SUCCESS;
            }
        }

        std::cerr << "Fuzzcover: unknown or missing argument; call '" << argv[0] << " --help' for more information." << std::endl;
        return EXIT_FAILURE;
    }

    // variable to store parsed tests for the --check option
    static nlohmann::json tests;

    void check()
    {
        for (const auto& entry : tests)
        {
            test_input_t input = entry.at("input");
            test_output_t output = entry.at("output");
            CAPTURE(entry.at("input"));
            CAPTURE(entry.at("output"));
            CAPTURE(entry.at("hash"));
            CHECK_EQ(test_function(input), output);
        }
    }

  private:
    /*!
     * @brief execute the test function for the corpus
     * @param[in] filenames names of the files to read from
     */
    void test(const std::vector<std::string>& filenames)
    {
        for (const auto& filename : filenames)
        {
            static_cast<void>(test_function(value_from_file(filename)));
        }
    }

    /*!
     * @brief dump the content of the corpus
     * @param[in] filenames names of the files to read from
     * @param[in] os stream to dump the corpus to
     */
    void dump(const std::vector<std::string>& filenames, std::ostream& os)
    {
        auto file_count = filenames.size();
        os << "[\n";

        for (const auto& filename : filenames)
        {
            nlohmann::json input = value_from_file(filename);
            nlohmann::json output = test_function(value_from_file(filename));
            nlohmann::json tuple = {{"input", std::move(input)}, {"output", std::move(output)}, {"hash", short_hash(filename)}};
            os << "  " << tuple.dump(-1, ' ', false, nlohmann::json::error_handler_t::ignore);
            if (--file_count != 0)
            {
                os << ",\n";
            }
            else
            {
                os << "\n";
            }
        }
        os << "]" << std::endl;
    }

    /*!
     * @brief abbreviate a file name by a 7-digit hash just as short git commit hashes
     * @param filename filename to abbreviate
     * @return first 7 characters of the basename of @a filename
     */
    static std::string short_hash(const std::string& filename)
    {
        auto slash = filename.find_last_of('/');
        slash = (slash == std::string::npos) ? 0 : slash + 1;
        return filename.substr(slash, 7);
    }

    /*!
     * @brief collect all files names in a given directory
     * @param directory directory to read
     * @return list of file names
     */
    std::vector<std::string> get_files(const char* directory)
    {
        std::vector<std::string> result;

        struct dirent* dir;
        DIR* d = opendir(directory);
        if (d != nullptr)
        {
            while ((dir = readdir(d)) != nullptr)
            {
                if (dir->d_type == DT_REG)
                {
                    result.push_back(std::string(directory) + "/" + dir->d_name);
                }
            }
            closedir(d);
        }

        return result;
    }

    /*!
     * @brief read input from a file (usually from the corpus)
     * @param[in] filename name of the file to read from
     * @return test input
     */
    test_input_t value_from_file(const std::string& filename)
    {
        std::ifstream file(filename, std::ios::binary);
        if (!file)
        {
            std::cerr << "Cannot open file '" << filename << "', aborting." << std::endl;
            std::exit(EXIT_FAILURE);
        }

        file.unsetf(std::ios::skipws);

        file.seekg(0, std::ios::end);
        const auto file_size = file.tellg();
        file.seekg(0, std::ios::beg);

        std::vector<std::uint8_t> bytes;
        bytes.reserve(static_cast<std::size_t>(file_size));
        bytes.insert(bytes.begin(), std::istream_iterator<std::uint8_t>(file),
                     std::istream_iterator<std::uint8_t>());

        return value_from_bytes(bytes.data(), bytes.size());
    }
};

template <class TestInput, class TestOutput>
nlohmann::json fuzzcover_interface<TestInput, TestOutput>::tests;

} // namespace fuzzcover

#define MAKE_MAIN(CLASS_NAME)                                    \
    namespace fuzzcover {                                        \
    int fuzz_wrapper(const std::uint8_t* data, std::size_t size) \
    {                                                            \
        CLASS_NAME instance;                                     \
        instance.fuzz(data, size);                               \
        return 0;                                                \
    }                                                            \
                                                                 \
    void doctest_wrapper()                                       \
    {                                                            \
        CLASS_NAME instance;                                     \
        instance.check();                                        \
    }                                                            \
    }                                                            \
                                                                 \
    TEST_CASE(#CLASS_NAME)                                       \
    {                                                            \
        fuzzcover::doctest_wrapper();                            \
    }                                                            \
                                                                 \
    int main(int argc, char** argv)                              \
    {                                                            \
        CLASS_NAME instance;                                     \
        return instance.handle_arguments(argc, argv);            \
    }

// clean up
#ifdef DOCTEST_CONFIG_IMPLEMENT
#undef DOCTEST_CONFIG_IMPLEMENT
#endif
#ifdef DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#undef DOCTEST_CONFIG_SUPER_FAST_ASSERTS
#endif
