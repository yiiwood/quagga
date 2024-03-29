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
import numpy as np
import ctypes as ct
from itertools import izip
from unittest import TestCase
from quagga.matrix import GpuMatrix
from quagga.matrix import CpuMatrix
from quagga.context import GpuContext
from quagga.context import CpuContext
from quagga.matrix import SparseMatrix


class TestMatrix(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rng = np.random.RandomState(seed=42)
        cls.gpu_context = GpuContext()
        cls.cpu_context = CpuContext()
        cls.N = 50

    @classmethod
    def get_random_array(cls, shape=None, high=7000):
        if shape:
            a = 4 * cls.rng.rand(*shape) - 2
        else:
            nrows, ncols = cls.rng.random_integers(low=high, size=2)
            a = 4 * cls.rng.rand(nrows, ncols) - 2
        return a.astype(dtype=np.float32)

    # def test_getitem(self):
    #     # TODO(sergii) this test is not up-to-date
    #     r = []
    #     for i in xrange(self.N):
    #         a = TestMatrix.get_random_array()
    #         j = self.rng.randint(a.shape[1])
    #         option = self.rng.randint(3)
    #         if option == 0:
    #             s = j
    #         elif option == 1:
    #             s = slice(None, j, None)
    #         else:
    #             s = slice(j, None, None)
    #
    #         a_cpu = CpuMatrix.from_npa(a)
    #         a_gpu = GpuMatrix.from_npa(a)
    #         a_cpu_column = a_cpu[:, s]
    #         a_gpu_column = a_gpu[:, s]
    #         r.append(np.allclose(a_cpu_column.to_host(),
    #                              a_gpu_column.to_host()))
    #     self.assertEqual(sum(r), self.N)

    def test_from_npa(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_cpu = CpuMatrix.from_npa(a).to_host()
            a_gpu = GpuMatrix.from_npa(a).to_host()
            r.append(np.allclose(a_cpu, a_gpu))
        self.assertEqual(sum(r), self.N)

    def test_to_host(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_cpu = CpuMatrix.from_npa(a).to_host()
            a_gpu = GpuMatrix.from_npa(a).to_host()
            r.append(np.allclose(a, a_cpu))
            r.append(np.allclose(a, a_gpu))
        self.assertEqual(sum(r), len(r))

    def test_assign(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.empty_like(a_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.empty_like(a_gpu)
            b_cpu.assign(self.cpu_context, a_cpu)
            b_gpu.assign(self.gpu_context, a_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host()))

            # strided
            N = self.rng.random_integers(7000)
            offset = [self.rng.random_integers(0, N - 1)]
            offset.append(self.rng.random_integers(offset[0] + 1, N))

            a = self.get_random_array((1, N))
            b = self.get_random_array((self.rng.random_integers(N), self.rng.random_integers(offset[1] - offset[0], N)))
            k = self.rng.randint(b.shape[0])

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)

            chunk_b_cpu = b_cpu[k]
            chunk_a_cpu = a_cpu[:, offset[0]:offset[1]]
            chunk_b_gpu = b_gpu[k]
            chunk_a_gpu = a_gpu[:, offset[0]:offset[1]]

            chunk_b_cpu.assign(self.cpu_context, chunk_a_cpu)
            chunk_b_gpu.assign(self.gpu_context, chunk_a_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_assign_npa(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_cpu = CpuMatrix.empty(a.shape[0], a.shape[1])
            a_gpu = GpuMatrix.empty(a.shape[0], a.shape[1])
            a_cpu.assign_npa(self.cpu_context, a)
            a_gpu.assign_npa(self.gpu_context, a)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))
            r.append(np.allclose(a_cpu.to_host(), a))
            r.append(np.allclose(a_gpu.to_host(), a))
        self.assertEqual(sum(r), len(r))

    def test_fill(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            fill_value = self.rng.rand()
            a_cpu = CpuMatrix.from_npa(a)
            a_gpu = GpuMatrix.from_npa(a)
            a_cpu.fill(self.cpu_context, fill_value)
            a_gpu.fill(self.gpu_context, fill_value)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))
        self.assertEqual(sum(r), self.N)

    def test_sync_fill(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            fill_value = self.rng.rand()
            a_cpu = CpuMatrix.from_npa(a)
            a_gpu = GpuMatrix.from_npa(a)
            a_cpu.sync_fill(fill_value)
            a_gpu.sync_fill(fill_value)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))
        self.assertEqual(sum(r), self.N)

    def test_slice_columns(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array((a.shape[0], a.shape[1]+10000))
            indxs = self.rng.choice(b.shape[1], a.shape[1]).astype(np.int32)
            indxs = indxs.reshape((1, len(indxs)))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            column_indxs_cpu = CpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            column_indxs_gpu = GpuMatrix.from_npa(indxs)

            b_cpu.slice_columns(self.cpu_context, column_indxs_cpu, a_cpu)
            b_gpu.slice_columns(self.gpu_context, column_indxs_gpu, a_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_scaled_columns_slice(self):
        r = []
        for i in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array((a.shape[0], a.shape[1]+10000))
            indxs = self.rng.choice(b.shape[1], a.shape[1]).astype(np.int32)
            indxs = indxs.reshape((1, len(indxs)))
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a, 'float')
            b_cpu = CpuMatrix.from_npa(b, 'float')
            column_indxs_cpu = CpuMatrix.from_npa(indxs)
            column_indxs_gpu = GpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a, 'float')
            b_gpu = GpuMatrix.from_npa(b, 'float')

            b_cpu.add_scaled_columns_slice(self.cpu_context, column_indxs_cpu, alpha, a_cpu)
            b_gpu.add_scaled_columns_slice(self.gpu_context, column_indxs_gpu, ct.c_float(alpha), a_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host(), atol=1e-6))

        self.assertEqual(sum(r), self.N)

    def test_slice_columns_and_transpose(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array((a.shape[1], a.shape[0]+10000))

            indxs = self.rng.choice(b.shape[1], a.shape[0]).astype(np.int32)
            indxs = indxs.reshape((1, len(indxs)))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            column_indxs_cpu = CpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            column_indxs_gpu = GpuMatrix.from_npa(indxs)

            b_cpu.slice_columns_and_transpose(self.cpu_context, column_indxs_cpu, a_cpu)
            b_gpu.slice_columns_and_transpose(self.gpu_context, column_indxs_gpu, a_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_slice_rows(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array((a.shape[0]+10000, a.shape[1]))
            indxs = self.rng.choice(b.shape[0], a.shape[0]).astype(np.int32)
            indxs = indxs.reshape((len(indxs), 1))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            row_indxs_cpu = CpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            row_indxs_gpu = GpuMatrix.from_npa(indxs)

            b_cpu.slice_rows(self.cpu_context, row_indxs_cpu, a_cpu)
            b_gpu.slice_rows(self.gpu_context, row_indxs_gpu, a_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_scaled_rows_slice(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            k = self.rng.random_integers(a.shape[0])
            m = TestMatrix.get_random_array((k, a.shape[1]))
            indxs = self.rng.choice(a.shape[0], k)
            indxs = np.array(indxs, dtype=np.int32, ndmin=2).T
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            m_cpu = CpuMatrix.from_npa(m)
            indxs_cpu = CpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a)
            m_gpu = GpuMatrix.from_npa(m)
            indxs_gpu = GpuMatrix.from_npa(indxs)

            a_cpu.add_scaled_rows_slice(self.cpu_context, indxs_cpu, alpha, m_cpu)
            a_gpu.add_scaled_rows_slice(self.gpu_context, indxs_gpu, alpha, m_gpu)

            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-5))

        self.assertEqual(sum(r), self.N)

    def test_slice_rows_batch(self):
        r = []
        for _ in xrange(self.N):
            embd_matrix = TestMatrix.get_random_array(high=1000)
            nrows, k = self.rng.random_integers(1000, size=2)
            dense_matrices = []
            for _ in xrange(k):
                matrix = np.empty((nrows, embd_matrix.shape[1]), np.float32)
                dense_matrices.append(matrix)
            embd_rows_indxs = self.rng.randint(embd_matrix.shape[0], size=(nrows, k)).astype(np.int32)

            embd_matrix_cpu = CpuMatrix.from_npa(embd_matrix)
            embd_rows_indxs_cpu = CpuMatrix.from_npa(embd_rows_indxs)
            dense_matrices_cpu = [CpuMatrix.from_npa(each) for each in dense_matrices]
            embd_matrix_gpu = GpuMatrix.from_npa(embd_matrix)
            embd_rows_indxs_gpu = GpuMatrix.from_npa(embd_rows_indxs)
            dense_matrices_gpu = [GpuMatrix.from_npa(each) for each in dense_matrices]

            embd_matrix_cpu.slice_rows_batch(self.cpu_context, embd_rows_indxs_cpu, dense_matrices_cpu)
            embd_matrix_gpu.slice_rows_batch(self.gpu_context, embd_rows_indxs_gpu, dense_matrices_gpu)

            for m_cpu, m_gpu in izip(dense_matrices_cpu, dense_matrices_gpu):
                if not np.allclose(m_cpu.to_host(), m_gpu.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

        self.assertEqual(sum(r), self.N)

    def test_add_scaled_rows_batch_slice(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            m = []
            K = self.rng.random_integers(a.shape[0])
            indxs = []
            for _ in xrange(self.rng.random_integers(100)):
                m.append(TestMatrix.get_random_array((K, a.shape[1])))
                indxs.append(self.rng.choice(a.shape[0], K))
            indxs = np.array(indxs, np.int32).T
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            m_cpu = [CpuMatrix.from_npa(e) for e in m]
            indxs_cpu = CpuMatrix.from_npa(indxs)
            a_gpu = GpuMatrix.from_npa(a)
            m_gpu = [GpuMatrix.from_npa(e) for e in m]
            indxs_gpu = GpuMatrix.from_npa(indxs)

            a_cpu.add_scaled_rows_batch_slice(self.cpu_context, indxs_cpu, alpha, m_cpu)
            a_gpu.add_scaled_rows_batch_slice(self.gpu_context, indxs_gpu, alpha, m_gpu)

            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-5))

            del a_gpu
            del indxs_gpu
            del m_gpu

        self.assertEqual(sum(r), self.N)

    def test_assign_hstack(self):
        r = []
        for _ in xrange(self.N):
            cpu_matrices = []
            gpu_matrices = []
            nrows = self.rng.random_integers(1, 7000)
            ncols = 0
            for k in xrange(self.rng.random_integers(10)):
                _ncols = self.rng.random_integers(1000)
                matrix = self.get_random_array(shape=(nrows, _ncols))
                ncols += _ncols
                cpu_matrices.append(CpuMatrix.from_npa(matrix))
                gpu_matrices.append(GpuMatrix.from_npa(matrix))
            cpu_stacked = CpuMatrix.empty(nrows, ncols, 'float')
            gpu_stacked = GpuMatrix.empty(nrows, ncols, 'float')
            cpu_stacked.assign_hstack(self.cpu_context, cpu_matrices)
            gpu_stacked.assign_hstack(self.gpu_context, gpu_matrices)
            r.append(np.allclose(cpu_stacked.to_host(), gpu_stacked.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_hsplit(self):
        r = []
        for _ in xrange(self.N):
            cpu_matrices = []
            gpu_matrices = []
            nrows = self.rng.random_integers(1, 7000)
            ncols = [0]
            for k in xrange(self.rng.random_integers(10)):
                _ncols = self.rng.random_integers(1000)
                ncols.append(ncols[-1] + _ncols)
                cpu_matrices.append(CpuMatrix.empty(nrows, _ncols, 'float'))
                gpu_matrices.append(GpuMatrix.empty(nrows, _ncols, 'float'))
            a = self.get_random_array((nrows, ncols[-1]))
            cpu_stacked = CpuMatrix.from_npa(a, 'float')
            gpu_stacked = GpuMatrix.from_npa(a, 'float')

            indxs = set(self.rng.choice(k+1, max(1, k-5), replace=False))
            col_slices = []
            _cpu_matrices = []
            _gpu_matrices = []
            for k in indxs:
                col_slices.append((ncols[k], ncols[k+1]))
                _cpu_matrices.append(cpu_matrices[k])
                _gpu_matrices.append(gpu_matrices[k])
            cpu_stacked.hsplit(self.cpu_context, _cpu_matrices, col_slices)
            gpu_stacked.hsplit(self.gpu_context, _gpu_matrices, col_slices)
            for cpu_m, gpu_m in izip(_cpu_matrices, _gpu_matrices):
                if not np.allclose(cpu_m.to_host(), gpu_m.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

            cpu_stacked.hsplit(self.cpu_context, cpu_matrices)
            gpu_stacked.hsplit(self.gpu_context, gpu_matrices)
            for cpu_m, gpu_m in izip(cpu_matrices, gpu_matrices):
                if not np.allclose(cpu_m.to_host(), gpu_m.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

        self.assertEqual(sum(r), len(r))

    def test_batch_hstack(self):
        r = []
        for _ in xrange(self.N):
            n, nrows = self.rng.random_integers(200, size=2)
            x_ncols, y_ncols = self.rng.random_integers(3000, size=2)
            x_sequence = []
            y_sequence = []
            output_sequence = []
            for i in xrange(n):
                x_sequence.append(self.get_random_array((nrows, x_ncols)))
                y_sequence.append(self.get_random_array((nrows, y_ncols)))
                output_sequence.append(np.empty((nrows, x_ncols + y_ncols), np.float32))

            x_sequence_cpu = []
            y_sequence_cpu = []
            output_sequence_cpu = []
            x_sequence_gpu = []
            y_sequence_gpu = []
            output_sequence_gpu = []
            for x, y, out in izip(x_sequence, y_sequence, output_sequence):
                x_sequence_cpu.append(CpuMatrix.from_npa(x))
                y_sequence_cpu.append(CpuMatrix.from_npa(y))
                output_sequence_cpu.append(CpuMatrix.from_npa(out))
                x_sequence_gpu.append(GpuMatrix.from_npa(x))
                y_sequence_gpu.append(GpuMatrix.from_npa(y))
                output_sequence_gpu.append(GpuMatrix.from_npa(out))

            CpuMatrix.batch_hstack(self.cpu_context, x_sequence_cpu, y_sequence_cpu, output_sequence_cpu)
            GpuMatrix.batch_hstack(self.gpu_context, x_sequence_gpu, y_sequence_gpu, output_sequence_gpu)

            for out_cpu, out_gpu in izip(output_sequence_cpu, output_sequence_gpu):
                if not np.allclose(out_cpu.to_host(), out_gpu.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

        self.assertEqual(sum(r), self.N)

    def test_batch_hsplit(self):
        r = []
        for _ in xrange(self.N):
            n, nrows = self.rng.random_integers(200, size=2)
            x_ncols, y_ncols = self.rng.random_integers(3000, size=2)
            x_sequence = []
            y_sequence = []
            input_sequence = []
            for i in xrange(n):
                x_sequence.append(np.empty((nrows, x_ncols), dtype=np.float32))
                y_sequence.append(np.empty((nrows, y_ncols), dtype=np.float32))
                input_sequence.append(self.get_random_array((nrows, x_ncols + y_ncols)))

            x_sequence_cpu = []
            y_sequence_cpu = []
            input_sequence_cpu = []
            x_sequence_gpu = []
            y_sequence_gpu = []
            input_sequence_gpu = []
            for x, y, out in izip(x_sequence, y_sequence, input_sequence):
                x_sequence_cpu.append(CpuMatrix.from_npa(x))
                y_sequence_cpu.append(CpuMatrix.from_npa(y))
                input_sequence_cpu.append(CpuMatrix.from_npa(out))
                x_sequence_gpu.append(GpuMatrix.from_npa(x))
                y_sequence_gpu.append(GpuMatrix.from_npa(y))
                input_sequence_gpu.append(GpuMatrix.from_npa(out))

            CpuMatrix.batch_hsplit(self.cpu_context, input_sequence_cpu, x_sequence_cpu, y_sequence_cpu)
            GpuMatrix.batch_hsplit(self.gpu_context, input_sequence_gpu, x_sequence_gpu, y_sequence_gpu)

            for sequence_cpu, y_sequence_gpu in [(x_sequence_cpu, x_sequence_gpu), (y_sequence_cpu, y_sequence_gpu)]:
                for a_cpu, a_gpu in izip(sequence_cpu, y_sequence_gpu):
                    if not np.allclose(a_cpu.to_host(), a_gpu.to_host()):
                        r.append(False)
                        break
                else:
                    r.append(True)

        self.assertEqual(sum(r), len(r))

    def test_assign_vstack(self):
        r = []
        for _ in xrange(self.N):
            cpu_matrices = []
            gpu_matrices = []
            ncols = self.rng.random_integers(1, 7000)
            nrows = 0
            for k in xrange(self.rng.random_integers(10)):
                _nrows = self.rng.random_integers(1000)
                matrix = self.get_random_array(shape=(_nrows, ncols))
                nrows += _nrows
                cpu_matrices.append(CpuMatrix.from_npa(matrix))
                gpu_matrices.append(GpuMatrix.from_npa(matrix))
            cpu_stacked = CpuMatrix.empty(nrows, ncols, 'float')
            gpu_stacked = GpuMatrix.empty(nrows, ncols, 'float')
            cpu_stacked.assign_vstack(self.cpu_context, cpu_matrices)
            gpu_stacked.assign_vstack(self.gpu_context, gpu_matrices)
            r.append(np.allclose(cpu_stacked.to_host(), gpu_stacked.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_vsplit(self):
        r = []
        for _ in xrange(self.N):
            cpu_matrices = []
            gpu_matrices = []
            ncols = self.rng.random_integers(1, 7000)
            nrows = [0]
            for k in xrange(self.rng.random_integers(10)):
                _nrows = self.rng.random_integers(1000)
                nrows.append(nrows[-1] + _nrows)
                cpu_matrices.append(CpuMatrix.empty(_nrows, ncols, 'float'))
                gpu_matrices.append(GpuMatrix.empty(_nrows, ncols, 'float'))
            a = self.get_random_array((nrows[-1], ncols))
            cpu_stacked = CpuMatrix.from_npa(a, 'float')
            gpu_stacked = GpuMatrix.from_npa(a, 'float')

            indxs = set(self.rng.choice(k+1, max(1, k-5), replace=False))
            row_slices = []
            _cpu_matrices = []
            _gpu_matrices = []
            for k in indxs:
                row_slices.append((nrows[k], nrows[k+1]))
                _cpu_matrices.append(cpu_matrices[k])
                _gpu_matrices.append(gpu_matrices[k])
            cpu_stacked.vsplit(self.cpu_context, _cpu_matrices, row_slices)
            gpu_stacked.vsplit(self.gpu_context, _gpu_matrices, row_slices)
            for cpu_m, gpu_m in izip(_cpu_matrices, _gpu_matrices):
                if not np.allclose(cpu_m.to_host(), gpu_m.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

            cpu_stacked.vsplit(self.cpu_context, cpu_matrices)
            gpu_stacked.vsplit(self.gpu_context, gpu_matrices)
            for cpu_m, gpu_m in izip(cpu_matrices, gpu_matrices):
                if not np.allclose(cpu_m.to_host(), gpu_m.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

        self.assertEqual(sum(r), len(r))

    def test_assign_sequential_mean_pooling(self):
        r = []
        for _ in xrange(self.N):
            a = [self.get_random_array(high=1000)]
            for _ in xrange(self.rng.random_integers(500)):
                a.append(self.get_random_array(a[-1].shape))

            a_cpu = [CpuMatrix.from_npa(each) for each in a]
            a_gpu = [GpuMatrix.from_npa(each) for each in a]

            a_cpu[0].assign_sequential_mean_pooling(self.cpu_context, a_cpu[1:])
            a_gpu[0].assign_sequential_mean_pooling(self.gpu_context, a_gpu[1:])

            r.append(np.allclose(a_cpu[0].to_host(), a_gpu[0].to_host(), atol=1e-6))

        self.assertEqual(sum(r), self.N)

    def test_sequentially_tile(self):
        r = []
        for _ in xrange(self.N):
            a = [self.get_random_array(high=1000)]
            for _ in xrange(self.rng.random_integers(500)):
                a.append(np.empty_like(a[0]))

            a_cpu = [CpuMatrix.from_npa(each) for each in a]
            a_gpu = [GpuMatrix.from_npa(each) for each in a]

            CpuMatrix.sequentially_tile(self.cpu_context, a_cpu[0], a_cpu[1:])
            GpuMatrix.sequentially_tile(self.gpu_context, a_gpu[0], a_gpu[1:])

            for a_cpu, a_gpu in izip(a_cpu[1:], a_gpu[1:]):
                if not np.allclose(a_cpu.to_host(), a_gpu.to_host()):
                    r.append(False)
                    break
            else:
                r.append(True)

        self.assertEqual(sum(r), self.N)

    def test_tile(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array((1, a.shape[1]))
            c = self.get_random_array((a.shape[0], 1))
            a_cpu = CpuMatrix.from_npa(a, 'float')
            a_gpu = GpuMatrix.from_npa(a, 'float')
            b_cpu = CpuMatrix.from_npa(b, 'float')
            b_gpu = GpuMatrix.from_npa(b, 'float')
            c_cpu = CpuMatrix.from_npa(c, 'float')
            c_gpu = GpuMatrix.from_npa(c, 'float')

            a_cpu.tile(self.cpu_context, axis=0, a=b_cpu)
            a_gpu.tile(self.gpu_context, axis=0, a=b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

            a_cpu.tile(self.cpu_context, axis=1, a=c_cpu)
            a_gpu.tile(self.gpu_context, axis=1, a=c_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_assign_repeat(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array(high=4200)
            axis = self.rng.randint(2)
            repeats = self.rng.random_integers(42)
            if axis == 0:
                b = np.empty((a.shape[0] * repeats, a.shape[1]), np.float32)
            else:
                b = np.empty((a.shape[0], a.shape[1] * repeats), np.float32)
            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            b_gpu.assign_repeat(self.gpu_context, a_gpu, repeats, axis)
            b_cpu.assign_repeat(self.cpu_context, a_cpu, repeats, axis)
            r.append(np.allclose(b_gpu.to_host(), b_cpu.to_host()))
        self.assertEqual(sum(r), len(r))

    def test_add_repeat_derivative(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array(high=4200)
            axis = self.rng.randint(2)
            repeats = self.rng.random_integers(42)
            if axis == 0:
                b = self.get_random_array((a.shape[0] * repeats, a.shape[1]))
            else:
                b = self.get_random_array((a.shape[0], a.shape[1] * repeats))
            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            a_gpu.add_repeat_derivative(self.gpu_context, b_gpu, repeats, axis)
            a_cpu.add_repeat_derivative(self.cpu_context, b_cpu, repeats, axis)
            r.append(np.allclose(a_gpu.to_host(), a_cpu.to_host()))
        self.assertEqual(sum(r), len(r))

    def test_dropout(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = np.empty_like(a)
            dropout_prob = self.rng.uniform()
            seed = self.rng.randint(1000)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            generator_cpu = CpuMatrix.get_random_generator(seed)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            generator_gpu = GpuMatrix.get_random_generator(seed)

            a_cpu.dropout(self.cpu_context, generator_cpu, dropout_prob, b_cpu)
            a_gpu.dropout(self.gpu_context, generator_gpu, dropout_prob, b_gpu)

            b_cpu = b_cpu.to_host()
            b_gpu = b_gpu.to_host()
            dropout_prob_cpu = 1.0 - np.count_nonzero(b_cpu) / float(b_cpu.size)
            dropout_prob_gpu = 1.0 - np.count_nonzero(b_gpu) / float(b_gpu.size)

            r.append(np.isclose(dropout_prob_cpu, dropout_prob_gpu, atol=1e-03) and
                     np.isclose(dropout_prob_gpu, dropout_prob, atol=1e-03))

        self.assertGreater(sum(r), int(0.9 * self.N))

    def test_assign_mask_zeros(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = (self.rng.randint(2, size=a.shape) * self.rng.rand(*a.shape)).astype(np.float32)
            c = np.empty_like(b)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            a_cpu.assign_mask_zeros(self.cpu_context, b_cpu, c_cpu)
            a_gpu.assign_mask_zeros(self.gpu_context, b_gpu, c_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_mask_zeros(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = (self.rng.randint(2, size=a.shape) * self.rng.rand(*a.shape)).astype(np.float32)
            c = np.empty_like(b)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            a_cpu.add_mask_zeros(self.cpu_context, b_cpu, c_cpu)
            a_gpu.add_mask_zeros(self.gpu_context, b_gpu, c_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_assign_masked_addition(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array(a.shape)
            c = np.empty_like(a)
            if self.rng.randint(2):
                mask = self.get_random_array(a.shape)
            else:
                mask = self.get_random_array((a.shape[0], 1))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            mask_cpu = CpuMatrix.from_npa(mask)
            a_gpu = CpuMatrix.from_npa(a)
            b_gpu = CpuMatrix.from_npa(b)
            c_gpu = CpuMatrix.from_npa(c)
            mask_gpu = CpuMatrix.from_npa(mask)

            c_cpu.assign_masked_addition(self.cpu_context, mask_cpu, a_cpu, b_cpu)
            c_gpu.assign_masked_addition(self.gpu_context, mask_gpu, a_gpu, b_gpu)
            r.append(np.allclose(c_cpu.to_host(), c_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_hprod_one_minus_mask(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array(a.shape)
            if self.rng.randint(2):
                mask = self.get_random_array(a.shape)
            else:
                mask = self.get_random_array((a.shape[0], 1))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            mask_cpu = CpuMatrix.from_npa(mask)
            a_gpu = CpuMatrix.from_npa(a)
            b_gpu = CpuMatrix.from_npa(b)
            mask_gpu = CpuMatrix.from_npa(mask)

            b_cpu.add_hprod_one_minus_mask(self.cpu_context, mask_cpu, a_cpu)
            b_gpu.add_hprod_one_minus_mask(self.gpu_context, mask_gpu, a_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_mask_column_numbers_row_wise(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            numbers = self.rng.randint(a.shape[1], size=a.shape[0]).astype(np.int32)
            numbers = numbers.reshape((numbers.size, 1))

            a_cpu = CpuMatrix.from_npa(a)
            numbers_cpu = CpuMatrix.from_npa(numbers)
            a_gpu = GpuMatrix.from_npa(a)
            numbers_gpu = GpuMatrix.from_npa(numbers)

            a_cpu.mask_column_numbers_row_wise(self.cpu_context, numbers_cpu)
            a_gpu.mask_column_numbers_row_wise(self.gpu_context, numbers_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_clip(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = np.empty_like(a)
            min_value = 2 * self.rng.rand() - 1
            max_value = 2 * self.rng.rand() - 1
            if min_value > max_value:
                min_value, max_value = max_value, min_value

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)

            a_cpu.clip(self.cpu_context, min_value, max_value, b_cpu)
            a_gpu.clip(self.gpu_context, min_value, max_value, b_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host()))

            a_cpu.clip(self.cpu_context, min_value, max_value)
            a_gpu.clip(self.gpu_context, min_value, max_value)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_tanh(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()

            a_cpu = CpuMatrix.from_npa(a)
            tanh_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            derivative_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            tanh_matrix_gpu = GpuMatrix.empty_like(a_gpu)
            derivative_matrix_gpu = GpuMatrix.empty_like(a_gpu)

            a_cpu.tanh(self.cpu_context, tanh_matrix_cpu)
            a_gpu.tanh(self.gpu_context, tanh_matrix_gpu)
            r.append(np.allclose(tanh_matrix_cpu.to_host(),
                                 tanh_matrix_gpu.to_host()))

            a_cpu.tanh(self.cpu_context, tanh_matrix_cpu, derivative_matrix_cpu)
            a_gpu.tanh(self.gpu_context, tanh_matrix_gpu, derivative_matrix_gpu)
            r.append(np.allclose(tanh_matrix_cpu.to_host(),
                                 tanh_matrix_gpu.to_host()))
            r.append(np.allclose(derivative_matrix_cpu.to_host(),
                                 derivative_matrix_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_sigmoid(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()

            a_cpu = CpuMatrix.from_npa(a)
            sigmoid_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            derivative_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            sigmoid_matrix_gpu = GpuMatrix.empty_like(a_gpu)
            derivative_matrix_gpu = GpuMatrix.empty_like(a_gpu)

            a_cpu.sigmoid(self.cpu_context, sigmoid_matrix_cpu)
            a_gpu.sigmoid(self.gpu_context, sigmoid_matrix_gpu)
            r.append(np.allclose(sigmoid_matrix_cpu.to_host(),
                                 sigmoid_matrix_gpu.to_host()))

            a_cpu.sigmoid(self.cpu_context, sigmoid_matrix_cpu, derivative_matrix_cpu)
            a_gpu.sigmoid(self.gpu_context, sigmoid_matrix_gpu, derivative_matrix_gpu)
            r.append(np.allclose(sigmoid_matrix_cpu.to_host(),
                                 sigmoid_matrix_gpu.to_host()))
            r.append(np.allclose(derivative_matrix_cpu.to_host(),
                                 derivative_matrix_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_tanh_sigm(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            for axis in [0, 1]:
                a_cpu = CpuMatrix.from_npa(a)
                tanh_sigm_matrix_cpu = CpuMatrix.empty_like(a_cpu)
                derivative_matrix_cpu = CpuMatrix.empty_like(a_cpu)
                a_gpu = GpuMatrix.from_npa(a)
                tanh_sigm_matrix_gpu = GpuMatrix.empty_like(a_gpu)
                derivative_matrix_gpu = GpuMatrix.empty_like(a_gpu)

                a_cpu.tanh_sigm(self.cpu_context, tanh_sigm_matrix_cpu, axis=axis)
                a_gpu.tanh_sigm(self.gpu_context, tanh_sigm_matrix_gpu, axis=axis)
                r.append(np.allclose(tanh_sigm_matrix_cpu.to_host(),
                                     tanh_sigm_matrix_gpu.to_host()))

                a_cpu.tanh_sigm(self.cpu_context, tanh_sigm_matrix_cpu, derivative_matrix_cpu, axis=axis)
                a_gpu.tanh_sigm(self.gpu_context, tanh_sigm_matrix_gpu, derivative_matrix_gpu, axis=axis)
                r.append(np.allclose(tanh_sigm_matrix_cpu.to_host(),
                                     tanh_sigm_matrix_gpu.to_host()))
                r.append(np.allclose(derivative_matrix_cpu.to_host(),
                                     derivative_matrix_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_relu(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()

            a_cpu = CpuMatrix.from_npa(a)
            relu_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            derivative_matrix_cpu = CpuMatrix.empty_like(a_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            relu_matrix_gpu = GpuMatrix.empty_like(a_gpu)
            derivative_matrix_gpu = GpuMatrix.empty_like(a_gpu)

            a_cpu.relu(self.cpu_context, relu_matrix_cpu)
            a_gpu.relu(self.gpu_context, relu_matrix_gpu)
            r.append(np.allclose(relu_matrix_cpu.to_host(),
                                 relu_matrix_gpu.to_host()))

            a_cpu.relu(self.cpu_context, relu_matrix_cpu, derivative_matrix_cpu)
            a_gpu.relu(self.gpu_context, relu_matrix_gpu, derivative_matrix_gpu)
            r.append(np.allclose(relu_matrix_cpu.to_host(),
                                 relu_matrix_gpu.to_host()))
            r.append(np.allclose(derivative_matrix_cpu.to_host(),
                                 derivative_matrix_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_softmax(self):
        r = []
        for _ in xrange(self.N):
            nrows = self.rng.random_integers(10000)
            ncols = self.rng.random_integers(1000)
            a = 4 * self.rng.rand(nrows, ncols).astype(np.float32) - 2
            b = np.empty_like(a)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)

            a_cpu.softmax(self.cpu_context, b_cpu)
            a_gpu.softmax(self.gpu_context, b_gpu)
            r.append(np.allclose(b_cpu.to_host(), b_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_assign_softmax_ce_derivative(self):
        r = []
        for _ in xrange(self.N):
            probs = self.get_random_array()
            target_classes = self.rng.randint(probs.shape[1], size=(probs.shape[0], 1)).astype(np.int32)
            derivative = np.empty_like(probs)

            probs_cpu = CpuMatrix.from_npa(probs)
            target_classes_cpu = CpuMatrix.from_npa(target_classes)
            derivative_cpu = CpuMatrix.from_npa(derivative)
            probs_gpu = GpuMatrix.from_npa(probs)
            target_classes_gpu = GpuMatrix.from_npa(target_classes)
            derivative_gpu = GpuMatrix.from_npa(derivative)

            derivative_cpu.assign_softmax_ce_derivative(self.cpu_context, probs_cpu, target_classes_cpu)
            derivative_gpu.assign_softmax_ce_derivative(self.gpu_context, probs_gpu, target_classes_gpu)
            r.append(np.allclose(derivative_cpu.to_host(), derivative_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_softmax_ce_derivative(self):
        r = []
        for _ in xrange(self.N):
            probs = self.get_random_array()
            target_classes = self.rng.randint(probs.shape[1], size=(probs.shape[0], 1)).astype(np.int32)
            derivative = self.get_random_array(probs.shape)

            probs_cpu = CpuMatrix.from_npa(probs)
            target_classes_cpu = CpuMatrix.from_npa(target_classes)
            derivative_cpu = CpuMatrix.from_npa(derivative)
            probs_gpu = GpuMatrix.from_npa(probs)
            target_classes_gpu = GpuMatrix.from_npa(target_classes)
            derivative_gpu = GpuMatrix.from_npa(derivative)

            derivative_cpu.add_softmax_ce_derivative(self.cpu_context, probs_cpu, target_classes_cpu)
            derivative_gpu.add_softmax_ce_derivative(self.gpu_context, probs_gpu, target_classes_gpu)
            r.append(np.allclose(derivative_cpu.to_host(), derivative_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_scale(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            alpha = ct.c_float(2 * self.rng.rand() - 1)

            a_cpu = CpuMatrix.from_npa(a)
            out_cpu = CpuMatrix.empty_like(a_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            out_gpu = GpuMatrix.empty_like(a_gpu)

            a_cpu.scale(self.cpu_context, alpha, out_cpu)
            a_gpu.scale(self.gpu_context, alpha, out_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host()))

            a_cpu.scale(self.cpu_context, alpha)
            a_gpu.scale(self.gpu_context, alpha)
            r.append(np.allclose(a_cpu.to_host(), out_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_scaled_addition_subtraction(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array(a.shape)
            c = self.get_random_array(a.shape)
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            c_cpu.assign_scaled_addition(self.cpu_context, alpha, a_cpu, b_cpu)
            c_gpu.assign_scaled_addition(self.gpu_context, alpha, a_gpu, b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

            c_cpu.assign_scaled_subtraction(self.cpu_context, alpha, a_cpu, b_cpu)
            c_gpu.assign_scaled_subtraction(self.gpu_context, alpha, a_gpu, b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

            c_cpu.add_scaled_subtraction(self.cpu_context, alpha, a_cpu, b_cpu)
            c_gpu.add_scaled_subtraction(self.gpu_context, alpha, a_gpu, b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_add_scaled_subtraction(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array(a.shape)
            c = self.get_random_array(a.shape)
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            c_cpu.add_scaled_subtraction(self.cpu_context, alpha, a_cpu, b_cpu)
            c_gpu.add_scaled_subtraction(self.gpu_context, alpha, a_gpu, b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_add_scaled_dense_matrix(self):
        r = []
        for _ in xrange(self.N):
            a = self.get_random_array()
            b = self.get_random_array(a.shape)
            c = self.get_random_array((1, a.shape[1]))
            d = np.zeros((1, a.shape[1] + 1), dtype=np.float32)
            alpha = ct.c_float(2 * self.rng.rand() - 1)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            d_cpu = CpuMatrix.from_npa(d)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            d_gpu = GpuMatrix.from_npa(d)

            a_cpu.add_scaled(self.cpu_context, alpha, b_cpu)
            a_gpu.add_scaled(self.gpu_context, alpha, b_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-6))

            a_cpu.add_scaled(self.cpu_context, alpha, c_cpu)
            a_gpu.add_scaled(self.gpu_context, alpha, c_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-6))

            try:
                a_cpu.add_scaled(self.cpu_context, alpha, d_cpu)
                r.append(False)
            except ValueError:
                r.append(True)
            try:
                a_gpu.add_scaled(self.gpu_context, alpha, d_gpu)
                r.append(False)
            except ValueError:
                r.append(True)

        self.assertEqual(sum(r), len(r))

    def test_add_scaled_sparse_matrix(self):
        r = []
        device_id = 0
        for _ in xrange(self.N):
            a = self.get_random_array()
            column_indxs = []
            column_dense_matrix = []
            for i in xrange(2):
                k = self.rng.random_integers(a.shape[1])
                column_indxs.append(self.rng.choice(a.shape[1], k).astype(np.int32))
                column_indxs[-1] = column_indxs[-1].reshape((1, k))
                column_dense_matrix.append(self.get_random_array((a.shape[0], k)))
            row_indxs = []
            row_dense_matrix = []
            for i in xrange(2):
                k = self.rng.random_integers(a.shape[0])
                row_indxs.append(self.rng.choice(a.shape[0], k).astype(np.int32))
                row_indxs[-1] = row_indxs[-1].reshape((k, 1))
                row_dense_matrix.append(self.get_random_array((k, a.shape[1])))
            batch_rows_indxs = []
            dense_matrices = []
            for i in xrange(2):
                k = self.rng.random_integers(a.shape[0])
                m = self.rng.random_integers(20)
                batch_rows_indxs.append(self.rng.choice(a.shape[0], (k, m)).astype(np.int32))
                dense_matrices.append([])
                for i in xrange(m):
                    dense_matrices[-1].append(self.get_random_array((k, a.shape[1])))
            alpha = ct.c_float(2 * self.rng.rand() - 1)

            a_gpu = GpuMatrix.from_npa(a)
            quagga.processor_type = 'gpu'
            sparse_m_gpu = SparseMatrix(device_id)
            for i in xrange(2):
                sparse_m_gpu.add_columns_slice(GpuMatrix.from_npa(column_indxs[i]),
                                               GpuMatrix.from_npa(column_dense_matrix[i]))
                sparse_m_gpu.add_rows_slice(GpuMatrix.from_npa(row_indxs[i]),
                                            GpuMatrix.from_npa(row_dense_matrix[i]))
                sparse_m_gpu.add_rows_batch_slice(GpuMatrix.from_npa(batch_rows_indxs[i]),
                                                  [GpuMatrix.from_npa(e) for e in dense_matrices[i]])

            a_cpu = CpuMatrix.from_npa(a)
            quagga.processor_type = 'cpu'
            sparse_m_cpu = SparseMatrix(device_id)
            for i in xrange(2):
                sparse_m_cpu.add_columns_slice(CpuMatrix.from_npa(column_indxs[i]),
                                               CpuMatrix.from_npa(column_dense_matrix[i]))
                sparse_m_cpu.add_rows_slice(CpuMatrix.from_npa(row_indxs[i]),
                                            CpuMatrix.from_npa(row_dense_matrix[i]))
                sparse_m_cpu.add_rows_batch_slice(CpuMatrix.from_npa(batch_rows_indxs[i]),
                                                  [CpuMatrix.from_npa(e) for e in dense_matrices[i]])

            a_cpu.add_scaled(self.cpu_context, alpha, sparse_m_cpu)
            a_gpu.add_scaled(self.gpu_context, alpha, sparse_m_gpu)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-5))

        self.assertEqual(sum(r), len(r))

    def test_assign_sum(self):
        r = []
        for _ in xrange(self.N):
            a = [TestMatrix.get_random_array()]
            for _ in xrange(self.rng.random_integers(10)):
                a.append(TestMatrix.get_random_array(a[-1].shape))

            a_cpu = [CpuMatrix.from_npa(each) for each in a]
            a_gpu = [GpuMatrix.from_npa(each) for each in a]

            a_cpu[0].assign_sum(self.cpu_context, a_cpu[1:])
            a_gpu[0].assign_sum(self.gpu_context, a_gpu[1:])

            r.append(np.allclose(a_cpu[0].to_host(), a_gpu[0].to_host(), atol=1e-6))

        self.assertEqual(sum(r), self.N)

    def test_add_sum(self):
        r = []
        for _ in xrange(self.N):
            a = [TestMatrix.get_random_array()]
            for _ in xrange(self.rng.random_integers(10)):
                a.append(TestMatrix.get_random_array(a[-1].shape))

            a_cpu = [CpuMatrix.from_npa(each) for each in a]
            a_gpu = [GpuMatrix.from_npa(each) for each in a]

            a_cpu[0].add_sum(self.cpu_context, a_cpu[1:])
            a_gpu[0].add_sum(self.gpu_context, a_gpu[1:])

            r.append(np.allclose(a_cpu[0].to_host(), a_gpu[0].to_host(), atol=1e-6))

        self.assertEqual(sum(r), self.N)

    def test_hprod(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            if self.rng.randint(2):
                b = TestMatrix.get_random_array(a.shape)
            else:
                b = TestMatrix.get_random_array((a.shape[0], 1))

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)

            a_cpu.hprod(self.cpu_context, b_cpu)
            a_gpu.hprod(self.gpu_context, b_gpu)

            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)

    def test_add_hprod(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array(a.shape)
            c = TestMatrix.get_random_array(a.shape)
            out = TestMatrix.get_random_array(a.shape)
            alpha = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            out_cpu = CpuMatrix.from_npa(out)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            out_gpu = GpuMatrix.from_npa(out)

            out_cpu.add_hprod(self.cpu_context, a_cpu, b_cpu, alpha=alpha)
            out_gpu.add_hprod(self.gpu_context, a_gpu, b_gpu, alpha=alpha)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-6))

            out_cpu.add_hprod(self.cpu_context, a_cpu, b_cpu, c_cpu, alpha)
            out_gpu.add_hprod(self.gpu_context, a_gpu, b_gpu, c_gpu, alpha)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-6))

        self.assertEqual(sum(r), len(r))

    def test_add_scaled_hprod(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array(a.shape)
            c = TestMatrix.get_random_array(a.shape)
            alpha = 2 * self.rng.rand() - 1
            beta = 2 * self.rng.rand() - 1

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            c_cpu.add_scaled_hprod(self.cpu_context, a_cpu, b_cpu, alpha, beta)
            c_gpu.add_scaled_hprod(self.gpu_context, a_gpu, b_gpu, alpha, beta)
            r.append(np.allclose(c_cpu.to_host(), c_gpu.to_host(), atol=1e-6))

        self.assertEqual(sum(r), len(r))

    def test_assign_hprod(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array(a.shape)
            c = TestMatrix.get_random_array(a.shape)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            out_cpu = CpuMatrix.empty_like(c_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            out_gpu = GpuMatrix.empty_like(c_gpu)

            out_cpu.assign_hprod(self.cpu_context, a_cpu, b_cpu, c_cpu)
            out_gpu.assign_hprod(self.gpu_context, a_gpu, b_gpu, c_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host()))

            out_cpu.assign_hprod(self.cpu_context, a_cpu, b_cpu)
            out_gpu.assign_hprod(self.gpu_context, a_gpu, b_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_assign_sum_hprod(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array(a.shape)
            c = TestMatrix.get_random_array(a.shape)
            d = TestMatrix.get_random_array(a.shape)
            e = TestMatrix.get_random_array(a.shape)
            f = TestMatrix.get_random_array(a.shape)
            g = TestMatrix.get_random_array(a.shape)
            h = TestMatrix.get_random_array(a.shape)
            i = TestMatrix.get_random_array(a.shape)
            j = TestMatrix.get_random_array(a.shape)
            k = TestMatrix.get_random_array(a.shape)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            d_cpu = CpuMatrix.from_npa(d)
            e_cpu = CpuMatrix.from_npa(e)
            f_cpu = CpuMatrix.from_npa(f)
            g_cpu = CpuMatrix.from_npa(g)
            h_cpu = CpuMatrix.from_npa(h)
            i_cpu = CpuMatrix.from_npa(i)
            j_cpu = CpuMatrix.from_npa(j)
            k_cpu = CpuMatrix.from_npa(k)
            out_cpu = CpuMatrix.empty_like(c_cpu)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            d_gpu = GpuMatrix.from_npa(d)
            e_gpu = GpuMatrix.from_npa(e)
            f_gpu = GpuMatrix.from_npa(f)
            g_gpu = GpuMatrix.from_npa(g)
            h_gpu = GpuMatrix.from_npa(h)
            i_gpu = GpuMatrix.from_npa(i)
            j_gpu = GpuMatrix.from_npa(j)
            k_gpu = GpuMatrix.from_npa(k)
            out_gpu = GpuMatrix.empty_like(c_gpu)

            out_cpu.assign_sum_hprod(self.cpu_context, a_cpu, b_cpu, c_cpu, d_cpu)
            out_gpu.assign_sum_hprod(self.gpu_context, a_gpu, b_gpu, c_gpu, d_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-6))

            out_cpu.assign_sum_hprod(self.cpu_context, a_cpu, b_cpu, c_cpu, d_cpu, e_cpu)
            out_gpu.assign_sum_hprod(self.gpu_context, a_gpu, b_gpu, c_gpu, d_gpu, e_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-6))

            out_cpu.assign_sum_hprod(self.cpu_context, a_cpu, b_cpu, c_cpu, d_cpu, e_cpu, f_cpu, g_cpu, h_cpu, i_cpu, j_cpu, k_cpu)
            out_gpu.assign_sum_hprod(self.gpu_context, a_gpu, b_gpu, c_gpu, d_gpu, e_gpu, f_gpu, g_gpu, h_gpu, i_gpu, j_gpu, k_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-5))

        self.assertEqual(sum(r), len(r))

    def test_assign_hprod_sum(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = TestMatrix.get_random_array(a.shape)

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            out_cpu = CpuMatrix.empty(a_cpu.nrows, 1)

            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            out_gpu = GpuMatrix.empty(a_gpu.nrows, 1)

            out_cpu.assign_hprod_sum(self.cpu_context, a_cpu, b_cpu)
            out_gpu.assign_hprod_sum(self.gpu_context, a_gpu, b_gpu)
            r.append(np.allclose(out_cpu.to_host(), out_gpu.to_host(), atol=1e-3))

        self.assertEqual(sum(r), self.N)

    def test_add_scaled_div_sqrt(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            b = np.abs(TestMatrix.get_random_array(a.shape))
            c = TestMatrix.get_random_array(a.shape)
            alpha = 2 * self.rng.rand() - 1
            epsilon = 2 * self.rng.rand() + 0.1

            a_cpu = CpuMatrix.from_npa(a)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            a_gpu = GpuMatrix.from_npa(a)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)

            c_cpu.add_scaled_div_sqrt(self.cpu_context, alpha, a_cpu, b_cpu, epsilon)
            c_gpu.add_scaled_div_sqrt(self.gpu_context, alpha, a_gpu, b_gpu, epsilon)
            r.append(np.allclose(c_cpu.to_host(), c_gpu.to_host()))

        self.assertEqual(sum(r), len(r))

    def test_assign_dot(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_v = TestMatrix.get_random_array((a.shape[0], 1))
            m = self.rng.randint(low=1, high=2000, size=1)[0]
            mat_op_b = self.rng.choice(['T', 'N'], 1)[0]
            mat_op_c = self.rng.choice(['T', 'N'], 1)[0]
            if mat_op_b == 'N':
                b = TestMatrix.get_random_array((a.shape[0], m))
            else:
                b = TestMatrix.get_random_array((m, a.shape[0]))
            if mat_op_c == 'N':
                c = TestMatrix.get_random_array((m, a.shape[1]))
                c_v = TestMatrix.get_random_array((m, 1))
            else:
                c = TestMatrix.get_random_array((a.shape[1], m))
                c_v = TestMatrix.get_random_array((1, m))

            a_cpu = CpuMatrix.from_npa(a)
            a_v_cpu = CpuMatrix.from_npa(a_v)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            c_v_cpu = CpuMatrix.from_npa(c_v)
            a_gpu = GpuMatrix.from_npa(a)
            a_v_gpu = GpuMatrix.from_npa(a_v)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            c_v_gpu = GpuMatrix.from_npa(c_v)

            a_cpu.assign_dot(self.cpu_context, b_cpu, c_cpu, mat_op_b, mat_op_c)
            a_gpu.assign_dot(self.gpu_context, b_gpu, c_gpu, mat_op_b, mat_op_c)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-3))

            a_v_cpu.assign_dot(self.cpu_context, b_cpu, c_v_cpu, mat_op_b, mat_op_c)
            a_v_gpu.assign_dot(self.gpu_context, b_gpu, c_v_gpu, mat_op_b, mat_op_c)
            r.append(np.allclose(a_v_cpu.to_host(), a_v_gpu.to_host(), atol=1e-3))

        self.assertEqual(sum(r), len(r))

    def test_add_dot(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()
            a_v = TestMatrix.get_random_array((a.shape[0], 1))
            m = self.rng.randint(low=1, high=2000, size=1)[0]
            mat_op_b = self.rng.choice(['T', 'N'], 1)[0]
            mat_op_c = self.rng.choice(['T', 'N'], 1)[0]
            if mat_op_b == 'N':
                b = TestMatrix.get_random_array((a.shape[0], m))
            else:
                b = TestMatrix.get_random_array((m, a.shape[0]))
            if mat_op_c == 'N':
                c = TestMatrix.get_random_array((m, a.shape[1]))
                c_v = TestMatrix.get_random_array((m, 1))
            else:
                c = TestMatrix.get_random_array((a.shape[1], m))
                c_v = TestMatrix.get_random_array((1, m))
            alpha = ct.c_float(2 * self.rng.rand() - 1)
            beta = ct.c_float(2 * self.rng.rand() - 1)

            a_cpu = CpuMatrix.from_npa(a)
            a_v_cpu = CpuMatrix.from_npa(a_v)
            b_cpu = CpuMatrix.from_npa(b)
            c_cpu = CpuMatrix.from_npa(c)
            c_v_cpu = CpuMatrix.from_npa(c_v)
            a_gpu = GpuMatrix.from_npa(a)
            a_v_gpu = GpuMatrix.from_npa(a_v)
            b_gpu = GpuMatrix.from_npa(b)
            c_gpu = GpuMatrix.from_npa(c)
            c_v_gpu = GpuMatrix.from_npa(c_v)

            a_cpu.add_dot(self.cpu_context, b_cpu, c_cpu, mat_op_b, mat_op_c, alpha, beta)
            a_gpu.add_dot(self.gpu_context, b_gpu, c_gpu, mat_op_b, mat_op_c, alpha, beta)
            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host(), atol=1e-3))

            a_v_cpu.add_dot(self.cpu_context, b_cpu, c_v_cpu, mat_op_b, mat_op_c, alpha, beta)
            a_v_gpu.add_dot(self.gpu_context, b_gpu, c_v_gpu, mat_op_b, mat_op_c, alpha, beta)
            r.append(np.allclose(a_v_cpu.to_host(), a_v_gpu.to_host(), atol=1e-3))

        self.assertEqual(sum(r), len(r))

    def test_column_argmax(self):
        r = []
        for _ in xrange(self.N):
            a = TestMatrix.get_random_array()

            a_cpu = CpuMatrix.from_npa(a)
            indxs_cpu = CpuMatrix.empty(a_cpu.nrows, 1, dtype='int')
            a_gpu = GpuMatrix.from_npa(a)
            indxs_gpu = GpuMatrix.empty(a_gpu.nrows, 1, dtype='int')

            a_cpu.argmax(self.cpu_context, indxs_cpu)
            a_gpu.argmax(self.gpu_context, indxs_gpu)

            r.append(np.allclose(a_cpu.to_host(), a_gpu.to_host()))

        self.assertEqual(sum(r), self.N)