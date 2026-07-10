import unicodedata
import time

# ---------------------------------------------------------------------------------------
# 1. Configuración Inicial (Variables, Ctes, Funciones Globales y Clases Auxiliares) 
# ---------------------------------------------------------------------------------------

# ------------------------
# 1.1. Constantes Globales
#
# i) Espaciado del grid (son valores heurísticos fijados en base a ensayo/error)
# Representan la distancia en pixels (en horizontal y vertical, respectivamente)
# del centro de un nodo a otro. 
# NOTA: Se le ha dado más ancho pensando en tener más margen para poder mostrar
#       el texto de la intensión y extensión de un concepto formal seleccionado,
#       sin que se superponga entre nodos.
ESPACIADO_X = 250  
ESPACIADO_Y = 180

# ii) Límite al tamaño máximo permitido a un Contexto Formal 
# (para que el retículo tenga a lo sumo 2^20 = O(10^6) nodos)
# entendido como que el MÍNIMO entre el número de objetos y el 
# número de atributos NO PUEDE EXCEDER DICHO LÍMITE (p.e. se 
# permitirán contextos de 1800 objetos y 20 atributos, pero NO
# un contexto de 20 objetos y 21 atributos, entre otras muchas
# casuísticas)
MAX_ELEMENTOS = 20

# iii) Límite al número de objetos (en la extensión) y atributos
# (en la intensión) del concepto formal seleccionado que se mostrarán
# directamente sobre la vista local del retículo, así como de los 
# objetos/atributos propios que se mostrarán sobre cualquier concepto 
# formal representado en la vista local (aplica por igual en ambos casos)
UMBRAL_MAX = 5

# iv) Valor base al calcular el radio visual en el 
# eje horizontal, para un nivel de zoom logico considerado
VALOR_BASE = 350

# v) Relleno (Padding) para la Vista local:
# Para dar un poco de margen entre los nodos que quedan en los bordes 
# de la vista local "estricta", se considera un cierto nivel de relleno 
# (Padding) tanto en el eje X como en el Y (concretamente la mitad del 
# espaciado entre nodos, en ambos ejes), ampliando ligeramente el recinto 
# local.
#
# NOTA: Esto es necesario para que el posterior algoritmo de cálculo de 
# las aristas entre nodos visibles y nodos ocultos, dentro del callback 
# "vista_local_reticulo" funcione correctamente, y las aristas resultantes 
# queden visualmente acordes con la lógica del algoritmo (de lo contrario 
# pueden darse comportamientos no deseados debido a que algunos nodos 
# "visibles" caen justo en el borde de la vista local)
MARGEN_X = ESPACIADO_X * 0.5
MARGEN_Y = ESPACIADO_Y * 0.5

# vi) Margen en pixels fuera del recinto de la vista local, para colocar 
# los indicadores visuales de que hay más nodos ocultos fuera de este
DELTA = 50 

# vii) Tiempo de espera máximo tolerado al calcular filtrados (conveniente 
# para casos con un retículo de conceptos cercano al límite de tamaño 
# permitido), y número máximo de resultados a mostrar en un filtrado 
# (para no saturar tampoco el panel, con un scroll demasiado largo)
MAX_TIMEOUT = 4.0 # En segundos
MAX_RESULTADOS_FILTRO = 50

# viii) Umbral para el número de objetos y atributos (en la extensión e 
# intensión, respectivamente) a mostrar en el panel inferior de la pantalla
# principal (donde se irán mostrando siempre la Extensión e Intensión del
# concepto formal seleccionado en cada momento). Que será más generoso
# que el impuesto sobre la vista in-situ en el retículo, pues se dispondrá
# de todo el ancho de la ventana para visualizar los elementos.
UMBRAL_MAX_PANEL_INF = 10 
   
# -----------------------
# 1.2. Variables Globales

ctx = None # Contexto Formal 
lista_conceptos = None # Para convertir la estructura interna del retículo obtenido por "concepts" en una lista
concepto_a_id = None # Diccionario para transformar los conceptos formales del retículo en IDs
nodos_master = [] # Lista de nodos del retículo (con sus coordenadas absolutas)
aristas_master = [] # Lista de aristas del retículo
max_zoom = 0 # Nivel máximo de zoom lógico
zoom_inicial = 0 # Nivel de zoom inicial
centro_inicial = '0' # Identificador del nodo central de la vista local inicial

# -------------------------
# 1.3. Funciones Auxiliares

# Función auxiliar que normaliza una cadena de texto relativa a la intensión de un 
# concepto formal, para poder ordenar los conceptos en orden lexicográfico de su 
# intensión:
#
# Para poder ordenar horizontalmente, dentro de un mismo nivel, los diferentes
# conceptos formales, primero se les quitan las tildes y otros símbolos especiales
# a las letras de cada atributo, y se pone todo en minúscula. A continuación, se 
# ordena la lista de atributos de dicha intensión por orden lexicográfico, y ya una
# vez en este formato "limpio", se puede proceder a ordenar los nodos del mismo nivel 
# de forma estricta en orden lexicográfico de su intensión.

