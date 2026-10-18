# LG Build SDK — U880 / U310

[English documentation](README.en.md)

SDK C per creare applicazioni native PXO per **LG U310 e LG U880**. Lo stesso sorgente si compila per entrambi: scegliere `--target u310` oppure `--target u880`. I binari sono specifici per modello e firmware, non intercambiabili.

Compatibilità di riferimento: **U310 H3G V10a (12 ottobre 2006)** e **U880 H3G Italia V10b (8 febbraio 2006)**. Altri firmware richiedono verifica delle API e del contenitore. Questo repository contiene compilatore di pacchetti, runtime, intestazioni C e gli esempi Hello World e barre colorate. Firmware, Calcolatrice originale, chiavi, programmi e test di sblocco non sono inclusi.

## Installazione su Linux

Su Ubuntu/Debian:

```bash
sudo apt update
sudo apt install git python3 python3-venv clang lld fonts-dejavu-core
git clone https://github.com/figarocool/lg-build-sdk-u880-u310.git
cd lg-build-sdk-u880-u310
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python u310sdk.py doctor
```

`doctor` controlla Clang, LLD e le librerie Python e indica quali template mancano. È normale che manchino alla prima installazione. Non serve GCC ARM: Clang genera direttamente codice ARM926EJ-S Thumb.

## Installazione su Windows

Usare **WSL2 con Ubuntu**, quindi eseguire nel terminale Ubuntu gli stessi comandi Linux. Per installare WSL, da PowerShell amministratore:

```powershell
wsl --install -d Ubuntu
```

Riavviare se richiesto e completare la creazione dell'utente Ubuntu. Conservare il progetto nella home Linux, per esempio `~/lg-build-sdk-u880-u310`. La compilazione nativa da CMD/PowerShell non è configurata. Linux è stato verificato; la procedura Windows tramite WSL non è stata eseguita su un PC Windows durante questa pubblicazione.

## Preparare il template originale

Serve il proprio **Calculator.pxo originale**, estratto da `MODULE/UPLOAD/Pxo/Calculator.pxo` del firmware compatibile. Il file deve essere quello originale, non una Calcolatrice già sostituita da un homebrew. L'SDK verifica SHA-256 e rifiuta template differenti. Non scarica né decripta firmware.

Importare solo il modello che si desidera usare, oppure entrambi:

```bash
python u310sdk.py import-template /percorso/u310/Calculator.pxo --target u310
python u310sdk.py import-template /percorso/u880/Calculator.pxo --target u880
python u310sdk.py doctor
```

Le copie vengono conservate in `templates/`, esclusa da Git. Per applicazioni più grandi si può importare anche il file originale `Version` con `--version /percorso/Version`.

## Compilare Hello World

Per U310:

```bash
python u310sdk.py build examples/hello --target u310
python u310sdk.py inspect examples/hello/build/Calculator.pxo
```

Per U880:

```bash
python u310sdk.py build examples/hello --target u880
python u310sdk.py inspect examples/hello/build/Calculator.pxo
```

Il risultato è `examples/hello/build/Calculator.pxo`. Ogni compilazione sovrascrive l'output precedente: conservare separatamente i risultati se servono entrambi i modelli. Il rapporto JSON mostra il target, la dimensione e le rilocazioni.

Il sorgente essenziale (`examples/hello/main.c`) è:

```c
#include "u310.h"
#include "hello_bitmap.h"

void app_draw(void) {
    u310_clear(0);
    u310_draw_bitmap(0, 90, hello_bitmap);
    u310_present();
}
```

`app.json` contiene sorgenti e testo: Pillow genera `hello_bitmap.h` durante la compilazione. Il nome storico `u310.h` si usa anche per U880; il target seleziona gli adattamenti del runtime. Lo schermo è 176×220. Il tasto Indietro viene gestito dal runtime.

Per creare il proprio progetto:

```bash
python u310sdk.py new mia_app
python u310sdk.py build mia_app --target u880
```

## Eseguire sul telefono

L'esempio usa lo **slot della Calcolatrice**: conservare una copia del `Calculator.pxo` originale e sostituire quello del telefono con il PXO compilato per il modello giusto, tramite il proprio metodo di trasferimento già funzionante per `UPLOAD/Pxo/Calculator.pxo`. Riavviare e aprire **Accessori → Calcolatrice**. Compare Hello World; Indietro chiude l'app. Per ripristinare, rimettere il file originale.

Copiare il PXO sulla scheda SD come file generico non lo installa, e rinominarlo non crea una nuova voce nel menu. Questo SDK non include un uploader USB né modifica il telefono automaticamente. Per la simulazione usare il progetto separato [LG Mobile Emulator](https://github.com/figarocool/lg-mobile-emulator), con i propri firmware; i vecchi comandi locali `run`/`emulate` non fanno parte di questo SDK autonomo.

La compilazione standard conserva dimensione e somma additiva della Calcolatrice originale (42.034 byte U310, 42.030 byte U880), quindi l'Hello World non richiede un nuovo `Version`. L'opzione avanzata `build --size 0x20000` genera anche `build/Version`, se è stato importato l'originale: in quel caso il trasferimento richiede entrambi i file e il `Version` deve corrispondere agli altri PXO presenti. Iniziare dall'esempio standard.

## Limiti e verifiche

È C freestanding, senza POSIX, SDL o libc completa. Le API disponibili sono dichiarate in `include/`; non tutte le API interne del firmware sono validate su entrambi i telefoni. Gli esempi non modificano CODE, rete o SIM. Per questa pubblicazione sono stati compilati Hello World e colorbars per entrambi i target con i template originali; controllate dimensione, checksum e selezione del target. Il test di compilazione non garantisce compatibilità con firmware diversi.

Licenza source-available per uso amatoriale non commerciale: vedere [LICENSE](LICENSE), con testo italiano e riepilogo inglese. Firmware e marchi restano dei rispettivi titolari.
