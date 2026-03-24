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



---

## Servizio

!!! info "Definizione"
    Con **servizio** si intende che un operatore connesso alla rete, detto **server**, ascolta _richieste_ da operatori, detti **client**, i quali vogliono usufruire del servizio predisposto dal **server**.

La comunicazione tra _ciascun_ **client** ed il **server** è univoca, ovvero il **server** ha tante connessioni aperte contemporaneamente quanti sono i **client** di cui vuole soddisfare la **richiesta**.

``` mermaid
graph LR
  C1[Client 1] -->|richiesta| S[Server]
  C2[Client 2] -->|richiesta| S
  C3[Client 3] -->|richiesta| S
  S -->|risposta| C1
  S -->|risposta| C2
  S -->|risposta| C3
```

---

## Ciclo di comunicazione HTTP

Ricapitoliamo un **ciclo di comunicazione HTTP**.

Tutto inizia dal client, il quale richiede al server di effettuare un'operazione sulla risorsa indicata dall'URL.

=== "Lato client"

    | Step | Operazione |
    |------|------------|
    | `c1` | Il client genera la richiesta HTTP |
    | `c2` | Il client si connette al server tramite protocollo TCP |
    | `c3` | Il client invia la richiesta e attende la risposta |
    | `c4` | Il client riceve la risposta dal server |
    | `c5` | Il client elabora la risposta |

=== "Lato server"

    | Step | Operazione |
    |------|------------|
    | `s1` | Il server è già in ascolto di eventuali connessioni in ingresso |
    | `s2` | Il server riceve la connessione del punto `c2` e la accetta |
    | `s3` | Il server riceve la richiesta inviata in `c3` |
    | `s4` | Il server effettua i controlli (validazione, esistenza, autorizzazione) |
    | `s5` | Il server elabora la richiesta producendo una risposta |
    | `s6` | Il server invia la risposta al client, che la riceve in `c4` |

``` mermaid
%%{init: {'sequence': {'actorMargin': 300}} }%%
sequenceDiagram
    participant C as Client
    participant S as Server
    Note over S: in ascolto (s1)
    Note over C: genera richiesta HTTP (c1)
    Note over C: connect (c2)
    C->>S: TCP connect
    Note over S: accept (s2)
    Note over C: send richiesta (c3)
    C->>S: richiesta HTTP
    Note over S: recv richiesta (s3)
    Note over C: attende risposta
    Note over S: validazione (s4)
    Note over S: elaborazione (s5)
    Note over S: send risposta (s6)
    S->>C: risposta HTTP
    Note over C: recv risposta (c4)
    Note over C: elabora risposta (c5)
```

---

## Più client, un solo server

!!! warning "Condizione"
    Il server è **single-core**.

Questo significa che la CPU **non** può effettuare **due o più** operazioni contemporaneamente.

Il rapporto client-server è un rapporto ==molti a uno==: più client vogliono soddisfare la propria richiesta al server. Il server però rimane sempre uno soltanto.

!!! question "Domanda"
    Può un server ==single-core== soddisfare più richieste contemporaneamente?

Per capirlo vedremo degli esempi:

- [Un client, un server.](es1_scst.md)
- [Due client, un server.](es2_scst.md)

*[TCP]: Transmission Control Protocol
*[HTTP]: HyperText Transfer Protocol
*[ACK]: Acknowledgment
*[URL]: Uniform Resource Locator
*[CPU]: Central Processing Unit
