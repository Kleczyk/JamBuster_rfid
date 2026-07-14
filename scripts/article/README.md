# Skrypty do artykułu

Narzędzia do tworzenia, edycji i konwersji artykułu naukowego (DOCX, Markdown, PDF).

## Uruchamianie

Z katalogu głównego projektu:

```bash
python scripts/article/create_new_article.py
python scripts/article/create_article_fixed.py
python scripts/article/read_article.py
python scripts/article/markdown_to_docx.py
python scripts/article/pdf_to_markdown.py
python scripts/article/generate_figures.py
python scripts/article/generate_ppo_transformer_figures.py
```

## Zawartość

- **article_writer.py** / **article_writer_fixed.py** – moduły do zapisu treści do DOCX
- **create_new_article.py** – tworzenie nowego artykułu z szablonu
- **create_article_fixed.py** – tworzenie poprawionej wersji artykułu
- **read_article.py** – analiza struktury dokumentu
- **markdown_to_docx.py** – konwersja Markdown → DOCX
- **pdf_to_markdown.py** – konwersja PDF → Markdown
- **generate_figures.py** – generowanie wykresów (figury 1–3)
- **generate_ppo_transformer_figures.py** – wykresy dla artykułu PPO-Transformer (R7, R8)
- **image_host_server.py** – serwer HTTP do hostowania obrazów (kie.ai API)
- **test_article_writer.py** – test modułu article_writer
- **test_kie_api.py** – test API kie.ai
