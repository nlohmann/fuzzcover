#include <fuzzcover/fuzzcover.hpp>
#include "iban.hpp"

class iban_fuzz : public fuzzcover::fuzzcover_interface<std::string, bool>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeRemainingBytesAsString();
    }

    test_output_t test_function(const test_input_t& value) override
    {
        return is_valid_iban(value);
    }
};

MAKE_MAIN(iban_fuzz)
