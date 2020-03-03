from __future__ import absolute_import

import codecs
import tensorflow as tf


class TextFeaturizer:
  """ Extract text feature based on char-level granularity.
  By looking up the vocabulary table, each line of transcript will be
  converted to a sequence of integer indexes.
  """

  def __init__(self, vocab_file):
    self.num_classes = 0
    lines = []
    with codecs.open(vocab_file, "r", "utf-8") as fin:
      lines.extend(fin.readlines())
    self.token_to_index = {}
    self.index_to_token = {}
    index = 1  # blank index = 0
    for line in lines:
      line = line[:-1]  # Strip the '\n' char
      if line.startswith("#"):  # Skip comment line
        continue
      self.token_to_index[line] = index
      self.index_to_token[index] = line
      index += 1
    self.num_classes = index - 1

  def compute_label_features(self, text):
    # Convert string to a list of integers
    tokens = list(text.strip().lower())
    feats = [self.token_to_index[token] for token in tokens]
    return tf.convert_to_tensor(feats, dtype=tf.int64)

# class UnicodeFeaturizer:
#     def __init__(self)
