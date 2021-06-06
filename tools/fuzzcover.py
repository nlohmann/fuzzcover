#!/usr/bin/env python3

import glob
import os
import shutil
import sys
import subprocess
import tempfile
from typing import Tuple
from PyInquirer import prompt, Separator
from tqdm import tqdm
import webbrowser

CORPUS_DIRECTORY = 'corpus'
FUZZCOVER_BINARY = ''
LAST_COVERAGE = None
LAST_CORPUS_SIZE = None


def reduce_files_additive():
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    last_coverage = (0, 0)
    removed_files = 0
    files = glob.glob(os.path.join(CORPUS_DIRECTORY, '*'))

    with tempfile.TemporaryDirectory() as temp_dir:
        with tqdm(total=len(files), unit="files", leave=False) as pbar:
            pbar.set_description('pass 1 (additive)   ')
            for file in files:
                shutil.copy(file, temp_dir)
                new_coverage = check_coverage(temp_dir)
                pbar.update(1)

                if new_coverage > last_coverage:
                    last_coverage = new_coverage
                else:
                    removed_files += 1
                    pbar.set_postfix(reduction=removed_files)
                    os.remove(os.path.join(temp_dir, os.path.basename(file)))

                if new_coverage == full_coverage:
                    shutil.rmtree(CORPUS_DIRECTORY)
                    shutil.move(temp_dir, CORPUS_DIRECTORY)
                    pbar.set_postfix(reduction=removed_files, refresh=False)
                    pbar.update(pbar.total - pbar.n)
                    return


def reduce_files_subtractive():
    full_coverage = check_coverage(CORPUS_DIRECTORY)
    files = glob.glob(os.path.join(CORPUS_DIRECTORY, '*'))
    removed_files = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        with tqdm(total=len(files), unit="files", leave=False) as pbar:
            pbar.set_description('pass 2 (subtractive)')
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
    corpus_size_without_reduction = 0
    bytes_saved_by_reduction = 0
    files = os.listdir(CORPUS_DIRECTORY)

    with tqdm(total=corpus_size()[1], unit="bytes", leave=False) as pbar:
        pbar.set_description('pass 3 (size)       ')
        for filename in files:
            source_path = os.path.join(CORPUS_DIRECTORY, filename)

            # determine coverage
            line_coverage = check_coverage(CORPUS_DIRECTORY)

            # read content
            file_content = open(source_path, 'rb').read()
            file_size = len(file_content)
            original_size = file_size
            corpus_size_without_reduction += file_size
            reduction = 0

            # iteratively remove bytes
            while file_size > 1:
                # write truncated file
                new_file_size = file_size - 1
                open(source_path, 'wb').write(file_content[0:new_file_size])

                # determine new coverage
                new_line_coverage = check_coverage(CORPUS_DIRECTORY)

                if new_line_coverage < line_coverage:
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


def check_coverage(corpus_directory: str) -> Tuple[int, int]:
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
                return int(lines) - int(missed_lines), int(branches) - int(missed_branches)


def merge_corpus():
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
        subprocess.check_output([FUZZCOVER_BINARY, "--fuzz", temp_dir, CORPUS_DIRECTORY, '-merge=1'],
                                stderr=subprocess.STDOUT, env=env)
        shutil.rmtree(CORPUS_DIRECTORY)
        shutil.move(temp_dir, CORPUS_DIRECTORY)
        os.remove(os.path.join(CORPUS_DIRECTORY, 'default.profraw'))


def dump():
    with tempfile.TemporaryDirectory() as temp_dir:
        env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
        call = [FUZZCOVER_BINARY, '--dump', '.']
        subprocess.run(call, env=env, cwd=CORPUS_DIRECTORY)


def show_coverage():
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
    print(answers)

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            env = dict(os.environ, LLVM_PROFILE_FILE=os.path.join(temp_dir, 'default.profraw'))
            call = [FUZZCOVER_BINARY, '--fuzz', CORPUS_DIRECTORY,
                    '-max_total_time=' + answers['max_total_time'],
                    '-runs=' + answers['runs'],
                    '-only_ascii=1' if answers['only_ascii'] else '-only_ascii=0',
                    '-max_len=' + answers['max_len']]
            subprocess.run(call, env=env)
    except KeyboardInterrupt:
        return


def corpus_size() -> Tuple[int, int]:
    total_size = 0
    for file in os.listdir(CORPUS_DIRECTORY):
        total_size += os.path.getsize(os.path.join(CORPUS_DIRECTORY, file))
    return len(os.listdir(CORPUS_DIRECTORY)), total_size


def overview():
    global LAST_COVERAGE
    global LAST_CORPUS_SIZE

    print(''' _____                                     ''')
    print('''|  ___|   _ ___________ _____   _____ _ __ ''')
    print('''| |_ | | | |_  /_  / __/ _ \ \ / / _ \ '__|''')
    print('''|  _|| |_| |/ / / / (_| (_) \ V /  __/ |   ''')
    print('''|_|   \__,_/___/___\___\___/ \_/ \___|_|   ''')
    print('''                                           ''')

    print('Fuzzcover binary:', os.path.relpath(FUZZCOVER_BINARY))

    corpus_files, corpus_bytes = corpus_size()
    if LAST_CORPUS_SIZE:
        print('Corpus: {name}, {files} files ({diff_files:+d}), {bytes} bytes ({diff_bytes:+d})'.format(
            name=CORPUS_DIRECTORY,
            files=corpus_files,
            diff_files=corpus_files - LAST_CORPUS_SIZE[0],
            bytes=corpus_bytes,
            diff_bytes=corpus_bytes - LAST_CORPUS_SIZE[1]
        ))
    else:
        print('Corpus: {name}, {files} files, {bytes} bytes'.format(
            name=CORPUS_DIRECTORY,
            files=corpus_files,
            bytes=corpus_bytes
        ))

    line, branch = check_coverage(CORPUS_DIRECTORY)
    if LAST_COVERAGE:
        print('Coverage: {line} lines ({diff_lines:+d}), {branch} branches ({diff_branches:+d})'.format(
            line=line, branch=branch, diff_lines=line - LAST_COVERAGE[0], diff_branches=branch - LAST_COVERAGE[1]
        ))
    else:
        print('Coverage: {line} lines, {branch} branches'.format(line=line, branch=branch))
    print()

    LAST_COVERAGE = line, branch
    LAST_CORPUS_SIZE = corpus_files, corpus_bytes


def main_menu():
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
    if len(sys.argv) not in [2, 3]:
        print('Usage: fuzzcover.py FUZZER_BINARY [CORPUS_DIRECTORY]')
        sys.exit(1)

    # process command line parameters
    FUZZCOVER_BINARY = os.path.abspath(sys.argv[1])
    CORPUS_DIRECTORY = sys.argv[2] if len(sys.argv) == 3 else os.path.basename(FUZZCOVER_BINARY) + '_corpus'

    # create corpus directory if it does not exist
    if not os.path.isdir(CORPUS_DIRECTORY):
        os.mkdir(CORPUS_DIRECTORY)

    main_menu()
