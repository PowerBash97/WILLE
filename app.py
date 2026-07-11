# Imports de terceros
import dash
from dash import html, dcc, Input, Output, State, no_update, ALL 
from concepts import Context
import base64
import pickle
import gzip

# Imports locales
from utils import *
from layouts import *

# ---------------------------------------------------------------------------------------
# 3. Lógica Central de la Aplicación
# ---------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 3.1. Instanciación del Servidor y definición como layout inicial de la aplicación 
#      el relativo a la pantalla inicial

# ------------------------------------------------------------------------------
# i) Instanciar el servidor web local (mediante Flask)
#    - Por medio de la variable __name__ propia de Python, se indica que todo el 
#      código de la aplicación está en este mismo archivo 
#    - Y "suppress_callback_exceptions=True" permite empezar la aplicación
#      por la primera pantalla, sin que los callbacks propios de la 
#      interacción con el retículo (en la segunda pantalla) empiecen a 
#      lanzar excepciones debido a que aún no existen ciertos elementos
#      que se crearán una vez se dé paso de la primera a la segunda pantalla.
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# -------------------------------------------------------------------------------------
# ii) Definición del layout inicial de la aplicación + Añadir componente de carga
#
# Envolvemos el contenedor principal en un componente de carga "dcc.Loading" (para que 
# de esta forma, cada vez que el sistema esté procesando una petición del usuario, este 
# último pueda tener cierto feedback visual de que efectivamente se están haciendo los 
# cálculos pertinentes)
app.layout = dcc.Loading(
    id="loading-pantalla",
    type="circle",          
    color="#1976D2",        
    fullscreen=True, # La animación ocupa toda la pantalla
    children=[
        html.Div(id="contenedor-principal", children=[
            layout_pantalla_inicio()
        ])
    ]
)

# ---------------------------------------------------------------------------------
# iii) Callbacks auxiliares (que actúan sobre el layout de la pantalla inicial)
#
# Estos dos Callback muestran en la pantalla inicial el nombre del archivo subido,
# (hay uno para cada una de las dos grandes vías de entrada: cargar un contexto o 
# restaurar una sesión)

# Vía 1: Cargar contexto
@app.callback(
    Output('nombre-archivo-csv', 'children'),
    Input('entrada-archivo-csv', 'filename')
)
def actualizar_nombre_archivo_contexto(filename):
    if filename is not None: # Solo si realmente se ha subido un archivo
        return f"Archivo seleccionado: {filename}"
    return "" # (En otro caso, el cuadro se mantiene vacío)

# Vía 2: Restaurar sesión
@app.callback(
    Output('nombre-archivo-wille', 'children'),
    Input('entrada-archivo-wille', 'filename')
)
def actualizar_nombre_archivo_sesion(filename):
    if filename is not None: 
        return f"Archivo seleccionado: {filename}"
    return "" 

# ---------------------------------------------------------------------------------
# 3.2. Transición de la pantalla inicial a la principal (el espacio principal de 
#      Exploración), incluyendo:
#      - Interpretar la entrada en función del método elegido en la pantalla inicial
#      - Cálculo del retículo de conceptos
#      - Cálculos asociados a la representación del retículo en forma de diagrama
#      - Carga del layout relativo a la pantalla principal (junto a sus paneles 
#        laterales y el panel inferior)
#      - Capturar las excepciones derivadas de un formato/contenido incorrecto,
#        así como el eventual desbordamiento de memoria durante el cálculo del
#        retículo de conceptos.
#
# Este callback escucha hasta que se haga click sobre el botón de ejecución 
# pertinente en la pantalla inicial, haciendo todos los cálculos necesarios y, 
# finalmente dando paso a la pantalla de exploración. 
#
# Tiene por parámetros de entrada el contenido de los difentes métodos de selección 
# de la entrada (ya fuera cargando un contexto: por medio de un ejemplo precargado,
# mediante un archivo subido, o escribiendo manualmente el contexto en un cuadro de 
# texto; o bien cargando el archivo .wille con la información de una sesión previa)

