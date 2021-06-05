#define private public

#include <cmath>
#include <cstring>
#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_lexer_scan_number : public fuzzcover::fuzzcover_interface<std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        test_input_t result = data_provider.ConsumeRemainingBytesAsString();

        if (!result.empty())
        {
            if (!isdigit(result[0]) and result[0] != '-')
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
        l.scan_number();
    }
};

MAKE_MAIN(fuzzer_lexer_scan_number)
