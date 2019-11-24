#pragma once

#include <cmath>
#include <cstring>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_to_chars : public fuzzcover::fuzzcover_interface<double>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        double value = 0.0;

        if (size != 8)
        {
            return value;
        }

        std::memcpy(&value, data, sizeof(double));

        if (not std::isfinite(value))
        {
            return 0.0;
        }

        return value;
    }

    void test_function(const test_input_t& value) override
    {
        char buffer[100];
        nlohmann::detail::to_chars(std::begin(buffer), std::end(buffer), value);
    }
};
