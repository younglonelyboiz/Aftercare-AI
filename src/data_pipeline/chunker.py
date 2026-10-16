from langchain_text_splitters import MarkdownHeaderTextSplitter

def split_markdown_by_headers(clean_text: str) -> list:
    headers_to_split_on = [
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    
    doc_chunks = markdown_splitter.split_text(clean_text)
    
    formatted_chunks = []
    for chunk in doc_chunks:
        content = chunk.page_content.strip()
        if not content or len(content) < 20: 
            continue
            
        header_metadata = chunk.metadata
        section_title = header_metadata.get("Header_3") or header_metadata.get("Header_2") or header_metadata.get("Header_1") or "Thông tin chung"
        
        formatted_chunks.append({
            "content": content,
            "section_title": section_title.strip()
        })
        
    return formatted_chunks