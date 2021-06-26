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

// entry point for libfuzzer
extern "C" int LLVMFuzzerRunDriver(int* argc, char*** argv, int (*UserCb)(const uint8_t* Data, size_t Size));

namespace fuzzcover {

// function to be defined via MAKE_MAIN later to glue the client code with fuzzcover
int fuzz_wrapper(const std::uint8_t* data, std::size_t size);

/*!
 * @brief interface for fuzzcover
 * @tparam TestInput type of the test input
 */
template <class TestInput>
class fuzzcover_interface
{
  public:
    using test_input_t = TestInput;

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
     */
    virtual void test_function(const test_input_t& value) = 0;

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
     * @brief execute the test function for the corpus
     * @param[in] filenames names of the files to read from
     */
    void test(const std::vector<std::string>& filenames)
    {
        for (const auto& filename : filenames)
        {
            test_function(value_from_file(filename));
        }
    }

    /*!
     * @brief dump the content of the corpus
     * @param[in] filenames names of the files to read from
     */
    void dump(const std::vector<std::string>& filenames)
    {
        for (const auto& filename : filenames)
        {
            std::cout
                << filename
                << ": "
                << nlohmann::json(value_from_file(filename)).dump(-1, ' ', false, nlohmann::json::error_handler_t::ignore)
                << '\n';
        }
        std::cout << std::flush;
    }

    int handle_arguments(int argc, char** argv)
    {
        if (argc >= 2)
        {
            std::string current = argv[1];

            if (current == "--fuzz")
            {
                return LLVMFuzzerRunDriver(&argc, &argv, fuzz_wrapper);
            }

            if (current == "--test")
            {
                test(get_files(argv[2]));
                return EXIT_SUCCESS;
            }

            if (current == "--dump")
            {
                dump(get_files(argv[2]));
                return EXIT_SUCCESS;
            }

            if (current == "--help")
            {
                std::cerr << "usage: " << argv[0] << " ARGUMENTS\n\n";
                std::cerr << "Fuzzcover - test suite generation for C++\n\n"
                          << "arguments:\n"
                             "  --help                   show this help message and exit\n"
                             "  --fuzz [OPTION...]       perform fuzzing\n"
                             "  --dump CORPUS_DIRECTORY  dump the corpus files as JSON\n"
                             "  --test CORPUS_DIRECTORY  run the test function on the corpus files\n"
                             "\n"
                             "  CORPUS_DIRECTORY  the corpus directory\n"
                             "  OPTION            an option for Libfuzzer (e.g., '-help=1' for more information)"
                          << std::endl;
                return EXIT_SUCCESS;
            }
        }

        std::cerr << "fuzzcover: unknown or missing argument; call '" << argv[0] << " --help' for more information." << std::endl;
        return EXIT_FAILURE;
    }

  private:
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

} // namespace fuzzcover

#define MAKE_MAIN(CLASSNAME)                                     \
    namespace fuzzcover {                                        \
    int fuzz_wrapper(const std::uint8_t* data, std::size_t size) \
    {                                                            \
        CLASSNAME instance;                                      \
        instance.fuzz(data, size);                               \
        return 0;                                                \
    }                                                            \
    }                                                            \
                                                                 \
    int main(int argc, char** argv)                              \
    {                                                            \
        CLASSNAME instance;                                      \
        return instance.handle_arguments(argc, argv);            \
    }
