#!/usr/bin/env python3
"""
Skrypt do konwersji artykułu Markdown do formatu DOCX z dwiema kolumnami.
"""

import re
from pathlib import Path
from _paths import PROJECT_ROOT
from article_writer_fixed import ArticleWriterFixed

def clean_markdown_text(text: str) -> str:
    """Czyści tekst z formatowania Markdown."""
    # Usuń ** (bold) - zostawiamy tekst
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    # Usuń ` (code)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Wzory inline - zostawiamy jako $...$ (będą widoczne w tekście)
    return text.strip()

def parse_markdown_to_docx(md_file_path: Path, output_docx_path: Path):
    """Parsuje plik Markdown i tworzy dokument DOCX."""
    
    # Wczytaj plik Markdown
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Utwórz writer
    writer = ArticleWriterFixed(output_docx_path)
    
    # Parsuj zawartość linia po linii
    lines = content.split('\n')
    
    title = ""
    abstract_text = ""
    keywords_text = ""
    formula_counter = 0
    table_counter = 0
    figure_counter = 0
    current_table_data = None
    current_table_title = None
    in_table = False
    in_abstract = False
    in_keywords = False
    current_paragraph_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        raw_line = lines[i]
        
        # Pomiń puste linie i separatory (---)
        if not line or line == '---' or line.startswith('*Artykuł'):
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            i += 1
            continue
        
        # Tytuł (pierwszy # na początku pliku)
        if line.startswith('# ') and not title and i < 5:
            title = line[2:].strip()
            writer.add_title(title)
            i += 1
            continue
        
        # Abstract
        if line.startswith('## Abstract'):
            in_abstract = True
            i += 1
            continue
        
        # Słowa kluczowe
        if '**Słowa kluczowe:**' in line or '**Keywords:**' in line:
            keywords_match = re.search(r'\*\*Słowa kluczowe:\*\*\s*(.+)', line, re.IGNORECASE)
            if keywords_match:
                keywords_text = keywords_match.group(1).strip()
                # Zamknij abstrakt jeśli był otwarty
                if in_abstract and abstract_text:
                    writer.add_abstract(abstract_text, abstract_text, title)
                    abstract_text = ""
                writer.add_keywords(keywords_text, keywords_text)
                in_abstract = False
                in_keywords = False
            i += 1
            continue
        
        # Zbieraj tekst abstraktu
        if in_abstract:
            if not line.startswith('##') and not line.startswith('**'):
                abstract_text += " " + line if abstract_text else line
            i += 1
            continue
        
        # Nagłówki sekcji (##)
        if line.startswith('## ') and not line.startswith('### '):
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            section_title = line[3:].strip()
            # Usuń numerację jeśli jest
            section_title = re.sub(r'^\d+\.\s*', '', section_title)
            writer.add_heading(section_title, level=2)
            i += 1
            continue
        
        # Podsekcje (###)
        if line.startswith('### '):
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            subsection_title = line[4:].strip()
            # Usuń numerację jeśli jest
            subsection_title = re.sub(r'^\d+\.\d+(\.\d+)?\s+', '', subsection_title)
            writer.add_heading(subsection_title, level=3)
            i += 1
            continue
        
        # Tytuły tabel (**Tabela X.**)
        table_title_match = re.search(r'\*\*Tabela\s+(\d+)\.\s*(.+?)\*\*', line)
        if table_title_match:
            table_counter = int(table_title_match.group(1))
            current_table_title = table_title_match.group(2).strip()
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            i += 1
            continue
        
        # Tabele (linie zaczynające się od |)
        if line.startswith('|') and '|' in line[1:]:
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            if not in_table:
                in_table = True
                current_table_data = []
            
            # Sprawdź czy następna linia to separator
            if i + 1 < len(lines) and lines[i+1].strip().startswith('|---'):
                # To jest nagłówek tabeli
                headers = [cell.strip() for cell in line.split('|')[1:-1]]
                current_table_data.append(headers)
                i += 2  # Pomiń linię separatora
                continue
            else:
                # To jest wiersz danych
                row = [cell.strip() for cell in line.split('|')[1:-1]]
                if row and any(cell for cell in row):  # Pomijamy puste wiersze
                    # Usuń formatowanie Markdown z komórek
                    row = [clean_markdown_text(cell) for cell in row]
                    current_table_data.append(row)
            i += 1
            continue
        else:
            # Zakończ tabelę jeśli była
            if in_table and current_table_data:
                if not current_table_title:
                    table_counter += 1
                    current_table_title = f"Tabela {table_counter}"
                writer.add_table(current_table_data, current_table_title, table_counter)
                current_table_data = None
                current_table_title = None
                in_table = False
        
        # Tytuły rysunków (**Rysunek X.**)
        figure_title_match = re.search(r'\*\*Rysunek\s+(\d+)\.\s*(.+?)\*\*', line, re.IGNORECASE)
        if figure_title_match:
            figure_counter = int(figure_title_match.group(1))
            caption = figure_title_match.group(2).strip()
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            writer.add_figure_caption(caption, figure_counter)
            i += 1
            continue
        
        # Obrazy (![Rysunek...](...))
        image_match = re.search(r'!\[([^\]]+)\]\(([^)]+)\)', line)
        if image_match:
            # Obrazy są już obsłużone przez tytuły rysunków, więc pomijamy
            i += 1
            continue
        
        # Wzory matematyczne ($$ ... $$)
        if '$$' in line:
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            # Wyciągnij wzór
            formula_match = re.search(r'\$\$([^\$]+)\$\$', line)
            if formula_match:
                formula_counter += 1
                formula_text = formula_match.group(1).strip()
                # Szukaj opisu po wzorze (następne linie)
                explanation = None
                j = i + 1
                explanation_lines = []
                while j < len(lines) and j < i + 3:  # Sprawdź maksymalnie 3 następne linie
                    next_line = lines[j].strip()
                    if next_line.startswith('gdzie') or next_line.startswith('where'):
                        explanation_lines.append(next_line)
                        j += 1
                        # Zbierz kolejne linie opisu aż do pustej linii
                        while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('$$'):
                            explanation_lines.append(lines[j].strip())
                            j += 1
                        break
                    j += 1
                
                if explanation_lines:
                    explanation = ' '.join(explanation_lines)
                writer.add_formula(formula_text, formula_counter, explanation)
                i = j
                continue
        
        # Listy punktowane (- lub *)
        if line.startswith('- ') or line.startswith('* '):
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            # Dodaj element listy jako akapit (uproszczone)
            list_item = line[2:].strip()
            list_item = clean_markdown_text(list_item)
            if list_item:
                writer.add_paragraph(f"• {list_item}")
            i += 1
            continue
        
        # Sekcja LITERATURA lub inne specjalne sekcje
        if line.startswith('## LITERATURA') or line.startswith('## LITERATURA'):
            # Zapisz poprzedni akapit
            if current_paragraph_lines:
                para_text = ' '.join(current_paragraph_lines)
                para_text = clean_markdown_text(para_text)
                if para_text:
                    writer.add_paragraph(para_text)
                current_paragraph_lines = []
            
            section_title = "LITERATURA"
            writer.add_heading(section_title, level=2)
            writer.add_literature_header()
            i += 1
            continue
        
        # Opisy rysunków - pomijamy na końcu
        if '**Opisy rysunków:**' in line:
            i += 1
            # Pomiń całą sekcję opisów
            while i < len(lines) and not (lines[i].strip().startswith('##')):
                i += 1
            continue
        
        # Zwykły tekst - zbieraj do akapitu
        if line and not line.startswith('**Proponowany'):
            current_paragraph_lines.append(line)
        
        i += 1
    
    # Zapisz ostatni akapit
    if current_paragraph_lines:
        para_text = ' '.join(current_paragraph_lines)
        para_text = clean_markdown_text(para_text)
        if para_text:
            writer.add_paragraph(para_text)
    
    # Dodaj końcowy break dla równych kolumn
    writer.add_continuous_break_at_end()
    
    # Zapisz
    writer.save()
    print(f"\n✓ Dokument DOCX utworzony pomyślnie!")
    print(f"  Lokalizacja: {output_docx_path}")

if __name__ == "__main__":
    md_file = PROJECT_ROOT / "article" / "comparison_architectures_smart_cities.md"
    output_file = PROJECT_ROOT / "article" / "comparison_architectures_smart_cities.docx"
    
    parse_markdown_to_docx(md_file, output_file)
