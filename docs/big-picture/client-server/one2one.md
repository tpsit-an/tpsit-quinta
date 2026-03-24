# Un client, un server

La situazione è la seguente: c'è un client, _client-1_ che vuole effettuare una richiesta al server _server-1_.

!!! warning "Condizione"
    Il server è **single-core**.

Le operazioni che verrano esaminate sono:

- Connessione (accept/connect)
- Scambio request (send/recv)
- Elaborazione della richiesta
- Invio response

<div class="grid" markdown>

``` python title="client"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(buffer_size)
sock_client.close()
```

``` python title="server"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(buffer_size)
response = elabora(request)
sa.send(response)
sa.close()
```
</div>
---

## Connessione (accept/connect)

<!-- - [ ] ^^Connessione (accept/connect)^^
- [ ] Scambio request (send/recv)
- [ ] Elaborazione della richiesta
- [ ] Invio response -->

Il server _server-1_ è in ascolto:

``` python title="server" hl_lines="4"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(buffer_size)
response = elabora(request)
sa.send(response)
sa.close()
```

Il client _client-1_ esegue la funzione `connect`:

``` python title="client" hl_lines="2"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(buffer_size)
sock_client.close()
```

La funzione `accept` si sblocca e ritorna un socket attivo `sa` connesso a _client-1_:

<div class="grid" markdown>
``` python title="Client"
sock_client.connect((IP_SERVER, 443)) # ✓ si sblocca
```

``` python title="Server"
sa = sp.accept() # ✓ si sblocca
```
</div>

!!! success "Connessione stabilita"
    Ora il socket `sa` nel server può scambiare pacchetti TCP con il socket `sock_client` nel client.

---

## Scambio request (send/recv)

<!-- - [x] Connessione (accept/connect)
- [ ] ^^Scambio request (send/recv)^^
- [ ] Elaborazione della richiesta
- [ ] Invio response -->

Successivamente, entrambi si ri-bloccano:


<div class="grid" markdown>

``` python title="Client" hl_lines="3"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(buffer_size)
sock_client.close()
```

``` python title="Server" hl_lines="5"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(buffer_size)
response = elabora(request)
sa.send(response)
sa.close()
```

</div>

Quando il server riceve i dati inviati dalla `send`, la `recv` si sblocca. Lo sblocco del client avviene quando riceve l'`ACK`[^1] dal server.

[^1]: L'**ACK** (acknowledgment) è un pacchetto TCP inviato automaticamente dal kernel per confermare la ricezione dei dati.

``` mermaid
%%{init: {'sequence': {'actorMargin': 300}} }%%
sequenceDiagram
    participant C as Client
    participant S as Server
    Note over C: send(request)
    C->>S: DATA
    Note over S: recv() si sblocca
    Note over S: invio ACK
    S->>C: ACK
    Note over C: send() si sblocca
```

## Elaborazione della richiesta


Ora il server effettua le operazioni sulla richiesta, mentre _client-1_ non fa nulla — aspetta la risposta.

<div class="grid" markdown>

``` python title="Client" hl_lines="4"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(buffer_size)
sock_client.close()
```

``` python title="Server" hl_lines="6"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(buffer_size)
response = elabora(request)
sa.send(response)
sa.close()
```

</div>

Per quanto riguarda il server, in questo caso non possiamo usare la parola **bloccato** per quanto riguarda la funzione `elabora` perché con **bloccato** intendiamo una operazione di **I/O** nel quale la CPU è ==^^inutilizzata^^==.

!!! warning "Attenzione"
    Con **bloccato** intendiamo una operazione di **I/O** nel quale la CPU è ==^^inutilizzata^^==.

!!! warning "Attenzione"
    La funzione `elabora` non è **I/O**.

## Invio response

<div class="grid" markdown>

``` python title="Client" hl_lines="4"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(buffer_size)
sock_client.close()
```

``` python title="Server" hl_lines="7"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(buffer_size)
response = elabora(request)
sa.send(response)
sa.close()
```
</div>

Quando il client riceve i dati inviati dalla send del server, la recv si sblocca. Lo sblocco del server avviene quando riceve l'ACK dal client.

<!-- Passiamo ora all'esempio due:
- [/quinta/bic-picture/es2_scst] -->

*[TCP]: Transmission Control Protocol
*[HTTP]: HyperText Transfer Protocol
*[ACK]: Acknowledgment
*[URL]: Uniform Resource Locator
*[CPU]: Central Processing Unit
