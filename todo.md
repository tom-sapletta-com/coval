
przenies folder projektu ./coval i ./pymll do /home/tom/github/tom-sapletta-com/coval

Wygeneuj paczkę python, ktora bedzie realizowala zadania geenrowania

Projekt COVAL (generate, run, repair code with any LLM) 
generuja, uruchamia i naprawia kod w kolejnych iteracjach  w oddzielnych folderach, aby następnie
uruchomic w docker compose i nadpisywac kolejno poprzez volume pliki od najstarszych do najnowyszych
dajac w transparentny sposob tylko te najnowsze zmiany do uruchomienia z mozliwoscia usuniecia  
starego legacy code poprzez usuniecie starej iteracji i kolejno iterujac nowe zmiany lub naprawy
w tej samej formie jako nowy folder iteracji z opcja kalkulacji co sie bardziej oplaca, zmiana w starym kodzie
czy generowanie nowego i uruchomineie w srodowisku docker