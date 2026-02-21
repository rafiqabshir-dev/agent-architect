store = []


def add(text, vector, metadata):
    store.append({"text": text, "vector": vector, "metadata": metadata})


def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    return dot / (norm_a * norm_b)


def search(query_vector, top_k=3):
    scored = []
    for chunk in store:
        score = cosine_similarity(query_vector, chunk["vector"])
        scored.append({**chunk, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
