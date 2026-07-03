# v55 Macro ampliado - additive

Esta carpeta parte desde el repo original `bcch_monitor_Chile` y agrega la expansión v55 de forma additive.

## Qué se agregó

- `config/indicator_additions_v55.py`: 190 indicadores nuevos con prefijo `v55_`.
- `utils/v55_derived.py`: 18 indicadores derivados nuevos.
- `components/v55_macro_additions.py`: nueva pestaña Streamlit `9. Macro ampliado v55`.
- `docs/series_v55_additive.csv`: inventario de series v55.

## Qué no se tocó conceptualmente

- FX queda separado.
- Derivados BCCh queda reservado y sin rediseño funcional.
- Los indicadores existentes se mantienen; los nuevos usan prefijo `v55_` para no sobreescribir IDs previos.

## Cómo correr

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Credenciales

No se incluyen credenciales reales. Usar la pantalla de login de la app o Streamlit Secrets.
No subir `.streamlit/secrets.toml` ni `.env` a GitHub.
