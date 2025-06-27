#!/usr/bin/env python3

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from collections import namedtuple
from typing import Optional

import colorful as cf
import questionary
from tqdm import tqdm

CorpusSize = namedtuple("CorpusSize", ["files", "bytes"])
CoverageInformation = namedtuple("CoverageInformation", ["lines", "branches"])

CORPUS_DIRECTORY = "corpus"
FUZZCOVER_BINARY = ""
LAST_COVERAGE = None  # type: Optional[CoverageInformation]
LAST_CORPUS_SIZE = None  # type: Optional[CorpusSize]


#############################################################################
# helpers
#############################################################################


def check_coverage(corpus_directory: str) -> CoverageInformation:
    """
    calculate coverage information
    :param corpus_directory: directory to use as input for the fuzzcover binary
    :return: line and branch coverage
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        profraw_file = os.path.join(temp_dir, "coverage.profraw")
        profdata_file = os.path.join(temp_dir, "coverage.profdata")

        env = dict(os.environ, LLVM_PROFILE_FILE=profraw_file)
        subprocess.check_output([FUZZCOVER_BINARY, "--test", corpus_directory], env=env)
        subprocess.check_output(
            ["llvm-profdata", "merge", "-sparse", profraw_file, "-o", profdata_file]
        )
        output = subprocess.check_output(
            ["llvm-cov", "report", FUZZCOVER_BINARY, "-instr-profile=" + profdata_file]
        )

        for line in output.decode("utf-8").splitlines():
            if line.startswith("TOTAL"):
                (
                    _,
                    _,
                    _,
                    _,
                    _,
                    _,
                    _,
                    lines,
                    missed_lines,
                    _,
                    branches,
                    missed_branches,
                    _,
                ) = line.split()
                return CoverageInformation(
                    lines=int(lines) - int(missed_lines),
                    branches=int(branches) - int(missed_branches),
                )


def corpus_size() -> CorpusSize:
    """
    determine corpus size
    :return: number of files and bytes of corpus
    """
    total_size = 0
    for file in os.listdir(CORPUS_DIRECTORY):
        total_size += os.path.getsize(os.path.join(CORPUS_DIRECTORY, file))
    return CorpusSize(files=len(os.listdir(CORPUS_DIRECTORY)), bytes=total_size)


def format_integer(i: int) -> str:
    s = "{i:+d}".format(i=i)
    if i == 0:
        return s
    else:
        return cf.bold_white(s)


def overview():
    """
    display program banner with corpus and coverage information
    """
    global LAST_COVERAGE
    global LAST_CORPUS_SIZE

    print(cf.bold_orange(r""" _____                                     """))
    print(cf.bold_orange(r"""|  ___|   _ ___________ _____   _____ _ __ """))
    print(cf.bold_orange(r"""| |_ | | | |_  /_  / __/ _ \ \ / / _ \ '__|"""))
    print(cf.bold_orange(r"""|  _|| |_| |/ / / / (_| (_) \ V /  __/ |   """))
    print(cf.bold_orange(r"""|_|   \__,_/___/___\___\___/ \_/ \___|_|   """))
    print(cf.bold_orange(r"""                                           """))

    print("Fuzzcover binary:", os.path.relpath(FUZZCOVER_BINARY))

    current_corpus_size = corpus_size()
    if LAST_CORPUS_SIZE:
        diff_files = current_corpus_size.files - LAST_CORPUS_SIZE.files
        diff_bytes = current_corpus_size.bytes - LAST_CORPUS_SIZE.bytes

        print(
            "Corpus: {name}, {files} files ({diff_files}), {bytes} bytes ({diff_bytes})".format(
                name=CORPUS_DIRECTORY,
                files=current_corpus_size.files,
                diff_files=format_integer(diff_files),
                bytes=current_corpus_size.bytes,
                diff_bytes=format_integer(diff_bytes),
            )
        )
    else:
        print(
            "Corpus: {name}, {files} files, {bytes} bytes".format(
                name=CORPUS_DIRECTORY,
                files=current_corpus_size.files,
                bytes=current_corpus_size.bytes,
            )
        )

    current_coverage = check_coverage(CORPUS_DIRECTORY)
    if LAST_COVERAGE:
        diff_lines = current_coverage.lines - LAST_COVERAGE.lines
        diff_branches = current_coverage.branches - LAST_COVERAGE.branches

        print(
            "Coverage: {line} lines ({diff_lines}), {branch} branches ({diff_branches})".format(
                line=current_coverage.lines,
                branch=current_coverage.branches,
                diff_lines=format_integer(diff_lines),
                diff_branches=format_integer(diff_branches),
            )
        )
    else:
        print(
            "Coverage: {line} lines, {branch} branches".format(
                line=current_coverage.lines, branch=current_coverage.branches
            )
        )
    print()

    LAST_COVERAGE = current_coverage
    LAST_CORPUS_SIZE = current_corpus_size


