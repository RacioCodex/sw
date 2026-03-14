import requests
import os
import sys
import hashlib
from datetime import datetime, timedelta, timezone

def ultimo_domingo(ano, mes):
    if mes == 12:
        ultimo_dia = datetime(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = datetime(ano, mes + 1, 1) - timedelta(days=1)
    
    while ultimo_dia.weekday() != 6:
        ultimo_dia -= timedelta(days=1)
    return ultimo_dia

def determinar_temporadas():
    hoy = datetime.now(timezone.utc)
    ano_actual = hoy.year % 100
    
    cambio_marzo = ultimo_domingo(hoy.year, 3)
    # Convertimos a UTC para poder comparar con 'hoy' que ahora es UTC
    cambio_marzo = cambio_marzo.replace(tzinfo=timezone.utc) 
    
    cambio_octubre = ultimo_domingo(hoy.year, 10)
    cambio_octubre = cambio_octubre.replace(tzinfo=timezone.utc)
    
    if hoy >= cambio_marzo and hoy < cambio_octubre:
        actual = f"sked-a{ano_actual:02d}.csv"
        anterior = f"sked-b{ano_actual - 1:02d}.csv"
    elif hoy >= cambio_octubre:
        actual = f"sked-b{ano_actual:02d}.csv"
        anterior = f"sked-a{ano_actual:02d}.csv"
    else:
        actual = f"sked-b{ano_actual - 1:02d}.csv"
        anterior = f"sked-a{ano_actual - 1:02d}.csv"
        
    return actual, anterior

def descargar_y_validar(nombre_archivo):
    url = f"http://www.eibispace.de/dx/{nombre_archivo}"
    print(f"Intentando descargar: {nombre_archivo}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        contenido_crudo = response.content
        texto = contenido_crudo.decode('latin-1')
        lineas = texto.splitlines()
        
        # VALIDACIÓN MEJORADA (Aporte de IA): +100 líneas, empieza con kHz y tiene ;
        if len(lineas) > 100 and lineas[0].startswith("kHz") and ";" in lineas[0]:
            print(f"✓ Archivo EiBi validado correctamente: {nombre_archivo}")
            return contenido_crudo, lineas
        else:
            print(f"⚠️ {nombre_archivo} no superó la validación estricta de CSV.")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error al descargar {nombre_archivo}: {e}")
        return None, None

def procesar_actualizacion():
    # Creamos la carpeta updates de forma segura
    os.makedirs("updates", exist_ok=True)
    
    archivo_actual, archivo_anterior = determinar_temporadas()
    
    contenido_crudo, lineas = descargar_y_validar(archivo_actual)
    
    if not contenido_crudo:
        print("Buscando el archivo de la temporada anterior como respaldo...")
        contenido_crudo, lineas = descargar_y_validar(archivo_anterior)
        
    if not contenido_crudo:
        print("❌ CRÍTICO: Ningún archivo CSV válido pudo ser descargado.")
        sys.exit(1)
        
    nuevo_hash = hashlib.sha256(contenido_crudo).hexdigest()
    archivo_hash = "updates/eibi_hash.dat"
    
    if os.path.exists(archivo_hash):
        with open(archivo_hash, "r") as f:
            hash_guardado = f.read().strip()
            
        if nuevo_hash == hash_guardado:
            print("✅ EiBi no ha cambiado. Hashes idénticos. Saliendo sin hacer nada.")
            sys.exit(0)
        else:
            print("🔄 EiBi ha cambiado. Procediendo a actualizar...")
    else:
        print("🚀 Primera ejecución detectada (No existe hash previo).")

    print("Convirtiendo a formato Skywave...")
    
    with open("updates/esch.csv", "w", encoding="utf-8", newline='\n') as f_csv:
        for i, linea in enumerate(lineas):
            if i == 0:
                linea = linea.rstrip(';')
            f_csv.write(linea + "\n")
            
    # Fecha UTC en formato 8 dígitos
    fecha_version = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    # Mantenemos el \n final porque la app lo espera (9 bytes en total)
    with open("updates/ver.txt", "w", encoding="utf-8", newline='\n') as f_ver:
        f_ver.write(fecha_version + "\n")
        
    with open(archivo_hash, "w", encoding="utf-8", newline='\n') as f_hash:
        f_hash.write(nuevo_hash + "\n")
        
    print(f"✓ ÉXITO: Archivos actualizados en 'updates/'. Versión: {fecha_version}")

if __name__ == "__main__":
    procesar_actualizacion()