def normalizar_para_ordenar(textos):
    textos_normalizados = []
    for t in textos:
        # La secuencia exacta de pasos es la siguiente:
        # 1) normalize('NFKD', t): Descompone los caracteres especiales en sus piezas fundamentales (p.e. una "á" en "a"+"´").
        # 2) encode('ASCII', 'ignore'): Convierte el texto al formato ASCII clásico (para eliminar caracteres especiales como las tildes)
        # 3) decode('utf-8'): Vuelve a convertir los bytes en un string siguiendo el estándar utf-8.
        # 4) lower(): Convierte todo a minúsculas
        limpio = unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('utf-8').lower()
        textos_normalizados.append(limpio)
    textos_normalizados.sort()
    return ",".join(textos_normalizados)

# ------------------------
# 1.4. Clases Accesorias
# 
# (Para la opción de cargar una sesión mediante un archivo .wille)
#
# Clase auxiliar que imita a la clase "concepts.Concept" (pero en una versión
# ligera, que solo almacena la extensión e intensión del concepto, en forma de
# sendos atributos "extent" e "intent" accesibles mediante métodos consultores)
# Su función será reemplazar a los objetos de la clase "concepts.Concept", cuando
# se cargue una sesión por medio de un archivo de extensión ".wille", en la
# lista "lista_conceptos", de la cual a lo largo de la aplicación tan solo se hace
# uso de los métodos consultores "extent" e "intent", iterando sobre sus elementos. 
# Por ende, esta clase, en esencia, almacena tan solo los conceptos formales 
# "planos" (solo con su extension e intensión), sin considerar también los 
# sub/super-conceptos inmediatos asociados a cada uno.

class ConceptoPlano:
    def __init__(self, extent, intent):
        self.extent = tuple(extent)
        self.intent = tuple(intent)
    
    # Estos dos métodos son necesarios para que pueda usarse esta clase como clave 
    # en el diccionario concepto_a_id (igual que si fueran objetos de la clase 
    # "concepts.Concept")
    def __hash__(self): # Genera un identificador único para cada instancia de la clase (para poder acceder cuando se usen como clave de un diccionario)
        return hash((self.extent, self.intent)) 
    def __eq__(self, other): # Dos conceptos son iguales si y solo si coinciden su extensión e intensión
        return self.extent == other.extent and self.intent == other.intent
    
# ------------------------------------------------------------
# 1.5. Funciones que encapsulan algunos algoritmos relevantes

# i) Cálculo de la representación espacial del diagrama de Hasse del retículo de conceptos
#    - Cálculo de las coordenadas espaciales de los nodos 
#    - Identificar los elementos máximo y mínimo del retículo 
#    - Cálculo del etiquetado reducido propio de los diagramas de retículos de conceptos)

# Función auxiliar que realiza el cálculo de las coordenadas de los nodos 
# del diagrama de Hasse del Retículo de Conceptos (tipo "Grid" y sin limitación
# de espacio), y en el que la disposición de los nodos en los dos ejes se realiza
# conforme al siguiente algoritmo:
# -> Eje Y (Ordenando los nodos por el número de objetos en la Extensión, por "niveles")
# -> Eje X (Ordenando los nodos por orden lexicográfico "normalizado" de la Intensión)
#
# El diagrama resultante, debido a la ordenación vertical de sus nodos, aporta peso 
# semántico a la representación (permitiendo identificar la diferencia de objetos entre
# dos nodos conectados por una arista, atendiendo a la distancia vertical que los separa)

def calcular_coordenadas_absolutas_diagrama(lista_conceptos, concepto_a_id):
    
    # i) Construir los diferentes niveles (eje Y) que constituyen el retículo, 
    #    y añadir los conceptos formales a cada nivel que le corresponda.
    niveles = {}
    for c in lista_conceptos:
        nivel = len(c.extent) # El nivel será literalmente el número de objetos de la extensión
        if nivel not in niveles:
            niveles[nivel] = []
        niveles[nivel].append(c)

    # Diccionario (por ID de cada concepto formal), que almacena las coordenadas
    # absolutas de cada nodo del retículo (para que sea legible por dash-cytoscape).
    coordenadas_absolutas = {}

    # Recorremos a continuación los niveles y sus conceptos (ya agrupados cada uno en el 
    # nivel que le corresponda)
    for nivel, conceptos_nivel in niveles.items():
        # Aplicamos la función previamente definida, para ahora sí, ordenar 
        # lexicográficamente los conceptos del mismo nivel por su intensión
        conceptos_nivel.sort(key=lambda c: normalizar_para_ordenar(c.intent))
                
        # Finalmente, se calculan las coordenadas absolutas, usando los espaciados
        # iniciales constantes "ESPACIADO_X\Y" así como atendiendo al número de
        # conceptos/nodos en el nivel considerado (num_nodos).
        # La idea es, dentro de un mismo nivel, centrar la fila de nodos perfectamente
        # alrededor del eje X=0
        num_nodos = len(conceptos_nivel)
        offset_x = - ((num_nodos - 1) * ESPACIADO_X) / 2.0
                
        for i, c in enumerate(conceptos_nivel):
            x = offset_x + i * ESPACIADO_X
            y = - nivel * ESPACIADO_Y # Las coordenadas graficas en una pantalla tienen el eje Y hacia abajo 
                                            # por lo que para subir de nivel, hay que restar
            coordenadas_absolutas[concepto_a_id[c]] = {'x': x, 'y': y}
    return coordenadas_absolutas

