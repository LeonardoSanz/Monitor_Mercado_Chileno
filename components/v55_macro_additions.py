from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import line_chart
from components.kpi_cards import render_kpi_grid
from config.indicator_additions_v55 import V55_ALL_IDS, V55_GROUPS
from utils.transformations import latest_by_indicator


CONTEXT_IDS = [
    "tpm",
    "tib",
    "bcp_2y",
    "bcp_5y",
    "bcp_10y",
    "bcu_2y",
    "bcu_5y",
    "bcu_10y",
    "us10y",
    "ipsa",
    "cobre",
    "ipc_anual",
    "desempleo",
    "reservas_internacionales",
    "deuda_publica_pib",
]


def _section_title(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _chart_title(title: str, subtitle: str = "") -> None:
    extra = f'<div class="muted-note">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="chart-title">{title}{extra}</div>', unsafe_allow_html=True)


def _subset(data: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    if data is None or data.empty or "serie_id" not in data.columns:
        return pd.DataFrame()
    return data[data["serie_id"].isin(ids)].copy()


def _plot_line(data: pd.DataFrame, ids: list[str], title: str, subtitle: str = "", key: str = "") -> None:
    frame = _subset(data, ids)
    _chart_title(title, subtitle)
    if frame.empty:
        st.info("Sin datos disponibles para este bloque en el rango seleccionado.")
        return
    st.plotly_chart(line_chart(frame, ids, show_ma=False), width="stretch", key=key or title)


def _compact_table(data: pd.DataFrame, ids: list[str]) -> pd.DataFrame:
    frame = _subset(data, ids)
    if frame.empty:
        return pd.DataFrame()
    latest = latest_by_indicator(frame)
    keep = [c for c in ["serie_id", "nombre_indicador", "fecha", "valor", "unidad", "fuente", "code"] if c in latest.columns]
    return latest[keep].sort_values("serie_id")


def render_v55_macro_additions(data: pd.DataFrame, opts: dict | None = None) -> dict[str, pd.DataFrame]:
    """Módulo v55 additive.

    Mantiene intactas las pestañas existentes y concentra lo nuevo en una vista
    navegable. Las series usan prefijo v55_ para no reemplazar indicadores actuales.
    """
    opts = opts or {}
    _section_title("Macro ampliado v55")

    st.caption(
        "Módulo additive: agrega series nuevas de SieteWS sin reemplazar indicadores existentes, "
        "sin cambiar FX y sin tocar Derivados BCCh."
    )

    macro_data = _subset(data, V55_ALL_IDS + CONTEXT_IDS)
    latest = latest_by_indicator(macro_data)

    render_kpi_grid(
        latest,
        pd.DataFrame(),
        [
            "v55_stress_local_total",
            "v55_incertidumbre_diaria",
            "v55_deuda_gc_total_usd",
            "v55_fees_usd",
            "v55_deuda_hogares_ingreso",
            "v55_remuneraciones_var_anual",
            "v55_pii_neta_pib",
            "v55_m2_mensual",
        ],
    )

    vista = st.selectbox(
        "Vista",
        [
            "Riesgo / stress",
            "Tasas / liquidez",
            "Crédito / bancos",
            "Fiscal / soberano",
            "Vivienda / hogares",
            "Sector externo",
            "Actividad / laboral",
            "Inflación granular",
            "Bolsa / expectativas",
            "Inventario v55",
        ],
        index=0,
    )

    export: dict[str, pd.DataFrame] = {}

    if vista == "Riesgo / stress":
        st.caption("Stress financiero, incertidumbre y comparables externos sin depender de un EMBI externo.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["v55_stress_local_total", "v55_stress_local_fx", "v55_stress_local_soberano"],
                "Índice de stress local",
                "Total, tipo de cambio y tasa soberana",
                "v55_stress_local",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_incertidumbre_diaria", "v55_epu_chile", "v55_epu_global"],
                "Incertidumbre económica",
                "Índice diario BCCh y EPU",
                "v55_incertidumbre",
            )

        with st.expander("Ver volatilidad, riesgo país y comparables 10Y", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_vol_soberana_10y_chile", "v55_vol_fx_chile"],
                    "Volatilidad soberana y cambiaria",
                    "Volatilidad local de mercado",
                    "v55_vols",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["bcp_10y", "us10y", "v55_10y_brasil", "v55_10y_mexico"],
                    "Tasas soberanas 10Y comparables",
                    "Chile, EE.UU., Brasil y México",
                    "v55_10y_comparables",
                )
            _plot_line(
                macro_data,
                ["v55_spread_chile_us10y", "v55_spread_chile_brasil_10y", "v55_spread_chile_mexico_10y"],
                "Spreads soberanos calculados",
                "Chile 10Y menos comparables seleccionados",
                "v55_spreads_soberanos",
            )

        ids = V55_GROUPS.get("Riesgo / stress", [])
        export["v55_riesgo_stress"] = _subset(macro_data, ids + ["bcp_10y", "us10y"])

    elif vista == "Tasas / liquidez":
        st.caption("Corredor monetario, liquidez operacional y agregados monetarios.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["tpm", "tib", "v55_tasa_fpl", "v55_tasa_fpd"],
                "TPM, TIB y corredor monetario",
                "Incluye tasas FPL/FPD agregadas",
                "v55_corredor",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_posicion_liquidez_diaria", "v55_liquidez_sistema_diaria", "v55_cuentas_corrientes_bcch"],
                "Liquidez operacional",
                "Posición de liquidez, liquidez diaria y cuentas corrientes BCCh",
                "v55_liquidez",
            )
        with st.expander("Ver agregados monetarios y encaje", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_m1_mensual", "v55_m2_mensual", "v55_m3_mensual"],
                    "Agregados monetarios",
                    "M1, M2 y M3",
                    "v55_agregados_monetarios",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_encaje_exigido", "v55_encaje_mantenido", "v55_brecha_encaje"],
                    "Encaje exigido vs mantenido",
                    "Incluye brecha calculada",
                    "v55_encaje",
                )
            _plot_line(
                macro_data,
                ["v55_base_monetaria_diaria", "v55_circulante_diario", "v55_m2_m1_ratio"],
                "Base monetaria y mix monetario",
                "Base, circulante y ratio M2/M1",
                "v55_base_monetaria",
            )

        ids = V55_GROUPS.get("Tasas / liquidez", [])
        export["v55_tasas_liquidez"] = _subset(macro_data, ids + ["tpm", "tib"])

    elif vista == "Crédito / bancos":
        st.caption("Precio, cantidad y funding bancario. Las series v55 no reemplazan los TODO existentes; conviven con prefijo propio.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["v55_tasa_comercial", "v55_tasa_consumo", "v55_tasa_hipotecaria"],
                "Tasas de crédito",
                "Comercial, consumo e hipotecaria UF",
                "v55_tasas_credito",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_spread_comercial_tpm", "v55_spread_consumo_tpm", "v55_spread_hipotecaria_bcu10y"],
                "Spreads de crédito",
                "Comercial/consumo contra TPM; hipotecaria contra BCU 10Y",
                "v55_spreads_credito",
            )
        with st.expander("Ver colocaciones, depósitos y proxies TMC", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_colocaciones_total_real", "v55_colocaciones_comerciales_real", "v55_colocaciones_consumo_real", "v55_colocaciones_vivienda_real"],
                    "Colocaciones reales",
                    "Total, comercial, consumo y vivienda",
                    "v55_colocaciones",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_depositos_mn_total", "v55_depositos_plazo_mn", "v55_depositos_me_total", "v55_depositos_me_plazo"],
                    "Depósitos MN y ME",
                    "Funding en moneda nacional y extranjera",
                    "v55_depositos",
                )
            _plot_line(
                macro_data,
                ["v55_tmc_proxy_pdbc_m30", "v55_tmc_proxy_pdbc_30", "v55_tmc_proxy_prbc_90_uf", "v55_tmc_proxy_bcd_1y_usd"],
                "Series BCCh para máxima convencional",
                "No reemplazan la TMC oficial CMF; quedan como proxy/insumo BCCh",
                "v55_tmc_proxy",
            )

        ids = V55_GROUPS.get("Crédito / bancos", [])
        export["v55_credito_bancos"] = _subset(macro_data, ids)

    elif vista == "Fiscal / soberano":
        st.caption("Balance, deuda, fondos soberanos y buffers fiscales.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["v55_balance_fiscal", "deuda_publica_pib"],
                "Balance fiscal y deuda pública / PIB",
                "Balance mensual % PIB y deuda pública si está disponible en el core",
                "v55_balance_deuda",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_deuda_gc_total_usd", "v55_deuda_gc_interna_usd", "v55_deuda_gc_externa_usd"],
                "Deuda Gobierno Central",
                "Total, interna y externa en USD",
                "v55_deuda_gc",
            )
        with st.expander("Ver ingresos, gastos y fondos soberanos", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_ingresos_gobierno_central", "v55_gasto_publico", "v55_resultado_fiscal_ingresos_gastos"],
                    "Ingresos vs gastos Gobierno Central",
                    "Incluye resultado calculado",
                    "v55_ingresos_gastos",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_fees_usd", "v55_frp_usd", "v55_fees_deuda_gc_pct", "v55_frp_deuda_gc_pct"],
                    "Fondos soberanos y cobertura de deuda",
                    "FEES, FRP y ratios contra deuda GC",
                    "v55_fondos_soberanos",
                )

        ids = V55_GROUPS.get("Fiscal / soberano", [])
        export["v55_fiscal_soberano"] = _subset(macro_data, ids + ["deuda_publica_pib"])

    elif vista == "Vivienda / hogares":
        st.caption("Vivienda, deuda de hogares, ingreso disponible y ahorro.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["v55_ipv_general", "v55_ipv_casas", "v55_ipv_departamentos", "v55_ipv_rm"],
                "Precios de vivienda",
                "IPV general, casas, departamentos y RM",
                "v55_ipv",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_deuda_hogares_ingreso", "v55_deuda_hogares_hipotecaria_ingreso", "v55_deuda_hogares_consumo_ingreso"],
                "Deuda de hogares / ingreso disponible",
                "Total, hipotecaria y consumo",
                "v55_deuda_hogares",
            )
        with st.expander("Ver ventas, LTV, morosidad y ahorro", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_ventas_viviendas_total", "v55_ventas_deptos_nuevos", "v55_ventas_deptos_usados"],
                    "Ventas efectivas de viviendas",
                    "Total, departamentos nuevos y usados",
                    "v55_ventas_vivienda",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_ltv_ponderado", "v55_morosidad_hipotecaria_90d", "v55_plazo_hipotecario_promedio"],
                    "Riesgo hipotecario",
                    "LTV, morosidad 90d y plazo promedio",
                    "v55_riesgo_hipotecario",
                )
            _plot_line(
                macro_data,
                ["v55_ahorro_hogares_ingreso", "v55_activos_financieros_netos_hogares_pib", "v55_capacidad_financiamiento_hogares_ingreso"],
                "Ahorro y posición financiera de hogares",
                "Ratios de hogares e IPSFL",
                "v55_ahorro_hogares",
            )

        ids = V55_GROUPS.get("Vivienda / hogares", [])
        export["v55_vivienda_hogares"] = _subset(macro_data, ids)

    elif vista == "Sector externo":
        st.caption("Cuenta corriente, PII, deuda externa, comercio y reservas.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["v55_cuenta_corriente_pib", "v55_pii_neta_pib"],
                "Cuenta corriente y PII / PIB",
                "Vulnerabilidad externa en ratios",
                "v55_externo_ratios",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_deuda_externa_total", "v55_deuda_externa_gc"],
                "Deuda externa",
                "Total y Gobierno Central",
                "v55_deuda_externa",
            )
        with st.expander("Ver comercio, reservas y términos de intercambio", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_balanza_comercial_mensual", "v55_exportaciones_bienes_servicios", "v55_importaciones_bienes_servicios"],
                    "Comercio exterior",
                    "Balanza comercial, exportaciones e importaciones",
                    "v55_comercio_exterior",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_reservas_netas", "v55_posicion_moneda_extranjera_bcch", "v55_terminos_intercambio"],
                    "Reservas y términos de intercambio",
                    "Liquidez externa y precios relativos externos",
                    "v55_reservas_tdi",
                )

        ids = V55_GROUPS.get("Sector externo", [])
        export["v55_sector_externo"] = _subset(macro_data, ids)

    elif vista == "Actividad / laboral":
        st.caption("Actividad real, inversión, mercado laboral y remuneraciones.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["imacec_total", "imacec_no_minero", "v55_imacec_industria", "v55_imacec_resto_bienes"],
                "IMACEC ampliado",
                "Core existente más componentes v55",
                "v55_imacec",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_fbkf_real", "v55_fbkf_construccion_real", "v55_fbkf_maquinaria_real"],
                "Inversión real",
                "FBCF total, construcción y maquinaria",
                "v55_inversion",
            )
        with st.expander("Ver mercado laboral y remuneraciones", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["desempleo", "v55_desempleo_sa", "v55_desempleo_hombres", "v55_desempleo_mujeres"],
                    "Desocupación",
                    "Total, desestacionalizada y por género",
                    "v55_desempleo",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_remuneraciones_var_anual", "v55_remuneraciones_reales_var_anual", "v55_costo_laboral_var_anual"],
                    "Remuneraciones y costos laborales",
                    "Variaciones anuales",
                    "v55_remuneraciones",
                )

        ids = V55_GROUPS.get("Actividad / laboral", [])
        export["v55_actividad_laboral"] = _subset(macro_data, ids + ["imacec_total", "imacec_no_minero", "desempleo"])

    elif vista == "Inflación granular":
        st.caption("Detalle de inflación por bienes, servicios, alimentos, transables/no transables y volátiles.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["ipc_anual", "v55_ipc_transables_anual", "v55_ipc_no_transables_anual"],
                "Inflación anual: transables/no transables",
                "Core existente más detalle v55",
                "v55_inflacion_tnt",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_ipc_bienes_mensual", "v55_ipc_servicios_mensual", "v55_ipc_alimentos_mensual"],
                "IPC mensual por agrupación",
                "Bienes, servicios y alimentos",
                "v55_ipc_mensual_detalle",
            )
        with st.expander("Ver IPC sin volátiles y componentes volátiles", expanded=False):
            _plot_line(
                macro_data,
                ["v55_ipc_bienes_sin_vol_anual", "v55_ipc_servicios_sin_vol_anual", "v55_ipc_alimentos_vol_anual", "v55_ipc_energia_vol_anual"],
                "IPC analítico",
                "Bienes/servicios sin volátiles y alimentos/energía volátil",
                "v55_ipc_analitico",
            )

        ids = V55_GROUPS.get("Inflación granular", [])
        export["v55_inflacion_granular"] = _subset(macro_data, ids + ["ipc_anual"])

    elif vista == "Bolsa / expectativas":
        st.caption("Bolsa local, valorización, confianza y expectativas de mercado.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            _plot_line(
                macro_data,
                ["ipsa", "v55_ipsa_volumen", "v55_bolsa_cap_bursatil_usd"],
                "Bolsa local: IPSA, monto y capitalización",
                "Precio, liquidez y tamaño de mercado",
                "v55_bolsa",
            )
        with c2:
            _plot_line(
                macro_data,
                ["v55_bolsa_rpu", "v55_bolsa_libro"],
                "Valorización Bolsa de Santiago",
                "RPU y bolsa/libro",
                "v55_valorizacion_bolsa",
            )
        with st.expander("Ver expectativas y confianza", expanded=False):
            c3, c4 = st.columns(2, gap="large")
            with c3:
                _plot_line(
                    macro_data,
                    ["v55_eee_tpm_siguiente", "v55_eee_tpm_subsiguiente", "v55_eee_tc_11m", "v55_eee_ipc_23m"],
                    "EEE: TPM, dólar e inflación",
                    "Expectativas de mercado",
                    "v55_eee",
                )
            with c4:
                _plot_line(
                    macro_data,
                    ["v55_imce_total", "v55_ipec_total"],
                    "Confianza empresarial y consumidores",
                    "IMCE e IPEC",
                    "v55_confianza",
                )
            _plot_line(
                macro_data,
                ["v55_eof_inflacion_proximo_ipc", "v55_eof_btp_5y_14d", "v55_eof_btp_10y_14d"],
                "EOF: inflación y tasas largas",
                "Expectativas de operadores financieros",
                "v55_eof",
            )

        ids = V55_GROUPS.get("Bolsa / mercado local", []) + V55_GROUPS.get("Expectativas / confianza", [])
        export["v55_bolsa_expectativas"] = _subset(macro_data, ids + ["ipsa"])

    else:
        st.caption("Inventario técnico de series agregadas en v55. Sirve para auditar carga, cobertura y códigos SieteWS.")
        rows = _compact_table(macro_data, V55_ALL_IDS)
        st.dataframe(rows, width="stretch", hide_index=True)
        export["v55_inventario"] = rows

    # Siempre entrega inventario para exportar.
    if "v55_inventario" not in export:
        export["v55_inventario"] = _compact_table(macro_data, V55_ALL_IDS)

    return export
