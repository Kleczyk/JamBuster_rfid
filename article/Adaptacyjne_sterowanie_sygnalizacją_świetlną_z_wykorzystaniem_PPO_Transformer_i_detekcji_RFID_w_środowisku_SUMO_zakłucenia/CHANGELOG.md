# Rejestr zmian w `ppo_transformer_paper_compact.tex`

Data ostatniej aktualizacji: 2026-05-25

---

## Sesja 9 — Przebudowa struktury, skróty, opisy modelu, wykresy, pojazdy, bibliografia (2026-05-25)

### Zmiana 20: Przebudowa struktury sekcji

| | |
|---|---|
| **Problem** | Wstęp powtarzał treści z Related Works; sekcje „Przegląd systemu" i „Podstawy teoretyczne" były rozdzielone mimo logicznego powiązania; sekcje „Wyniki" i „Dyskusja" stanowiły osobne rozdziały bez powiązanej analizy; brak wyraźnej luki badawczej. |
| **Co zmieniono** | Przebudowano strukturę artykułu z 9 sekcji do 6: (1) Wstęp — poszerzony o 4 akapity (problem, RFID vs kamery/luka, cel, wkład); (2) Przegląd literatury — zachowane 5 podsekcji, zmieniona nazwa 2.5 na „Luka badawcza i pozycjonowanie", dodany akapit końcowy z explicite sformułowaną luką badawczą; (3) Podstawy teoretyczne i model — scalono „Przegląd systemu" + „Podstawy teoretyczne", dodano podsekcje „Koncepcja systemu", „Sformułowanie problemu jako MDP", „Funkcja nagrody", „Obcięta funkcja celu PPO", „Model zakłóceń RFID", dodano akapit „Dlaczego PPO-Transformer" na początku; (4) Metodyka i konfiguracja eksperymentów — scalono „Metodyka" + „Konfiguracja", dodano podsekcje „Architektura agenta", „Metryki oceny", „Hiperparametry", „Scenariusze ruchu", „Protokół eksperymentalny"; (5) Analiza wyników — scalono „Wyniki" + „Dyskusja", dodano podsekcje „Wydajność", „Odporność na zakłócenia", „Weryfikacja statystyczna", „Krzywe uczenia", „Analiza rozkładów", „Ograniczenia"; (6) Wnioski i kierunki przyszłych badań — dodano podsekcję „Kierunki przyszłych badań". |

### Zmiana 21: Rozwinięcie skrótów przy pierwszym użyciu

| | |
|---|---|
| **Problem** | MDP, GAE, TRPO, TraCI, TSP, EVP, V2X, ITS nie miały pełnych rozwinięć angielskich; K=2, one-hot, ε nie były wyjaśnione. |
| **Co zmieniono** | Dodano rozwinięcia: „Proces Decyzyjny Markowa (Markov Decision Process, MDP)", „uogólnioną estymację przewagi (Generalized Advantage Estimation, GAE)", „Trust Region Policy Optimization (TRPO)", „Traffic Control Interface (TraCI)", „Transit Signal Priority (TSP)", „Emergency Vehicle Preemption (EVP)", „Vehicle-to-Everything (V2X)", „(Intelligent Transport Systems, ITS)", „(Deep Reinforcement Learning, DRL)". Dodano wyjaśnienie K=2 jako „liczba niekonfliktowych faz sygnalizacji", one-hot jako „wektor, w którym aktywna faza jest oznaczona wartością 1, a pozostałe 0", ε jako „ogranicza dopuszczalny zakres zmiany ρ_t(θ) do przedziału [1−ε, 1+ε]". |

### Zmiana 22: Doprecyzowanie funkcji celu PPO

| | |
|---|---|
| **Problem** | Wzór PPO podany bez słownego wyjaśnienia celu i składowych. |
| **Co zmieniono** | Wyodrębniono podsekcję „Obcięta funkcja celu PPO" z akapitem wyjaśniającym: cel (maksymalizacja nagrody z ograniczeniem aktualizacji), dlaczego obcięta (stabilność), słowny opis ρ_t(θ), Â_t (GAE), operator min. Dodano \cite{ref5} przy wzorze. |

### Zmiana 23: Doprecyzowanie funkcji nagrody

