# Architettura client-server: implementazione fisica.

## Livelli e tier

Con livello, in informatica, si intende di solito una **suddivisione logica** _astratta_ di un certo tipo di operazione.

Nel caso dell'architettura client-server:
> L'operazione è la visualizzazione/modifica del client di una risorsa presente nel server.

Più approfonditamente:
- Il client vuole **visualizzare [PL]** una risorsa presente online: genera una richiesta a chi possiede la risorsa (detto server).
- Il server ricevendo la richiesta deve gestirla ed elaborarla **[BLL]**, ovvero:
	- decodifica la request.
	- validazione i dati del client.
	- verificare i permessi del client.
- Il server una volta chiaro cosa deve fare e come deve re-inviarla al client, ottiene le informazioni dai propri strumenti di persistenza **[RML/PL]**:
	- Database.
	- File storage.

Abbiamo tre livelli (separazioni logiche):
- Presentation Layer.
- Business Logic Layer.
- Resource Management Layer/Persistence Layer.

Questi tre livelli possono essere eseguiti su N dispositivi fisici, qui chiamati **tier**.

## Architettura 1-tier:

Tutti i livelli astratti sono eseguiti nello stesso dispostivo (mainframe).
I terminali client non sono altro che dispositivi di I/O (schermo, mouse, tastiera).


## Architettura 2-tier:

### Modello thin

Client -> Browser
Server -> Webserver + DBMS.


## Architettura 1-tier:

Tutti i livelli astratti sono eseguiti nello stesso dispostivo (mainframe).
I terminali client non sono altro che dispositivi di I/O (schermo, mouse, tastiera).

# Reti locali e reti pubbliche

Un client non espone mai all'esterno i propri servizi, che in informatica si traduce con: un computer non esegue mai un socket passivo in ascolto di connessioni esterne.

Tali computer che fanno parte della rete locale vengono appunto detti client.

Un computer che fa parte di una rete locale e che espone i propri servizi all'esterno (ovvero espone un socket passivo in ascolto di connessioni esterne), implica che qualsiasi computer non facente parte della rete locale (sconosciuto) possa connettersi al server.

Se il server presenta delle vulnerabilità, questo può diventare un entrypoint per attività malevola.







