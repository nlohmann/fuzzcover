#pragma once

#define private public

#include <cmath>
#include <cstring>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_roundtrip_string : public fuzzcover::fuzzcover_interface<std::tuple<std::string, nlohmann::json::error_handler_t, bool>>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);

        const auto ensure_ascii = data_provider.ConsumeBool();
        const auto error_handler_int = data_provider.ConsumeIntegralInRange(0,2);
        const auto result = data_provider.ConsumeRemainingBytesAsString();

        nlohmann::json::error_handler_t error_handler = [error_handler_int]() {
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

        return {result, error_handler, ensure_ascii};
    }

    void test_function(const test_input_t& value) override
    {
        try
        {
            nlohmann::json(std::get<0>(value)).dump(-1, ' ', std::get<2>(value), std::get<1>(value));
        }
        catch (...)
        {}
    }
};
