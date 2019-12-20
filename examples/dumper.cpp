#include "json/fuzzer_parse.hpp"

int main(int argc, char* argv[])
{
    fuzzer_parse().dump(std::vector<std::string>(argv + 1, argv + argc));
}
