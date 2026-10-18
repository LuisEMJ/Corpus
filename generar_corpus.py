import os
import pandas as pd
from bs4 import BeautifulSoup
import re
from datetime import datetime


def dividir_en_oraciones(texto):
    if not texto or not isinstance(texto, str):
        return []

    oraciones = re.split(r'(?<!\w\.\w\.)(?<![A-Z][a-z]\.)(?<![A-Z]\.[A-Z]\.)(?<=\.|\?|\!)\s+(?=(?:"|¿|¡)?\s*["“]|[A-Z])', texto)

    oraciones_limpias = []
    for oracion in oraciones:
        oracion = oracion.strip()
        if oracion and len(oracion) > 1:
            oraciones_limpias.append(oracion)

    if not oraciones_limpias and texto.strip() and len(texto.strip()) > 1:
        return [texto.strip()]

    return oraciones_limpias


def limpiar_copyright(texto):
    if not texto or not isinstance(texto, str):
        return texto

    lineas = texto.split('\n')
    lineas_limpias = []

    for linea in lineas:
        if re.search(r'(copyright|©|la crónica de hoy|la cronica de hoy)', linea, re.IGNORECASE):
            continue
        lineas_limpias.append(linea)

    texto_limpio = '\n'.join(lineas_limpias)
    texto_limpio = re.sub(r'(?i)(copyright|©|la crónica de hoy|la cronica de hoy).*?($|\n)', '', texto_limpio)
    texto_limpio = re.sub(r'\n\s*\n\s*\n', '\n\n', texto_limpio)

    return texto_limpio.strip()


def extraer_texto_noticia(ruta_archivo):
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido_html = archivo.read()

        sopa = BeautifulSoup(contenido_html, 'html.parser')

        titulo = 'No se encontró título'
        if sopa.find('h1'):
            titulo = sopa.find('h1').get_text()
        elif sopa.find('title'):
            titulo = sopa.find('title').get_text()

        categoria = 'No se encontró categoría'
        categoria_elem = sopa.find('a', class_='c-overline b-overline')
        if categoria_elem:
            categoria = categoria_elem.text.strip()
        else:
            categoria_elem = sopa.find('meta', property='article:section')
            if categoria_elem and categoria_elem.get('content'):
                categoria = categoria_elem['content'].strip()

        fecha_publicacion = 'No se encontró fecha'
        fecha_elem = sopa.find('time', datetime=True)
        if fecha_elem and fecha_elem.get('datetime'):
            fecha_publicacion = fecha_elem['datetime'][:10]
        else:
            fecha_elem = sopa.find('meta', itemprop='datePublished')
            if fecha_elem and fecha_elem.get('content'):
                fecha_publicacion = fecha_elem['content'][:10]

        subtitulos = [h2.get_text().strip() for h2 in sopa.find_all('h2') if h2.get_text().strip()]

        parrafos_originales = []
        clases_parrafo = ['c-paragraph', 'paragraph', 'article-text', 'content']
        for clase in clases_parrafo:
            parrafos = sopa.find_all('p', class_=clase)
            if parrafos:
                parrafos_originales = [para.get_text().strip() for para in parrafos if para.get_text().strip()]
                break

        if not parrafos_originales:
            parrafos_originales = [para.get_text().strip() for para in sopa.find_all('p') if para.get_text().strip()]

        oraciones = []
        for parrafo in parrafos_originales:
            if parrafo and len(parrafo) > 10:
                parrafo_limpio = re.sub(r'(?i)(copyright|©|la crónica de hoy|la cronica de hoy).*?($|\.)', '', parrafo)
                oraciones_parrafo = dividir_en_oraciones(parrafo_limpio)
                for oracion in oraciones_parrafo:
                    if oracion and len(oracion) > 5:
                        oraciones.append(oracion)

        titulo = limpiar_copyright(titulo)
        categoria = limpiar_copyright(categoria)
        subtitulos = [limpiar_copyright(sub) for sub in subtitulos if sub]

        etiquetas = [span.get_text() for span in sopa.find_all('span', class_='tag')]
        enlaces = [a['href'] for a in sopa.find_all('a', href=True)]

        return titulo, categoria, fecha_publicacion, subtitulos, oraciones, etiquetas, enlaces
    except Exception as e:
        print(f"   Error extrayendo texto: {e}")
        return None, None, None, None, None, None, None


