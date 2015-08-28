from collections import defaultdict
from quagga.cuda import cudart, cublas, cudnn


def _create_disabled_timing_event():
    event = cudart.ct_cuda_event()
    cudart.cuda_event_create_with_flags(event, 'disable_timing')
    return event


class GpuContext(object):
    _events = defaultdict(_create_disabled_timing_event)
    _cublas_handle = None
    _cudnn_handle = None

    def __init__(self, device_id=None):
        with cudart.device(device_id):
            self.device_id = cudart.cuda_get_device()
            self.cuda_stream = cudart.ct_cuda_stream()
            cudart.cuda_stream_create(self.cuda_stream)

    def __del__(self):
        cudart.cuda_stream_destroy(self.cuda_stream)

    @property
    def cublas_handle(self):
        cublas_handle = GpuContext._cublas_handle[self.device_id]
        cublas.cublas_set_stream(cublas_handle, self.cuda_stream)
        return cublas_handle

    @property
    def cudnn_handle(self):
        cudnn_handle = GpuContext._cudnn_handle[self.device_id]
        cudnn.cudnn_set_stream(cudnn_handle, self.cuda_stream)
        return cudnn_handle

    def synchronize(self):
        cudart.cuda_stream_synchronize(self.cuda_stream)

    def activate(self):
        cudart.cuda_set_device(self.device_id)

    def wait(self, *args):
        """
        Makes all future work submitted to context wait until
        computations ends in `args` contexts
        """

        for context in args:
            context.activate()
            event = GpuContext._events[context, self]
            cudart.cuda_event_record(event, context.cuda_stream)
            self.activate()
            cudart.cuda_stream_wait_event(self.cuda_stream, event)

    def block(self, *args):
        for context in args:
            self.activate()
            event = GpuContext._events[self, context]
            cudart.cuda_event_record(event, self.cuda_stream)
            context.activate()
            cudart.cuda_stream_wait_event(context.cuda_stream, event)

GpuContext._cublas_handle = []
GpuContext._cudnn_handle = []
for device_id in xrange(cudart.cuda_get_device_count()):
    with cudart.device(device_id):
        GpuContext._cublas_handle.append(cublas.ct_cublas_handle())
        cublas.cublas_create(GpuContext._cublas_handle[-1])
        GpuContext._cudnn_handle.append(cudnn.ct_cudnn_handle())
        cudnn.cudnn_create(GpuContext._cudnn_handle[-1])