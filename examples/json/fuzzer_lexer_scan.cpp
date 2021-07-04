#define private public

#include <fuzzcover/fuzzcover.hpp>
#include <nlohmann/json.hpp>

namespace nlohmann {
void from_json(const nlohmann::json& j, nlohmann::json::lexer::token_type& t)
{
    t = static_cast<nlohmann::json::lexer::token_type>(j.get<int>());
}
}; // namespace nlohmann

class fuzzer_lexer_scan : public fuzzcover::fuzzcover_interface<std::string, nlohmann::json::lexer::token_type>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeRemainingBytesAsString();
    }

    test_output_t test_function(const test_input_t& value) override
    {
        if (value.empty())
        {
            return nlohmann::json::lexer::token_type::uninitialized;
        }

        nlohmann::detail::input_adapter ia(value.data(), value.size());
        nlohmann::detail::lexer<nlohmann::json> l(ia);
        l.get();
        return l.scan();
    }
};

MAKE_MAIN(fuzzer_lexer_scan)