def parse_fecha(fecha_str):
    if not fecha_str or fecha_str == 'No se encontró fecha':
        return datetime.max

    try:
        if re.match(r'\d{4}-\d{2}-\d{2}', fecha_str):
            return datetime.strptime(fecha_str.split()[0], '%Y-%m-%d')
        elif re.match(r'\d{2}/\d{2}/\d{4}', fecha_str):
            return datetime.strptime(fecha_str.split()[0], '%d/%m/%Y')
        else:
            return datetime.max
    except:
        return datetime.max


def obtener_info_noticia_para_orden(ruta_archivo):
    try:
        titulo, categoria, fecha_publicacion, subtitulos, oraciones, etiquetas, enlaces = extraer_texto_noticia(ruta_archivo)
        if titulo is None or not oraciones:
            return None

        fecha_obj = parse_fecha(fecha_publicacion)
        fecha_limpia = fecha_publicacion.split()[0] if fecha_publicacion and fecha_publicacion != 'No se encontró fecha' else 'No fecha'

        return {
            'ruta': ruta_archivo,
            'nombre_archivo': os.path.basename(ruta_archivo),
            'fecha_str': fecha_limpia,
            'fecha_obj': fecha_obj,
            'titulo': titulo,
            'categoria': categoria,
            'subtitulos': subtitulos,
            'oraciones': oraciones,
            'fecha_original': fecha_publicacion
        }
    except Exception as e:
        print(f"   Error obteniendo info para {ruta_archivo}: {e}")
        return None


def buscar_carpetas_con_html(ruta_raiz):
    carpetas_con_html = []
    carpetas_excluidas = 0

    for root, dirs, files in os.walk(ruta_raiz):
        if root.endswith('_files'):
            carpetas_excluidas += 1
            continue

        if 'Noticias' in root.split(os.sep):
            continue

        archivos_html = [f for f in files if f.endswith('.html') and not f.startswith('._')]
        if archivos_html:
            carpetas_con_html.append(root)
            print(f"Carpeta encontrada con {len(archivos_html)} archivos HTML: {root}")

    if carpetas_excluidas > 0:
        print(f"\nSe excluyeron {carpetas_excluidas} carpetas '_files' (recursos web)")

    return carpetas_con_html


def obtener_nombre_carpeta_padre(directorio):
    try:
        padre = os.path.dirname(directorio)
        if padre and padre != directorio:
            return os.path.basename(padre)
        else:
            return os.path.basename(directorio)
    except:
        return "CARPETA"


