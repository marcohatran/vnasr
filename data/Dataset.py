from __future__ import absolute_import

import tensorflow as tf
from augmentations.Augments import NoAugment


class Dataset:
    def __init__(self, data_path, mode="train"):
        self.data_path = data_path
        self.mode = mode

    def __call__(self, speech_featurizer, text_featurizer, batch_size=32, repeat=1, augmentations=tuple([NoAugment])):
        if self.mode == "train":
            self.entries = self.__create_train_entries()
            return self.__create_dataset(speech_featurizer=speech_featurizer, text_featurizer=text_featurizer,
                                         batch_size=batch_size, repeat=repeat, augmentations=augmentations)
        elif self.mode == "eval" or self.mode == "test":
            self.entries = self.__create_train_entries()
            return self.__create_dataset(speech_featurizer=speech_featurizer, text_featurizer=text_featurizer,
                                         batch_size=batch_size)
        elif self.mode == "infer":
            self.entries = self.__create_infer_entries()
            return self.__create_infer_dataset(speech_featurizer=speech_featurizer, batch_size=batch_size)
        else:
            raise ValueError("Mode must be 'train', 'eval' or 'infer'")

    def __create_train_entries(self):
        lines = []
        for file_path in self.data_path:
            with tf.io.gfile.GFile(file_path, "r") as f:
                temp_lines = f.read().splitlines()
                # Skip the header of csv file
                lines += temp_lines[1:]
        # The files is "\t" seperated
        lines = [line.split("\t", 2) for line in lines]
        # Sort input data by the length of audio sequence
        lines.sort(key=lambda item: int(item[1]))
        return [tuple(line) for line in lines]

    def __create_infer_entries(self):
        lines = []
        for file_path in self.data_path:
            with tf.io.gfile.GFile(file_path, "r") as f:
                lines = f.read().splitlines()
        return lines

    def __create_dataset(self, speech_featurizer, text_featurizer, batch_size, repeat=1,
                         augmentations=tuple([NoAugment])):
        # Dataset properties
        num_feature_bins = speech_featurizer.num_feature_bins

        def _gen_data():
            for audio_file, _, transcript in self.entries:
                for au in augmentations:
                    if not au.is_post:
                        features = au(audio_file)
                    else:
                        features = audio_file
                    features = speech_featurizer.compute_speech_features(features)
                    if au.is_post:
                        features = au(features)
                    labels = text_featurizer.compute_label_features(transcript)
                    input_length = [len(features)]
                    label_length = [len(labels) if labels is not None else None]

                    yield (
                        {
                            "features": features,
                            "input_length": input_length,
                            "labels": labels,
                            "label_length": label_length
                        },
                        -1  # Dummy label
                    )

        dataset = tf.data.Dataset.from_generator(
            _gen_data,
            output_types=(
                {
                    "features": tf.float32,
                    "input_length": tf.int32,
                    "labels": tf.int32,
                    "label_length": tf.int32
                },
                tf.int32
            ),
            output_shapes=(
                {
                    "features": tf.TensorShape([None, num_feature_bins, 1]),
                    "input_length": tf.TensorShape([1]),
                    "labels": tf.TensorShape([None]),
                    "label_length": tf.TensorShape([1])
                },
                tf.TensorShape([])
            )
        )
        # Repeat and batch the dataset
        dataset = dataset.repeat(repeat)
        # Padding the features to its max length dimensions
        dataset = dataset.padded_batch(
            batch_size=batch_size,
            padded_shapes=(
                {
                    "features": tf.TensorShape([None, num_feature_bins, 1]),
                    "input_length": tf.TensorShape([1]),
                    "labels": tf.TensorShape([None]),
                    "label_length": tf.TensorShape([1])
                },
                tf.TensorShape([])
            )
        )
        # Prefetch to improve speed of input length
        dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        return dataset

    def __create_infer_dataset(self, speech_featurizer, batch_size, repeat=1):
        # Dataset properties
        num_feature_bins = speech_featurizer.num_feature_bins

        def _gen_data():
            for audio_file in self.entries:
                features = speech_featurizer.compute_speech_features(audio_file)
                input_length = [len(features)]
                yield (
                    {
                        "features": features,
                        "input_length": input_length
                    },
                    -1  # Dummy label
                )

        dataset = tf.data.Dataset.from_generator(
            _gen_data,
            output_types=(
                {
                    "features": tf.float32,
                    "input_length": tf.int32
                },
                tf.int32
            ),
            output_shapes=(
                {
                    "features": tf.TensorShape([None, num_feature_bins, 1]),
                    "input_length": tf.TensorShape([1])
                },
                tf.TensorShape([])
            )
        )
        # Repeat and batch the dataset
        dataset = dataset.repeat(repeat)
        # Padding the features to its max length dimensions
        dataset = dataset.padded_batch(
            batch_size=batch_size,
            padded_shapes=(
                {
                    "features": tf.TensorShape([None, num_feature_bins, 1]),
                    "input_length": tf.TensorShape([1])
                },
                tf.TensorShape([])
            )
        )
        # Prefetch to improve speed of input length
        dataset = dataset.prefetch(buffer_size=tf.data.experimental.AUTOTUNE)
        return dataset
