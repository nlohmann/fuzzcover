#include <fuzzcover/fuzzcover.hpp>
#include "picohash.h"

class picohash_sha1 : public fuzzcover::fuzzcover_interface<std::string>
{
  public:
    test_input_t value_from_bytes(const std::uint8_t* data, std::size_t size) override
    {
        FuzzedDataProvider data_provider(data, size);
        return data_provider.ConsumeRemainingBytesAsString();
    }

    test_output_t test_function(const test_input_t& value) override
    {
        picohash_ctx_t ctx;
        char digest[PICOHASH_SHA1_DIGEST_LENGTH];

        picohash_init_sha1(&ctx);
        picohash_update(&ctx, value.c_str(), value.size());
        picohash_final(&ctx, digest);
        return true;
    }
};

MAKE_MAIN(picohash_sha1)