| | |
|---|---|
| **Problem** | Brak wyjaśnienia dlaczego ujemna, brak opisu wpływu poszczególnych wag na płynność ruchu. |
| **Co zmieniono** | Wyodrębniono podsekcję „Funkcja nagrody" z: (a) explicite „ujemna = agent karany za pogarszanie warunków", (b) listą trzech kryteriów z opisem wpływu na ruch (delay = czas podróży, queue = ryzyko blokowania, stops = płynność/komfort), (c) zdaniem o rozkładzie wag i priorytecie płynności. |

### Zmiana 24: Poprawka opisu Ray Tune i Tabeli 1

| | |
|---|---|
| **Problem** | Opis optymalizacji bayesowskiej nieprecyzyjny; Tabela 1 mogła być interpretowana jako wartości startowe. |
| **Co zmieniono** | Zmieniono na: „Architektura sieci i hiperparametry algorytmu PPO zostały wyznaczone przy użyciu optymalizacji bayesowskiej zintegrowanej z biblioteką Ray Tune w języku Python". Zmieniono podpis Tabeli 1 na: „Kluczowe parametry konfiguracyjne PPO-Transformer uzyskane po optymalizacji bayesowskiej". |

### Zmiana 25: Analizy do wykresów R7 i R8

| | |
|---|---|
| **Problem** | Brak komentarza analitycznego do krzywej uczenia R7; brak opisu baseline vs noisy; brak wstępu do wykresów pudełkowych R8 tłumaczącego cel analizy rozkładów. |
| **Co zmieniono** | (a) R7: dodano akapit o dynamice krzywej uczenia (szybki wzrost → stabilizacja), opis rozjazdu baseline/noisy, komentarz o overfitting, ocena stabilności. (b) Dodano zdanie: „krzywa ewaluacji z zakłóceniami konsekwentnie osiąga niższą skumulowaną nagrodę niż krzywa baseline". (c) R8: dodano akapit wstępny wyjaśniający cel analizy rozkładów trzech metryk (opóźnienie, kolejka, zatrzymania) jako uzupełnienie analizy średnich z Tabel 4–5. |

### Zmiana 26: Identyfikacja rysunków do modyfikacji

| | |
|---|---|
| **Problem** | Rysunki R3.png, R7.png, R8.png nie mają suffixu „popr" — mogą wymagać modyfikacji dla uniknięcia problemów autorskich. |
| **Co zmieniono** | Zidentyfikowano: R1_popr.jpeg, R4 Poprawione.png, R5_popr.jpeg, R6_popr.jpeg, R9 poprawione.png — już zmodyfikowane. R3.png, R7.png, R8.png — oznaczone do ręcznego przerobienia (R7/R8 mogą być wygenerowane ponownie skryptem Python z bieżących danych treningowych; R3 wymaga ręcznej modyfikacji). NIE ZMODYFIKOWANO plików graficznych — wymaga ręcznej pracy poza Cursorem. |

### Zmiana 27: Podmiana ambulance → delivery

| | |
|---|---|
| **Problem** | Pojazdy „ambulance" (vClass=emergency, speedFactor=1.5) nie odzwierciedlają realistycznego ruchu miejskiego w SUMO — brak tunelu ratunkowego, jedynie wyższa prędkość. |
| **Co zmieniono** | (a) routes.rou.xml + routes_test.rou.xml: zmieniono vType id="ambulance" → id="delivery", vClass="delivery", accel=1.5, decel=4.0, sigma=0.5, length=7.5, maxSpeed=36.0, speedFactor=1.0, guiShape="delivery". Zmieniono nazwy flow: ambulances → delivery. (b) envs/ppo_transformer_env.py: zmieniono „ambulance" → „delivery" w 3 miejscach (komentarz, warunek vtype, odczyt counts). (c) Artykuł LaTeX: „karetki pogotowia" → „pojazdy dostawcze", „Karetki/h" → „Dostawcze/h", n_{amb} → n_{del}, „pojazdy uprzywilejowane" → „pojazdy dostawcze" w kontekście klasyfikacji. UWAGA: Wyniki w Tabelach 4–5 i na Rysunkach 7–8 uzyskano z konfiguracją ambulance — po zmianie vType wymagana jest ponowna ewaluacja (5 epizodów baseline + 5 noisy) i aktualizacja tabel/wykresów. |

