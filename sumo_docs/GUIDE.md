# 🗺️ Przewodnik po dokumentacji SUMO (Roadmap)

Witaj w lokalnej kopii dokumentacji **SUMO (Simulation of Urban MObility)**. SUMO to potężne narzędzie, a jego dokumentacja jest bardzo obszerna. Ten przewodnik pomoże Ci odnaleźć się w gąszczu plików i podpowie, od czego zacząć w zależności od Twoich potrzeb.

---

## 🚀 1. Pierwsze kroki (Dla początkujących)

Jeśli dopiero zaczynasz przygodę z SUMO, nie czytaj wszystkiego po kolei. Zacznij tutaj:

-   **[SUMO at a Glance](SUMO_at_a_Glance.md)**: Szybki przegląd tego, czym jest SUMO i co potrafi.
-   **[Hello World Tutorial](Tutorials/Hello_World.md)**: **Absolutna podstawa.** Dowiesz się, jak stworzyć prostą sieć dróg i puścić jeden samochód.
-   **[OSM Web Wizard](Tutorials/OSMWebWizard.md)**: Najszybszy sposób na pobranie fragmentu prawdziwego miasta (np. Twojej okolicy) i uruchomienie tam ruchu w 5 minut.
-   **[Basics/Notation](Basics/Notation.md)**: Wyjaśnia, jak czytać komendy w dokumentacji (co wpisać w terminal, a co jest parametrem).

---

## 🛣️ 2. Budowanie Świata (Sieci drogowe)

SUMO potrzebuje mapy (`.net.xml`). Możesz ją stworzyć ręcznie lub zaimportować.

-   **[Netedit](Netedit/index.md)**: Wizualny edytor sieci. To tutaj będziesz spędzać najwięcej czasu, rysując skrzyżowania, dodając sygnalizację świetlną i ścieżki rowerowe.
-   **[Network Import](Networks/Import.md)**: Jeśli masz dane z OpenStreetMap, VISUM lub Vissim, tutaj sprawdzisz, jak je skonwertować.
-   **[Sygnalizacja Świetlna](Simulation/Traffic_Lights.md)**: Jak konfigurować programy świateł, fazy i detektory.

---

## 🚗 3. Generowanie Ruchu (Popyt - Demand)

Kiedy masz już drogi, musisz "wpuścić" na nie pojazdy.

-   **[Wprowadzenie do modelowania popytu](Demand/Introduction_to_demand_modelling_in_SUMO.md)**: Kluczowy dokument wyjaśniający różnicę między trasami (routes), podróżami (trips) i przepływami (flows).
-   **[Definicje pojazdów i tras](Definition_of_Vehicles,_Vehicle_Types,_and_Routes.md)**: "Biblia" formatu XML dla pojazdów. Tu sprawdzisz parametry takie jak prędkość, przyspieszenie czy rozmiar auta.
-   **[Random Routes](Demand/Random_Routes.md)**: Jak szybko wygenerować losowy ruch do testów, gdy nie masz realnych danych.

---

## 🖥️ 4. Uruchamianie Symulacji i Analiza

-   **[SUMO-GUI](sumo-gui.md)**: Jak korzystać z interfejsu graficznego, zmieniać kolory pojazdów, śledzić konkretne auto i nagrywać wideo.
-   **[SUMO (wiersz poleceń)](sumo.md)**: Jak uruchamiać symulacje wsadowo (bez grafiki) - znacznie szybciej, idealne do uczenia maszynowego lub optymalizacji.
-   **[Przegląd plików wyjściowych (Outputs)](Simulation/Output/index.md)**: SUMO nie pokazuje wyników "na ekranie" w tabelkach – zapisuje je do plików XML. Tutaj dowiesz się, jak wyciągnąć dane o korkach, emisji spalin czy czasie przejazdu.

---

## 🐍 5. Programowanie i Automatyzacja (TraCI)

To jest sekcja, która Cię interesuje, jeśli chcesz sterować symulacją "na żywo" za pomocą Pythona (np. do Reinforcement Learning).

-   **[Wprowadzenie do TraCI](TraCI.md)**: Protokół komunikacji między SUMO a Twoim skryptem.
-   **[Interfacing TraCI from Python](TraCI/Interfacing_TraCI_from_Python.md)**: Praktyczny przewodnik, jak napisać skrypt w Pythonie, który zmienia światła lub prędkość aut w trakcie działania symulacji.
-   **[Libsumo](Libsumo.md)**: Szybsza alternatywa dla TraCI, jeśli nie potrzebujesz uruchamiać symulacji na zdalnym serwerze (często używana w projektach AI).

---

## 🛠️ 6. Narzędzia pomocnicze (Tools)

W folderze `tools/` instalacji SUMO znajdują się setki skryptów Pythona.

-   **[Indeks narzędzi](Tools/index.md)**: Opis skryptów do konwersji plików, generowania statystyk, wizualizacji danych i wielu innych. To "szwajcarski scyzoryk" użytkownika SUMO.
-   **[Sumolib](Tools/Sumolib.md)**: Biblioteka Pythona do łatwego czytania plików sieci (`.net.xml`) i innych plików XML bez konieczności parsowania ich ręcznie.

---

## ❓ Kiedy co wykorzystać? (Szybka ściąga)

| Zadanie | Gdzie zajrzeć? |
| :--- | :--- |
| **Chcę szybko zobaczyć jak to działa** | `Tutorials/OSMWebWizard.md` |
| **Muszę zmienić pierwszeństwo na skrzyżowaniu** | `Netedit/index.md` |
| **Chcę dodać autobusy i tramwaje** | `Simulation/Public_Transport.md` |
| **Symulacja jest za wolna** | `Simulation/Meso.md` (model mezoskopowy) |
| **Samochody dziwnie się zachowują (np. wjeżdżają w siebie)** | `Simulation/Safety.md` oraz `Car-Following-Models.md` |
| **Chcę wyciągnąć dane do wykresów** | `Simulation/Output/index.md` |
| **Piszę agenta AI do sterowania ruchem** | `TraCI.md` oraz `TraCI/Interfacing_TraCI_from_Python.md` |

---

## 💡 Pro Tip
Zawsze sprawdzaj **[FAQ.md](FAQ.md)** – większość problemów, na które natrafisz (teleportujące się pojazdy, brak tras, błędy XML), ma tam już gotowe rozwiązanie.

n 






