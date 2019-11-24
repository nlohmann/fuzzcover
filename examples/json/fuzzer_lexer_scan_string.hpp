#pragma once

#define private public

#include <cmath>
#include <cstring>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_lexer_scan_string : public fuzzcover::fuzzcover_interface<std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        test_input_t result(data, data + size);

        if (!result.empty())
        {
            if (result[0] != '\"')
            {
                result.clear();
            }
        }

        return result;
    }

    void test_function(const test_input_t& value) override
    {
        if (value.empty())
        {
            return;
        }

        nlohmann::detail::input_adapter ia(value.data(), value.size());
        nlohmann::detail::lexer<nlohmann::json> l(ia);
        l.get();
        l.scan_string();
    }
};
