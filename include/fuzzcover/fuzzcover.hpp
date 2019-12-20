#pragma once

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <type_traits>
#include <vector>
#include <nlohmann/json.hpp>
#include "FuzzedDataProvider.h"

namespace fuzzcover {

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
    virtual test_input_t value_from_bytes(const std::uint8_t* data,
                                          std::size_t size) = 0;

    /*!
     * @brief execute a test with a given input
     * @param[in] value test input
     */
    virtual void test_function(const test_input_t& value) = 0;

    ///////////////////////////////////////////////////////////////////////////

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
        for (const auto& input : read_from_files(filenames))
        {
            test_function(input);
        }
    }

    /*!
     * @brief dump the content of the corpus
     * @param[in] filenames names of the files to read from
     */
    void dump(const std::vector<std::string>& filenames)
    {
        const auto inputs = read_from_files(filenames);
        for (std::size_t i = 0; i < filenames.size(); ++i)
        {
            std::cout
                << filenames[i]
                << ": "
                << nlohmann::json(inputs[i]).dump(-1, ' ', false, nlohmann::json::error_handler_t::ignore)
                << std::endl;
        }
    }

    virtual ~fuzzcover_interface() = default;

  private:
    /*!
     * @brief read input from a file (usually from the corpus)
     * @param[in] filename name of the file to read from
     * @return test input
     */
    test_input_t read_from_file(const std::string& filename)
    {
        std::ifstream file(filename, std::ios::binary);
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

    /*!
     * @brief read inputs from files (usually from the corpus)
     * @param[in] filenames names of the files to read from
     * @return test inputs
     */
    std::vector<test_input_t> read_from_files(const std::vector<std::string>& filenames)
    {
        std::vector<test_input_t> result;
        result.reserve(filenames.size());
        for (const auto& file : filenames)
        {
            result.push_back(read_from_file(file));
        }
        return result;
    }
};

} // namespace fuzzcover