@app.callback(
    Output('contenedor-principal', 'children'),
    Output('inicio-error', 'children'),
    Input('btn-nueva-sesion', 'n_clicks'),      # Botón de ejecución (opción 1 - Cargar contexto)
    Input('btn-restaurar-sesion', 'n_clicks'),  # Botón de ejecución (opción 2 - Cargar sesión)
    # Variables relativas al contenido de la entrada introducida (por 4 vías posibles)
    State('tabs-metodo-entrada', 'value'),
    State('entrada-ejemplo', 'value'),
    State('entrada-archivo-csv', 'contents'),      # Archivo .csv (contexto formal)
    State('entrada-texto', 'value'),
    State('entrada-archivo-wille', 'contents'),    # Archivo .wille (sesión guardad)
    State('entrada-archivo-wille', 'filename'),
    prevent_initial_call=True
)
def iniciar_exploracion(btn_nuevo, btn_restaurar, tab_activa, val_ejemplo, val_csv, val_texto, val_wille, filename_wille):

    # ---------------------------------------------------------------------------------
    # i) Identificar el botón que se ha pulsado, para establecer la vía de 
    #    acceso (cargando un contexto formal, o una sesión previa)
    #    +
    #    (En cualquiera de las vías) Comprobar que el usuario haya introducido algo, 
    #    y mediante un bloque try-catch interpretar la entrada, respetando el límite 
    #    de tamaño del contexto formal de entrada (si este fue el método de entrada), 
    #    así como capturar excepciones debidas a que que el formato no sea válido, o 
    #    que el cálculo del retículo produzca un desbordamiento de memoria RAM.
    #    +
    #    Procesar convenientemente cada una de las dos vías de acceso (Restaurando 
    #    una sesión previa, o bien cargando un contexto formal desde cero) 

    # Identificar el botón pulsado
    disparador = dash.ctx.triggered_id
    
    # Indicar a Python que se van a modificar las variables globales
    global ctx, lista_conceptos, concepto_a_id, nodos_master, aristas_master

    # Interpretar la entrada
    try:
        # Caso 1 (Cargar una sesión anterior a partir de un archivo .wille)
        if disparador == 'btn-restaurar-sesion':
            # 0) Validar que el usuario ha introducido ALGO
            if not val_wille or not filename_wille.endswith('.wille'):
                return no_update, "Por favor, suba un archivo de sesión válido (.wille)."
                
            content_type, content_string = val_wille.split(',')

            # 1) Decodificar en base 64 mediante la función "b64decode" los bytes del archivo (comprimido)
            decoded_comprimido = base64.b64decode(content_string)
            
            # 2) Descomprimir los bytes por medio de la función "decompress" de gzip
            decoded_original = gzip.decompress(decoded_comprimido)
            
            # 3) Deserializar con pickle (recuperando la estructura de datos original, el 
            # diccionario con cinco entradas conteniendo toda la información necesaria para 
            # representar el retículo e interactuar visualmente con él, así como localizar/buscar)
            datos_sesion = pickle.loads(decoded_original)
            
            # 4) Interpretar todos los datos de la sesión:
            # 
            #   a) Restaurar el contexto formal a partir del archivo en formato csv (generando
            #      el objeto de la clase "Concepts.context"), mediante el método "fromstring"
            ctx = Context.fromstring(datos_sesion['ctx_csv'], frmat='csv')

            #   b) Lista de conceptos formales (usando la clase "ConceptoPlano" - simplemente leyendo
            #      la lista de extensiones e intensiones y usando el constructor de la clase)
            lista_conceptos = [ConceptoPlano(d['e'], d['i']) for d in datos_sesion['conceptos_planos']]
            
            #   c) Reconstruir el diccionario de IDs de los conceptos (a efectos prácticos, como las 
            #      listas en Python mantienen un orden estricto de inserción, al hacer el enumerate, 
            #      a los elementos se les asigna exactamente el mismo ID que tenían antes de ser exportados)
            concepto_a_id = {c: str(i) for i, c in enumerate(lista_conceptos)}
            
            #   d) Identificar las listas de nodos y aristas (con las coordenadas absolutas, 
            #      las etiquetas, etc.), así como el identificador del nodo ínfimo global.
            # NOTA: El identificador de este último nodo seguirá siendo válido, relativo al resto 
            # de nodos, porque se han reinterpretado los elementos de la lista de conceptos en el 
            # mismo orden en que fueron exportados en una sesión previa (iterando con un bucle for, 
            # siguiendo el mismo orden que tuvieran cuando se serializaron y guardaron en disco) 
            nodos_master = datos_sesion['nodos_master']
            aristas_master = datos_sesion['aristas_master']
            id_infimo = datos_sesion['id_infimo']

            centro_inicial = datos_sesion.get('ultimo_nodo_central', id_infimo)
            zoom_inicial = datos_sesion.get('ultimo_nivel_zoom', 1)
    
        # Caso 2 (Cargar el contexto formal - y hacer todos los cálculos desde cero)
        elif disparador == 'btn-nueva-sesion':
            
            # Limpiamos las variables de las pestañas inactivas 
            # (Para que solo se tenga en cuenta el contenido de la pestaña activa 
            # al momento de pulsar el botón)
            if tab_activa == 'tab-ejemplo':
                val_csv = None
                val_texto = None
            elif tab_activa == 'tab-upload-csv':
                val_ejemplo = None
                val_texto = None
            elif tab_activa == 'tab-texto':
                val_ejemplo = None
                val_csv = None

            # 0) Validar que el usuario ha introducido ALGO
            if not val_ejemplo and not val_csv and not val_texto:
                return no_update, "Por favor, seleccione o introduzca un contexto válido en la pestaña actual."

            # Lectura de los datos según el método de entrada seleccionado:
            #
            #   1) Ejemplo Precargado (se interpretan mediante el método "fromfile" de la clase "Context" de "concepts")
            if val_ejemplo:
                ctx = Context.fromfile(val_ejemplo, frmat='csv', encoding='utf-8')

            #   2) Subir un Archivo Local (decodificándolo en base 64 mediante la función "b64decode" 
            #     del módulo base64, así como luego pasándolo a string mediante el método "decode", 
            #     en formato utf-8, para finalmente interpretarlo mediante el método "fromstring"
            #     de la clase "Context" de "concepts")
            elif val_csv:
                content_type, content_string = val_csv.split(',')
                decoded = base64.b64decode(content_string).decode('utf-8') # Decodificar el archivo subido en Base64 y pasarlo a string en formato utf-8
                ctx = Context.fromstring(decoded, frmat='csv')

            #   3) Cuadro de Texto Manual (análogo al método anterior, pero simplemente haciendo una
            #      lectura directa e interpretándolo mediante el método "fromstring" de la clase "Context")
            elif val_texto:
                ctx = Context.fromstring(val_texto, frmat='csv')

            # Controlar el comportamiento en casos límite, limitando el tamaño máximo
            # de los Contextos formales (tanto a 20 objetos como a 20 atributos)
            #
            # Primero se obtiene el número de objetos y atributos del contexto
            num_obj = len(ctx.objects)
            num_attr = len(ctx.properties)
            #
            # A continuación, en caso de que se exceda el límite impuesto, se congela la interacción y se
            # muestra un mensaje de error, avisando al usuario de que el contexto formal no cumple dicho límite
            if min(num_obj,num_attr) > MAX_ELEMENTOS:
                return no_update, f"[!] El contexto introducido ({num_obj} obj x {num_attr} atr) excede el límite de tamaño permitido. Por motivos de rendimiento y memoria, el mínimo entre el número de objetos y atributos no debe exceder {MAX_ELEMENTOS}."
            
            # ---------------------------------------------------------------------------------
            # ii) Generar el Retículo de Conceptos (con 'concepts') 
            #     + 
            #     Traducir los conceptos formales al lenguaje de dash/dash-cytoscape (por medio de un diccionario de IDs)

            lattice = ctx.lattice 
            lista_conceptos = list(lattice) # Convertir la estructura del objeto de la clase "Lattice" a una lista (de conceptos formales)
            concepto_a_id = {c: str(i) for i, c in enumerate(lista_conceptos)}

            # ---------------------------------------------------------------------------------
            # iii) Cálculo de las Coordenadas tipo "Grid" del diagrama de Hasse del Retículo 
            #      + 
            #      Identificar los nodos asociados a los conceptos supremo e ínfimo global

            coordenadas_absolutas = calcular_coordenadas_absolutas_diagrama(lista_conceptos, concepto_a_id)
            id_infimo, id_supremo = identificar_extremos_del_reticulo(lista_conceptos)

            # ---------------------------------------------------------------------------------
            # iv) Precalcular listas de Nodos y Aristas "master" (con toda la información necesaria para Dash)
            #
            # - Nodos: Sus etiquetas reducida (atributos/objetos propios, si tiene) y extendida (su 
            #          Extensión e Intensión), su ID, su nivel, y sus super/sub-conceptos directos, 
            #          así como su Posición (las coordenadas "absolutas" calculadas previamente)
            #
            # - Aristas: Arcos orientados, que parten de cada concepto formal hacia sus super-conceptos
            #            inmediatos
            
            # Nos aseguramos de empezar por vaciar las listas (por si el usuario vuelve a generar otro retículo)
            nodos_master = []
            aristas_master = []

            # Nodos: Recorremos todos los conceptos formales (a través del diccionario por ID)
            for c, cid in concepto_a_id.items():
                
                # 1) Cálculo de la etiqueta reducida (atributos/objetos propios + Identificador de los nodos 1 y 0) 
                lineas_reducida = []
                objetos_propios, atributos_propios = filtrar_objetos_y_atributos_propios(c)
                
                # Si se trata del nodo asociado al concepto supremo o ínfimo global del retículo, se identifican también como 
                # los nodos [1] y [0], respectivamente (para identificarlos visualmente con más facilidad)
                if cid == id_supremo: lineas_reducida.append("[1]")
                elif cid == id_infimo: lineas_reducida.append("[0]")
                
                # En cuanto a los atributos/objetos propios, en caso de que superen el umbral "UMBRAL_MAX", 
                # simplemente se indica su número, y en otro caso, se listan.
                if atributos_propios: 
                    if len(atributos_propios) > UMBRAL_MAX: lineas_reducida.append(f"(A) +{len(atributos_propios)} attr")
                    else: lineas_reducida.append("(A) " + ", ".join(atributos_propios))
                if objetos_propios: 
                    if len(objetos_propios) > UMBRAL_MAX: lineas_reducida.append(f"(O) +{len(objetos_propios)} obj")
                    else: lineas_reducida.append("(O) " + ", ".join(objetos_propios))
                
                # (Caso bastante común - Conceptos formales sin objetos ni atributos propios)
                # Si después de todo, el nodo no tiene etiqueta (es un nodo intermedio vacío), le ponemos un punto.
                # NOTA IMPORTANTE: De no considerar esto aquí, estos nodos no se llegan a visualizar.
                if not lineas_reducida: 
                    lineas_reducida.append("•")

                # Para componer las diferentes cadenas en una única "etiqueta reducida", las unimos con saltos de línea
                label_reducida = "\n".join(lineas_reducida)

                # 2) Cálculo de la etiqueta completa (Extensión e Intensión completas, desglosadas)
                lineas_completa = []
                
                # Igual que en la etiqueta reducida, indicamos si estamos ante el supremo o ínfimo globales
                if cid == id_supremo: lineas_completa.append("[1]")
                elif cid == id_infimo: lineas_completa.append("[0]")

                # De forma análoga a las etiquetas reducidas, si el número de elementos en la extensión
                # o la intensión supera el umbral permitido, simplemente se indica su número, y en otro 
                # caso, almacenamos la lista de atributos de la Intensión, separados por comas
                # y análogamente la lista de objetos de la Extensión (y si alguna de las dos es vacía, 
                # lo indicamos con el símbolo "Ø")
                if c.extent: 
                    if len(c.extent) > UMBRAL_MAX: lineas_completa.append(f"Ext: {len(c.extent)} objetos")
                    else: lineas_completa.append("Ext: " + ", ".join(c.extent))
                else: lineas_completa.append("Ext: Ø")

                if c.intent: 
                    if len(c.intent) > UMBRAL_MAX: lineas_completa.append(f"Int: {len(c.intent)} atributos")
                    else: lineas_completa.append("Int: " + ", ".join(c.intent))
                else: lineas_completa.append("Int: Ø")

                label_completa = "\n".join(lineas_completa) # Componemos igual que con las etiquetas reducidas

                # 3) Almacenar toda la información del nodo en la lista "nodos_master", en el formato 
                #    adecuado para luego pasársela a dash-cytoscape
                nodos_master.append({
                    'data': {
                        'id': cid, 
                        'label_reducida': label_reducida, 
                        'label_completa': label_completa,
                        # El nivel, como ya definimos previamente, es el número de objetos de la extensión
                        'nivel': len(c.extent),
                        # Almacenamos los IDs de sus super/sub-conceptos inmediatos
                        'super_inmediatos': [concepto_a_id[sup] for sup in c.upper_neighbors],
                        'sub_inmediatos': [concepto_a_id[sub] for sub in c.lower_neighbors]
                    },
                    # La posición del nodo es la previamente calculada en coordenadas "grid"
                    'position': coordenadas_absolutas[cid]
                })

            # Aristas: Igual que con los nodos, empezamos por recorrer la lista de conceptos
            #          empleando el diccionario "concepto_a_id" (para obtener tanto el propio concepto como su ID)
            #          y a partir del concepto, recorremos sus super-conceptos directos y 
            #          añadimos una arista conectando el nodo origen con el super-concepto (en realidad
            #          añadimos sus IDs, por medio del diccionario, que es lo que entiende dash-cytoscape)
            for c, cid in concepto_a_id.items():
                for sup in c.upper_neighbors:
                    aristas_master.append({'data': {'source': cid, 'target': concepto_a_id[sup]}, 'classes': 'arista'})

            # Valores por defecto para la vista local inicial (si se ha cargado un contexto formal de cero)
            centro_inicial = id_infimo
            zoom_inicial = 1

        # ---------------------------------------------------------------------------------
        # NOTA: El código que sigue a continuación ya es independiente de la vía de entrada empleada

        # El zoom máximo lo dicta el número máximo de niveles del retículo 
        # (i.e. el número de objetos del contexto formal)
        # De esta forma, y en línea con el algoritmo de cálculo de las posiciones de los nodos del 
        # diagrama, se permite visualizar simultáneamente todos los niveles del mismo en pantalla,
        # aún desde el nodo mínimo (el nodo 0).
        max_zoom = len(ctx.objects)
        
        # ---------------------------------------------------------------------------------
        # v) Cargar el Layout de la pantalla principal de exploración
        #
        # La variable "layout_app" define el diseño (layout) visual de la pantalla principal
        # siendo este bastante más complejo que el de la pantalla inicial
        layout_app = layout_pantalla_principal(max_zoom, zoom_inicial, centro_inicial)

        # El callback devuelve la variable "layout_app" para que Dash sobreescriba la pantalla 
        # de inicio, dando paso a la pantalla principal (concretamente, se sobreescribe el contenido
        # del parámetro "children" del layout de la app -> por medio del parámetro de salida
        # 'contenedor-principal' de este callback, que era el Identificador de app.layout)
        return layout_app, ""

    # ---------------------------------------------------------------------------------
    # vi) Captura de excepciones 
    
    # 1) Capturar el caso en que el cálculo del retículo por concepts conlleve 
    # un desbordamiento de memoria (excepción "MemoryError")
    except MemoryError:
        return no_update, "[!] Error Crítico: El cálculo del retículo asociado a este contexto ha desbordado la memoria RAM disponible del servidor."
    
    # 2) Capturamos también el resto de excepciones, que aquí se reducen a  
    #    errores de formato/contenido del contexto formal (i.e. se da un error
    #    al intentar procesar la entrada que eligió el usuario - en esencia,
    #    un archivo mal formateado o con contenido incompleto, o un contenido
    #    en un formato inadecuado en caso de introducir un contexto manualmente)
    except Exception as e:
        return no_update, f"[!] Error al procesar el contexto: Compruebe que esté correctamente formateado y libre de fallos tipográficos. ({str(e)})"

