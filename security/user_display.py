def build_display_name(
    nombres: str | None = None,
    apellidos: str | None = None,
) -> str:
    nombres_text = (nombres or '').strip()
    apellidos_text = (apellidos or '').strip()

    first_name = nombres_text.split()[0] if nombres_text.split() else ''
    first_last = apellidos_text.split()[0] if apellidos_text.split() else ''

    if first_name and first_last:
        return f'{first_name} {first_last}'

    parts = f'{nombres_text} {apellidos_text}'.strip().split()
    if len(parts) >= 2:
        return f'{parts[0]} {parts[1]}'
    return parts[0] if parts else ''
