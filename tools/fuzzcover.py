#!/usr/bin/env python3

import argparse
import glob
import os
import shutil
import sys
import subprocess
import tempfile
from typing import Optional
from PyInquirer import prompt
from tqdm import tqdm
import webbrowser
from collections import namedtuple
import colorful as cf

CorpusSize = namedtuple('CorpusSize', ['files', 'bytes'])
CoverageInformation = namedtuple('CoverageInformation', ['lines', 'branches'])

CORPUS_DIRECTORY = 'corpus'
FUZZCOVER_BINARY = ''
LAST_COVERAGE = None  # type: Optional[CoverageInformation]
LAST_CORPUS_SIZE = None  # type: Optional[CorpusSize]


def reduce_files_additive():
    """
    find a subset of the corpus with the same coverage
    """
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    last_coverage = CoverageInformation(lines=0, branches=0)
    removed_files = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        # prefer small files by checking them first
        files = sorted(glob.glob(os.path.join(CORPUS_DIRECTORY, '*')), key=lambda file: os.path.getsize(file))

        with tqdm(total=len(files), unit="files", leave=False, desc='pass 1 (additive)   ') as pbar:
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


def reduce_files_subtractive():
    """
    remove files from the corpus while preserving coverage
    """
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    removed_files = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        files = glob.glob(os.path.join(CORPUS_DIRECTORY, '*'))
        with tqdm(total=len(files), unit="files", leave=False, desc='pass 2 (subtractive)') as pbar:
            for file in files:
                shutil.move(file, temp_dir)
                new_coverage = check_coverage(CORPUS_DIRECTORY)
                pbar.update(1)
                if new_coverage < full_coverage:
                    # put file back
                    shutil.move(os.path.join(temp_dir, os.path.basename(file)), CORPUS_DIRECTORY)
                else:
                    removed_files += 1
                    pbar.set_postfix(reduction=removed_files, refresh=True)


def reduce_file_length():
    """
    reduce the file lengths of the corpus while preserving coverage
    """
    bytes_saved_by_reduction = 0
    current_coverage = check_coverage(CORPUS_DIRECTORY)

    with tqdm(total=corpus_size().bytes, unit="bytes", leave=False, desc='pass 3 (size)       ') as pbar:
        files = os.listdir(CORPUS_DIRECTORY)
        for filename in files:
            # read content
            source_path = os.path.join(CORPUS_DIRECTORY, filename)
            file_content = open(source_path, 'rb').read()
            file_size = len(file_content)
            original_size = file_size
            reduction = 0

            # iteratively remove bytes
            while file_size > 1:
                # write truncated file
                new_file_size = file_size - 1
                open(source_path, 'wb').write(file_content[0:new_file_size])

                # determine new coverage
                new_coverage = check_coverage(CORPUS_DIRECTORY)

                if new_coverage < current_coverage:
                    # restore file content
                    open(source_path, 'wb').write(file_content[0:file_size])
                    break

                # update size
                file_size = new_file_size
                bytes_saved_by_reduction += 1
                reduction += 1
                pbar.set_postfix(reduction=bytes_saved_by_reduction, refresh=False)
                pbar.update(1)

            pbar.update(original_size - reduction)


def check_coverage(corpus_directory: str) -> CoverageInformation:
    """
    calculate coverage information
    :param corpus_directory: directory to use as input for the fuzzcover binary
    :return: line and branch coverage
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        profraw_file = os.path.join(temp_dir, 'coverage.profraw')
        profdata_file = os.path.join(temp_dir, 'coverage.profdata')

        env = dict(os.environ, LLVM_PROFILE_FILE=profraw_file)
        subprocess.check_output([FUZZCOVER_BINARY, "--test", corpus_directory], env=env)
        subprocess.check_output(['llvm-profdata', 'merge', '-sparse', profraw_file, '-o', profdata_file])
        output = subprocess.check_output(['llvm-cov', 'report', FUZZCOVER_BINARY, '-instr-profile=' + profdata_file])

        for line in output.decode("utf-8").splitlines():
            if line.startswith('TOTAL'):
                _, _, _, _, _, _, _, lines, missed_lines, _, branches, missed_branches, _ = line.split()
                return CoverageInformation(lines=int(lines) - int(missed_lines),
                                           branches=int(branches) - int(missed_branches))


def merge_corpus():
    """
    call merge option from libfuzz to remove some unneeded corpus files
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
        subprocess.check_output([FUZZCOVER_BINARY, "--fuzz", temp_dir, CORPUS_DIRECTORY, '-merge=1'],
                                stderr=subprocess.STDOUT, env=env)
        shutil.rmtree(CORPUS_DIRECTORY)
        shutil.move(temp_dir, CORPUS_DIRECTORY)
        os.remove(os.path.join(CORPUS_DIRECTORY, 'default.profraw'))


