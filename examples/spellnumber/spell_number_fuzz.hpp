#pragma once

#define private public

#include "spell_number.hpp"
#include <fuzzcover/fuzzcover.hpp>

class roman_fuzz : public fuzzcover::fuzzcover_interface<unsigned long>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeIntegralInRange<unsigned long>(0, 1000000000);
    }

    void test_function(const test_input_t& value) override
    {
        spell(value);
    }
};
