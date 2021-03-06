from __future__ import absolute_import

from tensorflow.python.framework import ops
from tensorflow.python.ops import math_ops
from tensorflow.keras.optimizers.schedules import ExponentialDecay


class BoundExponentialDecay(ExponentialDecay):
  def __init__(self, min_lr=0.0, **kwargs):
    super().__init__(**kwargs)
    self.min_lr = min_lr

  def __call__(self, step):
    with ops.name_scope_v2(self.name or "ExponentialDecay") as name:
      initial_learning_rate = ops.convert_to_tensor(
        self.initial_learning_rate, name="initial_learning_rate")
      dtype = initial_learning_rate.dtype
      decay_steps = math_ops.cast(self.decay_steps, dtype)
      decay_rate = math_ops.cast(self.decay_rate, dtype)

      global_step_recomp = math_ops.cast(step, dtype)
      p = global_step_recomp / decay_steps
      if self.staircase:
        p = math_ops.floor(p)
      new_lr = math_ops.multiply(
        initial_learning_rate, math_ops.pow(decay_rate, p), name=name)
      return math_ops.maximum(self.min_lr, new_lr)
