def extract_amount_from_data(data: str, index: int = 2, decimals: int = 6) -> float:
    """
    Универсальный извлекатель значений из data EVM-транзакции.

    Args:
        data (str): hex-представление input данных (начинается с '0x')
        index (int): номер 32-байтового слова (начиная с 0)
        decimals (int): точность токена (по умолчанию 6 для USDC/USDT)

    Returns:
        float: значение, приведённое с учётом десятичной точности
    """
    try:
        if not data.startswith("0x"):
            return 0.0

        clean_data = data[10:]

        start = 64 * index
        end = start + 64
        hex_segment = clean_data[start:end]

        if len(hex_segment) != 64:
            return 0.0

        value = int(hex_segment, 16)
        return value / (10 ** decimals)

    except Exception:
        return 0.0

