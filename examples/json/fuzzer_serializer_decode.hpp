#pragma once

#define private public

#include <algorithm>
#include <set>
#include <tuple>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_serializer_decode : public fuzzcover::fuzzcover_interface<std::tuple<std::uint8_t, std::uint32_t, std::uint8_t, bool>>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        std::uint8_t state = 0;
        std::uint32_t codep = 0;
        std::uint8_t byte = 0;

        if (size >= sizeof(std::uint8_t) + sizeof(std::uint32_t) + sizeof(std::uint8_t))
        {
            std::memcpy(&state, data, sizeof(std::uint8_t));
            std::memcpy(&codep, data + sizeof(std::uint8_t), sizeof(std::uint32_t));
            std::memcpy(&byte, data + sizeof(std::uint8_t) + sizeof(std::uint32_t), sizeof(std::uint8_t));

            state = state % 0xC;
            codep = codep % 0x11000U;

            return {state, codep, byte, true};
        }

        return {0, 0, 0, false};
    }

    void test_function(const test_input_t& value) override
    {
        if (std::get<3>(value) == false)
        {
            return;
        }

        std::uint8_t state = std::get<0>(value);
        std::uint32_t codep = std::get<1>(value);
        std::uint8_t byte = std::get<2>(value);

        // reuse state as long as we do not see a repeating state
        std::set<std::uint8_t> states_seen;
        while (true)
        {
            state = nlohmann::detail::serializer<nlohmann::json>::decode(state, codep, byte);
            auto add_state = states_seen.insert(state);
            if (!add_state.second)
            {
                break;
            }
        }
    }
};
