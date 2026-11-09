from pydantic import conint

# SQLite stocke les entiers sur 64 bits : au-delà, la requête échouerait en erreur 500.
MAX_STORED_INT = 2**63 - 1

EntityId = conint(le=MAX_STORED_INT)
