import quagga
import warnings
import numpy as np
import ctypes as ct
from quagga.cuda import cudart, cublas, cudnn, curand, gpu_matrix_kernels, nonlinearities


warning_messages = ['P2P comunication is not possible between:']
for i in xrange(cudart.cuda_get_device_count()):
    for j in xrange(cudart.cuda_get_device_count()):
        if i != j:
            if not cudart.cuda_device_can_access_peer(i, j):
                warning_messages.append('GPU{}->GPU{}'.format(i, j))
if len(warning_messages) != 1:
    warnings.warn(' '.join(warning_messages), UserWarning)


class GpuMatrix(object):
    def __init__(self, data, nrows, ncols, dtype, device_id, is_owner, strides=None):
        self.data = data
        self._nrows = nrows
        self._ncols = ncols
        self.dtype = dtype
        self.np_dtype, self.c_dtype = self.str_to_dtypes(dtype)
        self._cudnn_tensor_descriptor = None
        self.device_id = device_id
        self.is_owner = is_owner
        if strides:
            self.strides = strides
        else:
            elem_size = ct.sizeof(self.c_dtype)
            self.strides = (elem_size, self.nrows * elem_size)

    @property
    def nelems(self):
        return self.nrows * self.ncols

    @property
    def nrows(self):
        return self._nrows

    @nrows.setter
    def nrows(self, value):
        self._nrows = value
        if self._cudnn_tensor_descriptor:
            cudnn.destroy_tensor_descriptor(self._cudnn_tensor_descriptor)
            self._cudnn_tensor_descriptor = None

    @property
    def ncols(self):
        return self._ncols

    @ncols.setter
    def ncols(self, value):
        self._ncols = value
        if self._cudnn_tensor_descriptor:
            cudnn.destroy_tensor_descriptor(self._cudnn_tensor_descriptor)
            self._cudnn_tensor_descriptor = None

    @property
    def nbytes(self):
        return self.nelems * ct.sizeof(self.c_dtype)

    @property
    def cudnn_tensor_descriptor(self):
        if not self._cudnn_tensor_descriptor:
            self._cudnn_tensor_descriptor = cudnn.ct_cudnn_tensor_descriptor()
            cudnn.create_tensor_descriptor(self._cudnn_tensor_descriptor)
            # CUDNN uses C-order, but CUBLAS uses F-order
            cudnn.set_tensor_4d_descriptor_ex(self._cudnn_tensor_descriptor,
                                              cudnn.data_type['CUDNN_DATA_FLOAT'],
                                              self.nrows, self.ncols, 1, 1,
                                              1, self.nrows, 1, 1)
        return self._cudnn_tensor_descriptor

    def __del__(self):
        if self.is_owner:
            cudart.cuda_free(self.data)
            if self._cudnn_tensor_descriptor:
                cudnn.destroy_tensor_descriptor(self._cudnn_tensor_descriptor)

    def __getitem__(self, key):
        if type(key) is int:
            data = self._get_pointer_to_element(key, 0)
            return GpuMatrix(data, 1, self.ncols, self.dtype, self.device_id, False, self.strides)
        if type(key) is slice and self.ncols == 1:
            key = (key, 0)
        if type(key[0]) is slice and not key[0].step and type(key[1]) is int:
            stop = key[0].stop if key[0].stop else self.nrows
            start = key[0].start if key[0].start else 0
            nrows = stop - start
            data = self._get_pointer_to_element(start, key[1])
            return GpuMatrix(data, nrows, 1, self.dtype, self.device_id, False)
        if key[0] == slice(None) and type(key[1]) is slice and not key[1].step:
            stop = key[1].stop if key[1].stop else self.ncols
            start = key[1].start if key[1].start else 0
            ncols = stop - start
            data = self._get_pointer_to_column(start)
            return GpuMatrix(data, self.nrows, ncols, self.dtype, self.device_id, False)
        raise ValueError('This slice: {} is unsupported!'.format(key))

    def __setitem__(self, key, value):
        if type(key[0]) is not int or type(key[1]) is not int:
            raise ValueError('You can set only one element!')
        if key[0] > self.nrows or key[1] > self.ncols:
            raise IndexError('One of the index is out of bounds for gpu array with shape ({}, {})'.format(self.nrows, self.ncols))
        data_element = self._get_pointer_to_element(key[0], key[1])
        cudart.cuda_memcpy(data_element, ct.byref(self.c_dtype(value)), ct.sizeof(self.c_dtype), 'default')

    def same_shape(self, other):
        return self.nrows == other.nrows and self.ncols == other.ncols

    def _get_pointer_to_column(self, k):
        void_p = ct.cast(self.data, ct.c_void_p).value + self.nrows * k * ct.sizeof(self.c_dtype)
        return ct.cast(void_p, ct.POINTER(self.c_dtype))

    def _get_pointer_to_row(self, k):
        void_p = ct.cast(self.data, ct.c_void_p).value + k * ct.sizeof(self.c_dtype)
        return ct.cast(void_p, ct.POINTER(self.c_dtype))

    def _get_pointer_to_element(self, i, j):
        void_p = ct.cast(self.data, ct.c_void_p).value + (self.nrows * j + i) * ct.sizeof(self.c_dtype)
        return ct.cast(void_p, ct.POINTER(self.c_dtype))

    @staticmethod
    def str_to_dtypes(dtype):
        if dtype == 'float':
            return np.float32, ct.c_float
        if dtype == 'int':
            return np.int32, ct.c_int
        raise TypeError(u'data type {} not understood'.format(dtype))

    @staticmethod
    def array_to_dtypes(a):
        if a.dtype == np.float32:
            return 'float', np.float32, ct.c_float
        if a.dtype == np.int32:
            return 'int', np.int32, ct.c_int
        raise TypeError(u'data type {} not understood'.format(a.dtype))

    @classmethod
    def from_npa(cls, a, dtype=None, device_id=None):
        if a.ndim != 2:
            raise ValueError('GpuMatrix works only with 2-d numpy arrays!')
        if dtype:
            np_dtype, c_dtype = cls.str_to_dtypes(dtype)
        else:
            dtype, np_dtype, c_dtype = cls.array_to_dtypes(a)
        if not np.isfortran(a):
            a = np.asfortranarray(a, dtype=np_dtype)
        elif a.dtype != np_dtype:
            a = a.astype(dtype=np_dtype)
        host_data = a.ctypes.data_as(ct.POINTER(c_dtype))
        elem_size = ct.sizeof(c_dtype)
        nbytes = a.size * elem_size
        with cudart.device(device_id):
            device_id = cudart.cuda_get_device()
            data = cudart.cuda_malloc(nbytes, c_dtype)
            cudart.cuda_memcpy(data, host_data, nbytes, 'default')
        return cls(data, a.shape[0], a.shape[1], dtype, device_id, True)

    @classmethod
    def empty(cls, nrows, ncols, dtype=None, device_id=None):
        dtype = dtype if dtype else quagga.dtype
        c_dtype = cls.str_to_dtypes(dtype)[1]
        nbytes = nrows * ncols * ct.sizeof(c_dtype)
        with cudart.device(device_id):
            device_id = cudart.cuda_get_device()
            data = cudart.cuda_malloc(nbytes, c_dtype)
        return cls(data, nrows, ncols, dtype, device_id, True)

    @classmethod
    def empty_like(cls, other, device_id=None):
        nbytes = other.nelems * ct.sizeof(other.c_dtype)
        with cudart.device(device_id):
            device_id = cudart.cuda_get_device()
            data = cudart.cuda_malloc(nbytes, other.c_dtype)
        return cls(data, other.nrows, other.ncols, other.dtype, device_id, True)

    def to_device(self, context, a, nrows=None, ncols=None):
        """
        This method transfer data from `a` to allocated gpu memory

        :param context: context in which transfer will occur
        :param a: numpy array or ctypes pointer
        :param nrows: optional, is used when `a` is a pointer
        :param ncols: optional, is used when `a` is a pointer
        """

        if type(a) is np.ndarray:
            if self.np_dtype != a.dtype:
                raise ValueError("Allocated memory has {} type. "
                                 "Can't transfer {} type".
                                 format(self.np_dtype, a.dtype))
            if a.ndim != 2:
                raise ValueError('GpuMatrix works only with 2-d numpy arrays!')
            if not np.isfortran(a):
                a = np.asfortranarray(a)
            self.nrows, self.ncols = a.shape
            a = a.ctypes.data_as(ct.POINTER(self.c_dtype))
        else:
            # this branch for ctypes array
            if a._type_ != self.dtype:
                raise ValueError("Allocated memory has {} type. "
                                 "Can't transfer {} type".
                                 format(self.dtype, a._type_))
            self.nrows, self.ncols = nrows, ncols
        context.activate()
        cudart.cuda_memcpy_async(self.data, a, self.nbytes, 'default', context.cuda_stream)

    def fill(self, context, value):
        gpu_matrix_kernels.fill(context.cuda_stream, self.nelems, value, self.data)

    def sync_fill(self, value):
        a = np.empty((self.nrows, self.ncols), self.np_dtype, 'F')
        a.fill(value)
        host_data = a.ctypes.data_as(ct.POINTER(self.c_dtype))
        elem_size = ct.sizeof(self.c_dtype)
        nbytes = a.size * elem_size
        with cudart.device(self.device_id):
            cudart.cuda_memcpy(self.data, host_data, nbytes, 'default')

    def to_host(self):
        c_dtype_p = ct.POINTER(self.c_dtype)
        host_array = (self.c_dtype * self.nelems)()
        host_ptr = ct.cast(host_array, c_dtype_p)
        with cudart.device(self.device_id):
            cudart.cuda_memcpy(host_ptr, self.data, self.nbytes, 'default')
        return np.ndarray(shape=(self.nrows, self.ncols),
                          dtype=self.np_dtype,
                          buffer=host_array,
                          order='F')

    def to_list(self):
        return [self[:, i] for i in xrange(self.ncols)]

    def copy_to(self, context, out):
        """
        self -> out
        """
        context.activate()
        if out.nrows == 1 and out.strides[0] != out.strides[1]:
            # TODO: Add real stride support
            spitch = out.strides[0]
            dpitch = out.strides[1]
            cudart.cuda_memcpy2d_async(out.data, dpitch, self.data, spitch, spitch, self.nelems, 'default', context.cuda_stream)
        else:
            cudart.cuda_memcpy_async(out.data, self.data, self.nbytes, 'default', context.cuda_stream)

    def ravel(self):
        return GpuMatrix(self.data, self.nelems, 1, self.dtype, self.device_id, False)

    def reshape(self, nrows, ncols):
        return GpuMatrix(self.data, nrows, ncols, self.dtype, self.device_id, False)

    def tile(self, context, axis, a):
        context.activate()
        if axis == 0:
            if a.nrows != 1:
                raise ValueError('Invalid shape! `a` must have number of rows '
                                 'equal to one!')
            if self.ncols != a.ncols:
                raise ValueError('Invalid shape! `a` matrix must have the '
                                 'same number of columns as matrix to be tiled!')
            for i in xrange(self.nrows):
                row = self._get_pointer_to_row(i)
                cublas.s_copy(context.cublas_handle, self.ncols, a.data, 1, row, self.nrows)
        elif axis == 1:
            if a.ncols != 1:
                raise ValueError('Invalid shape! `a` must have number of '
                                 'columns equal to one!')
            if self.nrows != a.nrows:
                raise ValueError('Invalid shape! `a` matrix must have the '
                                 'same number of rows as matrix to be tiled!')
            for i in xrange(self.ncols):
                column = self._get_pointer_to_column(i)
                cublas.s_copy(context.cublas_handle, self.nrows, a.data, 1, column, 1)
        else:
            raise ValueError('Invalid axis!')

    def slice_columns(self, context, column_indxs, out, reverse=False):
        context.activate()
        if reverse:
            gpu_matrix_kernels.reverse_slice_columns(context.cuda_stream, out.nrows, out.ncols, column_indxs.data, self.data, out.data)
        else:
            gpu_matrix_kernels.slice_columns(context.cuda_stream, out.nrows, out.ncols, column_indxs.data, self.data, out.data)

    def slice_columns_and_transpose(self, context, column_indxs, out):
        context.activate()
        gpu_matrix_kernels.slice_columns_and_transpose(context.cuda_stream, out.nrows, out.ncols, column_indxs.data, self.data, out.data)

    def slice_rows(self, context, row_indxs, out):
        context.activate()
        gpu_matrix_kernels.slice_rows(context.cuda_stream, self.nrows, row_indxs.data, self.data, out.nrows, out.ncols, out.data)

    def assign_hstack(self, context, matrices):
        ncols = 0
        for matrix in matrices:
            ncols += matrix.ncols
            if matrix.nrows != self.nrows:
                raise ValueError("The number of rows in the assigning matrix "
                                 "differs from the number of rows in buffers!")
        if ncols != self.ncols:
            raise ValueError("The number of columns in the assigning matrix differs"
                             "from the summed numbers of columns in buffers!")
        context.activate()
        n = len(matrices)
        ncols = (ct.c_int * n)(*(m.ncols for m in matrices))
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
        gpu_matrix_kernels.horizontal_stack(context.cuda_stream, n, ncols, self.nrows, matrices, self.data)

    def hsplit(self, context, matrices, col_slices=None):
        context.activate()
        n = len(matrices)
        if col_slices:
            max_col = -np.inf
            for col_slice in col_slices:
                max_col = col_slice[1] if col_slice[1] > max_col else max_col
            if max_col > self.ncols:
                raise ValueError("One of the slice does not match with the array size!")
            col_slices = (ct.c_int * (2 * n))(*(sum(col_slices, ())))
            matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
            gpu_matrix_kernels.horizontal_slice_split(context.cuda_stream, n, col_slices, self.nrows, matrices, self.data)
        else:
            ncols = 0
            for matrix in matrices:
                ncols += matrix.ncols
                if matrix.nrows != self.nrows:
                    raise ValueError("The number of rows in the matrix to be split "
                                     "differs from the number of rows in buffers!")
            if ncols != self.ncols:
                raise ValueError("The number of columns in the matrix to be split differs "
                                 "from the summed numbers of columns in buffers!")
            ncols = (ct.c_int * n)(*(m.ncols for m in matrices))
            matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
            gpu_matrix_kernels.hotizontal_split(context.cuda_stream, n, ncols, self.nrows, matrices, self.data)

    @staticmethod
    def batch_horizontal_stack(context, x_sequence, y_sequence, output_sequence):
        context.activate()
        n = len(output_sequence)
        c_dtype = output_sequence[0].c_dtype
        x_matrices = (ct.POINTER(c_dtype) * n)(*(m.data for m in x_sequence))
        y_matrices = (ct.POINTER(c_dtype) * n)(*(m.data for m in y_sequence))
        output_matrices = (ct.POINTER(c_dtype) * n)(*(m.data for m in output_sequence))
        elem_size = ct.sizeof(ct.POINTER(c_dtype))
        x_device_pointer = _get_temp_memory(context, 3 * n)
        cudart.cuda_memcpy_async(x_device_pointer, x_matrices, n * elem_size, 'default', context.cuda_stream)

        void_p = ct.cast(x_device_pointer, ct.c_void_p).value + n * elem_size
        y_device_pointer = ct.cast(void_p, ct.POINTER(ct.POINTER(c_dtype)))
        cudart.cuda_memcpy_async(y_device_pointer, y_matrices, n * elem_size, 'default', context.cuda_stream)

        void_p = ct.cast(y_device_pointer, ct.c_void_p).value + n * elem_size
        output_device_pointer = ct.cast(void_p, ct.POINTER(ct.POINTER(c_dtype)))
        cudart.cuda_memcpy_async(output_device_pointer, output_matrices, n * elem_size, 'default', context.cuda_stream)

        x_ncols = x_sequence[0].ncols
        y_ncols = y_sequence[0].ncols
        nrows = output_sequence[0].nrows

        gpu_matrix_kernels.batch_horizontal_stack(context.cuda_stream, n, nrows, x_ncols, y_ncols, x_device_pointer, y_device_pointer, output_device_pointer)

    def assign_vstack(self, context, matrices):
        nrows = 0
        for matrix in matrices:
            nrows += matrix.nrows
            if matrix.ncols != self.ncols:
                raise ValueError("The number of columns in the assigning matrix "
                                 "differs from the number of columns in buffers!")
        if nrows != self.nrows:
            raise ValueError("The number of rows in the assigning matrix differs"
                             "from the summed numbers of rows in buffers!")
        context.activate()
        n = len(matrices)
        nrows = (ct.c_int * n)(*(m.nrows for m in matrices))
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
        gpu_matrix_kernels.vertical_stack(context.cuda_stream, n, nrows, self.ncols, matrices, self.data)

    def vsplit(self, context, matrices, row_slices=None):
        context.activate()
        n = len(matrices)
        if row_slices:
            max_row = -np.inf
            for row_slice in row_slices:
                max_row = row_slice[1] if row_slice[1] > max_row else max_row
            if max_row > self.nrows:
                raise ValueError("One of the slice does not match with the array size!")
            row_slices = (ct.c_int * (2 * n))(*(sum(row_slices, ())))
            matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
            gpu_matrix_kernels.vertical_slice_split(context.cuda_stream, n, row_slices, self.nrows, self.ncols, matrices, self.data)
        else:
            nrows = 0
            for matrix in matrices:
                nrows += matrix.nrows
                if matrix.ncols != self.ncols:
                    raise ValueError("The number of columns in the matrix to be split "
                                     "differs from the number of columns in buffers!")
            if nrows != self.nrows:
                raise ValueError("The number of rows in the matrix to be split differs "
                                 "from the summed numbers of rows in buffers!")
            nrows = (ct.c_int * n)(*(m.nrows for m in matrices))
            matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
            gpu_matrix_kernels.vertical_split(context.cuda_stream, n, nrows, self.ncols, matrices, self.data)

    def scale(self, context, alpha, out=None):
        context.activate()
        if out:
            gpu_matrix_kernels.scale(context.cuda_stream, self.nelems, alpha, self.data, out.data)
        else:
            cublas.s_scal(context.cublas_handle, self.nelems, alpha, self.data, 1)

    def tanh(self, context, tanh_matrix, derivative_matrix=None):
        context.activate()
        if derivative_matrix:
            nonlinearities.tanh_der(context.cuda_stream, self.nelems, self.data, tanh_matrix.data, derivative_matrix.data)
        else:
            nonlinearities.tanh(context.cuda_stream, self.nelems, self.data, tanh_matrix.data)

    def sigmoid(self, context, sigmoid_matrix, derivative_matrix=None):
        context.activate()
        if derivative_matrix:
            nonlinearities.sigmoid_der(context.cuda_stream, self.nelems, self.data, sigmoid_matrix.data, derivative_matrix.data)
        else:
            nonlinearities.sigmoid(context.cuda_stream, self.nelems, self.data, sigmoid_matrix.data)

    def tanh_sigm(self, context, tanh_sigm_matrix, derivative_matrix=None, axis=0):
        """
        This is a fancy function that is used during forward propagation into
        lstm cell. It calculates for the first 1/4 elements along the axis
        tanh function and sigmoid for the 3/4 remaining elements.
        """
        if axis not in {0, 1}:
            raise ValueError('TODO!')
        context.activate()
        if derivative_matrix:
            nonlinearities.tanh_sigm_der(context.cuda_stream, axis, self.nrows, self.ncols, self.data, tanh_sigm_matrix.data, derivative_matrix.data)
        else:
            nonlinearities.tanh_sigm(context.cuda_stream, axis, self.nrows, self.ncols, self.data, tanh_sigm_matrix.data)

    def relu(self, context, relu_matrix, derivative_matrix=None):
        context.activate()
        if derivative_matrix:
            nonlinearities.relu_der(context.cuda_stream, self.nelems, self.data, relu_matrix.data, derivative_matrix.data)
        else:
            nonlinearities.relu(context.cuda_stream, self.nelems, self.data, relu_matrix.data)

    def softmax(self, context, softmax_matrix):
        context.activate()
        cudnn.softmax_forward(context.cudnn_handle,
                                    cudnn.softmax_algorithm['CUDNN_SOFTMAX_ACCURATE'],
                                    cudnn.softmax_mode['CUDNN_SOFTMAX_MODE_INSTANCE'],
                                    ct.c_float(1.0),
                                    self.cudnn_tensor_descriptor,
                                    self.data,
                                    ct.c_float(0.0),
                                    softmax_matrix.cudnn_tensor_descriptor,
                                    softmax_matrix.data)

    def assign_scaled_addition(self, context, alpha, a, b):
        """
        self = alpha * (a + b)
        """
        context.activate()
        if a.nrows != b.nrows and a.ncols == b.ncols:
            raise ValueError('TODO!')
        gpu_matrix_kernels.assign_scaled_addition(context.cuda_stream, self.nelems, alpha, a.data, b.data, self.data)

    def assign_add(self, context, a, b):
        self.assign_scaled_addition(context, 1.0, a, b)

    def assign_scaled_subtraction(self, context, alpha, a, b):
        """
        self = alpha * (a - b)
        """
        context.activate()
        if a.nrows != b.nrows and a.ncols == b.ncols:
            raise ValueError('TODO!')
        gpu_matrix_kernels.assign_scaled_subtraction(context.cuda_stream, self.nelems, alpha, a.data, b.data, self.data)

    def assign_softmax_ce_derivative(self, context, probs, target_classes):
        gpu_matrix_kernels.softmax_ce_derivative(context.cuda_stream, probs.nrows, probs.ncols, probs.data, target_classes.data, self.data)

    def assign_sub(self, context, a, b):
        self.assign_scaled_addition(context, 1.0, a, b)

    def add_scaled(self, context, alpha, a):
        """
        self += alpha * a
        """
        context.activate()
        if self.nrows != 1 and a.nrows == 1:
            if self.ncols != a.ncols:
                raise ValueError('Operands could not be broadcast together with shapes ({},{}) ({},{})!'.format(self.nrows, self.ncols, a.nrows, a.ncols))
            gpu_matrix_kernels.matrix_vector_row_addition(context.cuda_stream, self.nrows, self.ncols, self.data, alpha, a.data, self.data)
        else:
            cublas.s_axpy(context.cublas_handle, self.nelems, alpha, a.data, 1, self.data, 1)

    def add(self, context, a):
        self.add_scaled(context, ct.c_float(1.0), a)

    def add_sum(self, context, matrices):
        context.activate()
        n = len(matrices)
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        gpu_matrix_kernels.add_sum(context.cuda_stream, self.nelems, device_pointer, n, self.data)

    def assign_sum(self, context, matrices):
        context.activate()
        n = len(matrices)
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        gpu_matrix_kernels.assign_sum(context.cuda_stream, self.nelems, device_pointer, n, self.data)

    def sub(self, context, a):
        self.add_scaled(context, ct.c_float(-1.0), a)

    def sliced_columns_add_scaled(self, context, column_indxs, alpha, a):
        """
        self[column_indxs] += alpha * a
        """
        context.activate()
        gpu_matrix_kernels.sliced_inplace_add(context.cuda_stream, a.nrows, a.ncols, alpha, a.data, column_indxs.data, self.data)

    def sliced_columns_add(self, context, column_indxs, a):
        """
        self[column_indxs] += a
        """
        self.sliced_columns_add_scaled(context, column_indxs, 1.0, a)

    def hprod(self, context, a):
        """
        self = self .* a
        """
        if self.ncols != 1 and a.ncols == 1:
            if self.nrows != a.nrows:
                raise ValueError('Operands could not be broadcast together with shapes ({},{}) ({},{})!'.format(self.nrows, self.ncols, a.nrows, a.ncols))
            context.activate()
            gpu_matrix_kernels.matrix_vector_column_hprod(context.cuda_stream, self.nrows, self.ncols, self.data, a.data, self.data)
        else:
            self.add_hprod(context, self, a, alpha=0.0)

    def add_hprod(self, context, a, b, c=None, alpha=1.0):
        """
        self = a .* b + alpha * self        or
        self = a .* b .* c + alpha * self
        """
        context.activate()
        if not c:
            gpu_matrix_kernels.add_hadamard_product_2(context.cuda_stream, self.nelems, a.data, b.data, alpha, self.data)
        else:
            gpu_matrix_kernels.add_hadamard_product_3(context.cuda_stream, self.nelems, a.data, b.data, c.data, alpha, self.data)

    def assign_hprod(self, context, a, b, c=None):
        """
        self = a .* b       or
        self = a .* b .* c
        """
        context.activate()
        if not c:
            gpu_matrix_kernels.hadamard_product_2(context.cuda_stream, a.nelems, a.data, b.data, self.data)
        else:
            gpu_matrix_kernels.hadamard_product_3(context.cuda_stream, a.nelems, a.data, b.data, c.data, self.data)

    def assign_sum_hprod(self, context, a, b, c, d, e=None, f=None, g=None, h=None, i=None, j=None, k=None):
        """
        self = a .* b + c .* d                                   or
        self = a .* b .* c + d .* e                              or
        self = a .* b .* c + d .* e + f .* g + h .* i + j .* k
        """
        context.activate()
        if k is not None:
            gpu_matrix_kernels.sum_hprod_11(context.cuda_stream, self.nelems, a.data, b.data, c.data, d.data, e.data, f.data, g.data, h.data, i.data, j.data, k.data, self.data)
        elif e is not None:
            gpu_matrix_kernels.sum_hprod_5(context.cuda_stream, self.nelems, a.data, b.data, c.data, d.data, e.data, self.data)
        else:
            gpu_matrix_kernels.sum_hprod_4(context.cuda_stream, self.nelems, a.data, b.data, c.data, d.data, self.data)

    def assign_hprod_sum(self, context, a, b):
        """
        self = sum(a .* b, axis=1)
        """
        context.activate()
        gpu_matrix_kernels.hprod_sum(context.cuda_stream, a.nrows, a.ncols, a.data, b.data, self.data)

    def assign_dot(self, context, a, b, matrix_operation_a='N', matrix_operation_b='N'):
        self.add_dot(context, a, b, matrix_operation_a, matrix_operation_b, beta=ct.c_float(0.0))

    def add_dot(self, context, a, b, matrix_operation_a='N', matrix_operation_b='N', alpha=ct.c_float(1.0), beta=ct.c_float(1.0)):
        """
        self = alpha * op(a) * b + beta * self
        """
        context.activate()
        if self.ncols == 1 and matrix_operation_b == 'N':
            cublas.s_gemv(context.cublas_handle, matrix_operation_a, a.nrows, a.ncols, alpha, a.data, a.nrows, b.data, 1, beta, self.data, 1)
        else:
            k = b.nrows if matrix_operation_b == 'N' else b.ncols
            cublas.s_gemm(context.cublas_handle, matrix_operation_a, matrix_operation_b, self.nrows, self.ncols, k, alpha, a.data, a.nrows, b.data, b.nrows, beta, self.data, self.nrows)

    def assign_sequential_mean_pooling(self, context, matrices):
        context.activate()
        n = len(matrices)
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        self.fill(context, 0.0)
        gpu_matrix_kernels.assign_sequential_mean_pooling(context.cuda_stream, self.nrows, self.ncols, device_pointer, n, self.data)

    @staticmethod
    def sequentially_tile(context, matrices, a):
        for matrix in matrices:
            if matrix.nrows != a.nrows or matrix.ncols != a.ncols:
                raise ValueError('Invalid shape! `a` matrix must have the '
                                 'same number of rows and columns as matrices '
                                 'to be tiled!')
        context.activate()
        n = len(matrices)
        matrices = (ct.POINTER(a.c_dtype) * n)(*(m.data for m in matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        gpu_matrix_kernels.sequentially_tile(context.cuda_stream, a.nelems, a.data, device_pointer, n)

    def slice_rows_batch(self, context, embd_rows_indxs, dense_matrices):
        context.activate()
        n = len(dense_matrices)
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in dense_matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        gpu_matrix_kernels.slice_rows_batch(context.cuda_stream, embd_rows_indxs.data, embd_rows_indxs.nrows, embd_rows_indxs.ncols, self.data, self.nrows, self.ncols, device_pointer)

    def sliced_rows_batch_scaled_add(self, context, embd_rows_indxs, alpha, dense_matrices):
        """
        for k in range(K):
            self[column_indxs[:, k]] += alpha * dense_matrices[k]
        """
        context.activate()
        n = len(dense_matrices)
        matrices = (ct.POINTER(self.c_dtype) * n)(*(m.data for m in dense_matrices))
        device_pointer = _get_temp_memory(context, n)
        elem_size = ct.sizeof(ct.POINTER(ct.c_float))
        cudart.cuda_memcpy_async(device_pointer, matrices, n * elem_size, 'default', context.cuda_stream)
        gpu_matrix_kernels.sliced_rows_batch_scaled_add(context.cuda_stream, embd_rows_indxs.data, embd_rows_indxs.nrows, embd_rows_indxs.ncols, alpha, device_pointer, self.nrows, self.ncols, self.data)

    @staticmethod
    def get_random_generator(seed):
        generator = curand.ct_curand_generator()
        curand.create_generator(generator, curand.curand_rng_type['CURAND_RNG_PSEUDO_DEFAULT'])
        curand.pseudo_random_generator_seed(generator, seed)
        return generator

    def dropout(self, context, generator, dropout_prob, out):
        context.activate()
        curand.set_stream(generator, context.cuda_stream)
        curand.generate_uniform(generator, out.data, self.nelems)
        gpu_matrix_kernels.dropout(context.cuda_stream, self.nelems, dropout_prob, self.data, out.data, out.data)

    def mask_zeros(self, context, mask, out):
        """
        out = self * (mask != 0)
        """
        context.activate()
        gpu_matrix_kernels.mask_zeros(context.cuda_stream, self.nelems, self.data, mask.data, out.data)

    def mask_column_numbers_row_wise(self, context, numbers):
        """
        self[i, j] = j < numbers[i]
        """
        context.activate()
        gpu_matrix_kernels.mask_column_numbers_row_wise(context.cuda_stream, self.nrows, self.ncols, numbers.data, self.data)


def _get_temp_memory(context, N):
    global __temp_pointer
    global __N
    pointer = __temp_pointer.get(context)
    if N > __N.get(context, -np.inf):
        if pointer:
            cudart.cuda_free(pointer)
        __N[context] = N + 10
        c_dtype = ct.POINTER(ct.c_float)
        elem_size = ct.sizeof(c_dtype)
        pointer = cudart.cuda_malloc(__N[context] * elem_size, c_dtype)
        __temp_pointer[context] = pointer
    return pointer


__temp_pointer = {}
__N = {}