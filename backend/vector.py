from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document 
import os 

# Initialize embeddings - you can use models like 'nomic-embed-text' or 'mxbai-embed-large'
embeddings = OllamaEmbeddings(model='nomic-embed-text')

# Database location
db_loc = './vector_db'
add_documents = not os.path.exists(db_loc)

if add_documents:
    print("Creating new vector database...")
    
    # Read the text file
    with open('./professional_profile.txt', 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split content by the delimiter
    sections = content.split('---')
    
    documents = []
    for i, section in enumerate(sections):
        section = section.strip()
        if section:  # Skip empty sections
            # Extract title (first line) and content
            lines = section.split('\n', 1)
            title = lines[0].strip().rstrip(':')
            content_text = lines[1].strip() if len(lines) > 1 else section
            
            # Create document with metadata
            doc = Document(
                page_content=content_text,
                metadata={
                    'id': f'doc_{i}',
                    'title': title,
                    'section_number': i
                }
            )
            documents.append(doc)
    
    print(f"Created {len(documents)} documents")
    
    # Create and populate the vector store
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_loc
    )
    
    print("Vector database created and populated!")
    
else:
    print("Loading existing vector database...")
    # Load existing vector store
    vectorstore = Chroma(
        persist_directory=db_loc,
        embedding_function=embeddings
    )

# Test the retrieval
print("\n--- Testing Retrieval ---")
query = "What programming languages and tools do you use?"
results = vectorstore.similarity_search(query, k=3)

for i, doc in enumerate(results):
    print(f"\nResult {i+1}:")
    print(f"Title: {doc.metadata['title']}")
    print(f"Content: {doc.page_content[:200]}...")
    
# Set up retriever for use in RAG chain
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

print(f"\nRAG pipeline ready! Vector store contains {vectorstore._collection.count()} documents")
print("You can now use the 'retriever' object in your RAG chain.")