# ---------------------------------------------------------------------------------------
# 3.3. Lógica de Interacción en la pantalla principal, por medio de sendos "callbacks":
#    
#    - Uno para mostrar la "vista local" del retículo (haciendo un "recorte espacial" de 
#      aquellos elementos visuales que queden dentro del recinto centrado en el nodo 
#      seleccionado y teniendo en cuenta el "Zoom lógico" cosiderado: nodos, aristas 
#      e indicios de que hay más nodos ocultos en otras direcciones), haciendo uso de 
#      las coordenadas del diagrama calculadas previamente en la sección 3.2.
#
#    - Otro para navegar por clic (actualizando el centro de la vista al nodo clicado),
#      gestionar la localización de un concepto formal mediante el panel lateral "Derivador"
#      (actualizando también el centro de vista a dicho nodo), así como actualizar la vista 
#      si se selecciona alguno de los resultados de una Búsqueda (pulsando el botón "dinámico" 
#      correspondiente en el panel "Buscador").
#      NOTA: Es necesario englobar todas estas funcionalidades bajo un mismo callback, a 
#            fin de que sólo uno sea el encargado de modificar la misma variable (el 
#            centro de vista), y evitar así cualquier error lógico derivado de esta 
#            concurrencia de peticiones.
#
#    - Otro para ejecutar una Búsqueda en el panel "Buscador" (i.e. obtener los conceptos 
#      formales que contengan en su extensión/intensión un determinado subconjunto de 
#      objetos/atributos, respectivamente) añadiendo un botón a cada uno de los conceptos 
#      resultantes listados, para permitir centrar la vista en estos.
#
#    - Otro para actualizar el panel inferior de "Inspección", con la Extensión e Intensión
#      asociadas al concepto formal central de la vista en cada momento.
#    
#    - Otro para Guardar/Exportar la sesión (almacenando de forma persistente, en un archivo .wille, 
#      toda la información necesaria relativa a la sesión)
#
#    - Otros para gestiones "menores" de los dos paneles laterales (Derivador y Buscador), a saber:
#      a) Abrir y Cerrar los paneles pulsando el botón correspondiente
#      b) Actualizar las opciones del Dropdown de selección del panel (y que dependerán de
#         si se eligió escoger atributos u objetos)
# ---------------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------------
# i) Cálculo de la "Vista local" del retículo 

# Se dispara por el cambio de dos variables (inputs):
#  
# - El nodo central: Ya sea porque el usuario haya hecho clic en un nodo nuevo, o se ha localizado  
#   el concepto formal asociado a un subconjunto de elementos en el panel "Derivador",
#   o se ha clicado sobre un botón "dinámico" en alguno de los resultados de una búsqueda
#   en el panel "Buscador" (El ID del nodo central 'centro-store' ha cambiado de valor)
#
# - El nivel de Zoom: Se ha movido el slider de "Zoom lógico" (debiendo considerar una vista
#   ampliada o reducida, tanto en cuanto a niveles en altura mostrados por encima y debajo 
#   del nodo seleccionado, como también en cuanto a nodos dispuestos en horizontal en cada 
#   nivel)

# Y se actualiza la propiedad "elements" (los elementos visuales que visualiza dash-cytoscape)
# a partir de lo que calcule y devuelva la función que define al callback

