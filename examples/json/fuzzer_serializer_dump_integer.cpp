#define private public

#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

class fuzzer_serializer_dump_integer : public fuzzcover::fuzzcover_interface<std::int64_t, std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeIntegral<std::int64_t>();
    }

    test_output_t test_function(const test_input_t& value) override
    {
        std::string str;
        nlohmann::detail::output_adapter<char> oa(str);
        nlohmann::detail::serializer<nlohmann::json> s(oa, ' ');
        s.dump_integer(value);
        return str;
    }
};

MAKE_MAIN(fuzzer_serializer_dump_integer)
