from __future__ import annotations

import numpy as np
import pandas as pd


BASE_COLUMNS = [
    "fecha",
    "valor",
    "serie_id",
    "nombre_indicador",
    "categoria",
    "frecuencia",
    "unidad",
    "fuente",
    "fecha_actualizacion",
    "estado_fuente",
    "code",
]


def _metadata(out_id: str) -> dict:
    try:
        from config.indicators import indicator_map

        return indicator_map().get(out_id, {})
    except Exception:
        return {}


def _derive_from_ids(
    data: pd.DataFrame,
    out_id: str,
    base_id: str,
    needed_ids: list[str],
    formula,
) -> pd.DataFrame:
    if data is None or data.empty or "serie_id" not in data.columns:
        return pd.DataFrame(columns=BASE_COLUMNS)

    tmp = data[data["serie_id"].isin(needed_ids)][["fecha", "serie_id", "valor"]].copy()
    if tmp.empty or base_id not in set(tmp["serie_id"]):
        return pd.DataFrame(columns=BASE_COLUMNS)

    tmp["fecha"] = pd.to_datetime(tmp["fecha"], errors="coerce")
    tmp["valor"] = pd.to_numeric(tmp["valor"], errors="coerce")
    tmp = tmp.dropna(subset=["fecha", "valor"])

    if tmp.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    pivot = (
        tmp.pivot_table(index="fecha", columns="serie_id", values="valor", aggfunc="last")
        .sort_index()
    )

    base_dates = pd.Index(
        tmp.loc[tmp["serie_id"].eq(base_id), "fecha"].dropna().sort_values().unique()
    )
    if len(base_dates) == 0:
        return pd.DataFrame(columns=BASE_COLUMNS)

    full_index = pivot.index.union(base_dates).sort_values()
    pivot = pivot.reindex(full_index).ffill()

    try:
        values = formula(pivot)
    except Exception:
        return pd.DataFrame(columns=BASE_COLUMNS)

    values = (
        pd.Series(values, index=pivot.index)
        .reindex(base_dates)
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    if values.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    meta = _metadata(out_id)
    out = pd.DataFrame(
        {
            "fecha": values.index,
            "valor": values.values,
            "serie_id": out_id,
            "nombre_indicador": meta.get("name", out_id),
            "categoria": meta.get("category", "Macro ampliado"),
            "frecuencia": meta.get("frequency", ""),
            "unidad": meta.get("unit", ""),
            "fuente": meta.get("source", "Derivado"),
            "fecha_actualizacion": pd.Timestamp.today().normalize(),
            "estado_fuente": "Derivado v55",
            "code": meta.get("code"),
        }
    )
    return out.reindex(columns=BASE_COLUMNS)


def build_v55_derived_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """Agrega derivados v55 sin tocar FX ni el módulo de derivados BCCh.

    Las recetas usan IDs con prefijo v55_ para las series nuevas y, cuando conviene,
    se apoyan en series core existentes como tpm, tib, bcp_10y, bcu_10y o us10y.
    """
    if data is None or data.empty:
        return data

    recipes = [
        ("v55_breakeven_2y", "bcp_2y", ["bcp_2y", "bcu_2y"], lambda p: p["bcp_2y"] - p["bcu_2y"]),
        ("v55_breakeven_5y", "bcp_5y", ["bcp_5y", "bcu_5y"], lambda p: p["bcp_5y"] - p["bcu_5y"]),
        ("v55_breakeven_10y", "bcp_10y", ["bcp_10y", "bcu_10y"], lambda p: p["bcp_10y"] - p["bcu_10y"]),
        (
            "v55_spread_comercial_tpm",
            "v55_tasa_comercial",
            ["v55_tasa_comercial", "tpm"],
            lambda p: p["v55_tasa_comercial"] - p["tpm"],
        ),
        (
            "v55_spread_consumo_tpm",
            "v55_tasa_consumo",
            ["v55_tasa_consumo", "tpm"],
            lambda p: p["v55_tasa_consumo"] - p["tpm"],
        ),
        (
            "v55_spread_hipotecaria_bcu10y",
            "v55_tasa_hipotecaria",
            ["v55_tasa_hipotecaria", "bcu_10y"],
            lambda p: p["v55_tasa_hipotecaria"] - p["bcu_10y"],
        ),
        (
            "v55_share_depositos_plazo",
            "v55_depositos_mn_total",
            ["v55_depositos_mn_total", "v55_depositos_plazo_mn"],
            lambda p: np.where(
                p["v55_depositos_mn_total"].abs() > 0,
                100 * p["v55_depositos_plazo_mn"] / p["v55_depositos_mn_total"],
                np.nan,
            ),
        ),
        (
            "v55_brecha_interbancaria_tpm",
            "tib",
            ["tib", "tpm"],
            lambda p: p["tib"] - p["tpm"],
        ),
        (
            "v55_brecha_encaje",
            "v55_encaje_mantenido",
            ["v55_encaje_mantenido", "v55_encaje_exigido"],
            lambda p: p["v55_encaje_mantenido"] - p["v55_encaje_exigido"],
        ),
        (
            "v55_resultado_fiscal_ingresos_gastos",
            "v55_ingresos_gobierno_central",
            ["v55_ingresos_gobierno_central", "v55_gasto_publico"],
            lambda p: p["v55_ingresos_gobierno_central"] - p["v55_gasto_publico"],
        ),
        (
            "v55_spread_chile_us10y",
            "bcp_10y",
            ["bcp_10y", "us10y"],
            lambda p: p["bcp_10y"] - p["us10y"],
        ),
        (
            "v55_spread_chile_brasil_10y",
            "bcp_10y",
            ["bcp_10y", "v55_10y_brasil"],
            lambda p: p["bcp_10y"] - p["v55_10y_brasil"],
        ),
        (
            "v55_spread_chile_mexico_10y",
            "bcp_10y",
            ["bcp_10y", "v55_10y_mexico"],
            lambda p: p["bcp_10y"] - p["v55_10y_mexico"],
        ),
        (
            "v55_fees_deuda_gc_pct",
            "v55_fees_usd",
            ["v55_fees_usd", "v55_deuda_gc_total_usd"],
            lambda p: np.where(
                p["v55_deuda_gc_total_usd"].abs() > 0,
                100 * p["v55_fees_usd"] / p["v55_deuda_gc_total_usd"],
                np.nan,
            ),
        ),
        (
            "v55_frp_deuda_gc_pct",
            "v55_frp_usd",
            ["v55_frp_usd", "v55_deuda_gc_total_usd"],
            lambda p: np.where(
                p["v55_deuda_gc_total_usd"].abs() > 0,
                100 * p["v55_frp_usd"] / p["v55_deuda_gc_total_usd"],
                np.nan,
            ),
        ),
        (
            "v55_depositos_me_plazo_share",
            "v55_depositos_me_plazo",
            ["v55_depositos_me_plazo", "v55_depositos_me_total"],
            lambda p: np.where(
                p["v55_depositos_me_total"].abs() > 0,
                100 * p["v55_depositos_me_plazo"] / p["v55_depositos_me_total"],
                np.nan,
            ),
        ),
        (
            "v55_m2_m1_ratio",
            "v55_m2_mensual",
            ["v55_m2_mensual", "v55_m1_mensual"],
            lambda p: np.where(
                p["v55_m1_mensual"].abs() > 0,
                p["v55_m2_mensual"] / p["v55_m1_mensual"],
                np.nan,
            ),
        ),
        (
            "v55_deuda_hogares_hipotecaria_share",
            "v55_deuda_hogares_hipotecaria_ingreso",
            ["v55_deuda_hogares_hipotecaria_ingreso", "v55_deuda_hogares_ingreso"],
            lambda p: np.where(
                p["v55_deuda_hogares_ingreso"].abs() > 0,
                100 * p["v55_deuda_hogares_hipotecaria_ingreso"] / p["v55_deuda_hogares_ingreso"],
                np.nan,
            ),
        ),
    ]

    derived_frames: list[pd.DataFrame] = []
    for out_id, base_id, needed, formula in recipes:
        frame = _derive_from_ids(data, out_id, base_id, needed, formula)
        if not frame.empty:
            derived_frames.append(frame)

    if not derived_frames:
        return data

    return pd.concat([data, *derived_frames], ignore_index=True, sort=False)
