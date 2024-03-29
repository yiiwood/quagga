# ----------------------------------------------------------------------------
# Copyright 2015 Grammarly, Inc.
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
# ----------------------------------------------------------------------------
import quagga
from quagga.matrix import CpuMatrix, GpuMatrix


class MatrixType(type):
    def __getattr__(cls, name):
        return getattr(cls._get_matrix_class(), name)

    @staticmethod
    def _get_matrix_class():
        if quagga.processor_type == 'cpu':
            return CpuMatrix
        elif quagga.processor_type == 'gpu':
            return GpuMatrix
        else:
            raise ValueError(u'Processor type: {} is undefined'.
                             format(quagga.processor_type))


class Matrix(object):
    __metaclass__ = MatrixType

    def __init__(self, *args, **kwargs):
        raise ValueError('Do not construct directly!')