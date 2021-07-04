#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_parse : public fuzzcover::fuzzcover_interface<std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeRemainingBytesAsString();
    }

    test_output_t test_function(const test_input_t& value) override
    {
        try
        {
            auto j = nlohmann::json::parse(value);
            return true;
        }
        catch (...)
        {
            return false;
        }
    }
};

MAKE_MAIN(fuzzer_parse)
