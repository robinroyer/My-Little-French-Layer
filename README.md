## My Litle French Layer - MLFL

1. Download all the pdf for law code
** https://www.legifrance.gouv.fr/liste/code?etatTexte=VIGUEUR&etatTexte=VIGUEUR_DIFF

2. Extract from the pdf, the text and separate it before indexing the vector database

3. Inject in vector database Qdrant. 

** see https://huggingface.co/BAAI/bge-small-en-v1.5

4. Query LLM and adding context from RAG

** compare query.py and query_vanilla.py