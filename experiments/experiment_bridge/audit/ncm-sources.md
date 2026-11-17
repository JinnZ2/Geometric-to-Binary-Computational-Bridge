# NCM audit source URLs

Retrieved 2026-11-17. The official repository revision inspected is c70274273f489abc73832b2b98584a8483b6b203. No repository operations with git, model training, inference, or benchmarking were performed.

Primary preprint: https://arxiv.org/abs/2610.14162

Primary paper HTML, version 1: https://arxiv.org/html/2610.14162v1

Primary paper PDF: https://arxiv.org/pdf/2610.14162

Official Stanford publication page, preprint status and author links to paper/code: https://scalingintelligence.stanford.edu/pubs/ncm/

Official author explanation and H100 speedup claims: https://scalingintelligence.stanford.edu/blogs/ncm/

Official code: https://github.com/HazyResearch/ncm

Pinned code: https://github.com/HazyResearch/ncm/tree/c70274273f489abc73832b2b98584a8483b6b203

Quantizer, configurable levels, trained EMA codebooks, prefix dropout, no distance-reject branch: https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/quant.py

Raw quantizer: https://raw.githubusercontent.com/HazyResearch/ncm/c70274273f489abc73832b2b98584a8483b6b203/models/quant.py

Released TinyStories config: https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/config/eval/tinystories.yaml

Raw config: https://raw.githubusercontent.com/HazyResearch/ncm/c70274273f489abc73832b2b98584a8483b6b203/config/eval/tinystories.yaml

Generator implementation: https://github.com/HazyResearch/ncm/blob/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py

Raw generator: https://raw.githubusercontent.com/HazyResearch/ncm/c70274273f489abc73832b2b98584a8483b6b203/models/next_concept.py

Tokenizer model: https://raw.githubusercontent.com/HazyResearch/ncm/c70274273f489abc73832b2b98584a8483b6b203/models/vqvae.py

Original nested-dropout paper: https://proceedings.mlr.press/v32/rippel14.html

Author-released checkpoint/dataset collection linked from README: https://huggingface.co/collections/hazyresearch/ncm

Claim locations in full local PDF text: sections 3.1–3.4 mechanism and dropout; section 4.6 timing; Table 5 architecture/levels; Table 6 generator parameters; Appendix D.2 timing baseline provenance; Appendix F.1.1 depth ablation; Appendix H hierarchy probes; Appendix I fixed runtime schedule and scaling limitations.