### Zmiana 28: Poprawki bibliografii

| | |
|---|---|
| **Problem** | ref4: booktitle = „IEEE Xplore" (nie nazwa konferencji); ref11: journal = „arXiv (Cornell University)" (niestandardowe); ref7, ref9: URL zbyt ogólne. |
| **Co zmieniono** | ref4: booktitle → „Proc. IEEE International Conference on Intelligent Transportation Systems (ITSC)". ref11: journal → „arXiv preprint arXiv:2409.12330". ref7: dodano Publication No. FHWA-HRT-04-040 i URL path. ref9: dodano Publication No. FHWA-HOP-08-024 i URL path. ref16: DOI zweryfikowany — artykuł opublikowany w ASTRJ 2026, 20(5):372–385, bez zmian. |

---

## Sesja 8 — Testy istotności statystycznej (B2)

### Zmiana 19 (B2): Tabela testów t-Welcha + akapit interpretacyjny

| | |
|---|---|
| **Problem** | Brak testów istotności statystycznej — wyniki podane wyłącznie jako średnia ± std bez p-value. |
| **Lokalizacja** | Sekcja Wyniki, po porównaniu Tabel 4–5, przed Rysunkiem R7 |
| **Co dodano** | (a) Nową Tabelę `tab:stat` z wynikami testu t-Welcha (dwustronny, α=0,05, n=5) dla trzech metryk: opóźnienie (t=1,53, p=0,165), długość kolejki (t=1,46, p=0,182), liczba zatrzymań (t=6,00, p=0,001). Raportowane: Δ%, t, p, Cohen's d. (b) Akapit interpretacyjny: opóźnienie i kolejka NIE wykazują istotnej różnicy statystycznej → formalne potwierdzenie odporności. Jedyna istotna degradacja to zatrzymania (p<0,01), ale zmiana bezwzględna niewielka (+0,06/krok). Zastrzeżenie o małej próbie (n=5). |
| **Obliczenia** | scipy.stats Welch's t-test na bazie mean/std z Tabel 4–5 (`uv run python3`). |

---

## Sesja 7 — Cytowanie wcześniejszej pracy autorów [ref16] (A8, C2)

### Zmiana 18: Dodanie ref16 (Kleczyński, Drzał, Pawłowicz, ASTRJ 2026)

Usunięto placeholder ref25. Dodano 8 cytowań `\cite{ref16}` w: pozycjonowanie, tabela porównawcza, obserwacja, wagi nagrody, architektura, dwie głowy MLP, L=48, hiperparametry.

---

## Sesja 6 — Tabela porównawcza pozycjonowania

### Zmiana 17: Tabela cech wybranych prac (Tab. lit)

7 kolumn, 8 wierszy (6 prac + ref16 + niniejsza praca). Pokazuje unikalne cechy: PPO+Transformer, RFID, analiza odporności 20%.

---

## Sesja 5 — Sekcja Przegląd literatury (B1, D5)

### Zmiana 16: 4 podsekcje + cytowanie ref8–ref15

Klasyczne metody, RL w sterowaniu, symulacja/kalibracja, RFID w ITS. Wszystkie 8 niecytowanych referencji użytych.

---

## Sesja 4 — Korekta przepustowości (A6)

### Zmiana 15: Przeliczenie 1,65→1188 poj/h

Metryka `throughput_tls` (per-krok) × 720 = poj/h. Tabele 4–5 poprawione.

---

## Sesja 3 — Odwołania do równań i środowiska (A4, A5)

### Zmiana 13: `\label`/`\eqref` dla 12 równań

### Zmiana 14: 16→110 środowisk w Tabeli 1

---

## Sesja 2 — Błędy logiczne (A1, A2, A3)

### Zmiana 1 (A1): Przepisanie Abstractu — usunięcie porównania z Millerem

### Zmiana 2 (A2): γ wag nagrody → $w_d, w_q, w_s$

### Zmiana 3 (A3): $r_t(\theta)$ → $\rho_t(\theta)$

---

## Sesja 1 — Czyszczenie nazw plików

### Zmiany 4–12: Usunięcie `\path{}`, nazw zmiennych, ścieżek plików, nazw funkcji API