def dump():
    """
    dump corpus content to standard output
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
        call = [FUZZCOVER_BINARY, '--dump', '.']
        subprocess.run(call, env=env, cwd=CORPUS_DIRECTORY)


def show_coverage():
    """
    create coverage report and open it in default browser
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        profraw_file = os.path.join(temp_dir, 'coverage.profraw')
        profdata_file = os.path.join(temp_dir, 'coverage.profdata')
        info_file = os.path.join(temp_dir, 'coverage.info')

        env = dict(os.environ, LLVM_PROFILE_FILE=profraw_file)
        subprocess.check_output([FUZZCOVER_BINARY, "--test", CORPUS_DIRECTORY], env=env)
        subprocess.check_output(['llvm-profdata', 'merge', '-sparse', profraw_file, '-o', profdata_file])
        with open(info_file, "wb") as info_output:
            subprocess.Popen(
                ['llvm-cov', 'export', FUZZCOVER_BINARY, '-instr-profile=' + profdata_file, '--format=lcov'],
                stdout=info_output)
        subprocess.check_output(
            ['genhtml', '--branch-coverage', info_file, '--output-directory', CORPUS_DIRECTORY + '_coverage'])
        webbrowser.get().open_new(
            'file://' + os.path.realpath(os.path.join(CORPUS_DIRECTORY + '_coverage', 'index.html')))


def fuzz():
    """
    ask for fuzzing options and execute fuzzcover binary
    """
    questions = [
        {
            'type': 'input',
            'name': 'max_total_time',
            'message': 'The maximal time the fuzzer should run in seconds (0 means forever)',
            'default': '30'
        },
        {
            'type': 'input',
            'name': 'runs',
            'message': 'The maximal fuzzer runs (-1 means infinite)',
            'default': '-1'
        },
        {
            'type': 'input',
            'name': 'max_len',
            'message': 'The maximal length for generated inputs in bytes (0 means no limit)',
            'default': '0'
        },
        {
            'type': 'confirm',
            'name': 'only_ascii',
            'message': 'Only create ASCII characters',
            'default': False
        }
    ]
    answers = prompt(questions)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
            call = [FUZZCOVER_BINARY, '--fuzz', CORPUS_DIRECTORY,
                    '-max_total_time=' + answers['max_total_time'],
                    '-runs=' + answers['runs'],
                    '-only_ascii=1' if answers['only_ascii'] else '-only_ascii=0',
                    '-max_len=' + answers['max_len']]
            print(' '.join(call))
            subprocess.run(call, env=env)
    except KeyboardInterrupt:
        return


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
    s = '{i:+d}'.format(i=i)
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

    print(cf.bold_orange(''' _____                                     '''))
    print(cf.bold_orange('''|  ___|   _ ___________ _____   _____ _ __ '''))
    print(cf.bold_orange('''| |_ | | | |_  /_  / __/ _ \ \ / / _ \ '__|'''))
    print(cf.bold_orange('''|  _|| |_| |/ / / / (_| (_) \ V /  __/ |   '''))
    print(cf.bold_orange('''|_|   \__,_/___/___\___\___/ \_/ \___|_|   '''))
    print(cf.bold_orange('''                                           '''))

    print('Fuzzcover binary:', os.path.relpath(FUZZCOVER_BINARY))

    current_corpus_size = corpus_size()
    if LAST_CORPUS_SIZE:
        diff_files = current_corpus_size.files - LAST_CORPUS_SIZE.files
        diff_bytes = current_corpus_size.bytes - LAST_CORPUS_SIZE.bytes

        print('Corpus: {name}, {files} files ({diff_files}), {bytes} bytes ({diff_bytes})'.format(
            name=CORPUS_DIRECTORY,
            files=current_corpus_size.files,
            diff_files=format_integer(diff_files),
            bytes=current_corpus_size.bytes,
            diff_bytes=format_integer(diff_bytes)
        ))
    else:
        print('Corpus: {name}, {files} files, {bytes} bytes'.format(
            name=CORPUS_DIRECTORY,
            files=current_corpus_size.files,
            bytes=current_corpus_size.bytes
        ))

    current_coverage = check_coverage(CORPUS_DIRECTORY)
    if LAST_COVERAGE:
        diff_lines=current_coverage.lines - LAST_COVERAGE.lines
        diff_branches=current_coverage.branches - LAST_COVERAGE.branches

        print('Coverage: {line} lines ({diff_lines}), {branch} branches ({diff_branches})'.format(
            line=current_coverage.lines, branch=current_coverage.branches,
            diff_lines=format_integer(diff_lines),
            diff_branches=format_integer(diff_branches)
        ))
    else:
        print('Coverage: {line} lines, {branch} branches'.format(line=current_coverage.lines,
                                                                 branch=current_coverage.branches))
    print()

    LAST_COVERAGE = current_coverage
    LAST_CORPUS_SIZE = current_corpus_size


