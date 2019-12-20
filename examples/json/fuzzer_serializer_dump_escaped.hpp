#pragma once

#define private public

#include <algorithm>
#include <string>
#include <tuple>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_serializer_dump_escaped : public fuzzcover::fuzzcover_interface<std::tuple<std::string, bool, nlohmann::detail::error_handler_t>>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        const auto ensure_ascii = data_provider.ConsumeBool();
        const auto error_handler_int = data_provider.ConsumeIntegralInRange<std::uint8_t>(0, 2);
        const auto str = data_provider.ConsumeRemainingBytesAsString();

        nlohmann::detail::error_handler_t error_handler = [error_handler_int] {
            switch (error_handler_int)
            {
                case 0:
                    return nlohmann::detail::error_handler_t::ignore;
                case 1:
                    return nlohmann::detail::error_handler_t::replace;
                default:
                    return nlohmann::detail::error_handler_t::strict;
            }
        }();

        return {str, ensure_ascii, error_handler};
    }

    void test_function(const test_input_t& value) override
    {
        std::string str;
        nlohmann::detail::output_adapter<char> oa(str);
        nlohmann::detail::serializer<nlohmann::json> s(oa, ' ', std::get<2>(value));
        try
        {
            s.dump_escaped(std::get<0>(value), std::get<1>(value));
        }
        catch (...)
        {}
    }
};
