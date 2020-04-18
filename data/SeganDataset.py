from __future__ import absolute_import

import glob
import os
import librosa
import tensorflow as tf
from utils.Utils import slice_signal


class SeganDataset:
  def __init__(self, clean_data_dir, noisy_data_dir, window_size=2**14, stride=0.5):
    self.clean_data_dir = clean_data_dir
    self.noisy_data_dir = noisy_data_dir
    self.window_size = window_size
    self.stride = stride

  def create(self, batch_size, repeat=1):
    def _gen_data():
      for clean_wav_path in glob.iglob(os.path.join(self.clean_data_dir, "**", "*.wav"), recursive=True):
        name = os.path.basename(clean_wav_path)
        noisy_wav_path = os.path.join(self.noisy_data_dir, name)

        clean_wav, clean_sr = librosa.load(clean_wav_path, sr=None)
        noisy_wav, noisy_sr = librosa.load(noisy_wav_path, sr=None)
        assert clean_sr == 16000 and noisy_sr == 16000, "sample rate of dataset must be 16k"
        clean_slices = slice_signal(clean_wav, self.window_size, self.stride)
        noisy_slices = slice_signal(noisy_wav, self.window_size, self.stride)

        for clean_slice, noisy_slice in zip(clean_slices, noisy_slices):
          yield clean_slice, noisy_slice

    dataset = tf.data.Dataset.from_generator(
      _gen_data,
      output_types=(
        tf.int32,
        tf.int32
      ),
      output_shapes=(
        tf.TensorShape([self.window_size]),
        tf.TensorShape([self.window_size])
      )
    )
    # Repeat and batch the dataset
    dataset = dataset.repeat(repeat)
    dataset = dataset.batch(batch_size)
    # Prefetch to improve speed of input length
    dataset = dataset.prefetch(4)
    return dataset
