#include "json/fuzzer_parse.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size)
{
    fuzzer_parse().fuzz(data, size);
    return 0;
}
