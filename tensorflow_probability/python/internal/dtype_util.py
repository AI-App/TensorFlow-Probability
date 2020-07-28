# Copyright 2018 The TensorFlow Probability Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Utility functions for dtypes."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Dependency imports
import numpy as np

import tensorflow.compat.v2 as tf


__all__ = [
    'as_numpy_dtype',
    'assert_same_float_dtype',
    'base_dtype',
    'base_equal',
    'common_dtype',
    'is_bool',
    'is_complex',
    'is_floating',
    'is_integer',
    'is_numpy_compatible',
    'max',
    'min',
    'name',
    'real_dtype',
    'size',
]


JAX_MODE = False
NUMPY_MODE = False
SKIP_DTYPE_CHECKS = False


def is_numpy_compatible(dtype):
  """Returns if dtype has a corresponding NumPy dtype."""
  if JAX_MODE or NUMPY_MODE:
    return True
  else:
    return tf.as_dtype(dtype).is_numpy_compatible


def as_numpy_dtype(dtype):
  """Returns a `np.dtype` based on this `dtype`."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'as_numpy_dtype'):
    return dtype.as_numpy_dtype
  return dtype


def base_dtype(dtype):
  """Returns a non-reference `dtype` based on this `dtype`."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'base_dtype'):
    return dtype.base_dtype
  return dtype


def base_equal(a, b):
  """Returns `True` if base dtypes are identical."""
  return base_dtype(a) == base_dtype(b)


def common_dtype(args_list, dtype_hint=None):
  """Returns explict dtype from `args_list` if there is one."""
  dtype = None
  seen = []
  for a in tf.nest.flatten(args_list):
    if hasattr(a, 'dtype') and a.dtype:
      dt = as_numpy_dtype(a.dtype)
      seen.append(dt)
    else:
      seen.append(None)
      continue
    if dtype is None:
      dtype = dt
    elif dtype != dt:
      if SKIP_DTYPE_CHECKS:
        dtype = (np.ones([2], dtype) + np.ones([2], dt)).dtype
      else:
        raise TypeError(
            'Found incompatible dtypes, {} and {}. Seen so far: {}'.format(
                dtype, dt, seen))
  return dtype_hint if dtype is None else base_dtype(dtype)


def convert_to_dtype(tensor_or_dtype, dtype=None, dtype_hint=None):
  """Get a dtype from a list/tensor/dtype using convert_to_tensor semantics."""
  if tensor_or_dtype is None:
    return dtype or dtype_hint

  # Tensorflow dtypes need to be typechecked
  if tf.is_tensor(tensor_or_dtype):
    dt = base_dtype(tensor_or_dtype.dtype)
  elif isinstance(tensor_or_dtype, tf.DType):
    dt = base_dtype(tensor_or_dtype)
  # Numpy dtypes defer to dtype/dtype_hint
  elif isinstance(tensor_or_dtype, np.ndarray):
    dt = base_dtype(dtype or dtype_hint or tensor_or_dtype.dtype)
  elif np.issctype(tensor_or_dtype):
    dt = base_dtype(dtype or dtype_hint or tensor_or_dtype)
  else:
    # If this is a Python object, call `convert_to_tensor` and grab the dtype.
    # Note that this will add ops in graph-mode; we may want to consider
    # other ways to handle this case.
    dt = tf.convert_to_tensor(tensor_or_dtype, dtype, dtype_hint).dtype

  if not SKIP_DTYPE_CHECKS and dtype and not base_equal(dtype, dt):
    raise TypeError('Found incompatible dtypes, {} and {}.'.format(dtype, dt))
  return dt


def is_bool(dtype):
  """Returns whether this is a boolean data type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'is_bool'):
    return dtype.is_bool
  # We use `kind` because:
  # np.issubdtype(np.uint8, np.bool) == True.
  return np.dtype(dtype).kind == 'b'


def is_complex(dtype):
  """Returns whether this is a complex floating point type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'is_complex'):
    return dtype.is_complex
  return np.issubdtype(np.dtype(dtype), np.complexfloating)