# Función auxiliar que identifica a los conceptos ínfimo y supremo globales
def identificar_extremos_del_reticulo(lista_conceptos):

    # Los nodos ínfimo global (nodo 0) y supremo global (nodo 1) son fáciles de
    # reconocer -> simplemente son los que no tienen subconceptos ni superconceptos
    # directos, respectivamente (pero por defecto - si p.e. el retículo colapsara 
    # en un solo concepto formal, les asignamos a ambos el índice 0)
    id_infimo = '0'
    id_supremo = '0'
    for i, c in enumerate(lista_conceptos):
        if not c.lower_neighbors: id_infimo = str(i)
        if not c.upper_neighbors: id_supremo = str(i)
    return id_infimo, id_supremo

# Función auxiliar que filtra los objetos y atributos propios de un concepto formal
def filtrar_objetos_y_atributos_propios(concepto):

    # Atributos/objetos propios (Etiquetado reducido propio de los diagramas de Hasse) 
    # -> Basta hacer la resta de conjuntos entre el de la propia intensión frente a la unión de la de sus 
    #    super-conceptos y de la propia extensión frente a la de sus sub-conceptos, respectivamente
    atributos_propios = set(concepto.intent) - set().union(*(sup.intent for sup in concepto.upper_neighbors))
    objetos_propios = set(concepto.extent) - set().union(*(sub.extent for sub in concepto.lower_neighbors))

    return objetos_propios, atributos_propios

# ii) Algoritmos de localización por derivación y filtrado de conceptos formales
#     - Localizar el concepto formal asociado a un subconjunto de elementos, por derivación
#     - Filtrar aquellos conceptos formales conteniendo un cierto subconjunto de elementos

# Función auxiliar que calcula la extension e intension del concepto 
# formal asociado a partir de un subconjunto de objetos o atributos:
def calcular_concepto_formal_asociado(tipo_elementos, lista_elementos, ctx):
    if tipo_elementos == 'obj': # (X -> Subconjunto de Objetos)
        intension = ctx.intension(lista_elementos)  # X' (Intensión)
        extension = ctx.extension(intension)        # X'' (Extensión)
    else: # 'attr' (Y -> Subconjunto de Atributos)
        extension = ctx.extension(lista_elementos)  # Y' (Extensión)
        intension = ctx.intension(extension)        # Y'' (Intensión)
    return extension, intension

# Función auxiliar que calcula la sublista de conceptos resultantes tras 
# filtrar por un subconjunto de objetos o atributos, y controla que se 
# respete el timeout impuesto en los filtrados:
def filtrar_conceptos_formales_por_subconjunto(tipo_elementos, lista_elementos, lista_conceptos):
    # Para controlar que el tiempo de respuesta ante un filtrado no supere
    # el límite impuesto por "MAX_TIMEOUT", se inicia un contador de tiempo
    # nada más dispararse el callback
    start_time = time.time()
    timeout_alcanzado = False # E inicialmente, el timeout no se ha alcanzado aún
    
    resultados = [] # La lista de resultados inicialmente está vacía
    
    # Se itera sobre la lista de conceptos del retículo, en busca de aquellos
    # que contengan el subconjunto de objetos/atributos solicitado en el panel
    for c in lista_conceptos:
        # Se comprueba el tiempo en cada iteración (cada concepto)
        # Y si se alcanza el timeout, se levanta la bandera "timeout_alcanzado"
        # y se sale del bucle
        if (time.time() - start_time) > MAX_TIMEOUT:
            timeout_alcanzado = True
            break
            
        # Si el subconjunto solicitado era de objetos, se comprueba si todos 
        # sus elementos están en la extensión del concepto formal (con ayuda de
        # la función "all", que comprueba que se cumpla la condición para todos
        # los elementos del subconjunto seleccionado)
        if tipo_elementos == 'obj':
            if all(s in c.extent for s in lista_elementos):
                resultados.append(c)
        # Análogamente se haría para atributos
        else: # 'attr'
            if all(s in c.intent for s in lista_elementos):
                resultados.append(c)
    return resultados, timeout_alcanzado