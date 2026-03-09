# Data collection server for POLEMIC / POLWELL

Server that collects data sources from research participants.

The support for multiple studies is unnecessary and creates additional complexity in this project. It will be phased out as models get edited.


## Participants

Participants create an login account and sign up to a study. This starts a consent worflow that asks for consent and shows setup instructions for all required data sources.

Participants can review their own data and have the option to withdraw consent.

## Researchers


Researchers create an researcher account through a different url, 'signup/researcher/'. They must be added to the study by an admin. Researchers in a study gain access to the data sources provided by the participants, during the time frame given in their consent.

Researchers are expected to use the data API with their personal access token to fetch the data.

## Data Sources

Data sources define how their data is fetched or stored, as well as their setup instructions.
