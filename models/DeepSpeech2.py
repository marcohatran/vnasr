"""
Read https://www.tensorflow.org/api_docs/python/tf/keras/layers/LSTM
to use cuDNN-LSTM
"""
from __future__ import absolute_import

import functools
import tensorflow as tf
from models.RowConv1D import RowConv1D


class DeepSpeech2:
    def __init__(self):
        self.clipped_relu = functools.partial(tf.keras.activations.relu, max_value=20)
        self.optimizer = tf.keras.optimizers.Adam

    def __call__(self, features):
        layer = features
        for _ in range(3):
            layer = tf.keras.layers.Conv2D(filters=32, kernel_size=(21, 11),
                                           strides=(1, 2), padding="same")(layer)
            layer = tf.keras.layers.BatchNormalization()(layer)
            layer = tf.keras.layers.Activation(activation=self.clipped_relu)(layer)
            layer = tf.keras.layers.Dropout(0.2)(layer)

        # combine channel dimension to features
        batch_size = tf.shape(layer)[0]
        feat_size, channel = layer.get_shape().as_list()[2:]
        layer = tf.reshape(layer, [batch_size, -1, feat_size * channel])

        # RNN layers
        for _ in range(3):
            layer = tf.keras.layers.Bidirectional(
                tf.keras.layers.LSTM(128, return_sequences=True,
                                     recurrent_dropout=0))(layer)
            layer = tf.keras.layers.BatchNormalization()(layer)

        return layer


class DeepSpeech2RowConv:
    def __init__(self):
        self.clipped_relu = functools.partial(tf.keras.activations.relu, max_value=20)
        self.optimizer = tf.keras.optimizers.Adam
        self.rnn_unit = 256

    def __call__(self, features):
        layer = features
        for _ in range(3):
            layer = tf.keras.layers.Conv2D(filters=32, kernel_size=(21, 11),
                                           strides=(1, 2), padding="same")(layer)
            layer = tf.keras.layers.BatchNormalization()(layer)
            layer = tf.keras.layers.Activation(activation=self.clipped_relu)(layer)
            layer = tf.keras.layers.Dropout(0.2)(layer)

        # combine channel dimension to features
        batch_size = tf.shape(layer)[0]
        feat_size, channel = layer.get_shape().as_list()[2:]
        layer = tf.reshape(layer, [batch_size, -1, feat_size * channel])

        # RNN layers
        for _ in range(3):
            layer = tf.keras.layers.LSTM(self.rnn_unit, activation='tanh',
                                         recurrent_activation='sigmoid',
                                         return_sequences=True,
                                         recurrent_dropout=0,
                                         unroll=False, use_bias=True)(layer)
            layer = RowConv1D(filters=self.rnn_unit, future_context=2, strides=1,
                              padding="same")(layer)
            layer = tf.keras.layers.BatchNormalization()(layer)

        return layer
