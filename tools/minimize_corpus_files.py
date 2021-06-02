#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Tuple


state = {'coverage_calls': 0, 'coverage_time': 0.0}


def get_coverage() -> Tuple[int, int]:
    state['coverage_calls'] += 1
    start_time = time.time()

    try:
        output = subprocess.check_output(["make", "check_coverage_fast"], stderr=subprocess.STDOUT)
        for line in output.decode("utf-8").splitlines():
            if line.startswith('TOTAL'):
                state['coverage_time'] += time.time() - start_time
                _, _, _, _, _, _, _, lines, missed_lines, _, branches, missed_branches, _ = line.split()
                return int(lines) - int(missed_lines), int(branches) - int(missed_branches)

    except subprocess.CalledProcessError:
        # call failed, because tests were run on empty corpus
        return 0, 0


if __name__ == '__main__':
    corpus_directory = sys.argv[1]

    with tempfile.TemporaryDirectory() as temp_dir:
        total_files = len(os.listdir(corpus_directory))
        original_coverage = get_coverage()
        print('original coverage: {lines} lines, {branches} branches'.format(
            lines=original_coverage[0], branches=original_coverage[1]
        ))

        for file_number, filename in enumerate(os.listdir(corpus_directory)):
            print('[{file_number}/{total_files}] processing {filename}'.format(
                file_number=file_number+1,
                total_files=total_files, filename=filename
            ))

            # move file from corpus to temp dir and check coverage without the file
            shutil.move(os.path.join(corpus_directory, filename), temp_dir)
            new_coverage = get_coverage()

            if new_coverage < original_coverage:
                # move file back to corpus
                shutil.move(os.path.join(temp_dir, filename), corpus_directory)
            else:
                print(' - file can be removed without changing coverage')

    new_total_files = len(os.listdir(corpus_directory))

    print('{coverage_calls} coverage checks took {coverage_time:.2f} seconds ({average_time:.2f} seconds/call)'.format(
        coverage_calls=state['coverage_calls'],
        coverage_time=state['coverage_time'],
        average_time=state['coverage_time']/state['coverage_calls']
    ))
    print()
    print('[DONE] Corpus:')
    print(' - before: {total_files} files'.format(total_files=total_files))
    print(' - after:  {new_total_files} files (reduction: -{perc:.1f}%)'.format(
        new_total_files=new_total_files,
        perc=100.0 - (100.0 * new_total_files/total_files)
    ))
    print()