def procesar_todos_los_archivos_html_recursivo(ruta_raiz):
    ruta_excel = r'C:/Users/lm354/Desktop/NOTICIAS 2026 CORPUS NUEVOS/CON FUNCION DE APTITUD/MODIFICADO/LOS DOS CORPUS ANT Y DESP/Base_de_Datos_Noticias.xlsx'
    os.makedirs(os.path.dirname(ruta_excel), exist_ok=True)

    if os.path.exists(ruta_excel):
        try:
            df_existente = pd.read_excel(ruta_excel)
            ids_existentes = set(df_existente["IDENTIFICADOR DE NOTICIA"])
            print(f"Base de datos existente cargada con {len(df_existente)} registros")
        except Exception as e:
            print(f"Error cargando Excel: {e}")
            df_existente = pd.DataFrame()
            ids_existentes = set()
    else:
        df_existente = pd.DataFrame()
        ids_existentes = set()
        print("Creando nueva base de datos")

    print(f"\nBuscando carpetas con archivos HTML en: {ruta_raiz}")
    carpetas = buscar_carpetas_con_html(ruta_raiz)

    if not carpetas:
        print("No se encontraron carpetas con archivos HTML")
        return

    print(f"\nSe encontraron {len(carpetas)} carpetas para procesar")
    print("=" * 60)

    todos_los_datos = []
    total_nuevas = 0
    total_existentes = 0
    carpetas_con_error = []

    for idx_carpeta, directorio in enumerate(carpetas, 1):
        print(f"\nProcesando carpeta {idx_carpeta}/{len(carpetas)}")
        print("-" * 40)

        try:
            directorio_salida = os.path.join(directorio, 'Noticias')
            os.makedirs(directorio_salida, exist_ok=True)

            archivos = [f for f in os.listdir(directorio) if f.endswith('.html') and not f.startswith('._')]

            if not archivos:
                print(f"No hay archivos HTML válidos en {directorio}")
                continue

            print(f"Procesando carpeta: {directorio}")
            print(f"   Total de archivos HTML: {len(archivos)}")

            print("   Ordenando noticias cronológicamente...")
            noticias_info = []
            for archivo in archivos:
                ruta_archivo = os.path.join(directorio, archivo)
                info = obtener_info_noticia_para_orden(ruta_archivo)
                if info:
                    noticias_info.append(info)

            if not noticias_info:
                print(f"   No se pudo procesar ninguna noticia en {directorio}")
                continue

            noticias_ordenadas = sorted(noticias_info, key=lambda x: x['fecha_obj'])

            print("   Orden encontrado (de más antigua a más nueva):")
            for i, noticia in enumerate(noticias_ordenadas, 1):
                print(f"      {i}. {noticia['fecha_str']} - {noticia['titulo'][:50]}... ({len(noticia['oraciones'])} oraciones)")

            texto_noticias_combinado = ""
            datos_carpeta = []
            nuevas_carpeta = 0
            existentes_carpeta = 0

            for i, noticia_info in enumerate(noticias_ordenadas, start=1):
                try:
                    titulo = noticia_info['titulo']
                    categoria = noticia_info['categoria']
                    fecha_publicacion = noticia_info['fecha_original']
                    subtitulos = noticia_info['subtitulos']
                    oraciones = noticia_info['oraciones']
                    archivo = noticia_info['nombre_archivo']

                    parte_titulo = titulo[:2].upper() if titulo and titulo != 'No se encontró título' else 'NT'
                    parte_titulo = re.sub(r'[^A-Z0-9]', '', parte_titulo)

                    nombre_carpeta_padre = obtener_nombre_carpeta_padre(directorio)
                    parte_carpeta = nombre_carpeta_padre[:3].upper()
                    parte_carpeta = re.sub(r'[^A-Z0-9]', '', parte_carpeta)
                    if not parte_carpeta:
                        parte_carpeta = "CAR"

                    parte_categoria = categoria[:2].upper() if categoria and categoria != 'No se encontró categoría' else 'NC'
                    parte_categoria = re.sub(r'[^A-Z0-9]', '', parte_categoria)
                    if not parte_categoria:
                        parte_categoria = "NC"

                    parte_fecha = fecha_publicacion.replace("-", "_") if fecha_publicacion and fecha_publicacion != 'No se encontró fecha' else 'ND'
                    parte_fecha = re.sub(r'[^0-9_]', '', parte_fecha)

                    nombre_archivo_txt = f"{parte_titulo}-{parte_carpeta}-{parte_categoria}-{len(archivos)}_{i}_{parte_fecha}.txt"
                    identificador_noticia = nombre_archivo_txt.replace(".txt", "")
                    es_nueva = identificador_noticia not in ids_existentes

                    docid = identificador_noticia
                    fecha_limpia = fecha_publicacion.split()[0] if fecha_publicacion and fecha_publicacion != 'No se encontró fecha' else 'No fecha'

                    xml_noticia = f"""<DOC>

<DOCNO>
<s docid="{docid}" num="1" wdcount="1"> {fecha_limpia} </s>
</DOCNO> \n\n

<FILEID>
<s docid="{docid}" num="2" wdcount="1">{docid}</s>
</FILEID> \n\n

<HEAD>
<s docid="{docid}" num="3" wdcount="{len(titulo.split())}"> {titulo} </s>
</HEAD> \n\n

<SUBHEAD>
"""
                    num_s = 4
                    if subtitulos and len(subtitulos) > 0:
                        primer_subtitulo = subtitulos[0]
                        xml_noticia += f'<s docid="{docid}" num="{num_s}" wdcount="{len(primer_subtitulo.split())}"> {primer_subtitulo} </s>'
                        num_s += 1

                    xml_noticia += f"""
</SUBHEAD> \n\n

<CATEGORY>
<s docid="{docid}" num="{num_s}" wdcount="{len(categoria.split())}"> {categoria} </s>
</CATEGORY> \n\n
"""
                    num_s += 1

                    xml_noticia += f"""
<DATE>
<s docid="{docid}" num="{num_s}" wdcount="{len(fecha_limpia.split())}"> {fecha_limpia} </s>
</DATE> \n\n
"""
                    num_s += 1

                    xml_noticia += """
<TEXT>
"""
                    for oracion in oraciones:
                        if oracion and oracion.strip() and len(oracion.strip()) > 5:
                            wdcount = len(oracion.split())
                            xml_noticia += f'<s docid="{docid}" num="{num_s}" wdcount="{wdcount}"> {oracion} </s>\n\n'
                            num_s += 1

                    xml_noticia += """
</TEXT> \n\n

</DOC>
"""

                    xml_noticia = limpiar_copyright(xml_noticia)
                    texto_noticias_combinado += xml_noticia

                    ruta_archivo_salida = os.path.join(directorio_salida, nombre_archivo_txt)
                    with open(ruta_archivo_salida, 'w', encoding='utf-8') as archivo_salida:
                        archivo_salida.write(xml_noticia)

                    if es_nueva:
                        print(f"   [NUEVO] {archivo} -> {nombre_archivo_txt} ({len(oraciones)} oraciones)")
                        nuevas_carpeta += 1
                    else:
                        print(f"   [REPROCESADO] {archivo} -> {nombre_archivo_txt} ({len(oraciones)} oraciones)")

                    if es_nueva:
                        datos_carpeta.append({
                            "Nombre de la noticia": titulo,
                            "Carpeta": os.path.basename(directorio),
                            "Categoria": categoria,
                            "Numero de noticias": f"{len(archivos)}_{i}",
                            "Fecha": fecha_limpia,
                            "IDENTIFICADOR DE NOTICIA": identificador_noticia,
                            "Total oraciones": len(oraciones)
                        })
                        ids_existentes.add(identificador_noticia)
                    else:
                        existentes_carpeta += 1

                except Exception as e:
                    print(f"   Error procesando noticia {i}: {e}")
                    continue

            if texto_noticias_combinado:
                texto_noticias_combinado = limpiar_copyright(texto_noticias_combinado)
                ruta_combinado = os.path.join(directorio_salida, 'Noticias_Juntas.txt')
                with open(ruta_combinado, 'w', encoding='utf-8') as f:
                    f.write(texto_noticias_combinado)
                print("   [COMBINADO] Noticias_Juntas.txt guardado")

            if noticias_ordenadas:
                nombre_carpeta = os.path.basename(os.path.normpath(directorio))
                nombre_carpeta_limpio = re.sub(r'[^A-Za-z0-9\s]', '', nombre_carpeta)
                palabras = nombre_carpeta_limpio.split()
                iniciales_carpeta = ''.join([palabra[0].upper() for palabra in palabras if palabra]) if palabras else "CORP"
                if not iniciales_carpeta:
                    iniciales_carpeta = "CORP"

                try:
                    fecha_min = noticias_ordenadas[0]['fecha_str']
                    fecha_max = noticias_ordenadas[-1]['fecha_str']
                    rango_fechas = f"{fecha_min}_a_{fecha_max}"
                    rango_fechas = re.sub(r'[^A-Za-z0-9_\-]', '', rango_fechas)
                except:
                    rango_fechas = "fechas_desconocidas"

                total_noticias_carpeta = len([n for n in noticias_ordenadas if n is not None])

                nombre_corp = f"CORP-{iniciales_carpeta}-{total_noticias_carpeta}.txt"
                ruta_corp = os.path.join(directorio_salida, nombre_corp)
                docid_corp = f"CORP-{iniciales_carpeta}-{total_noticias_carpeta}"
                docid_corp = re.sub(r'[^A-Za-z0-9_\-()]', '', docid_corp)

                xml_corp = f"""<DOC>

<FILEID>
<s docid="{docid_corp}" num="1" wdcount="1"> {docid_corp} </s>
</FILEID> \n\n

<HEAD>
<s docid="{docid_corp}" num="2" wdcount="{len(nombre_carpeta.split())}"> {nombre_carpeta} </s>
</HEAD> \n\n

<TEXT>
"""
                num_s = 3
                total_oraciones = 0
                for noticia_info in noticias_ordenadas:
                    for oracion in noticia_info['oraciones']:
                        if oracion and oracion.strip() and len(oracion.strip()) > 5:
                            wdcount = len(oracion.split())
                            xml_corp += f'<s docid="{docid_corp}" num="{num_s}" wdcount="{wdcount}"> {oracion} </s>\n\n'
                            num_s += 1
                            total_oraciones += 1

                xml_corp += "</TEXT> \n\n</DOC>\n"
                xml_corp = limpiar_copyright(xml_corp)

                with open(ruta_corp, 'w', encoding='utf-8') as f:
                    f.write(xml_corp)
                print(f"   [CORP] {nombre_corp} ({total_oraciones} oraciones)")

                nombre_corp_seg = f"CORP-SEG-{iniciales_carpeta}-{total_noticias_carpeta}.txt"
                ruta_corp_seg = os.path.join(directorio_salida, nombre_corp_seg)

                corp_seg = ""
                num_seg = 1

                corp_seg += f"{{{{{num_seg},1}}}} {docid_corp}\n\n"
                num_seg += 1

                corp_seg += f"{{{{{num_seg},{len(nombre_carpeta.split())}}}}} {nombre_carpeta}\n\n"
                num_seg += 1

                for noticia_info in noticias_ordenadas:
                    for oracion in noticia_info['oraciones']:
                        if oracion and oracion.strip() and len(oracion.strip()) > 5:
                            wdcount = len(oracion.split())
                            corp_seg += f"{{{{{num_seg},{wdcount}}}}} {oracion}\n\n"
                            num_seg += 1

                corp_seg = limpiar_copyright(corp_seg)

                with open(ruta_corp_seg, 'w', encoding='utf-8') as f:
                    f.write(corp_seg)
                print(f"   [CORP-SEG] {nombre_corp_seg}")

                nombre_corp_blanco = f"CORP-BLANCO-{iniciales_carpeta}-{total_noticias_carpeta}.txt"
                ruta_corp_blanco = os.path.join(directorio_salida, nombre_corp_blanco)

                corp_blanco = ""
                corp_blanco += f"{docid_corp}\n\n"
                corp_blanco += f"{nombre_carpeta}\n\n"

                for noticia_info in noticias_ordenadas:
                    for oracion in noticia_info['oraciones']:
                        if oracion and oracion.strip() and len(oracion.strip()) > 5:
                            corp_blanco += f"{oracion}\n\n"

                corp_blanco = limpiar_copyright(corp_blanco)

                with open(ruta_corp_blanco, 'w', encoding='utf-8') as f:
                    f.write(corp_blanco)
                print(f"   [CORP-BLANCO] {nombre_corp_blanco}")

            if datos_carpeta:
                todos_los_datos.extend(datos_carpeta)
                total_nuevas += nuevas_carpeta
                total_existentes += existentes_carpeta
                print(f"   En esta carpeta: {nuevas_carpeta} nuevas, {existentes_carpeta} existentes")

        except Exception as e:
            print(f"Error procesando carpeta {directorio}: {e}")
            carpetas_con_error.append(directorio)

    if todos_los_datos:
        try:
            df_nuevo = pd.DataFrame(todos_los_datos)
            df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
            df_final.to_excel(ruta_excel, index=False)
            print(f"\nBase de datos actualizada con {total_nuevas} nuevas noticias")
            print(f"Base de datos guardada en: {ruta_excel}")
        except Exception as e:
            print(f"Error guardando Excel: {e}")
    else:
        print("\nNo se procesaron nuevas noticias para Excel")

    print("\n" + "=" * 60)
    print("PROCESAMIENTO COMPLETADO")
    print(f"Total de carpetas procesadas: {len(carpetas) - len(carpetas_con_error)}")
    print(f"Total de archivos generados: {total_nuevas + total_existentes}")
    print(f"   - Nuevos en Excel: {total_nuevas}")
    print(f"   - Reprocesados: {total_existentes}")

    if carpetas_con_error:
        print(f"\nCarpetas con errores ({len(carpetas_con_error)}):")
        for carpeta in carpetas_con_error:
            print(f"   - {carpeta}")


ruta_raiz = r'C:/Users/lm354/Desktop/NOTICIAS 2026 CORPUS NUEVOS/CON FUNCION DE APTITUD/MODIFICADO/LOS DOS CORPUS ANT Y DESP/2 CORPUS DE NOTICIAS'

if __name__ == "__main__":
    procesar_todos_los_archivos_html_recursivo(ruta_raiz)
