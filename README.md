# TODO

- [ ] Cpu/GpuMatrix assertions
    - [ ] Add shape assertions into Cpu/GpuMatrix methods
    - [ ] Add contexts assertions into Cpu/GpuMatrix methods
- [x] Split gpu_matrix_kernels.cu files into several
- [x] Change `ctypes` usage to `ct` abbreviation
- [ ] Add benchmarks
- [x] Implement MergeBlock
    - [x] Implement VStackBlock
        - [x] add VStackBlock
        - [x] Implement vstack in Cpu/GpuMatrix classes
        - [x] Implement vsplit in Cpu/GpuMatrix classes
        - [x] Add tests
    - [x] Implement HStackBlock
        - [x] add HStackBlock
        - [x] Implement hstack kernel
        - [x] Implement hstack in Cpu/GpuMatrix classes
        - [x] Add tests
- [x] Add `sigm_tanh` function to Gpu/CpuMatrix
    - [x] Implement kernel that mix sigmoid and tanh
    - [x] Add function to nonlinearities
    - [x] Add tests
- [ ] Add different types of rnn
    - [ ] Implement NpLstmBlock
        - [ ] Implement NpLstmBlock block
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests
        - [ ] Add theano grads tests
    - [ ] Implement NpLstmRnn
        - [x] Implement inner non autonomous NpLstmCell block
        - [x] Implement NpLstmRnn block
        - [x] Add cpu/gpu comparisons tests for fprop
        - [x] Add cpu/gpu comparisons tests for bprop
        - [x] Add finite difference tests
        - [x] Add theano grads tests
    - [ ] Implement GruRnn
        - [ ] Implement GruCell
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests     
- [x] Connector improvement
    - [x] Review `update` field usage in the Connector class
    - [x] Adapt Connector for multi-gpu purpose
- [ ] Cpu/GpuMatrix improvement    
    - [ ] Fix tests current tests
    - [ ] Review current usage of kernels
    - [ ] Synchronize Cpu/GpuMatrix classes
- [x] Implement EmbeddingBlock
- [ ] Implement LogisticRegressionCe
    - [ ] Add reduction kernel for CE
    - [x] Implement LogisticRegressionCe block
    - [x] Add finite difference tests
- [ ] Implement SoftmaxCe
    - [ ] Add reduction kernel for CE
    - [x] Implement SoftmaxCe block
    - [ ] Add finite difference tests   
- [ ] Merge softmax and logreg    
- [x] Implement MeanPoolingBlock
    - [x] Implement `tile` method
    - [x] Add `tile` test
    - [x] Add tests
- [ ] Implement MaxPoolingBlock
- [x] Add multi-gpu Context (http://on-demand.gputechconf.com/gtc-express/2011/presentations/cuda_webinars_multi_gpu.pdf)
- [x] Fix event creation in proper device context
- [x] Add `activate` context in all GpuMatrix operations
- [ ] Add different types of Optimizers
    - [x] Implement SgdOptimizer
    - [ ] Implement NagOptimizer
- [x] Implement DenseBlock
    - [x] Write tests    
- [x] Implement sanity check
    - [x] implement indexing
- [x] Add Interruptions
- [ ] Add learning rate and momentum policies
    - [x] Implemented fixed learning policy
- [ ] Add reduction kernels for mean value
- [x] Change checking for `_b_usage_context` on some function or property
- [ ] Review usage of `vsplit` and `hsplit` (python code instead of c) 
- [x] check `.data` usage in the CpuMatrix probably one should replace `data` assignment with `[...]=` assignment
- [ ] check that one need to have fortran array order in `CpuMatrix`
- [ ] Split DenseBlock into nonlinearity block and dense block
- [ ] Add `Matrix` batch (assign_)addition I will use it into `Connector` bprop
- [ ] Add fast dropout LSTM
- [x] You should accept that your idea with precomputed W * x in LSTM work only for SGD and there is a very big consequences, You should revisit your ideas!
- [ ] Add broadcasting to matrix addition