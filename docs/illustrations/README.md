# Illustrated baseline workflows

The two vector PDFs follow indexing, retrieval, answer generation, source
traceability and retrieval evaluation:

- [Classical RAG workflow](classical-rag-workflow.pdf): Figures 18-22, six pages.
- [GraphRAG Local Search workflow](graphrag-workflow.pdf): Figures 7-17, twelve pages.

Figure and reference numbers match Appendices F-I of the master's thesis.
Each guide includes its own scope, notation and bibliography. The fictional
planetarium example illustrates the method; its passages, records, responses
and numeric values are constructed. It is separate from the runnable RFC 2795
example in the notebooks.

The [SVG sources and page text](source/) remain editable. To rebuild both PDFs,
use Python with `reportlab` and `pypdf`, plus Inkscape:

```console
python docs/illustrations/source/build.py --inkscape inkscape
```

Pass the Inkscape executable path when it is outside `PATH`. These tools are only
needed to maintain the illustrations; they are not pipeline dependencies.
After changes, render and visually check every page, verify the method against
the notebooks and thesis, and renew the exported package's code binding.