@app.callback(
    Output('reticulo-cytoscape', 'elements'), # La representación visual del retículo con Cytoscape
    Input('centro-store', 'data'), # El identificador del nodo sobre el que está centrada la vista
    Input('zoom-slider', 'value') # El valor de "zoom lógico" aplicado
)
def vista_local_reticulo(centro_id, nivel_zoom):
    nivel_centro = None
    x_centro = None
    super_del_centro = []
    sub_del_centro = []

    # 1) Encontrar las coordenadas de la cámara
    #    (simplemente se localiza el nodo seleccionado de entre la lista "nodos_master", 
    #    precalculada en la sección 3.2., y lo toma como el centro de la cámara, 
    #    tomando de él sus coordenadas, así como los nodos asociados a sus 
    #    super/sub-conceptos inmediatos)
    for nodo in nodos_master:
        if nodo['data']['id'] == centro_id:
            nivel_centro = nodo['data']['nivel']
            x_centro = nodo['position']['x']
            super_del_centro = nodo['data']['super_inmediatos']
            sub_del_centro = nodo['data']['sub_inmediatos']
            break
            
    # 2) Filtrado espacial (de Nodos y Aristas)

    #   El límite horizontal (radio_visual_x) crece dinámicamente con el zoom, 
    #   de hecho, de forma lineal con este, con el factor constante "ESPACIADO_X"
    #   Y como se verá más abajo, el límite vertical (tanto hacia arriba como hacia
    #   abajo), está fijado literalmente con el nivel de zoom
    radio_visual_x = VALOR_BASE + (nivel_zoom * ESPACIADO_X)

    # Inicializamos sendos conjuntos para almacenar los IDs de los nodos que serán
    # visibles en la vista local, así como los nodos ocultos (ya sean tanto nodos 
    # cualesquiera, como super/sub-conceptos directos del nodo seleccionado)
            
    # - Nodos (y Aristas) visibles + Indicadores de nodos ocultos 
    ids_visibles = set()
    elementos_filtrados = [] # Este conjunto reescribirá el conjunto "elements" de dash-cytoscape
    nodos_ocultos = [] # Esta será la lista de nodos "ocultos" (que no sobreviven al filtrado espacial)

    # - Nodos ocultos (arriba/abajo, izda/dcha en cada nivel)
    #   No solo se guardan los roles de los nodos ocultos (si solo son nodos "normales" 
    #   o también hay alguno que sea "super"/"sub"-concepto del concepto seleccionado), 
    #   sino también el conteo de estos
    #
    #   En el caso de nodos que estén en niveles por encima o por debajo de los
    #   mostrados en la vista local actual, simplemente basta con manejar un par de
    #   conjuntos y contadores
    count_arriba = 0
    roles_arriba = set()
    count_abajo = 0
    roles_abajo = set()
    #   Mientras que en el caso de los nodos ocultos a izquierda/derecha, es necesario
    #   hacer uso de sendos diccionarios, que usarán como clave el nivel y, por cada nivel, 
    #   almacene el conjunto con los roles, así como el contador respectivo
    #   (i.e. Diccionario: nivel -> {'roles': set(), 'count': int})
    ocultos_izq = {} 
    ocultos_der = {}

    # a) Filtrado/rastreo de NODOS VISIBLES
    for nodo in nodos_master:
        # Empezamos almacenando en variables locales el id y las coordenadas del nodo
        nid = nodo['data']['id']
        nivel_nodo = nodo['data']['nivel']
        x_nodo = nodo['position']['x']
        
        # Calculamos la distancia del nodo al centro de la cámara
        distancia_y = abs(nivel_nodo - nivel_centro)
        distancia_x = abs(x_nodo - x_centro)
        
        # Identificamos qué relación tiene nodo respecto al nodo central
        # (o bien no tiene relación directa, o bien es un "super/sub-concepto" 
        # directo de este)
        rol_nodo = 'nada' # Por defecto, no está relacionado con el central
        if nid in super_del_centro: rol_nodo = 'super'
        elif nid in sub_del_centro: rol_nodo = 'sub'
        
        # Filtrado (solo dejamos aquellos nodos que estén dentro del límite de 
        # distancia horizontal o de distancia máxima en cuanto a nivel - i.e. 
        # el nivel de "zoom lógico") -> Solo estos se añadirán como nodos visibles
        if distancia_y <= nivel_zoom and distancia_x <= radio_visual_x:
            ids_visibles.add(nid)
            nodo_copia = {'data': nodo['data'].copy(), 'position': nodo['position'], 'classes': 'nodo'}
            
            if nid == centro_id: # Si el nodo es el central, su etiqueta mostrada será la Completa (Intent+Extent)
                nodo_copia['data']['rol'] = 'centro'
                nodo_copia['data']['label'] = nodo['data']['label_completa']
            else: # En otro caso, la etiqueta reducida (solo los atributos/objetos propios)
                nodo_copia['data']['rol'] = rol_nodo
                nodo_copia['data']['label'] = nodo['data']['label_reducida']
                
            elementos_filtrados.append(nodo_copia) # Añadimos los nodos visibles a los "elementos filtrados"

        # Si el nodo cae fuera del recinto visible, guardamos su rol (así como otros datos necesarios,
        # como sus coordenadas y su nivel), para posteriormente asignarlo en el "rastreador" correspondiente
        else:
            nodo_copia = {'data': nodo['data'].copy(), 'position': nodo['position']}
            nodo_copia['data']['rol'] = rol_nodo
            nodo_copia['data']['nivel'] = nivel_nodo
            nodos_ocultos.append(nodo_copia)

    # b) Coordenadas de la Caja Delimitadora "Estricta"
    #
    #    Una vez filtrados los nodos visibles, se puede establecer los límites "reales" 
    #    de la caja delimitadora que comprenderá la vista local considerada

    # Para que el acceso posterior a las posiciones de los nodos sea más rápido, 
    # se precalcula un diccionario a partir de la lista "nodos_master", con el identificador
    # del nodo como clave.
    pos_nodos = {n['data']['id']: n['position'] for n in nodos_master}

    # Empezaremos por extraer las coordenadas REALES de los nodos que han sobrevivido 
    # al filtrado de la vista local (para calcular la posición tanto de las aristas 
    # "discontinuas", como de los indicadores visuales, sin dejar grandes espacios 
    # arbitrariamente, sino en base a los límites de los nodos que se van a representar 
    # - i.e. adaptando su posición a los nodos finalmente visualizados)
    x_visibles = [pos_nodos[nid]['x'] for nid in ids_visibles]
    y_visibles = [pos_nodos[nid]['y'] for nid in ids_visibles]
    
    # Si hay nodos, calculamos la región "estricta" de la vista local, determinada por las
    # coordenadas de los nodos supervivientes que quedan en las esquinas. En otro caso (caso
    # raro) se usan las coordenadas del nodo central de la vista.
    x_min_real = min(x_visibles) if x_visibles else x_centro
    x_max_real = max(x_visibles) if x_visibles else x_centro
    y_min_real = min(y_visibles) if y_visibles else -nivel_centro * ESPACIADO_Y # Borde superior 
    y_max_real = max(y_visibles) if y_visibles else -nivel_centro * ESPACIADO_Y # Borde inferior

    # c) Rastreo de los NODOS OCULTOS
    # 
    # Se rastrean los nodos "ocultos" (los que no sobrevivieron al filtrado espacial)
    # y en función de su posición relativa a la caja delimitadora "estricta" de la vista
    # local considerada, se guarda su rol en el "rastreador" correspondiente (para localizar 
    # en qué dirección estaría respecto a la vista local, y poder mostrar los indicadores 
    # visuales pertinentes) e incrementamos el contador correspondiente en uno, por cada nodo 
    # detectado.
    for nodo in nodos_ocultos: 
        nid = nodo['data']['id']
        x_nodo = nodo['position']['x']
        y_nodo = nodo['position']['y']
        rol_nodo = nodo['data']['rol']
        nivel_nodo = nodo['data']['nivel']

        # Caso 1 (Se escapa por el eje vertical)
        if y_nodo < y_min_real: # Está por encima de la vista local
            count_arriba += 1
            roles_arriba.add(rol_nodo)
        elif y_nodo > y_max_real: # Está por debajo de la vista local
            count_abajo += 1
            roles_abajo.add(rol_nodo)
        # Caso 2 (NO se escapa por el eje vertical, PERO SÍ por el horizontal)    
        else:
            if x_nodo < x_min_real: # Está a la izquierda (de los nodos de la vista local al nivel de este)
                if nivel_nodo not in ocultos_izq: # Si aún no había registrada una entrada en el diccionario para ese nivel, se inicializa
                    ocultos_izq[nivel_nodo] = {'roles': set(), 'count': 0}
                ocultos_izq[nivel_nodo]['roles'].add(rol_nodo)
                ocultos_izq[nivel_nodo]['count'] += 1
            elif x_nodo > x_max_real: # Está a la derecha 
                if nivel_nodo not in ocultos_der: 
                    ocultos_der[nivel_nodo] = {'roles': set(), 'count': 0}
                ocultos_der[nivel_nodo]['roles'].add(rol_nodo)
                ocultos_der[nivel_nodo]['count'] += 1

    # d) Filtrado de las ARISTAS (VISIBLES + Recortar las que conectan un nodo visible y uno oculto)
    # 
    #  - Dejando por un lado aquellas que unen nodos dentro de la misma vista local, representadas 
    #    con un trazo continuo
    #  - Y por otro, se calculan también aquellas aristas que unen nodos de la vista local con 
    #    otros fuera de esta, representando estas con trazo discontinuo, así como usando 
    #    nodos auxiliares en los bordes de la vista local, cuyas coordenadas se calculan como la 
    #    intersección de la recta que une los dos nodos "reales" (entendida como una idealización 
    #    de la arista que los une) con el borde de la vista local considerada.

    # Para empezar, las fronteras definitivas de la vista local (conformada no solo por los
    # nodos visibles, sino también de las aristas, tanto con trazo continuo como discontinuo)
    # vendrán dadas por las rectas determinadas por x_min, x_max, y_min, y_max, respectivamente
    # (tras añadir el relleno, o "margen")
    x_min = x_min_real - MARGEN_X
    x_max = x_max_real + MARGEN_X
    y_min = y_min_real - MARGEN_Y
    y_max = y_max_real + MARGEN_Y

    for arista in aristas_master: # Se recorren todas las aristas
        # Se almacenan para cada una los IDs de los nodos origen y destino
        src = arista['data']['source']
        tgt = arista['data']['target']
            
        # Caso 1: Ambos nodos están dentro (en cuyo caso se dibuja la arista de forma "normal", 
        #         con trazo continuo)
        if (src in ids_visibles) and (tgt in ids_visibles):
            elementos_filtrados.append(arista)
                
        # Caso 2: Uno está dentro y el otro fuera (en cuyo caso se calcula la intersección de la 
        #         arista con el borde de la vista local)
        elif (src in ids_visibles) or (tgt in ids_visibles):
                
            # Primero identificamos cuál de los dos es el nodo visible y cuál es el oculto.
            # Y almacenamos sus coordenadas, consultando estas en el diccionario de posiciones.
            visible_id = src if (src in ids_visibles) else tgt
            oculto_id = tgt if (src in ids_visibles) else src
            x1, y1 = pos_nodos[visible_id]['x'], pos_nodos[visible_id]['y'] # Posición del nodo visible
            x2, y2 = pos_nodos[oculto_id]['x'], pos_nodos[oculto_id]['y'] # Posición del nodo oculto
                
            # NOTA: En realidad, el presente algoritmo es una particularización del, aún más general, 
            #       de Liang-Barsky. En nuestro caso, se sabe que hay necesariamente un nodo
            #       dentro del recinto rectangular (de la vista local), y otro fuera, y se sabe
            #       cuál es cuál. Por tanto, basta con calcular los parámetros t del punto de 
            #       intersección de la recta que sale del punto dentro del recinto (x1,y1), 
            #       hacia el punto fuera de este (x2,y2), con las cuatro rectas que definen los
            #       propios límites del recinto (las dos rectas horizontales dadas por y_min e y_max,
            #       así como las dos verticales dadas por x_min y x_max) y quedarse, entre los 
            #       positivos, con aquel que sea menor (Para este t, se tendrá el punto de corte 
            #       con el recinto)

            # Vector director de la recta que une ambos puntos (dx,dy)
            dx = x2 - x1
            dy = y2 - y1

            # Lista de parámetros t de las 4 posibles intersecciones
            t_candidatos = [] 
                
            # Interseccion con las 2 rectas verticales
            if dx != 0: # Para evitar dividir por cero (si la arista es horizontal)
                t_candidatos.append((x_min - x1) / dx) 
                t_candidatos.append((x_max - x1) / dx)

            # Interseccion con las 2 rectas horizontales
            if dy != 0: # Para evitar dividir por cero (si la arista es vertical)
                t_candidatos.append((y_min - y1) / dy)
                t_candidatos.append((y_max - y1) / dy)
                    
            # Buscamos el valor mínimo del parámetro t, dentro de los positivos 
            # (dirección hacia afuera del recinto)
            t_positivos = [t for t in t_candidatos if t > 0] # Primero nos quedamos con los valores positivos de t
            if t_positivos:
                t_min = min(t_positivos)
                t_min = min(t_min, 1.0) # Para evitar desbordamientos de float
                    
                # Coordenadas del punto de intersección con el borde de la vista local (nodo auxiliar)
                aux_x = x1 + t_min * dx
                aux_y = y1 + t_min * dy
                
                # Le asignamos un ID único al nodo auxiliar ("invisible"), y lo añadimos a los
                # lista de elementos filtrados (como si se tratase de un nodo más a dibujar en 
                # la vista local - en el borde de esta)
                aux_id = f"aux_{src}_{tgt}"
                elementos_filtrados.append({
                    'data': {'id': aux_id, 'label': ''},
                    'position': {'x': aux_x, 'y': aux_y},
                    'classes': 'nodo-corte'
                })
                
                # Conectamos el nodo visible con el nodo auxiliar con un trazo discontinuo
                elementos_filtrados.append({
                    'data': {
                        'source': src if src in ids_visibles else aux_id,
                        'target': aux_id if src in ids_visibles else tgt
                    },
                    'classes': 'arista-corte'
                })
    
    # 3) Indicadores visuales para los nodos "ocultos" (mediante flechas)
    #    -> Los indicadores visuales se añadirán también a los elementos filtrados

    # (Función auxiliar para colorear un indicador visual de forma 
    # apropiada en caso de que en esa dirección haya oculto un nodo
    # que sea super/sub-concepto inmediato al concepto central, con el 
    # formato ya definido en el layout de dash-cytoscape para los diferentes 
    # tipos de indicador - tal y como se puede encontrar en el layout de la 
    # pantalla principal definido en el archivo 'layouts.py')
    def obtener_clase_indicador(roles_detectados):
        if 'super' in roles_detectados: return 'indicador indicador-super'
        if 'sub' in roles_detectados: return 'indicador indicador-sub'
        return 'indicador indicador-nada'

    # a) Indicadores Laterales (se dibujan a la dcha/izda, en línea con cada 
    #    uno de los niveles representados en la vista local, con algo de margen
    #    adicional, "DELTA" respecto al recinto local visualizado, para evitar 
    #    el solapamiento con los nodos y aristas de dicha vista local, y acompañados 
    #    del número de conceptos "ocultos" que quedan en dicha dirección para 
    #    cada nivel)
    for nivel, data in ocultos_izq.items(): # Nodos ocultos a izda.
        elementos_filtrados.append({
            'data': {'id': f'ind_izq_{nivel}', 'label': f'◀ ... ({data["count"]})'},
            'position': {'x': x_min - DELTA, 'y': -nivel * ESPACIADO_Y}, 
            'classes': obtener_clase_indicador(data['roles'])
        })
    for nivel, data in ocultos_der.items(): # Nodos ocultos a dcha.
        elementos_filtrados.append({
            'data': {'id': f'ind_der_{nivel}', 'label': f'({data["count"]}) ... ▶'},
            'position': {'x': x_max + DELTA, 'y': -nivel * ESPACIADO_Y}, 
            'classes': obtener_clase_indicador(data['roles'])
        })
        
    # b) Indicadores Verticales (de forma similar a los horizontales, estos se dibujan 
    #    en la parte superior o inferior derecha, con un cierto margen dado por "DELTA", 
    #    con respecto al recinto local visualizado, y van acompañados por el número de nodos 
    #    que quedan fuera de la vista local en dicha dirección)
    # NOTA: A diferencia de los indicadores horizontales, aquí no hace falta tener en cuenta el
    #       nivel (simplemente saber si hay o no nodos ocultos hacia arriba o hacia abajo - i.e.
    #       en niveles por encima o por debajo de los mostrados en la vista local)
    if count_arriba > 0: # Hay nodos ocultos arriba.
        elementos_filtrados.append({
            'data': {'id': 'ind_arriba', 'label': f'(+{count_arriba})\n▲\n⋮'},
            'position': {'x': x_max + DELTA, 'y': y_min},
            'classes': obtener_clase_indicador(roles_arriba)
        })
    if count_abajo > 0: # Hay nodos ocultos abajo.
        elementos_filtrados.append({
            'data': {'id': 'ind_abajo', 'label': f'⋮\n▼\n(+{count_abajo})'},
            'position': {'x': x_max + DELTA, 'y': y_max},
            'classes': obtener_clase_indicador(roles_abajo)
        })
            
    return elementos_filtrados

