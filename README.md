# TODO

- [ ] Cpu/GpuMatrix assertions
    - [ ] Add shape assertions into Cpu/GpuMatrix methods
    - [ ] Add shape contexts into Cpu/GpuMatrix methods
- [x] Split gpu_matrix_kernels.cu files into several
- [x] Change `ctypes` usage to `ct` abbreviation
- [ ] Add benchmarks
- [x] Implement MergeBlock
    - [ ] Implement VStackBlock
        - [ ] add VStackBlock
        - [ ] Implement vstack in Cpu/GpuMatrix classes
        - [ ] Add tests
    - [ ] Implement HStackBlock
        - [ ] add HStackBlock
        - [ ] Implement hstack kernel
        - [ ] Implement hstack in Cpu/GpuMatrix classes
        - [ ] Add tests
- [ ] Add `sigm_tanh` function to Gpu/CpuMatrix
    - [x] Implement kernel that mix sigmoid and tanh
    - [x] Add function to nonlinearities
    - [ ] Add tests
- [ ] Add different types of rnn
    - [ ] Implement NpLstmCell
        - [ ] Implement NpLstmCell block
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests
    - [ ] Implement NpLstmRnn
        - [x] Implement inner non autonomous NpLstmCell block
        - [x] Implement NpLstmRnn block
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests
    - [ ] Implement GruRnn
        - [ ] Implement GruCell
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests
    - [ ] Implement VanillaLstmRnn        
        - [ ] Implement VanillaLstmCell
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests
    - [ ] Implement VanillaRnn        
        - [ ] Implement RecurrentCell
        - [ ] Add cpu/gpu comparisons tests
        - [ ] Add finite difference tests        
- [ ] Connector improvement
    - [x] Review `update` field usage in the Connector class
    - [ ] Adapt Connector for multi-gpu purpose
- [ ] Cpu/GpuMatrix improvement    
    - [ ] Fix tests current tests
    - [ ] Review current usage of kernels
    - [ ] Synchronize Cpu/GpuMatrix classes
- [ ] Implement EmbeddingBlock
- [ ] Implement SliceBlock
- [ ] Implement LogisticRegressionCe
    - [x] Implement LogisticRegressionCe block
    - [ ] Add finite difference tests
- [ ] Implement SoftmaxCe
    - [x] Implement SoftmaxCe block
    - [ ] Add finite difference tests   
- [ ] Merge softmax and logreg    
- [ ] Implement MeanPoolingBlock
- [x] Add multi-gpu Context (http://on-demand.gputechconf.com/gtc-express/2011/presentations/cuda_webinars_multi_gpu.pdf)
- [x] Fix event creation in proper device context
- [ ] Add `activate` context in all GpuMatrix operations