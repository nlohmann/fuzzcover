#define private public

#include <algorithm>
#include <set>
#include <tuple>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_serializer_decode : public fuzzcover::fuzzcover_interface<std::tuple<std::uint8_t, std::uint32_t, std::uint8_t>, std::set<std::uint8_t>>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);

        const auto state = data_provider.ConsumeIntegral<std::uint8_t>();
        const auto codep = data_provider.ConsumeIntegral<std::uint32_t>();
        const auto byte = data_provider.ConsumeIntegral<std::uint8_t>();

        return {state, codep, byte};
    }

    test_output_t test_function(const test_input_t& value) override
    {
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

        return states_seen;
    }
};

MAKE_MAIN(fuzzer_serializer_decode)
