# Public source and reference records

The source is **RFC 2795: The Infinite Monkey Protocol Suite (IMPS)** by S. Christey,
published on 1 April 2000. This 20-page specification describes communication,
resource requests and transcript review in a fictional monkey/typewriter network.

- [RFC Editor entry](https://www.rfc-editor.org/info/rfc2795/)
- [Original PDF in the IETF archive](https://www.ietf.org/ietf-ftp/rfc/rfc2795.txt.pdf)
- SHA256: `2572eb2cf639028f4c8e86458bce0b1442e86c9724af739dedaefd261f4bebfc`

The PDF is included unmodified, with all 20 pages and the original copyright,
permission and disclaimer text. Page-based extraction preserves source text,
headers, footers and ASCII table/diagram characters; only whitespace is normalised.

`reference_packages.json` binds the document and the four illustrative questions.
Their reference facts, minimal evidence sets and all-page relevance grades were
checked against the fixed source. These annotations are specific to the example,
separate from the private experiment references and answer-quality judgements.

| Question | Scope | Direct reference pages |
|---|---|---|
| DEMO-IMPS-Q-001 | STOP request code, permitted replies and misuse | 7, 8 and 16 together |
| DEMO-IMPS-Q-002 | Protocol for ZOO-to-BARD transcript transfer | 3, 4, 12 or 13, each sufficient |
| DEMO-IMPS-Q-003 | PAN code-0 encryption selection and discovery boundary | 15 |
| DEMO-IMPS-Q-004 | Unspecified CHIMP SEND FOOD timeout | No sufficient reference; abstention expected |

The three answerable questions have relevance grades 0/1/2 for all 20 pages.
The timeout question has no primary retrieval qrels or minimal evidence set.
Protocol codes are exact identifiers; they do not require a numeric tolerance.

The [data notebook](../../notebooks/01_data_and_evidence.ipynb) prepares the page
chunks, origins, question records and input-only manifest under ignored `local/`.
The [Classical-RAG notebook](../../notebooks/02_classical_rag.ipynb) can generate
from those inputs or replay the saved public Azure results. The
[metric notebook](../../notebooks/05_retrieval_metrics.ipynb) computes nDCG@5 and
checks whether a complete reference evidence set is present.

## Source permission

Copyright (C) The Internet Society (2000). All Rights Reserved.

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to the Internet Society or other Internet organizations, except as needed for the purpose of developing Internet standards in which case the procedures for copyrights defined in the Internet Standards process must be followed, or as required to translate it into languages other than English.
