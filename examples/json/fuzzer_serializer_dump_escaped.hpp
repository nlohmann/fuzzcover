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

        return {std::string(reinterpret_cast<const char*>(data), size), ensure_ascii, error_handler};
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