def main_menu():
    """
    display main menu and call selected functions
    """
    questions = [
        {
            'type': 'list',
            'name': 'main_menu',
            'message': 'What do you want?',
            'choices': ['Start fuzzing', 'Reduce corpus', 'Dump corpus', 'Show coverage', 'Clear corpus', 'Quit']
        }
    ]

    while True:
        overview()
        answers = prompt(questions)

        if answers['main_menu'] == 'Quit':
            sys.exit(0)

        elif answers['main_menu'] == 'Start fuzzing':
            fuzz()

        elif answers['main_menu'] == 'Dump corpus':
            dump()

        elif answers['main_menu'] == 'Show coverage':
            show_coverage()

        elif answers['main_menu'] == 'Reduce corpus':
            try:
                merge_corpus()
                reduce_files_additive()
                reduce_files_subtractive()
                reduce_file_length()
            except KeyboardInterrupt:
                pass

        elif answers['main_menu'] == 'Clear corpus':
            confirm = prompt([{
                'type': 'confirm',
                'message': 'Do you really want to clear the corpus directory?',
                'name': 'clear',
                'default': False,
            }])
            if confirm['clear']:
                shutil.rmtree(CORPUS_DIRECTORY)
                os.mkdir(CORPUS_DIRECTORY)

        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fuzzcover - test suite generation for C++")
    parser.add_argument('binary', metavar='FUZZER_BINARY', type=str, help='The binary linked to the fuzzcover library.')
    parser.add_argument('corpus', metavar='CORPUS_DIRECTORY', type=str, nargs='?',
                        help='The directory of the corpus. If not provided, the name of the corpus directory will be '
                             'derived from the name of the fuzzer binary. The directory will be created if it does not '
                             'exist.')
    args = parser.parse_args()

    try:
        subprocess.check_output(['llvm-profdata', '--help'], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red('WARNING: The tool llvm-profdata was not found in the PATH!'))
    try:
        subprocess.check_output(['llvm-cov', '--version'], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red('WARNING: The tool llvm-cov was not found in the PATH!'))
    try:
        subprocess.check_output(['genhtml', '--version'], stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(cf.bold_red('WARNING: The tool genhtml was not found in the PATH!'))

    # process command line parameters
    FUZZCOVER_BINARY = os.path.abspath(args.binary)
    CORPUS_DIRECTORY = args.corpus if args.corpus else os.path.basename(FUZZCOVER_BINARY) + '_corpus'

    # create corpus directory if it does not exist
    if not os.path.isdir(CORPUS_DIRECTORY):
        os.mkdir(CORPUS_DIRECTORY)

    main_menu()
