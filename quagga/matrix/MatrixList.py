class MatrixList(object):
    def __init__(self, matrices):
        self.matrices = matrices
        self.length = len(matrices)

    def set_length(self, length):
        self.length = length

    def __getitem__(self, k):
        if type(k) is slice:
            return self.matrices[k]
        elif type(k) is int:
            if -self.length <= k < self.length:
                return self.matrices[k % self.length]
            else:
                raise IndexError('MatrixContainer index out of range')
        else:
            raise TypeError('MatrixList indices must be integer or slice')

    def __iter__(self):
        return iter(self.matrices[:self.length])

    def __len__(self):
        return self.length

    def to_host(self):
        return [e.to_host() for e in self]