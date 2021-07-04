#define private public

#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

namespace nlohmann {
void from_json(const nlohmann::json& j, nlohmann::json::lexer::token_type& t)
{
    t = static_cast<nlohmann::json::lexer::token_type>(j.get<int>());
}
}; // namespace nlohmann

class fuzzer_lexer_scan_string : public fuzzcover::fuzzcover_interface<std::string, nlohmann::json::lexer::token_type>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        test_input_t result = data_provider.ConsumeRemainingBytesAsString();

        if (!result.empty())
        {
            if (result[0] != '\"')
            {
                result.clear();
            }
        }

        return result;
    }

    test_output_t test_function(const test_input_t& value) override
    {
        if (value.empty())
        {
            return nlohmann::json::lexer::token_type::parse_error;
        }

        nlohmann::detail::input_adapter ia(value.data(), value.size());
        nlohmann::detail::lexer<nlohmann::json> l(ia);
        l.get();
        return l.scan_string();
    }
};

MAKE_MAIN(fuzzer_lexer_scan_string)
