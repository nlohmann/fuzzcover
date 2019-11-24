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
        std::string result(data, data + size);

        bool ensure_ascii = false;
        nlohmann::detail::error_handler_t error_handler = nlohmann::detail::error_handler_t::ignore;

        if (size > 0)
        {
            ensure_ascii = data[0] % 2;

            switch (data[0] % 3)
            {
                case 0:
                    error_handler = nlohmann::detail::error_handler_t::ignore;
                    break;
                case 1:
                    error_handler = nlohmann::detail::error_handler_t::replace;
                    break;
                case 2:
                    error_handler = nlohmann::detail::error_handler_t::strict;
                    break;
            }
        }

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
