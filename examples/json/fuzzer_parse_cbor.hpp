#pragma once

#define private public

#include <cmath>
#include <cstring>
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

    void test_function(const test_input_t& value) override
    {
        try {
            nlohmann::json::from_cbor(value);
        } catch (...) {}
    }
};
