#pragma once

#define private public

#include <fuzzcover/fuzzcover.hpp>
#include "picohash.h"

class picohash_sha256 : public fuzzcover::fuzzcover_interface<std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeRemainingBytesAsString();
    }

    void test_function(const test_input_t& value) override
    {
        picohash_ctx_t ctx;
        char digest[PICOHASH_SHA256_DIGEST_LENGTH];

        picohash_init_sha256(&ctx);
        picohash_update(&ctx, value.c_str(), value.size());
        picohash_final(&ctx, digest);
    }
};
