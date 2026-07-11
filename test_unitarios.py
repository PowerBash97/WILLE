import pytest
import time
from concepts import Context

from utils import (
    calcular_coordenadas_absolutas_diagrama,
    identificar_extremos_del_reticulo,
    filtrar_objetos_y_atributos_propios,
    calcular_concepto_formal_asociado,
    buscar_por_subconjunto
)

# ==============================================================================
# CLASES AUXILIARES Y FIXTURES (PREPARACIÓN DEL ENTORNO)
# ==============================================================================

# Clase para Objetos simulados (o Mock) de la clase "concepts.lattices.Concept"
class ConceptoMock:
    """Clase falsa para simular los conceptos de la librería 'concepts' en las 
       pruebas unitarias del cálculo de la representación visual del retículo,
       así como de la gestión de los filtrados (i.e. simula a la clase 
       "concepts.lattices.Concept")"""
    def __init__(self, extent, intent, id_falso="0"):
        self.extent = extent
        self.intent = intent
        self.lower_neighbors = []
        self.upper_neighbors = []
        self.id_falso = id_falso # Indicamos explícitamente que se trata de un id_falso,
        # para evitar confusión con aquellos propios de un objeto de la clase nativa de "concepts"

@pytest.fixture
def contexto_ejemplo():
    """Crea un contexto formal de ejemplo para comprobar la ejecución de la derivación de
       un subconjunto de elementos (objetos o atributos)."""
    return Context.fromstring('''
       |A|B|C|
      1|X| |X|
      2| |X|X|
      3|X|X|X|
    ''')

# ==============================================================================
# BATERÍA DE PRUEBAS UNITARIAS (X.2)
# ==============================================================================

# 1. Prueba del Cálculo de las Coordenadas Absolutas de los nodos del diagrama de Hasse
def test_calcular_coordenadas_absolutas(monkeypatch):
    """Verifica que los nodos se agrupan en el eje Y por el tamaño de su extensión y se 
       disponen horizontalmente centrados respecto a la recta X=0."""

    # Simulamos 3 conceptos: Uno en el nivel 1 (1 objeto) y dos en el nivel 2 (2 objetos)
    c1 = ConceptoMock(['obj1'], ['A', 'B'], id_falso="1")
    c2 = ConceptoMock(['obj1', 'obj2'], ['A'], id_falso="2")
    c3 = ConceptoMock(['obj1', 'obj3'], ['B'], id_falso="3")
    
    lista = [c1, c2, c3]

    diccionario_ids = {c1: "1", c2: "2", c3: "3"}
    
    # Mockeamos las variables globales, así como el diccionario "concepto_a_id" y la 
    # función auxiliar "normalizar_para_ordenar" que usa la función objeto de pruebas, dentro 
    # del código de la aplicación
    monkeypatch.setattr("utils.ESPACIADO_X", 100)
    monkeypatch.setattr("utils.ESPACIADO_Y", 50)
    monkeypatch.setattr("utils.normalizar_para_ordenar", lambda x: tuple(x))

    coordenadas = calcular_coordenadas_absolutas_diagrama(lista, diccionario_ids)

    # Verificaciones Eje Y (Niveles): c1 está en nivel 1 (-50), c2 y c3 en nivel 2 (-100)
    assert coordenadas["1"]['y'] == -50
    assert coordenadas["2"]['y'] == -100
    assert coordenadas["3"]['y'] == -100

    # Verificaciones Eje X (Centrado): Nivel 2 tiene 2 nodos, deben estar simétricos respecto al 0
    # Offset = -((2-1)*100)/2 = -50. Por tanto, x1 = -50, x2 = 50.
    assert coordenadas["2"]['x'] == -50
    assert coordenadas["3"]['x'] == 50

# 2. Prueba de Identificación de los conceptos formales supremo e ínfimo global del retículo
def test_identificar_extremos_del_reticulo():
    """Comprueba que se localizan correctamente el Supremo global (sin superconceptos) y el 
       Ínfimo global (sin subconceptos)."""
    infimo = ConceptoMock([], ['A', 'B', 'C'])
    medio = ConceptoMock(['1'], ['A', 'B'])
    supremo = ConceptoMock(['1', '2', '3'], [])
    
    # Configuramos la jerarquía de conceptos
    infimo.upper_neighbors = [medio]
    medio.lower_neighbors = [infimo]
    medio.upper_neighbors = [supremo]
    supremo.lower_neighbors = [medio]
    
    lista = [infimo, medio, supremo]
    
    id_inf, id_sup = identificar_extremos_del_reticulo(lista)
    
    # El ínfimo es el índice 0, el supremo es el índice 2
    assert id_inf == "0"
    assert id_sup == "2"

