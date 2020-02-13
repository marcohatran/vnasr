from __future__ import absolute_import

import tensorflow as tf

from models.CTCModel import CTCModel
from decoders.Decoders import BeamSearchDecoder
from decoders.Decoders import GreedyDecoder
from utils.Utils import wer, cer
from data.Dataset import Dataset
from augmentations.Augments import NoAugment


class SpeechToText:
    def __init__(self, speech_featurizer, text_featurizer, configs,
                 train_dataset=None, eval_dataset=None, test_dataset=None):
        self.speech_featurizer = speech_featurizer
        self.text_featurizer = text_featurizer
        self.train_dataset = train_dataset
        self.eval_dataset = eval_dataset
        self.test_dataset = test_dataset
        self.configs = configs
        self.models = self.__init_models()

    def __init_models(self):
        decoder = self.configs["decoder"]
        if decoder == "beamsearch":
            if "beam_width" not in self.configs.keys():
                raise ValueError("Missing 'beam_width' value in the configuration")
            decoder = BeamSearchDecoder(index_to_token=self.text_featurizer.index_to_token,
                                        beam_width=self.configs["beam_width"])
        elif decoder == "beamsearch_lm":
            if "beam_width" not in self.configs.keys():
                raise ValueError("Missing 'beam_width' value in the configuration")
            if "lm_path" not in self.configs.keys():
                raise ValueError("Missing 'lm_path' value in the configuration")
            decoder = BeamSearchDecoder(index_to_token=self.text_featurizer.index_to_token,
                                        beam_width=self.configs["beam_width"],
                                        lm_path=self.configs["lm_path"])
        elif decoder == "greedy":
            decoder = GreedyDecoder(index_to_token=self.text_featurizer.index_to_token)
        else:
            raise ValueError("'decoder' value must be either 'beamsearch', 'beamsearch_lm' or 'greedy'")

        models = CTCModel(num_classes=self.text_featurizer.num_classes,
                          num_feature_bins=self.speech_featurizer.num_feature_bins,
                          learning_rate=self.configs["learning_rate"],
                          base_model=self.configs["base_model"],
                          decoder=decoder)
        return models

    def train_and_eval(self):
        print("Training and evaluating model ...")
        if "augmentations" in self.configs.keys():
            augmentations = self.configs["augmentations"]

            def check_no_augment():
                for au in augmentations:
                    if isinstance(au, NoAugment):
                        return True
                return False

            if not check_no_augment():
                augmentations.append(NoAugment())
        else:
            augmentations = [NoAugment]
        tf_train_dataset = self.train_dataset(speech_featurizer=self.speech_featurizer,
                                              text_featurizer=self.text_featurizer,
                                              batch_size=self.configs["batch_size"], augmentations=augmentations)

        tf_eval_dataset = self.eval_dataset(speech_featurizer=self.speech_featurizer,
                                            text_featurizer=self.text_featurizer,
                                            batch_size=self.configs["batch_size"])
        self.models.train_model.summary()
        cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=self.configs["checkpoint_weights"],
                                                         save_weights_only=True,
                                                         verbose=1)
        self.models.train_model.fit(x=tf_train_dataset, epochs=self.configs["num_epochs"],
                                    validation_data=tf_eval_dataset, shuffle="batch", callbacks=[cp_callback])
        self.models.train_model.save_weights(filepath=self.configs["export_weights"])

    def test(self):
        print("Testing model ...")
        self.models.test_model.load_weights(filepath=self.configs["export_weights"])
        tf_test_dataset = self.test_dataset(speech_featurizer=self.speech_featurizer,
                                            text_featurizer=self.text_featurizer,
                                            batch_size=self.configs["batch_size"])
        predictions = self.models.test_model.predict(x=tf_test_dataset)
        total_wer = 0
        total_cer = 0
        for pred in predictions:
            total_wer += wer(decode=pred[0], target=pred[1])
            total_cer += cer(decode=pred[0], target=pred[1])

        print("WER: ", total_wer / len(predictions))
        print("CER: ", total_cer / len(predictions))

    def infer(self, speech_file_path):
        self.models.infer_model.load_weights(filepath=self.configs["export_weights"])
        tf_infer_dataset = Dataset(data_path=speech_file_path, mode="infer")
        tf_infer_dataset = tf_infer_dataset(speech_featurizer=self.speech_featurizer, batch_size=1)
        return self.models.infer_model.predict(x=tf_infer_dataset)
