import os
import voyageai

vo_client = voyageai.Client(api_key=os.environ["VOYAGE_API_KEY"])


def embed_text(text):
    return vo_client.embed([text], model="voyage-3").embeddings[0]