# ---------------------------------------------------------------------------------------
# ii) Actualizar el centro de la vista, por cualquiera de los posibles
#     eventos que pueden llevar a modificar este. A saber:
# 
#    - Navegación por click (actualizar el centro de la vista como el 
#      nodo seleccionado) 
#       
#    - Gestión de la Localización por derivación del panel lateral (por el 
#      cual se obtiene el concepto formal asociado a un subconjunto y 
#      se actualiza el centro de vista nuevamente en dicho nodo)
#      
#    - Actualizar el centro de vista cuando se pulsa uno de los botones 
#      "dinámicos" (en el sentido de que no son un número fijo, sino que 
#      aparecen en función de la búsqueda concreta que se lleve a cabo, y 
#      cada uno lleva el ID de un nodo en particular en el retículo) en el 
#      panel "Buscador"

@app.callback(
    Output("derivador-resultados", "children"),
    Output("centro-store", "data"),
    Input("reticulo-cytoscape", "tapNodeData"),
    Input("btn-ejecutar-derivador", "n_clicks"),
    Input({'type': 'btn-centrar-dinamico', 'index': ALL}, 'n_clicks'),
    # Las variables State son variables de estado/lectura (no disparan la función si cambian)
    State("derivador-tipo", "value"),
    State("derivador-seleccion", "value"),
    State("centro-store", "data"),
    prevent_initial_call=True # Evita que se dispare cuando sus Inputs toman su primer valor
)
def actualizar_centro_vista(tap_data, n_clicks_btn, n_clicks_dinamicos, tipo_entrada, elementos_seleccionados, centro_actual):
    
    # Identificamos qué componente ha disparado el callback (capturando su ID)
    disparador_id = dash.ctx.triggered_id

    # 1) Navegación por clic (Tap en un nodo de Cytoscape)
    if disparador_id == 'reticulo-cytoscape': 
        if tap_data is None: return no_update, no_update
        # Actualizamos el centro ("centro-store"), pero no el texto del panel ("derivador-resultados")
        return no_update, tap_data['id']

    # 2) Consulta desde el Panel "Derivador" (Obtener el Concepto Formal asociado)
    if disparador_id == 'btn-ejecutar-derivador': 
        if not elementos_seleccionados: # Si no se han seleccionado aún elementos para el subconjunto de la consulta
            # Actualizamos solo el texto del panel con un mensaje de error
            return "[X] Por favor, seleccione al menos un elemento.", no_update
        
        # Si se ha seleccionado algún subconjunto de elementos, realizamos 
        # el cálculo con "concepts" según el tipo de datos (si son objetos 
        # o atributos)
        try:
            res_text = "" # Esta variable guarda el texto para el panel de resultados

            # a) El subconjunto X es de objetos -> Concepto formal: (X'',X')
            if tipo_entrada == 'obj':
                # Precalculamos ya tanto la derivación simple como la doble derivación
                objetos_cierre, atributos_comunes = calcular_concepto_formal_asociado(tipo_entrada, elementos_seleccionados, ctx)
                # Buscamos el ID del concepto formal resultante (para centrar la vista en él)
                target_id = centro_actual
                for c, cid in concepto_a_id.items():
                    if set(c.extent) == set(objetos_cierre) and set(c.intent) == set(atributos_comunes):
                        target_id = cid
                        break
                # Formateamos el texto de salida (mostrando tanto la Intensión como Extensión)
                res_text += f"Ext: {', '.join(objetos_cierre)}\nInt: {', '.join(atributos_comunes)}\n"
                # Actualizamos tanto el panel de resultados como también el centro de vista (al concepto resultante)
                return res_text, target_id 
            
            # b) El subconjunto Y es de atributos -> Concepto formal: (Y',Y'')
            #    (Es totalmente análogo al caso a), solo que cambiando de orden los resultados de las 
            #    derivaciones al formar el concepto formal asociado)
            else: # Tipo 'attr'
                objetos_comunes, atributos_cierre = calcular_concepto_formal_asociado(tipo_entrada, elementos_seleccionados, ctx)
                target_id = centro_actual
                for c, cid in concepto_a_id.items():
                    if set(c.extent) == set(objetos_comunes) and set(c.intent) == set(atributos_cierre):
                        target_id = cid
                        break
                res_text += f"Ext: {', '.join(objetos_comunes)}\nInt: {', '.join(atributos_cierre)}\n"
                return res_text, target_id

        # Capturamos también las eventuales excepciones (actualizando únicamente 
        # el panel de resultados)
        except Exception as e:
            return f"[X] Error: {str(e)}", no_update
        
    # 3) Clic en un botón "dinámico" del Panel "Buscador"
    #
    # Nótese que de los tres eventos escuchados por este callback (los tres parámetros "Input"),
    # los dos primeros tienen un ID normal (son simples cadenas de texto), mientras 
    # que el tercero tiene un ID dinámico (es un diccionario), por lo que para capturar este 
    # último caso, es necesario hacer una comprobación explícita sobre si es una instancia de 
    # la clase "dict" (un Diccionario nativo de Python), en cuyo caso, se pasa a comprobar si
    # el valor asociado a su clave 'type' es el relativo a un botón dinámico del panel "Buscador"
    if isinstance(disparador_id, dict) and disparador_id.get('type') == 'btn-centrar-dinamico':

        # NOTA: Para evitar problemas con "clics fantasma" (i.e. aparentemente se centra la vista
        # en uno de los conceptos listados tras la búsqueda, sin ni siquiera haber clicado sobre ninguno)
        # es necesario ignorar explícitamente el evento de "nacimiento" de estos botones, para lo
        # cual basta con leer el número de clics, y si dicho valor es 'None' significa que acaba de
        # renderizarse en pantalla, pudiendo entonces ignorarse.
        
        # "dash.ctx.triggered" es la lista con los eventos recientes
        # y su propiedad 'value' contiene el número de clics.
        evento_valor = dash.ctx.triggered[0]['value'] 
        
        if evento_valor is None:
            return no_update, no_update # Ignoramos el evento de "nacimiento"

        # En otro caso, actualizamos el centro de la vista en consecuencia, a partir del 
        # índice del botón dinámico concreto que fue pulsado en el panel "Buscador"
        nuevo_centro_id = disparador_id['index']
        return no_update, nuevo_centro_id
    
    # Si no se dan ninguno de los tres casos anteriores, no se actualiza nada (i.e. esto actúa como un catch-all)
    # Es necesario, porque en otro caso, si no se devuelve "no_update", los elementos tipo "Output"
    # (i.e. el ID del nodo centro de la vista, así como el panel de resultados) se borran directamente 
    # (al recibir "None" en lugar de "no_update")
    return no_update, no_update

