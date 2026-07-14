#!/usr/bin/env python3
"""
Script to convert PDF to Markdown format for Cursor context.
Based on the tutorial: https://forum.cursor.com/t/tutorial-adding-full-repo-context-pdfs-and-other-docs/33925
"""

import sys
from pathlib import Path

try:
    import pymupdf  # PyMuPDF (fitz)
except ImportError:
    try:
        import fitz  # Alternative import name
    except ImportError:
        print("ERROR: PyMuPDF not installed. Installing...")
        print("Please run: pip install pymupdf")
        sys.exit(1)

def pdf_to_markdown(pdf_path: Path, output_path: Path = None) -> str:
    """
    Convert PDF file to Markdown format.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Optional path to save the Markdown file
        
    Returns:
        Markdown content as string
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Use pymupdf or fitz
    try:
        doc = pymupdf.open(str(pdf_path))
    except NameError:
        import fitz
        doc = fitz.open(str(pdf_path))
    
    # Save total pages count before processing
    total_pages = len(doc)
    
    markdown_content = []
    markdown_content.append(f"# {pdf_path.stem}\n\n")
    markdown_content.append(f"*Converted from PDF: {pdf_path.name}*\n\n")
    markdown_content.append("---\n\n")
    
    # Extract text from each page
    for page_num, page in enumerate(doc, start=1):
        markdown_content.append(f"## Page {page_num}\n\n")
        
        # Extract text
        text = page.get_text()
        
        # Clean up the text
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        # Add text content
        if cleaned_lines:
            markdown_content.append('\n'.join(cleaned_lines))
            markdown_content.append('\n\n')
        
        # Try to extract tables
        try:
            tables = page.find_tables()
            if tables:
                markdown_content.append("### Tables\n\n")
                for table in tables:
                    # Convert table to markdown format
                    table_data = table.extract()
                    if table_data:
                        # Create markdown table
                        if len(table_data) > 0:
                            # Header row
                            header = table_data[0]
                            markdown_content.append("| " + " | ".join(str(cell) if cell else "" for cell in header) + " |\n")
                            markdown_content.append("| " + " | ".join(["---"] * len(header)) + " |\n")
                            # Data rows
                            for row in table_data[1:]:
                                markdown_content.append("| " + " | ".join(str(cell) if cell else "" for cell in row) + " |\n")
                            markdown_content.append("\n")
        except Exception as e:
            # If table extraction fails, continue
            pass
        
        markdown_content.append("---\n\n")
    
    doc.close()
    
    # Join all content
    result = ''.join(markdown_content)
    
    # Save to file if output path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding='utf-8')
        print(f"✓ Converted PDF to Markdown: {output_path}")
        print(f"  Total pages: {total_pages}")
    
    return result


def main():
    """Main function to convert PDF to Markdown."""
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py <pdf_file> [output_file]")
        print("\nExample:")
        print("  python pdf_to_markdown.py article/ASTRJ-05794-2025-02.pdf article/ASTRJ-05794-2025-02.md")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        # Default output: same name with .md extension
        output_path = pdf_path.with_suffix('.md')
    
    try:
        markdown_content = pdf_to_markdown(pdf_path, output_path)
        print(f"\n✓ Conversion complete!")
        print(f"  Input:  {pdf_path}")
        print(f"  Output: {output_path}")
        print(f"  Size:   {len(markdown_content)} characters")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

