# Thread-Socket-HTTP

I tre argomenti principali di quest'anno:

- [x] **Thread**
- [x] **Socket**
- [x] **Protocollo HTTP**

Sono strumenti indispensabili per il funzionamento di qualsiasi servizio.

I socket ed il protocollo HTTP sono abbastanza intuitivi nel loro funzionamento:

- i socket implementano un canale di trasmissione, con differenze sostanziali tra TCP e UDP.
- Il protocollo HTTP permette al _client_ di effettuare un'operazione su una risorsa posseduta dal _server_ attraverso un ciclo di request-response (richiesta-risposta).

I thread invece non sono facilmente descrivibili in una frase, e per capirle è necessario tornarvici sopra più volte da angolature diverse.

Ripassiamo le caratteristiche principali dei thread:

- Il thread è un processo leggero **creato da** un processo pesante.
- Un processo pesante può avere più thread in esecuzione contemporaneamente.
- I thread dello stesso processo pesante **condividono lo stesso spazio di indirizzamento**.
- Ogni processo pesante ha almeno un thread, detto Main Thread.


Argomenti propedeutici:

1. Descrizione riassuntiva dei thread.
2. La ==linea di esecuzione==.
3. La sequenzialità di esecuzione.