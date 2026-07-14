"""
Script to create a new article with authors and abstract from existing article,
but with a new introduction.
"""

from _paths import PROJECT_ROOT
from article_writer import open_article
from pathlib import Path

def main():
    # Create new article document
    new_article_path = PROJECT_ROOT / "article" / "Artykuł_nowy.docx"
    writer = open_article(new_article_path)
    
    print("Creating new article...")
    print("=" * 50)
    
    # Add authors (from existing article)
    writer.add_authors([
        "Daniel KLECZYŃSKI1",
        "Jakub DRZAŁ2", 
        "Bartosz PAWŁOWICZ3"
    ])
    
    # Add affiliation
    writer.add_affiliation(
        "Politechnika Rzeszowska, Wydział Elektrotechniki i Informatyki (1), "
        "Politechnika Rzeszowska, Katedra Metrologii i Systemów Diagnostycznych (2), "
        "Politechnika Rzeszowska, Systemów Elektronicznych i Telekomunikacyjnych (3)"
    )
    
    # Add ORCID
    writer.add_orcid([
        "1. 0009-0006-6814-7043",
        "2. 0009-0004-5997-0666",
        "3. 0000-0001-9469-2754"
    ])
    
    # Add DOI (placeholder)
    writer.add_doi("10.xxxx/xxxxx")
    
    # Add title
    writer.add_title("Symulacyjne badania algorytmów uczenia maszynowego w sterowaniu ruchem drogowym")
    
    # Add abstract (Polish)
    abstract_pl = (
        "W artykule przedstawiono wyniki symulacyjnych badań algorytmów uczenia maszynowego "
        "stosowanych w zagadnieniach sterowania ruchem drogowym. Symulacje przeprowadzono w "
        "środowisku SUMO, a wyniki zaprezentowano poprzez zestawienie działania algorytmu uczenia "
        "maszynowego z klasycznymi metodami sterowania ruchem. Przedstawione wyniki wpisują się "
        "w dotychczasowe prace zespołu, w ramach których opracowano i uruchomiono fizyczną makietę "
        "sterowania ruchem, opisaną we wcześniejszych publikacjach. W końcowej części artykułu "
        "wskazano możliwe kierunki dalszych badań związanych z wykorzystaniem makiety oraz "
        "integracją rozwiązań z systemami Smart City."
    )
    
    # Add abstract (English)
    abstract_en = (
        "The article presents the results of simulation studies of machine learning algorithms "
        "used in traffic control issues. The simulations were carried out in the SUMO environment, "
        "and the results were presented by comparing the operation of the machine learning algorithm "
        "with classical traffic control methods. The presented results are part of the team's "
        "previous work, which involved the development and launch of a physical traffic control model, "
        "described in earlier publications. The final part of the article indicates possible "
        "directions for further research related to the use of the model and the integration of "
        "solutions with Smart City systems."
    )
    
    title_en = "Simulation studies of machine learning algorithms in traffic control"
    
    writer.add_abstract(abstract_pl, abstract_en, title_en)
    
    # Add keywords
    writer.add_keywords(
        "sterowanie ruchem drogowym, uczenie maszynowe, środowisko SUMO, inteligentne miasto",
        "traffic control, machine learning, SUMO environment, Smart City"
    )
    
    # Add section break (for two-column layout)
    writer.add_continuous_break()
    
    # Add new introduction
    writer.add_heading("Wstęp", level=2)
    
    writer.add_paragraph(
        "Współczesne miasta borykają się z rosnącymi problemami związanymi z zarządzaniem ruchem "
        "drogowym. Wzrastająca liczba pojazdów, dynamicznie zmieniające się natężenie ruchu oraz "
        "konieczność optymalizacji przepustowości skrzyżowań stanowią wyzwania, które wymagają "
        "nowoczesnych rozwiązań. Tradycyjne systemy sterowania ruchem, oparte na sztywnych "
        "cyklach czasowych lub prostych detektorach, często nie radzą sobie z adaptacją do "
        "zmiennych warunków ruchowych."
    )
    
    writer.add_paragraph(
        "W ostatnich latach obserwuje się dynamiczny rozwój technik uczenia maszynowego i "
        "sztucznej inteligencji, które znajdują zastosowanie w wielu dziedzinach życia. "
        "W kontekście sterowania ruchem drogowym, algorytmy uczenia maszynowego oferują możliwość "
        "automatycznego uczenia się optymalnych strategii kontroli sygnalizacji świetlnej na "
        "podstawie danych historycznych i bieżących warunków ruchowych. Rozwiązania te mogą "
        "znacząco poprawić efektywność przepływu pojazdów, redukować czas oczekiwania na "
        "skrzyżowaniach oraz zmniejszać emisję zanieczyszczeń."
    )
    
    writer.add_paragraph(
        "Środowisko symulacyjne SUMO (Simulation of Urban MObility) stanowi zaawansowane narzędzie "
        "do modelowania i analizy systemów transportowych. Dzięki swojej otwartej architekturze "
        "i bogatemu zestawowi funkcji, SUMO umożliwia przeprowadzanie realistycznych symulacji "
        "ruchu drogowego, co czyni je idealnym narzędziem do testowania i walidacji algorytmów "
        "sterowania ruchem. Integracja SUMO z frameworkami uczenia maszynowego, takimi jak "
        "SUMO-RL, otwiera nowe możliwości w zakresie badań nad inteligentnymi systemami transportowymi."
    )
    
    writer.add_paragraph(
        "Celem niniejszej pracy jest przedstawienie wyników badań symulacyjnych algorytmów uczenia "
        "maszynowego w kontekście sterowania ruchem drogowym. W artykule zaprezentowano porównanie "
        "działania algorytmu uczenia maszynowego z klasycznymi metodami sterowania, takimi jak "
        "sterowanie czasowe i sterowanie adaptacyjne. Badania przeprowadzono na modelu pojedynczego "
        "skrzyżowania, co pozwoliło na szczegółową analizę efektywności różnych podejść. Wyniki "
        "badań stanowią kontynuację prac zespołu nad fizyczną makietą sterowania ruchem, "
        "zaprezentowaną w poprzednich publikacjach."
    )
    
    writer.add_paragraph(
        "Artykuł zorganizowany jest następująco: w sekcji drugiej przedstawiono metodologię badań "
        "oraz konfigurację środowiska symulacyjnego. Sekcja trzecia zawiera opis zastosowanych "
        "algorytmów uczenia maszynowego oraz klasycznych metod sterowania. W sekcji czwartej "
        "zaprezentowano wyniki symulacji i ich analizę. Sekcja piąta zawiera dyskusję wyników "
        "oraz wskazania dotyczące dalszych kierunków badań, w tym integracji z systemami Smart City."
    )
    
    # Save the document
    writer.save()
    
    print(f"\n✓ New article created successfully!")
    print(f"  Location: {new_article_path}")
    print(f"\nArticle contains:")
    info = writer.get_document_info()
    print(f"  - {info['paragraphs']} paragraphs")
    print(f"  - {info['tables']} tables")
    print(f"  - {len(info['sections'])} sections")

if __name__ == "__main__":
    main()


















