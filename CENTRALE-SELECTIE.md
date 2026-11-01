# Eén centrale nieuwsselectie — ontwerp

Status: voorbereid, nog niet gekoppeld aan de dagelijkse ChatGPT-taak.

## Doel
Het dashboard, de ChatGPT-briefing en het voorleesscript gebruiken exact dezelfde gecureerde nieuwsitems, in dezelfde volgorde. Maximaal 15 minuten leestijd en maximaal 15 minuten luistertijd. Business English en podcasts staan los van de nieuwstijd.

## Voorstel gegevenscontract
Een dagelijkse publicatie bevat:
- date (Europe/Amsterdam, YYYY-MM-DD)
- updated (ISO-8601)
- selection_mode: "curated"
- articles: 8–15 items met id, category, source, title, url, summary, relevance, published
- narration: Nederlandstalig script uitsluitend gebaseerd op de items in articles
- item_ids: lijst van artikel-id's in exact dezelfde volgorde als articles
- estimated_read_minutes en estimated_listen_minutes, beide maximaal 15

## Publicatievoorwaarden
1. De nieuwsselectie wordt op één plek samengesteld en op feiten en bronlinks gecontroleerd.
2. Publicatie weigeren als item_ids afwijkt van articles, er dubbele URL's zijn, bronnen ontbreken of een tijdslimiet wordt overschreden.
3. Audio is optioneel en mag pas als beschikbaar worden aangeduid wanneer daadwerkelijk gegenereerd en bereikbaar.
4. De huidige RSS-automatisering mag een gecureerde selectie niet overschrijven.
5. De bestaande ChatGPT-automatisering schrijft momenteel niet automatisch naar GitHub. Hiervoor is een aparte publicatieroute nodig.
6. Tot die route werkt, mogen dashboard en ChatGPT niet als gegarandeerd identiek worden gepresenteerd.

## Deze eerste wijziging
Het dashboard kan een expliciet als 'curated' gemarkeerde selectie verwerken; de briefinglijst gebruikt dezelfde categorieën en artikelen zonder willekeurige limiet van 12. De bestaande live-site blijft ongewijzigd totdat de wijzigingen worden goedgekeurd en samengevoegd.