# ---------------------------------------------------------------------------------------
# iii) Ejecución de las Búsquedas del panel lateral izquierdo:
#      
#      Esencialmente, una vez seleccionado el subconjunto de elementos 
#      (objetos o atributos) se itera por la lista de conceptos formales del
#      retículo, identificando aquellos que contengan dicho subconjunto en 
#      su extensión o intensión, respectivamente, y finalmente se crean los
#      elementos visuales relativos a cada concepto resultante (se muestra tanto
#      el número de elementos en su extensión e intensión, como el listado de
#      estos elementos, y se inserta un botón para permitir centrar la vista
#      en dicho concepto formal)
#
#      Así mismo, cuando el subconjunto seleccionado corresponda con la extensión
#      (si constaba de objetos) o la intensión (si eran atributos) de un concepto
#      formal existente, se destacarán visualmente los resultados relativos a 
#      estos conceptos formales, para mayor claridad del usuario, usando la misma
#      convención de colores empleada en las vistas locales del diagrama del retículo.
#
#      Por otro lado, se dispone de dos límites, uno de tiempo (especialmente 
#      necesario en retículos cercanos al límite de tamaño impuesto por medio 
#      del contexto) y otro de número máximo de resultados a mostrar (para no 
#      sobrecargar el cuadro de resultados del panel), y se controla que se 
#      respeten ambos, indicando con el mensaje de aviso pertinente si no es 
#      el caso.
#     
# NOTA: Nótese que los botones generados en la lista de resultados son "dinámicos"
# en el sentido de que puede aparecer un número indeterminado de ellos, y cada uno
# apuntará a un concepto formal en principio arbitrario dentro del retículo, de modo
# que en lugar de asignarle un ID de texto simple a cada botón, se le asigna
# un ID en forma de diccionario {'type': 'btn-centrar-dinamico', 'index': ID_DEL_NODO},
# para almacenar exactamente el ID del nodo relativo al retículo de conceptos