# 3. Prueba del Cálculo de las Etiquetas reducidas (Objetos y Atributos propios)
def test_filtrar_objetos_y_atributos_propios():
    """Valida la correcta obtención de los objetos y atributos propios de un
       concepto formal"""
    concepto = ConceptoMock(['obj1', 'obj2'], ['atr1', 'atr2'])
    padre = ConceptoMock(['obj1', 'obj2', 'obj3'], ['atr1'])
    hijo = ConceptoMock(['obj1'], ['atr1', 'atr2', 'atr3'])
    
    concepto.upper_neighbors = [padre]
    concepto.lower_neighbors = [hijo]
    
    obj_propios, atr_propios = filtrar_objetos_y_atributos_propios(concepto)
    
    # Objetos propios: ['obj1', 'obj2'] - ['obj1'] = {'obj2'}
    # Atributos propios: ['atr1', 'atr2'] - ['atr1'] = {'atr2'}
    assert obj_propios == {'obj2'}
    assert atr_propios == {'atr2'}

# 4. Prueba de la Consulta del Concepto Formal asociado a un Subconjunto de entrada
def test_calcular_concepto_formal_asociado(monkeypatch, contexto_ejemplo):
    """Comprueba que el cálculo de la extensión e intensión del concepto formal
       asociado a un subconjunto, por medio de los operadores de derivación, es
       correcto"""
    
    # Prueba del cálculo del concepto formal asociado al subconjunto de atributos {'A'}: 
    # 1) (Primera derivación - Extensión) Si se selecciona 'A', los objetos que lo poseen son '1' y '3'
    # 2) (Segunda derivación - Intensión) Esos objetos comparten los atributos 'A' y 'C'
    ext, intension = calcular_concepto_formal_asociado('attr', ['A'], contexto_ejemplo)
    
    assert set(ext) == {'1', '3'}
    assert set(intension) == {'A', 'C'}


# 5. Pruebas de Búsqueda por Subconjunto y Control de Timeout en dicha operación
def test_buscar_por_subconjunto_exito(monkeypatch):
    """Verifica que se localizan los conceptos que contienen los elementos buscados
       y que se extrae correctamente la información de vecindad si hay coincidencia 
       exacta con la extensión/intensión de algún concepto formal."""
    # Creamos los conceptos simulados
    c1 = ConceptoMock(['1', '2', '3'], ['A'])
    c2 = ConceptoMock(['1', '2'], ['A', 'B'])
    c3 = ConceptoMock(['3'], ['C'])
    lista_conceptos = [c1, c2, c3]
    concepto_a_id = {c1: "id_c1", c2: "id_c2", c3: "id_c3"}
    
    # Simulamos la estructura de datos que Cytoscape/nodos_master almacenaría para el concepto "c2"
    # Simulamos la estructura de datos que Cytoscape/nodos_master almacenaría para c1 y c2
    nodos_master = [
        {
            'data': {
                'id': 'id_c1',
                'super_inmediatos': [],
                'sub_inmediatos': ['id_c2'] # c2 es subconcepto de c1
            }
        },
        {
            'data': {
                'id': 'id_c2',
                'super_inmediatos': ['id_c1'], # c1 es superconcepto de c2
                'sub_inmediatos': []
            }
        }
    ]
    
    monkeypatch.setattr("utils.MAX_TIMEOUT", 5.0) # Tiempo holgado (para asegurar que no se alcanza)
    
    # Búsqueda por atributo 'A' (Debe encontrar c1 y c2, y SÍ hay coincidencia exacta de intensión 
    # para c1, siendo c2 su subconcepto inmediato)
    resultados, timeout, base_cid, vecinos_super, vecinos_sub = buscar_por_subconjunto(
        'attr', ['A'], lista_conceptos, concepto_a_id, nodos_master
    )
    
    assert timeout is False
    assert len(resultados) == 2
    assert c1 in resultados
    assert c2 in resultados
    assert base_cid == "id_c1"              # Ha encontrado el concepto exacto
    assert vecinos_super == []              # No tiene hijos en este mock
    assert vecinos_sub == ["id_c2"]         # Ha recuperado correctamente a su vecino inferior ("c2") 
          
def test_buscar_por_subconjunto_timeout(monkeypatch):
    """Verifica que el bucle de búsqueda se aborta si se excede el tiempo límite de seguridad."""
    
    # Se crea una lista enorme falsa para provocar demora
    lista_conceptos = [ConceptoMock(['1'], ['A']) for _ in range(1000)]
    
    # Para el caso de timeout, podemos pasar diccionarios/listas vacías ya que el bucle 
    # romperá en la primera etapa y nunca llegará a evaluar los vecinos.
    concepto_a_id = {}
    nodos_master = []
    
    # Se fuerza un timeout imposible (0 segundos)
    monkeypatch.setattr("utils.MAX_TIMEOUT", 0.0)
    
    # Se introduce además un pequeño retardo artificial inyectando un sleep en time.time()
    tiempo_simulado = [0, 1] 
    monkeypatch.setattr(time, "time", lambda: tiempo_simulado.pop(0) if tiempo_simulado else 2)
    
    # Ejecutamos desempaquetando los 5 valores de retorno
    resultados, timeout, base_cid, vecinos_super, vecinos_sub = buscar_por_subconjunto(
        'attr', ['A'], lista_conceptos, concepto_a_id, nodos_master
    )
    
    assert timeout is True                        # Debe abortar casi de inmediato
    assert len(resultados) < len(lista_conceptos) # Rompió el ciclo prematuramente (Solo procesó un concepto: el que consumió el tiempo 0 antes de devolver 1)
    assert base_cid is None                       # No llegó a evaluar coincidencias exactas