from src.extract.xm_api import extraer_xm_metricas, extraer_xm_listado_recursos
from src.extract.ideam_socrata import extraer_ideam_temperatura
from src.extract.trm_sui import extraer_trm_fuente_propia
from src.extract.noaa_index import extraer_noaa_oni
from src.extract.enerandes_excel import extraer_enerandes_excel
from src.utils.storage import guardar_bronze_y_sample

def ejecutar_pipeline():
    print("🚀 Iniciando Pipeline Capa Bronce - Observatorio Energía...")

    # 1. XM API
    print("-> Extrayendo XM Generación...")
    df_gene = extraer_xm_metricas("Gene")
    guardar_bronze_y_sample(df_gene, "xm_generacion")

    print("-> Extrayendo XM Listado Recursos...")
    df_recursos = extraer_xm_listado_recursos()
    guardar_bronze_y_sample(df_recursos, "xm_listado_recursos")

    # 2. IDEAM
    print("-> Extrayendo IDEAM Temperatura...")
    df_temp = extraer_ideam_temperatura()
    guardar_bronze_y_sample(df_temp, "ideam_temperatura")

    # 3. Fuente Propia (TRM)
    print("-> Extrayendo Fuente Propia (TRM)...")
    df_trm = extraer_trm_fuente_propia()
    guardar_bronze_y_sample(df_trm, "trm_colombia")

    # 4. NOAA
    print("-> Extrayendo NOAA ONI...")
    df_noaa = extraer_noaa_oni()
    guardar_bronze_y_sample(df_noaa, "noaa_oni_index")

    # 5. EnerAndes Excel
    print("-> Extrayendo EnerAndes Excel...")
    df_enerandes = extraer_enerandes_excel()
    if not df_enerandes.empty:
        guardar_bronze_y_sample(df_enerandes, "enerandes_ventas")

    print("✅ Pipeline ejecutado con éxito. Revisa la carpeta data/bronze y data/sample.")

if __name__ == "__main__":
    ejecutar_pipeline()