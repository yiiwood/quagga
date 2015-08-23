from quagga.matrix import Matrix
from quagga.context import Context
from quagga.matrix import MatrixList
from quagga.connector import Connector


class SequentialEmbeddingBlock(object):
    def __init__(self, embedding_init, indexes, learning=True, reverse=False, device_id=None):
        self.embedding = Matrix.from_npa(embedding_init(), device_id=device_id)
        self.context = Context(device_id)
        device_id = self.context.device_id
        self.output = []
        for i in xrange(indexes.ncols):
            output = Matrix.empty(indexes.nrows, self.embedding.ncols, device_id=device_id)
            output = Connector(output, self.context, self.context if learning else None)
            self.output.append(output)
        self.output = MatrixList(self.output)
        if learning:
            self.dL_doutput = None
        self.indexes = indexes.register_usage(self.context)
        self.reverse = reverse

    def fprop(self):
        self.output.set_length(self.indexes.ncols)
        self.embedding.slice_columns(self.context, self.indexes, self.output, self.reverse)
        for output in self.output:
            output.fprop()

    def bprop(self):
        for output in self.output:
            output.bprop()
            # gather derivatives

    @property
    def params(self):
        return [self.embedding]

    @property
    def grads(self):
        return [(self.context, (self.indexes, self.output.backward_matrix))]