@app.callback(
    Output("buscador-resultados", "children"),
    Input("btn-ejecutar-buscador", "n_clicks"),
    State("buscador-tipo", "value"),
    State("buscador-seleccion", "value"),
    State("buscador-orden", "value"),
    prevent_initial_call=True
)
def ejecutar_busqueda(n_clicks, tipo, seleccion, orden):
    if not seleccion: # Si no se ha seleccionado aún ningún elemento en el dropdown
        return html.P("Selecciona al menos un elemento.")
    
    # 1) Se ejecuta la búsqueda, llamando a la función auxiliar
    resultados, timeout_alcanzado, base_cid, vecinos_super, vecinos_sub = buscar_por_subconjunto(tipo, seleccion, lista_conceptos, concepto_a_id, nodos_master)
                
    # Si se termina de iterar por los conceptos del retículo sin obtener
    # resultado alguno, pero tampoco se llegó a alcanzar el timeout, se 
    # indica al usuario que no se encontraron conceptos compatibles 
    if not resultados and not timeout_alcanzado: 
        return html.P("No hay conceptos que cumplan el criterio.")
    
    # (En otro caso - i.e. Si se ha obtenido algún resultado)
    #
    # 2) Se ordenan los resultados según el criterio que haya especificado el 
    # usuario
    if orden == 'ext_asc': # Número de objetos (cardinal) en la Extensión ascendente
        resultados.sort(key=lambda c: len(c.extent))
    elif orden == 'ext_desc': # Número de objetos (cardinal) en la Extensión descendente 
        resultados.sort(key=lambda c: len(c.extent), reverse=True)
    elif orden == 'int_asc': # Número de atributos (cardinal) en la Intensión ascendente
        resultados.sort(key=lambda c: len(c.intent))
    elif orden == 'int_desc': # Número de atributos (cardinal) en la Intensión descendente
        resultados.sort(key=lambda c: len(c.intent), reverse=True)
        
    # Lista de elementos visuales que poblarán el cuadro de texto del panel
    # de Búsqueda (donde se mostrarán los resultados)
    lista_ui = []

    # 3) Mensajes de aviso (si saltaron los sistemas de seguridad - o bien el timeout, o el 
    # límite de resultados a mostrar - en cualquier caso indicar el número de resultados 
    # obtenidos e indicar que solo se muestran los primeros hasta "MAX_RESULTADOS_BUSQUEDA"
    #
    # Caso 1: Se alcanzó el límite de tiempo de espera (timeout)
    if timeout_alcanzado:
        lista_ui.append(html.Div([
            html.P(f"[!] Búsqueda abortada a los {MAX_TIMEOUT}s para evitar colapso. Se han recuperado {len(resultados)} conceptos. Mostrando solo los primeros {MAX_RESULTADOS_BUSQUEDA} para no saturar el panel.", 
                   style={'color': '#D32F2F', 'fontWeight': 'bold', 'fontSize': '12px'}),
            html.Hr()
        ]))
    # Caso 2: No se alcanzó el Timeout, pero sí se superó el número máximo de resultados a mostrar
    elif len(resultados) > MAX_RESULTADOS_BUSQUEDA:
        lista_ui.append(html.Div([
            html.P(f"Éxito. Se han encontrado {len(resultados)} conceptos. Mostrando solo los primeros {MAX_RESULTADOS_BUSQUEDA} para no saturar el panel.", 
                   style={'color': '#E65100', 'fontWeight': 'bold', 'fontSize': '12px'}),
            html.Hr()
        ]))

    # 4) En cualquier caso, se genera la lista de elementos visuales para los 
    # primeros resultados obtenidos (hasta el tope "MAX_RESULTADOS_BUSQUEDA")
    for c in resultados[:MAX_RESULTADOS_BUSQUEDA]:
        cid = concepto_a_id[c] # El ID del concepto, se puede obtener del diccionario "concepto_a_id"
        
        # Estilo base para cada resultado individual
        estilo_resultado = {
            'padding': '12px', 
            'borderRadius': '6px', 
            'marginBottom': '10px', 
            'border': '1px solid #ddd',
            'backgroundColor': 'white',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.05)'
        }
        etiqueta_rol = ""
        
        # Para los casos especiales (resultados relativos al concepto formal asociado
        # al subconjunto de elementos seleccionado, o sus vecinos superiores o inferiores)
        # se sobreescribe el estilo, para destacarlos visualmente. En particular, se aplican 
        # colores coincidentes con los roles del lienzo de Cytoscape (de las vistas locales).
        if cid == base_cid: # Verde (Nodo Focal)
            estilo_resultado['backgroundColor'] = '#E8F5E9' 
            estilo_resultado['borderLeft'] = '5px solid #2E7D32'
            etiqueta_rol = html.Span(" [Concepto Formal asociado]", style={'color': '#2E7D32', 'fontWeight': 'bold', 'fontSize': '11px'})
        elif cid in vecinos_super: # Azul (Superconcepto inmediato)
            estilo_resultado['backgroundColor'] = '#E3F2FD' 
            estilo_resultado['borderLeft'] = '5px solid #1976D2'
            etiqueta_rol = html.Span(" [Superconcepto Inmediato]", style={'color': '#1976D2', 'fontWeight': 'bold', 'fontSize': '11px'})
        elif cid in vecinos_sub: # Magenta (Subconcepto inmediato)
            estilo_resultado['backgroundColor'] = '#FCE4EC' 
            estilo_resultado['borderLeft'] = '5px solid #C2185B'
            etiqueta_rol = html.Span(" [Subconcepto Inmediato]", style={'color': '#C2185B', 'fontWeight': 'bold', 'fontSize': '11px'})
        
        lista_ui.append(html.Div([
            # Etiqueta en caso de que el resultado corresponda al concepto formal asociado a 
            # la selección de objetos/atributos, o bien a un sub/super-concepto directo de este
            html.P([etiqueta_rol], style={'margin': '0', 'fontSize': '12px', 'color': 'gray'}),
            # Elementos de la Extensión (Objetos)
            html.P(f"Ext ({len(c.extent)}): {','.join(c.extent) if c.extent else 'Ø'}", style={'margin': '4px 0', 'fontSize': '12px'}),
            # Elementos de la Intensión (Atributos)
            html.P(f"Int ({len(c.intent)}): {','.join(c.intent) if c.intent else 'Ø'}", style={'margin': '4px 0', 'fontSize': '12px'}),
            # Botón para centrar la vista en dicho Concepto formal (se le inserta el ID del concepto en el campo 'index')
            html.Button("Centrar aquí", id={'type': 'btn-centrar-dinamico', 'index': cid}, style={
                'backgroundColor': '#E64A19', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'padding': '5px 10px', 'marginTop': '5px'
            }),
            html.Hr(style={'margin': '10px 0'}) # Barra horizontal que separa cada resultado del siguiente
        ], style=estilo_resultado))
        
    return lista_ui

# ---------------------------------------------------------------------------------------
#  iv) Actualizar el panel inferior de "Inspección" (que muestra la Extensión
#      e Intensión del Concepto Formal sobre el que está centrada la vista
#      en cada momento) cada vez que cambie el nodo central de la vista

@app.callback(
    Output("panel-inferior-info-conceptos", "children"), # El propio panel inferior
    Input("centro-store", "data") # El identificador del nodo sobre el que está centrada la vista
)
def actualizar_panel_inferior(centro_id):
    # Evidentemente, si aún no hay ningún concepto formal seleccionado, ni se 
    # ha generado aún la lista de conceptos del retículo, no se actualiza nada
    if not centro_id or not lista_conceptos:
        return no_update

    # (En otro caso)
    # Consultamos el concepto formal de la lista de conceptos, a partir del 
    # identificador del nodo central de la vista (almacenado en "centro-store")
    concepto = lista_conceptos[int(centro_id)]

    # 1) Para la extensión, si esta no es vacía, comprobamos si su número de
    #    elementos no excede el umbral máximo impuesto para este panel, y en  
    #    caso contrario simplemente se muestran hasta llegar a este límite, 
    #    y se indica con puntos suspensivos que hay más elementos 
    if concepto.extent:
        if len(concepto.extent) > UMBRAL_MAX_PANEL_INF:
            str_extent = ", ".join(concepto.extent[:UMBRAL_MAX_PANEL_INF]) + " ..."
        else: # No se excede el límite de objetos -> Se muestran todos
            str_extent = ", ".join(concepto.extent)
        # Se muestran tanto los atributos de la extensión, como también su número
        txt_extent = f"({len(concepto.extent)}): {str_extent}"
    else: # Si la extensión es vacía (hay 0 elementos)
        txt_extent = "(0): Ø"

    # 2) En la intensión se procede de forma totalmente análoga a la extensión.
    if concepto.intent: 
        if len(concepto.intent) > UMBRAL_MAX_PANEL_INF:
            str_intent = ", ".join(concepto.intent[:UMBRAL_MAX_PANEL_INF]) + " ..."
        else: 
            str_intent = ", ".join(concepto.intent)
        
        txt_intent = f"({len(concepto.intent)}): {str_intent}" 
    else: 
        txt_intent = "(0): Ø"

    # 3) Finalmente, se devuelve una estructura visual para Dash, en dos columnas 
    # (una que ocupa alrededor de la mitad izquierda del ancho total, dedicada
    # a la intensión, y otra análoga para la extensión)
    return [
        html.Div([
            html.Strong("Ext ", style={"color": "#1b5e20"}), 
            html.Span(txt_extent)
        ], style={"width": "48%", "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"}),

        html.Div([
            html.Strong("Int ", style={"color": "#1b5e20"}), 
            html.Span(txt_intent)
        ], style={"width": "48%", "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"})
    ]

# ---------------------------------------------------------------------------------------
# v) Guardar/exportar sesion (en forma de un archivo de extensión .wille)
#
#    Esencialmente se extraen los cinco elementos necesarios para representar
#    una sesión (y permitir después cargarla de nuevo, sin necesidad de volver
#    a hacer todos los cálculos desde cero a partir del contexto formal):
#
#    - La lista de conceptos formales "planos" - i.e. solo con su
#      extensión e intensión, para evitar almacenar punteros hacia los vecinos
#      superiores/inferiores con el consecuente gasto innecesario de espacio 
#      debido a la eventual recursividad)
#
#    - El contexto formal en forma de matriz booleana (como si estuviera
#      representado en forma de archivo .csv)
#
#    - Las listas "nodos_master" y "aristas_master" (con toda la información 
#      relativa a la representación visual del retículo de conceptos, en forma de
#      diagrama de Hasse, incluyendo las coordenadas absolutas, el identificador, 
#      las etiquetas, tanto reducida como extendida de cada nodo, así como las 
#      aristas del retículo)
#
#    - El identificador del nodo "ínfimo global"
# 
#    En cuanto al "Estado" propiamente de la sesión (el que determina la vista 
#    local que había en el momento de exportar la sesión), este a su vez está
#    determinado por:
#
#    - El identificador del nodo central de la vista 
#
#    - El nivel de zoom considerado. 
#
# Por ende, también estos dos atributos son exportados, como parte de la sesión.

