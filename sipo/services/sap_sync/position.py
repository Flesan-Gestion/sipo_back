def get_posicion_sap(user_id: str | int) -> str:
    return str(int(user_id) + 20_000_000)
