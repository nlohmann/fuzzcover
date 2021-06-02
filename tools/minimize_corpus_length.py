#!/usr/bin/env python3

import os
import subprocess
import sys
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

    corpus_size_without_reduction = 0
    bytes_saved_by_reduction = 0
    total_files = len(os.listdir(corpus_directory))

    for file_number, filename in enumerate(os.listdir(corpus_directory)):
        source_path = os.path.join(corpus_directory, filename)

        # determine coverage
        line_coverage = get_coverage()

        # read content
        file_content = open(source_path, 'rb').read()
        file_size = len(file_content)
        corpus_size_without_reduction += file_size

        print('[{file_number}/{total_files}] processing {filename} ({file_size} bytes)'.format(
            file_number=file_number+1,
            total_files=total_files,
            filename=filename,
            file_size=file_size
        ))

        # iteratively add bytes, starting from 1
        #new_file_size = 0
        #while new_file_size != file_size:
        #    # write truncated file
        #    new_file_size += 1
        #    open(source_path, 'wb').write(file_content[0:new_file_size])

        #    # determine new coverage
        #    new_line_coverage = get_coverage()

        #    if new_line_coverage == line_coverage:
        #        break

        # iteratively remove bytes
        while file_size > 1:
            # write truncated file
            new_file_size = file_size - 1
            open(source_path, 'wb').write(file_content[0:new_file_size])

            # determine new coverage
            new_line_coverage = get_coverage()

            if new_line_coverage < line_coverage:
                # restore file content
                open(source_path, 'wb').write(file_content[0:file_size])
                break

            # update size
            file_size = new_file_size
            bytes_saved_by_reduction += 1

        if len(file_content) > file_size:
            size_difference = len(file_content) - file_size

            print(' - file can be reduced to {file_size} bytes (reduction: {size_difference} bytes, -{perc:.1f}%)'.format(
                file_size=file_size,
                size_difference=size_difference,
                perc=100.0 - (100.0 * file_size / len(file_content))
            ))

    print('{coverage_calls} coverage checks took {coverage_time:.2f} seconds ({average_time:.2f} seconds/call)'.format(
        coverage_calls=state['coverage_calls'],
        coverage_time=state['coverage_time'],
        average_time=state['coverage_time']/state['coverage_calls']
    ))
    print()
    print('[DONE] Corpus: {total_files} files'.format(total_files=total_files))
    print(' - before: {total_bytes} bytes'.format(total_bytes=corpus_size_without_reduction))
    print(' - after:  {final_size} bytes (reduction: {diff} bytes, -{perc:.1f}%)'.format(
        final_size=corpus_size_without_reduction - bytes_saved_by_reduction,
        diff=bytes_saved_by_reduction,
        perc=100.0 - (100.0 * (corpus_size_without_reduction - bytes_saved_by_reduction) / corpus_size_without_reduction)
    ))
    print()