def delete_corpus():
    shutil.rmtree(CORPUS_DIRECTORY)
    os.mkdir(CORPUS_DIRECTORY)


#############################################################################
# reduction of corpus
#############################################################################


def merge_corpus():
    """
    call merge option from libfuzz to remove some unneeded corpus files
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(
            os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, "default.profraw")
        )
        subprocess.check_output(
            [FUZZCOVER_BINARY, "--fuzz", temp_dir, CORPUS_DIRECTORY, "-merge=1"],
            stderr=subprocess.STDOUT,
            env=env,
        )
        shutil.rmtree(CORPUS_DIRECTORY)
        shutil.move(temp_dir, CORPUS_DIRECTORY)
        os.remove(os.path.join(CORPUS_DIRECTORY, "default.profraw"))


def reduce_files_additive(quiet=False):
    """
    find a subset of the corpus with the same coverage
    """
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    last_coverage = CoverageInformation(lines=0, branches=0)
    removed_files = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        # prefer small files by checking them first
        files = sorted(
            glob.glob(os.path.join(CORPUS_DIRECTORY, "*")),
            key=lambda file: os.path.getsize(file),
        )

        with tqdm(
            total=len(files),
            unit="files",
            leave=False,
            desc="pass 1 (additive)   ",
            disable=quiet,
        ) as pbar:
            for file in files:
                # copy file to new corpus directory and check coverage
                shutil.copy(file, temp_dir)
                new_coverage = check_coverage(temp_dir)
                pbar.update(1)

                if new_coverage > last_coverage:
                    last_coverage = new_coverage
                else:
                    # coverage did not improve: remove the current file
                    removed_files += 1
                    pbar.set_postfix(reduction=removed_files)
                    os.remove(os.path.join(temp_dir, os.path.basename(file)))

                # maximal coverage reached: we can skip all remaining files
                if new_coverage == full_coverage:
                    shutil.rmtree(CORPUS_DIRECTORY)
                    shutil.move(temp_dir, CORPUS_DIRECTORY)
                    pbar.set_postfix(reduction=removed_files, refresh=False)
                    pbar.update(pbar.total - pbar.n)
                    return


def reduce_files_subtractive(quiet=False):
    """
    remove files from the corpus while preserving coverage
    """
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    removed_files = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        files = glob.glob(os.path.join(CORPUS_DIRECTORY, "*"))
        with tqdm(
            total=len(files),
            unit="files",
            leave=False,
            desc="pass 2 (subtractive)",
            disable=quiet,
        ) as pbar:
            for file in files:
                shutil.move(file, temp_dir)
                new_coverage = check_coverage(CORPUS_DIRECTORY)
                pbar.update(1)
                if new_coverage < full_coverage:
                    # put file back
                    shutil.move(
                        os.path.join(temp_dir, os.path.basename(file)), CORPUS_DIRECTORY
                    )
                else:
                    removed_files += 1
                    pbar.set_postfix(reduction=removed_files, refresh=True)


def reduce_file_length(quiet=False):
    """
    reduce the file lengths of the corpus while preserving coverage
    """
    bytes_saved_by_reduction = 0
    current_coverage = check_coverage(CORPUS_DIRECTORY)

    with tqdm(
        total=corpus_size().bytes,
        unit="bytes",
        leave=False,
        desc="pass 3 (size)       ",
        disable=quiet,
    ) as pbar:
        files = os.listdir(CORPUS_DIRECTORY)
        for filename in files:
            # read content
            source_path = os.path.join(CORPUS_DIRECTORY, filename)
            file_content = open(source_path, "rb").read()
            file_size = len(file_content)
            original_size = file_size
            reduction = 0

            # iteratively remove bytes
            while file_size > 1:
                # write truncated file
                new_file_size = file_size - 1
                open(source_path, "wb").write(file_content[0:new_file_size])

                # determine new coverage
                new_coverage = check_coverage(CORPUS_DIRECTORY)

                if new_coverage < current_coverage:
                    # restore file content
                    open(source_path, "wb").write(file_content[0:file_size])
                    break

                # update size
                file_size = new_file_size
                bytes_saved_by_reduction += 1
                reduction += 1
                pbar.set_postfix(reduction=bytes_saved_by_reduction, refresh=False)
                pbar.update(1)

            pbar.update(original_size - reduction)


def reduce_corpus(quiet=False):
    try:
        merge_corpus()
        reduce_files_additive(quiet)
        reduce_files_subtractive(quiet)
        reduce_file_length(quiet)
    except KeyboardInterrupt:
        pass


#############################################################################
# dump corpus
#############################################################################


def dump(filename=None):
    """
    dump corpus content
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(
            os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, "default.profraw")
        )
        call = [FUZZCOVER_BINARY, "--dump", CORPUS_DIRECTORY]

        if filename:
            call.append(filename)

        subprocess.run(call, env=env)

        if filename:
            print(
                "Saved corpus to {filename}.".format(filename=cf.bold_white(filename))
            )


