#include "fuzzer_lexer_scan_number.hpp"

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size)
{
    fuzzer_lexer_scan_number().fuzz(data, size);
    return 0;
}
