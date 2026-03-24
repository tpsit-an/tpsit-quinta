# Due client, un server

La situazione è la seguente: ci sono due client, _client-1_ e _client-2_, che vogliono effettuare una richiesta al server _server-1_.


!!! warning "Condizione"
    Il server è **single-core**.

Entrambi i client inviano la richiesta nello stesso momento:

``` mermaid
%%{init: {'sequence': {'actorMargin': 200}} }%%
sequenceDiagram
    participant C1 as Client-1
    participant S as Server
    participant C2 as Client-2
    Note over S: in ascolto
    C1->>S: connect
    C2->>S: connect
    Note over C1,C2: Entrambi vogliono connettersi allo stesso momento
```

Partiamo direttamente dalla conclusione della comunicazione dell'esempio precedente, quella tra _client-1_ e _server_.

<div class="grid" markdown>

``` python title="client-1" hl_lines="5"
sock_client = socket(AF_INET, SOCK_STREAM)
sock_client.connect((IP_SERVER, 443))
sock_client.send(request)
response = sock_client.recv(BS)
sock_client.close()
elabora(response)
```

``` python title="server" hl_lines="8"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
sa = sp.accept()
request = sa.recv(BS)
response = elabora(request)
sa.send(response)
sa.close()
```
</div>

---

### Nuova connessione da client-2

L'unico modo per soddisfare la richiesta de client-2 è trasformare il server in questo modo, ripartendo dall'`accept`:

``` python title="Server" hl_lines="5"
sp = socket(AF_INET, SOCK_STREAM)
sp.bind((IP_SERVER, 443))
sp.listen()
while true:
    sa = sp.accept()
    request = sa.recv(BS)
    response = elabora(request)
    sa.send(response)
    sa.close()
```

In questo modo, il _client-2_ procederà come il _client-1_.

Il problema è che _client-2_ deve aspettare che il server finisca **tutto** con _client-1_ prima di essere servito:

``` mermaid
%%{init: {'theme': 'dark'}}%%
gantt
    dateFormat YYYY-MM-DD
    axisFormat %j
    title CPU del server (single-thread)

    section Client-1
    Richiesta client-1 :milestone, m1, 2000-01-01, 0d
    accept() - I/O    :done, c1_accept, 2000-01-01, 3d
    recv() - I/O      :done, c1_recv, after c1_accept, 5d
    elabora() - CPU   :active, c1_elab, after c1_recv, 8d
    send() - I/O      :done, c1_send, after c1_elab, 5d

    section Client-2
    Richiesta client-2 :milestone, m2, 2000-01-01, 0d
    in attesa          :crit, c2_wait, 2000-01-01, 21d
    accept() - I/O    :done, c2_accept, after c2_wait, 3d
    recv() - I/O      :done, c2_recv, after c2_accept, 5d
    elabora() - CPU   :active, c2_elab, after c2_recv, 8d
    send() - I/O      :done, c2_send, after c2_elab, 5d
```

!!! note "Osservazione"
    Durante le operazioni di **I/O** (`accept`, `recv`, `send`) la CPU del server è **inutilizzata**. In un server multi-thread, quei tempi morti potrebbero essere usati per servire _client-2_.

Utilizzo effettivo della CPU:

``` mermaid
%%{init: {'theme': 'dark', 'gantt': {'displayMode': 'compact'}} }%%
gantt
    dateFormat YYYY-MM-DD
    axisFormat %j
    tickInterval 2day
    title CPU del server (single-thread) — con utilizzo CPU

    section CPU
    . :crit, cp0, 2000-01-01, 1d
    . :crit, cp1, 2000-01-03, 2d
    . :crit, cp2, 2000-01-08, 10d
    . :crit, cp3, 2000-01-21, 2d
    . :crit, cp4, 2000-01-24, 2d
    . :crit, cp5, 2000-01-29, 10d
    . :crit, cp6, 2000-02-11, 1d

    section Client-1
    accept() - I/O    :active, c1_accept, 2000-01-01, 3d
    recv() - I/O      :active, c1_recv, after c1_accept, 5d
    elabora() - CPU   :active, c1_elab, after c1_recv, 8d
    send() - I/O      :active, c1_send, after c1_elab, 5d

    section Client-2
    in attesa          :done, c2_wait, 2000-01-01, 21d
    accept() - I/O    :active, c2_accept, after c2_wait, 3d
    recv() - I/O      :active, c2_recv, after c2_accept, 5d
    elabora() - CPU   :active, c2_elab, after c2_recv, 8d
    send() - I/O      :active, c2_send, after c2_elab, 5d

```

*[TCP]: Transmission Control Protocol
*[HTTP]: HyperText Transfer Protocol
*[ACK]: Acknowledgment
*[URL]: Uniform Resource Locator
*[CPU]: Central Processing Unit
