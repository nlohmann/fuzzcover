#include <cmath>
#include <cstring>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_to_chars : public fuzzcover::fuzzcover_interface<double>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        const auto value = data_provider.ConsumeFloatingPoint<double>();
        return std::isfinite(value) ? value : 0.0;
    }

    void test_function(const test_input_t& value) override
    {
        char buffer[100];
        nlohmann::detail::to_chars(std::begin(buffer), std::end(buffer), value);
    }
};

MAKE_MAIN(fuzzer_to_chars)