#############################################################################
# show coverage report
#############################################################################


def show_coverage(open_browser=True):
    """
    create coverage report and open it in default browser
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        profraw_file = os.path.join(temp_dir, "coverage.profraw")
        profdata_file = os.path.join(temp_dir, "coverage.profdata")
        html_output_dir = CORPUS_DIRECTORY + "_coverage"

        # Run the binary with coverage profiling
        env = dict(os.environ, LLVM_PROFILE_FILE=profraw_file)
        subprocess.check_call([FUZZCOVER_BINARY, "--test", CORPUS_DIRECTORY], env=env)

        # Merge raw profile data
        subprocess.check_call(
            ["llvm-profdata", "merge", "-sparse", profraw_file, "-o", profdata_file]
        )

        # Generate HTML report using llvm-cov show
        subprocess.check_call(
            [
                "llvm-cov",
                "show",
                FUZZCOVER_BINARY,
                f"-instr-profile={profdata_file}",
                "-format=html",
                f"-output-dir={html_output_dir}",
                "-show-branches=percent",  # Optional: can adjust granularity
                "-show-line-counts-or-regions",
            ]
        )

        # Open index.html in default browser
        if open_browser:
            index_path = os.path.realpath(os.path.join(html_output_dir, "index.html"))
            webbrowser.get().open_new(f"file://{index_path}")


#############################################################################
# call fuzzer
#############################################################################


def fuzz(max_total_time=0, runs=-1, only_ascii=False, max_len=0, quiet=False, jobs=0):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = dict(
                os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, "default.profraw")
            )
            call = [
                FUZZCOVER_BINARY,
                "--fuzz",
                CORPUS_DIRECTORY,
                "-max_total_time=" + str(max_total_time),
                "-runs=" + str(runs),
                "-only_ascii=1" if only_ascii else "-only_ascii=0",
                f"-jobs={jobs}",
                #'-use_value_profile=1',
                #'-print_final_stats=1',
                #'-len_control=100000', # only slowly increase input length
                "-max_len=" + str(max_len),
            ]

            stdout = subprocess.DEVNULL if quiet else None
            stderr = subprocess.DEVNULL if quiet else None

            subprocess.run(call, env=env, stdout=stdout, stderr=stderr)
    except KeyboardInterrupt:
        return


#############################################################################
# I'm feeling lucky
#############################################################################


def lucky():
    print("Creating corpus with default arguments...")
    delete_corpus()
    fuzz(max_total_time=10, only_ascii=True, quiet=True)
    reduce_corpus()
    dump(filename=os.path.basename(FUZZCOVER_BINARY) + ".json")


#############################################################################
# menus
#############################################################################


def fuzz_menu():
    """
    ask for fuzzing options and execute fuzzcover binary
    """
    max_total_time = questionary.text(
        "The maximal time the fuzzer should run in seconds (0 means forever)",
        default="30",
    ).ask()

    runs = questionary.text(
        "The maximal fuzzer runs (-1 means infinite)", default="-1"
    ).ask()

    jobs = questionary.text(
        "The number of parallel fuzz jobs (0 means no concurrency)", default="0"
    ).ask()

    max_len = questionary.text(
        "The maximal length for generated inputs in bytes (0 means no limit)",
        default="0",
    ).ask()

    only_ascii = questionary.confirm(
        "Only create ASCII characters?", default=False
    ).ask()

    fuzz(
        max_total_time=int(max_total_time),
        runs=int(runs),
        only_ascii=only_ascii,
        max_len=int(max_len),
        jobs=jobs,
    )


def main_menu():
    """
    display main menu and call selected functions
    """
    while True:
        overview()

        choice = questionary.select(
            "What do you want?",
            choices=[
                "Start fuzzing",
                "Reduce corpus",
                "Dump corpus",
                "Save corpus to JSON file",
                "Show coverage",
                "Clear corpus",
                "I'm feeling lucky",
                "Quit",
            ],
        ).ask()

        if choice == "Quit":
            sys.exit(0)

        elif choice == "Start fuzzing":
            fuzz_menu()
            show_coverage(open_browser=False)

        elif choice == "Dump corpus":
            dump(filename=None)

        elif choice == "Save corpus to JSON file":
            dump(filename=os.path.basename(FUZZCOVER_BINARY) + ".json")

        elif choice == "Show coverage":
            show_coverage()

        elif choice == "Reduce corpus":
            reduce_corpus()
            show_coverage(open_browser=False)

        elif choice == "Clear corpus":
            confirm = questionary.confirm(
                "Do you really want to clear the corpus directory?", default=False
            ).ask()
            if confirm:
                delete_corpus()

        elif choice == "I'm feeling lucky":
            lucky()
            show_coverage(open_browser=False)

        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fuzzcover - test suite generation for C++"
    )
    parser.add_argument(
        "binary",
        metavar="FUZZER_BINARY",
        type=str,
        help="The binary linked to the fuzzcover library.",
    )
    parser.add_argument(
        "corpus",
        metavar="CORPUS_DIRECTORY",
        type=str,
        nargs="?",
        help="The directory of the corpus. If not provided, the name of the corpus directory will be "
        "derived from the name of the fuzzer binary. The directory will be created if it does not "
        "exist.",
    )
    parser.add_argument(
        "--lucky",
        action="store_true",
        help="Create a test suite without user interaction.",
    )
    args = parser.parse_args()

    try:
        subprocess.check_output(["llvm-profdata", "--help"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red("WARNING: The tool llvm-profdata was not found in the PATH!"))
    try:
        subprocess.check_output(["llvm-cov", "--version"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red("WARNING: The tool llvm-cov was not found in the PATH!"))
    try:
        subprocess.check_output(
            ["llvm-profdata", "--version"], stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        print(cf.bold_red("WARNING: The tool llvm-profdata was not found in the PATH!"))
    try:
        subprocess.check_output(["llvm-cov", "--version"], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red("WARNING: The tool llvm-cov was not found in the PATH!"))

    # process command line parameters
    FUZZCOVER_BINARY = os.path.abspath(args.binary)
    CORPUS_DIRECTORY = (
        args.corpus if args.corpus else os.path.basename(FUZZCOVER_BINARY) + "_corpus"
    )

    # create corpus directory if it does not exist
    if not os.path.isdir(CORPUS_DIRECTORY):
        os.mkdir(CORPUS_DIRECTORY)

    if args.lucky:
        lucky()
    else:
        main_menu()
