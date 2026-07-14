"""
Test script to demonstrate the article_writer functionality.
"""

from _paths import PROJECT_ROOT  # noqa: F401 - sets up sys.path
from article_writer import open_article
from pathlib import Path

def main():
    # Open the existing article
    writer = open_article()
    
    print("Article Writer Test")
    print("=" * 50)
    
    # Get document info
    info = writer.get_document_info()
    print(f"\nCurrent document has:")
    print(f"  - {info['paragraphs']} paragraphs")
    print(f"  - {info['tables']} tables")
    print(f"  - {len(info['sections'])} sections")
    
    print("\nDocument structure analyzed successfully!")
    print("\nYou can now use the ArticleWriter class to add content:")
    print("\nExample usage:")
    print("""
    from article_writer import open_article
    
    writer = open_article()
    
    # Add a new section
    writer.add_heading('Nowa Sekcja', level=2)
    
    # Add paragraphs
    writer.add_paragraph('Tekst akapitu z odpowiednim formatowaniem...')
    
    # Add a formula
    writer.add_formula('J = A/r + B', formula_number=2, 
                      explanation='gdzie: J – gęstość prądu, r – odległość')
    
    # Add a table
    writer.add_table(
        data=[
            ['Parametr', 'Wartość', 'Jednostka'],
            ['Napięcie', '220', 'V'],
            ['Prąd', '10', 'A']
        ],
        title='Parametry układu',
        table_num=2
    )
    
    # Save the document
    writer.save()
    """)
    
    print("\nAll formatting follows the Polish academic paper format:")
    print("  - Arial font in specified sizes")
    print("  - Proper margins (1.8cm top/left/right, 2.5cm bottom)")
    print("  - First line indent 5mm")
    print("  - Justified text")
    print("  - Two-column layout support")

if __name__ == "__main__":
    main()


















