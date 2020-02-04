#! /usr/bin/env python3
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

# from math import sqrt #needed for aditional statistics
import os
import sys
import ctypes
import argparse
import itertools
import Levenshtein
try:
    from itertools import izip as zip
except ImportError:
    pass


"""
Class which allows a more efficient way of computing the edit distance on a changing hypothesis.
Stores the C++ wrapper for the actual edit distance computation in self.ed_wrapper.
The reference is stored and converted to a sequence of integers on initialisation in self.ref via _word_to_num().
Since the hypothesis changes after each shift it is added on call __call__().
"""
class EditDistance():
    def __init__(self, ref, ed):
        self.dic = {}
        self.i = 0
        self.ed_wrapper = ed
        self.ref = self._word_to_num(ref)

    def __call__(self, hyp):
        return self._edit_distance(hyp)

    # Calls the C++ implementation of the edit distance
    def _edit_distance(self, hyp):
        hyp_c = (ctypes.c_ulonglong * len(hyp))()
        ref_c = (ctypes.c_ulonglong * len(self.ref))()
        hyp_c[:] = self._word_to_num(hyp)
        ref_c[:] = self.ref
        norm = len(ref_c)
        result = self.ed_wrapper.wrapper(hyp_c, ref_c, len(hyp_c), len(ref_c), norm)
        return result

    # Converts a sequence of words into a sequence of numbers.
    # Each (unique) word is allocated a unique integer.
    def _word_to_num(self, words):
        res = []
        for word in words:
            if word in self.dic:
                res.append(self.dic[word])
            else:
                self.dic[word] = self.i
                res.append(self.dic[word])
                self.i = self.i + 1
        return res


# Character error rate calculator, both hyp and ref are word lists
def cer(hyp_words, ref_words, ed_wrapper):
    hyp_backup = hyp_words
    edit_distance = EditDistance(ref_words, ed_wrapper)
    pre_score = edit_distance(hyp_words)
    if pre_score == 0:
        return 0
    """
    Shifting phrases of the hypothesis sentence until the edit distance from
    the reference sentence is minimized
    """
    while True:
        diff, new_words = shifter(hyp_words, ref_words, pre_score, edit_distance)
        if diff <= 0:
            break

        hyp_words = new_words
        pre_score = pre_score - diff

    shift_cost = _shift_cost(hyp_words, hyp_backup)
    shifted_chars = " ".join(hyp_words)
    ref_chars = " ".join(ref_words)

    if len(shifted_chars) == 0:
        return 1.0

    edit_cost = Levenshtein.distance(shifted_chars, ref_chars) + shift_cost
    return min(1.0, edit_cost / len(shifted_chars))


"""
Some phrases in hypothesis sentences will be shifted, in order to minimize
edit distances from reference sentences. As input the hypothesis and reference
word lists as well as the cached edit distance calculator are required. It will
return the difference of edit distances between before and after shifting, and
the shifted version of the hypothesis sentence.
"""
def shifter(hyp_words, ref_words, pre_score, edit_distance):

    scores = []
    # Changing the phrase order of the hypothesis sentence
    for hyp_start, ref_start, length in couple_discoverer(hyp_words, ref_words):
        shifted_words = hyp_words[:hyp_start] + hyp_words[hyp_start+length:]
        shifted_words[ref_start:ref_start] = hyp_words[hyp_start:hyp_start+length]
        scores.append((pre_score - edit_distance(shifted_words), shifted_words))
    # The case that the phrase order has not to be changed
    if not scores:
        return 0, hyp_words

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

        # Avoid costs created by unnecessary shifts
        if original_words[original_start] == shifted_words[original_start]:
            original_start += 1
            continue

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


# Parsing arguments
def parse_args():
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
    hyp_lines = [x for x in open(args.hyp, 'r')]
    ref_lines = [x for x in open(args.ref, 'r')]
    """
    Check whether the hypothesis and reference files have the same number of
    sentences
    """
    if len(hyp_lines) != len(ref_lines):
        print("Error! {0} lines in the hypothesis file, but {1} lines in the"
              " reference file.".format(len(hyp_lines), len(ref_lines)))
        sys.exit(1)

    # Initialise the connection to C++
    ed_wrapper = ctypes.CDLL(os.path.dirname(os.path.abspath(__file__)) + '/libED.so')
    ed_wrapper.wrapper.restype = ctypes.c_float

    scores = []

    # Split the hypothesis and reference sentences into word lists
    for index, (hyp, ref) in enumerate(zip(hyp_lines, ref_lines), start=1):
        ref, hyp = ref.split(), hyp.split()
        score = cer(hyp, ref, ed_wrapper)
        scores.append(score)
        # Print out scores of every sentence
        if args.verbose:
            print("CharacTER of sentence {0} is {1:.4f}".format(index, score))
    average = sum(scores) / len(scores)
    # variance = sum((s - average) ** 2 for s in scores) / len(scores)
    # standard_deviation = sqrt(variance)
    print(average)


if __name__ == '__main__':
    main()
    sys.exit(0)

