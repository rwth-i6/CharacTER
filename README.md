# CharacTER

CharacTER: Translation Edit Rate on Character Level

CharacTer is a novel character level metric inspired by the commonly applied translation edit rate (Ter). It is defined as the minimum number of character edits required to adjust a hypothesis, until it completely matches the reference, normalized by the length of the hypothesis sentence. CharacTer calculates the character level edit distance while performing the shift edit on word level. Unlike the strict matching criterion in Ter, a hypothesis word is considered to match a reference word and could be shifted, if the edit distance between them is below a threshold value. The Levenshtein distance between the reference and the shifted hypothesis sequence is computed on the character level. In addition, the lengths of hypothesis sequences instead of reference sequences are used for normalizing the edit distance, which effectively counters the issue that shorter translations normally achieve lower Ter.

Paper can be found under ./WMT2016_CharacTer.pdf

Implementations in CharacTER.py

usage: CharacTER.py [-h] -r REF -o HYP [-v]

CharacTER: Character Level Translation Edit Rate

optional arguments:\n
  -h, --help         show this help message and exit\n
  -r REF, --ref REF  Reference file\n
  -o HYP, --hyp HYP  Hypothesis file\n
  -v, --verbose      Print score of each sentence\n

Please apply 'PYTHONIOENCODING' in environment variables, if 
UnicodeEncodeError occurs.

