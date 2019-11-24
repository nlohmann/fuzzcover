#include "fuzzer_lexer_scan_number.hpp"

int main(int argc, char* argv[])
{
    fuzzer_lexer_scan_number().dump(std::vector<std::string>(argv + 1, argv + argc));
}
