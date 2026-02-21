from lib.embed import embed_text
from lib.vector_store import search


def get_relevant_knowledge(query):
    embedded_query = embed_text(query)
    return search(embedded_query, 3)