def is_floating(dtype):
  """Returns whether this is a (non-quantized, real) floating point type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'is_floating'):
    return dtype.is_floating
  return np.issubdtype(np.dtype(dtype), np.floating)


def is_integer(dtype):
  """Returns whether this is a (non-quantized) integer type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'is_integer') and not callable(dtype.is_integer):
    return dtype.is_integer
  return np.issubdtype(np.dtype(dtype), np.integer)


def max(dtype):  # pylint: disable=redefined-builtin
  """Returns the maximum representable value in this data type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'max') and not callable(dtype.max):
    return dtype.max
  use_finfo = is_floating(dtype) or is_complex(dtype)
  return np.finfo(dtype).max if use_finfo else np.iinfo(dtype).max


def min(dtype):  # pylint: disable=redefined-builtin
  """Returns the minimum representable value in this data type."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'min') and not callable(dtype.min):
    return dtype.min
  use_finfo = is_floating(dtype) or is_complex(dtype)
  return np.finfo(dtype).min if use_finfo else np.iinfo(dtype).min


def name(dtype):
  """Returns the string name for this `dtype`."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'name'):
    return dtype.name
  if hasattr(dtype, '__name__'):
    return dtype.__name__
  return str(dtype)


def size(dtype):
  """Returns the number of bytes to represent this `dtype`."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'size') and hasattr(dtype, 'as_numpy_dtype'):
    return dtype.size
  return np.dtype(dtype).itemsize


def real_dtype(dtype):
  """Returns the dtype of the real part."""
  dtype = tf.as_dtype(dtype)
  if hasattr(dtype, 'real_dtype'):
    return dtype.real_dtype
  # TODO(jvdillon): Find a better way.
  return np.array(0, as_numpy_dtype(dtype)).real.dtype


def _assert_same_base_type(items, expected_type=None):
  r"""Asserts all items are of the same base type.

  Args:
    items: List of graph items (e.g., `Variable`, `Tensor`, `SparseTensor`,
        `Operation`, or `IndexedSlices`). Can include `None` elements, which
        will be ignored.
    expected_type: Expected type. If not specified, assert all items are
        of the same base type.

  Returns:
    Validated type, or none if neither expected_type nor items provided.

  Raises:
    ValueError: If any types do not match.
  """
  original_expected_type = expected_type
  mismatch = False
  for item in items:
    if item is not None:
      item_type = base_dtype(item.dtype)
      if expected_type is None:
        expected_type = item_type
      elif expected_type != item_type:
        mismatch = True
        break
  if mismatch:
    # Loop back through and build up an informative error message (this is very
    # slow, so we don't do it unless we found an error above).
    expected_type = original_expected_type
    original_item_str = None
    get_name = lambda x: x.name if hasattr(x, 'name') else str(x)
    for item in items:
      if item is not None:
        item_type = base_dtype(item.dtype)
        if not expected_type:
          expected_type = item_type
          original_item_str = get_name(item)
        elif expected_type != item_type:
          raise ValueError(
              '{}, type={}, must be of the same type ({}){}.'.format(
                  get_name(item),
                  item_type,
                  expected_type,
                  ((' as {}'.format(original_item_str))
                   if original_item_str else '')))
    return expected_type  # Should be unreachable
  else:
    return expected_type


def assert_same_float_dtype(tensors=None, dtype=None):
  """Validate and return float type based on `tensors` and `dtype`.

  For ops such as matrix multiplication, inputs and weights must be of the
  same float type. This function validates that all `tensors` are the same type,
  validates that type is `dtype` (if supplied), and returns the type. Type must
  be a floating point type. If neither `tensors` nor `dtype` is supplied,
  the function will return `dtypes.float32`.

  Args:
    tensors: Tensors of input values. Can include `None` elements, which will
      be ignored.
    dtype: Expected type.

  Returns:
    Validated type.

  Raises:
    ValueError: if neither `tensors` nor `dtype` is supplied, or result is not
      float, or the common type of the inputs is not a floating point type.
  """
  if tensors:
    dtype = _assert_same_base_type(tensors, dtype)
  if not dtype:
    dtype = tf.float32
  elif not is_floating(dtype):
    raise ValueError('Expected floating point type, got {}.'.format(dtype))
  return dtype
