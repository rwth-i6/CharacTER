#! /usr/bin/env python2
# -*- coding:utf-8 -*-

"""
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software 
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division, print_function
import re
import codecs
import sys
import itertools
import math


# Character error rate calculator, both hyp and ref are word lists
def cer(hyp, ref):
    hyp_words, ref_words = list(hyp), list(ref)
    ed_calc = CachedEditDistance(ref_words)
    hyp_backup = hyp_words

    """
    Shifting phrases of the hypothesis sentence until the edit distance from
    the reference sentence is minimized
    """
    while True:
        (diff, hyp_words) = shifter(hyp_words, ref_words, ed_calc)

        if diff <= 0:
            break

    shift_cost = _shift_cost(hyp_words, hyp_backup)
    shifted_chars = list(" ".join(hyp_words))
    ref_chars = list(" ".join(ref_words))
    edit_cost = edit_distance(shifted_chars, ref_chars) + shift_cost
    return edit_cost / len(shifted_chars)


"""
Some phrases in hypothesis sentences will be shifted, in order to minimize
edit distances from reference sentences. As input the hypothesis and reference
word lists as well as the cached edit distance calculator are required. It will
return the difference of edit distances between before and after shifting, and
the shifted version of the hypothesis sentence.
"""


def shifter(hyp_words, ref_words, ed_calc):
    pre_score = ed_calc(hyp_words)
    scores = []

    # Changing the phrase order of the hypothesis sentence
    for hyp_start, ref_start, length in couple_discoverer(hyp_words, ref_words):
        shifted_words = hyp_words[:hyp_start] + hyp_words[hyp_start+length:]
        shifted_words[ref_start:ref_start] = hyp_words[hyp_start:hyp_start+length]
        scores.append((pre_score - ed_calc(shifted_words), shifted_words))

    # The case that the phrase order has not to be changed
    if not scores:
        return (0, hyp_words)

    scores.sort()
    return scores[-1]


"""
This function will find out the identical phrases in sentence_1 and sentence_2,
and yield the corresponding begin positions in both sentences as well as the
maximal phrase length. Both sentences are represented as word lists.
"""


def couple_discoverer(sentence_1, sentence_2):
    # Applying the cartesian product to traversing both sentences
    for start_1, start_2 in \
            itertools.product(range(len(sentence_1)), range(len(sentence_2))):

        # No need to shift if the positions are the same
        if start_1 == start_2:
            continue

        # If identical words are found in different positions of two sentences
        if sentence_1[start_1] == sentence_2[start_2]:
            length = 1

            # Go further to next positions of sentence_1 to learn longer phrase
            for step in range(1, len(sentence_1) - start_1):
                end_1, end_2 = start_1 + step, start_2 + step

                # If the new detected phrase is also contained in sentence_2
                if end_2 < len(sentence_2) and sentence_1[end_1] == sentence_2[end_2]:
                    length += 1
                else:
                    break

            yield (start_1, start_2, length)


# Identical to Levenshtein distance
def edit_distance(sentence_1, sentence_2):

    # Keep sentence_2 as the shorter sentence
    if len(sentence_1) < len(sentence_2):
        return edit_distance(sentence_2, sentence_1)

    """
    If one sentence does not contain any words, the edit distance should be the
    length of the other sentence
    """
    if len(sentence_2) == 0:
        return len(sentence_1)

    previous_row = range(len(sentence_2) + 1)

    # Go through the first sentence
    for i, character_1 in enumerate(sentence_1):
        current_row = [i+1]

        # Go through the second sentence and check the Levenshtein distance
        for j, character_2 in enumerate(sentence_2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (character_1 != character_2)
            current_row.append(min(insertions, deletions, substitutions))

        previous_row = current_row

    return previous_row[-1]


"""
Shift cost: the average word length of the shifted phrase
shifted_words: list of words in the shifted hypothesis sequence
original_words: list of words in the original hypothesis sequence
"""


def _shift_cost(shifted_words, original_words):
    shift_cost = 0
    original_start = 0

    # Go through all words in the shifted hypothesis sequence
    while original_start < len(shifted_words):
        avg_shifted_charaters = 0
        original_index = original_start

        # Go through words with larger index in original hypothesis sequence
        for shift_start in range(original_start+1, len(shifted_words)):

            # Check whether there is word matching
            if original_words[original_start] == shifted_words[shift_start]:
                length = 1

                """
                Go on checking the following word pairs to find the longest
                matched phrase pairs
                """
                for pos in range(1, len(original_words) - original_index):
                    original_end, shift_end = \
                            original_index + pos, shift_start + pos

                    # Check the next word pair
                    if shift_end < len(shifted_words) and \
                            original_words[original_end] == \
                            shifted_words[shift_end]:
                        length += 1

                        # Skip the already matched word pairs in the next loop
                        if original_start+1 < len(original_words):
                            original_start += 1

                    else:
                        break

                shifted_charaters = 0

                # Sum over the lengths of the shifted words
                for index in range(length):
                    shifted_charaters += \
                            len(original_words[original_index+index])

                avg_shifted_charaters = float(shifted_charaters) / length
                break

        shift_cost += avg_shifted_charaters
        original_start += 1

    return shift_cost


"""
Function to calculate the number of edits (The same as TER):
1. Dynamic programming for calcualting edit distance
2. Greedy search to find the shift which most reduces minimum edit distance
Python code copyright (c) 2011 Hiroyuki Tanaka
"""


class CachedEditDistance(object):

    def __init__(self, rwords):
        self.rwds = rwords
        self._cache = {}
        self.list_for_copy = [0 for _ in range(len(self.rwds) + 1)]

    def __call__(self, iwords):
        start_position, cached_score = self._find_cache(iwords)
        score, newly_created_matrix = \
            self._edit_distance(iwords, start_position, cached_score)
        self._add_cache(iwords, newly_created_matrix)
        return score

    def _edit_distance(self, iwords, spos, cache):

        if cache is None:
            cache = [tuple(range(len(self.rwds) + 1))]
        else:
            cache = [cache]

        l = cache + [list(self.list_for_copy)
                     for _ in range(len(iwords) - spos)]
        assert len(l) - 1 == len(iwords) - spos

        for i, j in itertools.product(range(1, len(iwords) - spos + 1),
                                      range(len(self.rwds) + 1)):

            if j == 0:
                l[i][j] = l[i - 1][j] + 1
            else:
                l[i][j] = min(l[i - 1][j] + 1,
                              l[i][j - 1] + 1,
                              l[i - 1][j - 1] + (0 if iwords[spos + i - 1] ==
                                                 self.rwds[j - 1] else 1))

        return l[-1][-1], l[1:]

    def _add_cache(self, iwords, mat):
        node = self._cache
        skipnum = len(iwords) - len(mat)

        for i in range(skipnum):
            node = node[iwords[i]][0]

        assert len(iwords[skipnum:]) == len(mat)

        for word, row in itertools.izip(iwords[skipnum:], mat):

            if word not in node:
                node[word] = [{}, None]

            value = node[word]

            if value[1] is None:
                value[1] = tuple(row)

            node = value[0]

    def _find_cache(self, iwords):
        node = self._cache
        start_position, row = 0, None

        for idx, word in enumerate(iwords):

            if word in node:
                start_position = idx + 1
                node, row = node[word]
            else:
                break

        return start_position, row


# Parsing arguments
def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description='CharacTER: Character Level Translation Edit Rate',
        epilog="Please apply 'PYTHONIOENCODING' in environment variables, "
               "if UnicodeEncodeError occurs."
        )
    parser.add_argument('-r', '--ref', help='Reference file', required=True)
    parser.add_argument('-o', '--hyp', help='Hypothesis file', required=True)
    parser.add_argument('-v', '--verbose', help='Print score of each sentence',
                        action='store_true', default=False)
    return parser.parse_args()


def main():
    args = parse_args()
    hyp_lines = [x for x in codecs.open(args.hyp, 'r', 'utf-8').readlines()]
    ref_lines = [x for x in codecs.open(args.ref, 'r', 'utf-8').readlines()]

    """
    Check whether the hypothesis and reference files have the same number of
    sentences
    """
    if len(hyp_lines) != len(ref_lines):
        print("Error! {0} lines in the hypothesis file, but {1} lines in the"
              " reference file.".format(len(hyp_lines), len(ref_lines)))
        sys.exit(1)

    scores = []

    # Split the hypothesis and reference sentences into word lists
    for index, (hyp, ref) in \
            enumerate(itertools.izip(hyp_lines, ref_lines), start=1):
        ref, hyp = ref.split(), hyp.split()
        score = cer(hyp, ref)
        scores.append(score)

        # Print out scores of every sentence
        if args.verbose:
            print("CharacTER of sentence {0} is {1:.4f}".format(index, score))

    average = sum(scores) / len(scores)
    variance = sum((s - average) ** 2 for s in scores) / len(scores)
    standard_deviation = math.sqrt(variance)
    print(average)


if __name__ == '__main__':
    main()
