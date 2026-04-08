# Rejestr zmian w `ppo_transformer_paper_compact.tex`

Data ostatniej aktualizacji: 2026-03-30

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
