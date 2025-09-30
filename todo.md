
przenies folder projektu ./coval i ./pymll do /home/tom/github/tom-sapletta-com/coval

Wygeneuj paczkę python, ktora bedzie realizowala zadania geenrowania

Projekt COVAL (generate, run, repair code with any LLM) 
generuja, uruchamia i naprawia kod w kolejnych iteracjach  w oddzielnych folderach, aby następnie
uruchomic w docker compose i nadpisywac kolejno poprzez volume pliki od najstarszych do najnowyszych
dajac w transparentny sposob tylko te najnowsze zmiany do uruchomienia z mozliwoscia usuniecia  
starego legacy code poprzez usuniecie starej iteracji i kolejno iterujac nowe zmiany lub naprawy
w tej samej formie jako nowy folder iteracji z opcja kalkulacji co sie bardziej oplaca, zmiana w starym kodzie
czy generowanie nowego i uruchomineie w srodowisku docker


podczas generowania plikow podawaj pelne sciezke do drzewa plikow i folderow, aby mozna bylo je sprawdzic czy istnieja i maja zawartosc
dodatkowo do kazdej pozycji pliku podawaj ilosc linii kodu i ilosc kb

Zrob refaktoryzacje kodu, podziel na komplementarne modularne komponenty, 
każdy plik kodu powinien mieć mniej niż 500 linii


na podstawie wytycznych z pliku VALIDATION.md i
dokumentacji, plikow z folderu pymll/ oraz z pliku repair.py
zrob refaktoryzacje kodu, napraw błędy logiczne w kodzie i popraw dokumentacje
oraz napisz testy, aby kod spełniał wytyczne