@app.callback(
    Output('descargar-sesion', 'data'),
    Input('btn-guardar-sesion', 'n_clicks'),
    State('centro-store', 'data'), # Se captura el centro actual
    State('zoom-slider', 'value'), # Se captura el nivel de zoom actual
    prevent_initial_call=True
)
def guardar_sesion(n_clicks, centro_actual, zoom_actual):
    # Indicar a Python que se va a acceder a las variables globales
    global ctx, lista_conceptos, nodos_master, aristas_master
    
    # 1) Se aplana la lista de conceptos (instancias de la clase "Concepts.concept") 
    #    pasando a almacenar tan solo la lista de tuplas formadas por la extensión
    #    e intensión de cada concepto (como listas a su vez de objetos y atributos,
    #    respectivamente), para eliminar todo rastro de recursividad (que hace 
    #    innecesariamente pesados los archivos generados)
    conceptos_planos = [{'e': c.extent, 'i': c.intent} for c in lista_conceptos]
    
    # 2) Se construye/extrae la matriz booleana del contexto formal 
    #     (en formato CSV) como texto plano, simplemente iterando por 
    #     los objetos del contexto, calculando su derivación (por medio
    #     del método "intent"), que por definición serán los atributos 
    #     que posea dicho objeto, y simplemente para la línea relativa
    #     a dicho objeto, escribir el símbolo "X" si el atributo 
    #     correspondiente a la columna es poseído por el objeto, y dejar
    #     sin rellenar en otro caso
    lineas_csv = ["," + ",".join(ctx.properties)]
    for obj in ctx.objects:
        intent_o = ctx.intension([obj])
        fila = [obj] + ["X" if a in intent_o else "" for a in ctx.properties]
        lineas_csv.append(",".join(fila))
    ctx_csv = "\n".join(lineas_csv)

    # 3) Identificar el nodo ínfimo global del retículo
    id_infimo = '0' # Por si "nodos_master" estuviera vacío (i.e. el 
    # retículo consta de un único elemento)
    for nodo in nodos_master:
        if not nodo['data']['sub_inmediatos']:
            id_infimo = nodo['data']['id']
            break
            
    # 4) Llegados a este punto, se almacenan los cinco elementos que 
    # encapsulan la sesión en forma de un único diccionario
    datos_a_guardar = {
        'ctx_csv': ctx_csv,
        'conceptos_planos': conceptos_planos,
        'nodos_master': nodos_master,
        'aristas_master': aristas_master,
        'id_infimo': id_infimo,
        'ultimo_nodo_central': centro_actual,
        'ultimo_nivel_zoom': zoom_actual
    }
    
    # 5) Se serializa el diccionario con todos los datos, convirtiéndolos
    # en una secuencia de bytes, por medio de la función "dumps" de pickle
    datos_bytes = pickle.dumps(datos_a_guardar)
    
    # 6) Se comprimen los datos con la función "commpress" de gzip, para 
    # que el archivo resultante pese menos
    datos_comprimidos = gzip.compress(datos_bytes)
    
    # 7) Finalmente, devolvemos el archivo comprimido, al componente "download"
    # asociado al botón de "Guardar sesión", por mediación del componente "send_bytes", 
    # enviando los datos tras la compresión, y por defecto, asignándole al archivo
    # resultante el nombre "sesion_navegacion.wille" (nombre que por supuesto 
    # podrá personalizarse sin ninguna dificultad cuando se vaya a guardar localmente
    # en el equipo)
    return dcc.send_bytes(datos_comprimidos, "sesion_navegacion.wille")

# ---------------------------------------------------------------------------------------
# vi) Gestiones menores de los paneles laterales:
#      
#   - Abrir y cerrar los paneles (por medio del botón dedicado a esto,
#      que simplemente actuará como un conmutador)
#   - Actualizar/poblar las opciones del Dropdown de selección del panel, 
#      según si se ha elegido considerar Objetos o Atributos, simplemente 
#      recorriendo el Contexto Formal y listando estos elementos, 
#      respectivamente.

# ------------------
# Panel "Derivador":
#
# 1) Abrir y cerrar el panel pulsando el botón correspondiente
@app.callback(
    Output("panel-lateral-derivador", "style"), # El propio panel lateral
    Input("btn-abrir-cerrar-derivador", "n_clicks"), # El botón 
    State("panel-lateral-derivador", "style"),
    prevent_initial_call=True
)
def desplegar_panel_derivador(n_clicks, style):
    if style.get("right") == "0px": # El panel está pegado al borde derecho (visible)
        style["right"] = "-350px"   # -> Ocultar
    else:                           # En otro caso, el panel estaba oculto 
        style["right"] = "0px"      # -> Mostrar
    return style

# 2) Actualizar las opciones del dropdown para seleccionar elementos
@app.callback(
    Output("derivador-seleccion", "options"), # Opciones mostradas
    Output("derivador-seleccion", "value"),   # Selección de opciones que hubiera marcadas
    Input("derivador-tipo", "value")          # El tipo seleccionado (objetos o atributos)
)
def actualizar_dropdown_derivador(tipo_entrada):
    # Si se eligen objetos, simplemente se añade una opción por cada objeto 
    # en el contexto
    if tipo_entrada == 'obj':
        opciones = [{'label': obj, 'value': obj} for obj in ctx.objects]
    else: # Análogo con atributos
        opciones = [{'label': attr, 'value': attr} for attr in ctx.properties]
    # Devolvemos las opciones y vaciamos la selección actual que hubiera 
    # (para evitar errores lógicos, por si antes se tenían seleccionadas 
    # algunas opciones de atributos, y se cambia de idea y se consideran 
    # objetos)
    return opciones, [] 

# ----------------------------------------------------
# Panel "Buscador" (muy similar al panel "Derivador"):
#
# 1) Abrir y cerrar el panel (totalmente análogo al panel "Derivador",
#    salvo porque este está situado a la izquierda - basta cambiar 
#    "right" por "left")
@app.callback(
    Output("panel-lateral-buscador", "style"),
    Input("btn-abrir-cerrar-buscador", "n_clicks"),
    State("panel-lateral-buscador", "style"),
    prevent_initial_call=True
)
def desplegar_panel_buscador(n_clicks, style):
    if style.get("left") == "0px": 
        style["left"] = "-350px"
    else: 
        style["left"] = "0px"
    return style

# 2) Actualizar las opciones del dropdown para seleccionar elementos (igual que 
#    en el panel "Derivador")
@app.callback(
    Output("buscador-seleccion", "options"),
    Output("buscador-seleccion", "value"),
    Input("buscador-tipo", "value")
)
def actualizar_dropdown_elementos_buscador(tipo_entrada):
    if tipo_entrada == 'obj':
        opciones = [{'label': obj, 'value': obj} for obj in ctx.objects]
    else:
        opciones = [{'label': attr, 'value': attr} for attr in ctx.properties]
    return opciones, [] 

# 3) Actualizar las opciones del dropdown de selección del criterio de orden
#    (que serán diferentes, en función de si se eligieron objetos o atributos)
@app.callback(
    Output("buscador-orden", "options"),
    Output("buscador-orden", "value"),
    Input("buscador-tipo", "value")
)
def actualizar_dropdown_orden_buscador(tipo_entrada):
    if tipo_entrada == 'obj':
        opciones = [{'label': 'Cardinal de la Extensión Ascendente', 'value': 'ext_asc'},
                    {'label': 'Cardinal de la Extensión Descendente', 'value': 'ext_desc'}]
        value='ext_asc'
    else:
        opciones = [{'label': 'Cardinal de la Intensión Ascendente', 'value': 'int_asc'},
                    {'label': 'Cardinal de la Intensión Descendente', 'value': 'int_desc'}]
        value='int_asc'
    return opciones, value
# ---------------------------------------------------------------------------------------
# 3.4. Arrancar el servidor y ejecutar la aplicación

# Este comando indica que solo permite arrancar el servidor ejecutando este 
# archivo (y no importándolo desde otro como si fuera un módulo)
if __name__ == '__main__':
    # Y esta es la instrucción que arranca el servidor local de Flask/Dash
    # e inicia la aplicación
    app.run(debug=True) 