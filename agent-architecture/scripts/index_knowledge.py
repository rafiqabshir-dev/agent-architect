import os
from lib import embed, vector_store


def load_knowledge():
    file_names = [f for f in os.listdir("knowledge") if f.endswith(".md")]
    file_text_chunks = []

    for file_name in file_names:
        with open(f"knowledge/{file_name}") as f:
            chunks = [c.strip() for c in f.read().split("##") if c.strip()]
            for chunk in chunks:
                file_text_chunks.append({"text": chunk, "metadata": file_name})

    for text_chunk in file_text_chunks:
        vector_store.add(
            text=text_chunk["text"],
            vector=embed.embed_text(text_chunk["text"]),
            metadata=text_chunk["metadata"],
        )

    print(f"Indexed {len(file_text_chunks)} chunks from {len(file_names)} files.")


load_knowledge()
