import os
import json
import re
import shutil
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Define exact paths relative to backend/scripts/ingest_data.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POLICIES_DIR = PROJECT_ROOT / "data" / "raw" / "policies"
CHROMA_DIR = PROJECT_ROOT / "data" / "processed" / "chroma_db"

def ingest_policies():
    print(f"Reading from: {POLICIES_DIR}")
    
    # Ensure directories exist
    if not POLICIES_DIR.exists():
        print(f"Error: Directory not found at {POLICIES_DIR}. Create it and add your .txt files.")
        return
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    
    all_chunks = []
    
    for file_path in POLICIES_DIR.glob("*.txt"):
        try:
            loader = TextLoader(str(file_path), encoding='utf-8')
            docs = loader.load()
            
            # Preserve the destination declared inside the source document when present.
            raw_text = docs[0].page_content
            metadata_match = re.search(r"METADATA:\s*(\{.*?\})", raw_text)
            source_metadata = json.loads(metadata_match.group(1)) if metadata_match else {}
            country_name = source_metadata.get("country")
            city_name = source_metadata.get("city")
            if not country_name or not city_name:
                raise ValueError(f"{file_path.name} must declare country and city metadata")
            for doc in docs:
                doc.metadata["country"] = country_name
                doc.metadata["city"] = city_name
                doc.metadata["source_file"] = file_path.name
                
            chunks = text_splitter.split_documents(docs)
            all_chunks.extend(chunks)
            print(f"Processed {file_path.name}: {len(chunks)} chunks.")
        except Exception as e:
            print(f"Failed to process {file_path.name}: {e}")
            
    if all_chunks:
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR)
        Chroma.from_documents(documents=all_chunks, embedding=embeddings, persist_directory=str(CHROMA_DIR))
        print(f"\nSuccess! {len(all_chunks)} chunks saved to {CHROMA_DIR}")
    else:
        print("No text files found to process. Please ensure they are named correctly.")

if __name__ == "__main__":
    ingest_policies()
