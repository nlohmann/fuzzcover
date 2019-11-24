#pragma once

#define private public

#include <algorithm>
#include <tuple>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_serializer_dump_integer : public fuzzcover::fuzzcover_interface<std::int64_t>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        std::int64_t result = 0;

        if (size >= sizeof(std::int64_t))
        {
            std::memcpy(&result, data, sizeof(std::int64_t));
        }

        return result;
    }

    void test_function(const test_input_t& value) override
    {
        std::string str;
        nlohmann::detail::output_adapter<char> oa(str);
        nlohmann::detail::serializer<nlohmann::json> s(oa, ' ');
        s.dump_integer(value);
    }
};
