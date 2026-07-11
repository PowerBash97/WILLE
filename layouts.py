from dash import html, dcc
import dash_cytoscape as cyto
from utils import max_zoom, zoom_inicial, centro_inicial

# ---------------------------------------------------------------------------------------
# 2. Layouts (estructura visual de la interfaz de usuario) de las dos pantallas de las 
#    que se compone la aplicación:
#    - La pantalla de inicio (donde ingresar la entrada, por la vía deseada, e iniciar o 
#      retomar una sesión)
#    - La pantalla principal (donde tendrá lugar una sesión)

# ---------------------------------------------------------------------------------------
# 2.1. Pantalla de Inicio 
#
#      Esencialmente se definen 2 bloques a grandes rasgos relativos a los principales métodos 
#      de entrada: O bien mediante la carga de un contexto formal, o bien reanudando una sesión 
#      previamente exportada como un archivo .wille. Se han dispuesto en la pantalla a modo de 
#      dos columnas bien diferenciadas, y cada una dispone de su propio botón para iniciar la 
#      interacción con el sistema (ambos siendo escuchados por el callback "iniciar_exploracion").
# 
#      Así mismo, en caso de cargar un contexto formal, se dispone a su vez de 3 formas de 
#      proporcionarlo, para lo cual se pueden considerar tres elementos usando el componente 
#      "dcc.Tab", i.e. a modo de pestañas, que permitan posteriormente saber aquella sobre la que 
#      el usuario estaba al momento de presionar el botón que inicia la transición a la pantalla 
#      principal (dando un ID representativo a cada uno, para posteriormente capturar dicha  
#      información y procesar el contexto adecuadamente en el Callback "iniciar_exploracion").

def layout_pantalla_inicio():
    return html.Div([
        html.Div([
            # i) Título de la aplicación
            html.H1("WILLE", style={'fontSize': '48px', 'marginBottom': '10px', 'color': '#1976D2', 'fontFamily': 'sans-serif', 'textAlign': 'center'}),
            html.H3("Web-based Interactive concept Lattice's Line diagram Explorer", style={'color': '#555', 'marginTop': '0', 'fontFamily': 'sans-serif', 'textAlign': 'center'}),
            html.Hr(style={'margin': '30px 0'}), # Línea horizontal separadora
            
            # Contenedor Flexbox para dividir la pantalla en dos columnas
            html.Div([
                # ii) Columna izquierda: "NUEVA SESIÓN" (Cargar un contexto formal)
                #      Dividido a su vez en 3 pestañas, usando el componente "dcc.Tab"
                html.Div([
                    html.H2("Iniciar nueva Sesión", style={'color': '#2e7d32', 'fontFamily': 'sans-serif', 'marginTop': '0'}),
                    html.P("A partir de un Contexto Formal:", style={'color': 'gray', 'fontFamily': 'sans-serif'}),
                    
                    dcc.Tabs(id='tabs-metodo-entrada', value='tab-ejemplo', children=[
                        # Método 1: Ejemplos Precargados (con un elemento "Dropdown" que liste los ejemplos)
                        dcc.Tab(label='1. Ejemplos', value='tab-ejemplo', children=[
                            html.Div([
                                dcc.Dropdown(
                                    id='entrada-ejemplo',
                                    options=[
                                        {'label': 'Contexto A (4x4 "completo")', 'value': 'contexto_ejemplo_A_(4x4_elementos_completo).csv'},
                                        {'label': 'Contexto B (6x6 "completo")', 'value': 'contexto_ejemplo_B_(6x6_elementos_completo).csv'},
                                        {'label': 'Contexto C (7x7 "completo")', 'value': 'contexto_ejemplo_C_(7x7_elementos_completo).csv'},
                                        {'label': 'Contexto D (Algunos animales marinos y terrestres)', 'value': 'contexto_ejemplo_D_(animales_marinos_y_terrestres).csv'},
                                        {'label': 'Contexto E (12x12 "completo")', 'value': 'contexto_ejemplo_E_(12x12_elementos_completo).csv'},
                                        {'label': 'Contexto F (20x20 "completo") - Caso Límite', 'value': 'contexto_ejemplo_F_(20x20_elementos_completo).csv'},
                                    ],
                                    placeholder="Seleccione un contexto..."
                                )
                            ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderTop': 'none'})
                        ]),
                        # Método 2: Subir un Archivo Local (con un elemento "Upload")
                        dcc.Tab(label='2. Archivo .csv', value='tab-upload-csv', children=[
                            html.Div([
                                dcc.Upload(
                                    id='entrada-archivo-csv',
                                    children=html.Div(['Arrastra o ', html.A('Selecciona un archivo .csv')]),
                                    style={
                                        'width': '100%', 'height': '60px', 'lineHeight': '60px',
                                        'borderWidth': '2px', 'borderStyle': 'dashed', 'borderColor': '#2e7d32',
                                        'borderRadius': '5px', 'textAlign': 'center', 'cursor': 'pointer'
                                    }, multiple=False # Solo se permite subir un archivo a la vez (no tiene sentido lo contrario)
                                ),
                                html.Div(id='nombre-archivo-csv', style={
                                    'marginTop': '10px', 'fontSize': '12px', 'color': 'gray',
                                    'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'
                                })
                            ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderTop': 'none'})
                        ]),
                        # Método 3: Cuadro de Texto para Inserción Manual (con un elemento "Textarea")
                        dcc.Tab(label='3. Texto Manual', value='tab-texto', children=[
                            html.Div([
                                dcc.Textarea(
                                    id='entrada-texto',
                                    placeholder="Ejemplo:\n,A1,A2\nO1,X,\nO2,,X",
                                    style={'width': '100%', 'height': '100px', 'fontFamily': 'monospace'}
                                )
                            ], style={'padding': '20px', 'border': '1px solid #ddd', 'borderTop': 'none'})
                        ]),
                    ], style={'marginBottom': '20px', 'fontFamily': 'sans-serif'}),
                    
                    # Botón de ejecución (desencadenando el callback "iniciar_exploracion")
                    html.Button("Generar Retículo", id='btn-nueva-sesion', style={
                        'width': '100%', 'padding': '15px', 'backgroundColor': '#2e7d32', 
                        'color': 'white', 'fontSize': '16px', 'fontWeight': 'bold', 
                        'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer'
                    })
                ], style={'flex': '1', 'minWidth': 0, 'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'border': '1px solid #eee'}),
                
                # iii) Columna derecha: "RESTAURAR SESIÓN" (Cargar una sesión previa)
                html.Div([
                    html.H2("Restaurar Sesión", style={'color': '#1976D2', 'fontFamily': 'sans-serif', 'marginTop': '0'}),
                    html.P("Continuar una Sesión de exploración guardada:", style={'color': 'gray', 'fontFamily': 'sans-serif'}),
                    
                    # Subir un Archivo Local (con un elemento "Upload")
                    html.Div([
                        dcc.Upload(
                            id='entrada-archivo-wille',
                            children=html.Div(['Arrastra o ', html.A('Selecciona un archivo .wille')]),
                            style={
                                'width': '100%', 'height': '120px', 'lineHeight': '120px',
                                'borderWidth': '2px', 'borderStyle': 'dashed', 'borderColor': '#1976D2',
                                'borderRadius': '5px', 'textAlign': 'center', 'cursor': 'pointer'
                            }, multiple=False
                        ),
                        html.Div(id='nombre-archivo-wille', style={
                            'marginBottom': '20px', 'fontSize': '12px', 'color': 'gray',
                            'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'
                        })
                    ]),
                    
                    # Botón de ejecución (desencadenando el callback "iniciar_exploracion")
                    html.Button("Cargar Sesión", id='btn-restaurar-sesion', style={
                        'width': '100%', 'padding': '15px', 'backgroundColor': '#1976D2', 
                        'color': 'white', 'fontSize': '16px', 'fontWeight': 'bold', 
                        'border': 'none', 'borderRadius': '8px', 'cursor': 'pointer'
                    })
                ], style={'flex': '1', 'minWidth': 0, 'padding': '20px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'border': '1px solid #eee'})
                
            ], style={'display': 'flex', 'gap': '30px', 'flexWrap': 'wrap'}), 
            
            # iv) Caja para mostrar errores si el usuario no introduce ningún dato o lo hace en un formato incorrecto
            html.Div(id='inicio-error', style={'color': 'red', 'marginTop': '20px', 'textAlign': 'center', 'fontWeight': 'bold', 'fontFamily': 'sans-serif'})
            
        ], style={'maxWidth': '900px', 'margin': '0 auto', 'backgroundColor': 'white', 'padding': '40px', 'borderRadius': '12px', 'boxShadow': '0 10px 25px rgba(0,0,0,0.1)'})
    ], style={'backgroundColor': '#f0f2f5', 'minHeight': '100vh', 'paddingTop': '50px', 'boxSizing': 'border-box'})

# ---------------------------------------------------------------------------------------
# 2.2. Pantalla Principal 
#
#      Se trata de la pantalla sobre la que tiene lugar la exploración interactiva del 
#      retículo de conceptos generado. Principalmente, se definen los siguientes elementos 
#      visuales:
#
#      - Un "slider" para poder regular el nivel de "Zoom lógico" (entendido como
#        la máxima distancia considerada en cuanto a "niveles" del vecindario de nodos
#        mostrados, y consecuentemente también el máximo número de nodos mostrados 
#        horizontalmente para cada uno de los niveles que aparezcan en la vista local)
#
#      - El lienzo reservado a la vista local e interactiva del retículo, usando 
#        "dash-cytoscape" (y su estilo visual, tanto a nivel del fondo, como de los
#        elementos visualizados, como los propios nodos, las aristas, y los indicios
#        visuales de que hay más nodos que no son visibles con el nivel de "Zoom" actual)
#
#      - Un panel lateral derecho desplegable, dedicado a "Localizar" por derivación a 
#        partir de un subconjunto de atributos u objetos (obteniendo el concepto formal asociado, 
#        volviendo a derivar el resultado de la primera derivación - i.e. empleando el resultado de ACF para 
#        calcular los conceptos formales tomando subconjuntos del conjunto de objetos o atributos)
#
#      - Un panel lateral izquierdo desplegable, dedicado a "Buscar", a partir de un subconjunto
#        de atributos u objetos, aquellos conceptos formales que lo contengan en su intensión o 
#        extensión, respectivamente. Su diseño es muy similar al del panel de "Localizar"
#
#      - Finalmente, un panel informativo, en el borde inferior de la pantalla, que muestra la
#        extensión/intensión del concepto formal seleccionado o localizado (sobre el que está
#        centrada la vista local en todo momento)
 
def layout_pantalla_principal(max_zoom, zoom_inicial, centro_inicial):
    return html.Div([
        # i) Título de la aplicación
        html.H1([
            html.Span("WILLE", style={'color': '#1976D2', 'fontWeight': 'bold'}),
            html.Span("Web-based Interactive concept Lattice's Line diagram Explorer", style={
                'color': 'black', 
                'fontSize': '18px',     
                'fontWeight': 'normal', 
                'marginLeft': '12px'    
            })
        ], style={'fontSize': '32px', 'marginBottom': '0', 'fontFamily': 'sans-serif', 'textAlign': 'center'}),

        # ii) El slider (a su vez, se desglosa como una etiqueta de html, 
        # y el propio slider, o barra deslizante, como componente de de Dash)
        html.Div([
            html.Label("Zoom:", style={'fontWeight': 'bold', 'fontFamily': 'sans-serif'}),
            dcc.Slider(
                id='zoom-slider',
                min=0,
                max=max_zoom,
                step=1,
                value=zoom_inicial, # Por defecto el nivel de zoom inicial es 1 (salvo cuando se ha cargado una sesión, 
                                    # en cuyo caso se parte del nivel de zoom que hubiera en la última vista local)
                marks=None,   
                tooltip=None  
            )
        ], style={'width': '60%', 'margin': 'auto', 'paddingBottom': '0'}),

        # iii) Un botón que permitirá guardar/exportar la sesión a un archivo, y poder 
        # restaurarla en el futuro (sin necesidad de volver a hacer los cálculos relativos
        # al retículo de conceptos, así como al cálculo de las coordenadas, de las 
        # etiquetas, etc.)
        html.Div([
            html.Button("Guardar Sesión", id='btn-guardar-sesion', style={
                'padding': '10px 20px', 'backgroundColor': '#1976D2', 'color': 'white', 
                'border': 'none', 'borderRadius': '5px', 'cursor': 'pointer', 'fontWeight': 'bold',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
            }),
            # Los componentes "Download" de Dash permiten descargar archivos
            # desde la aplicación (como se verá en el callback "guardar_sesion",
            # en conjunción con otro componente de Dash llamado "send_bytes", se 
            # permitirá que el navegador descargue el archivo generado al 
            # guardar/exportar la sesión)
            dcc.Download(id='descargar-sesion')
        ], style={'textAlign': 'center', 'marginBottom': '20px'}),

        # Este es un almacén interno que no dibuja nada en pantalla.
        # En concreto guarda el ID del nodo central (sobre el que está 
        # centrada la vista local en cada momento)
        #
        # Por defecto, cuando se ha optado por introducir el contexto formal como entrada, 
        # se parte con la vista centrada en el nodo ínfimo global (0), mientras que si se 
        # trata de una sesión restaurada, el nodo central será el último que hubo en esta 
        dcc.Store(id='centro-store', data=centro_inicial),
            
        # iv) Este es el puente de Cytoscape.js con dash, en lo que se conoce como "dash-cytoscape"
        #      (concretamente se está instanciando un objeto de la clase dash-cytoscape)
        #      Esencialmente aquí se definen la parte de la pantalla de la página web que será
        #      ocupada por cytoscape, así como los elementos que se visualizarán (nodos, aristas y 
        #      otros indicios visuales), y el estilo que se dará tanto al fondo como a los propios 
        #      elementos (colores, fuente, etc.), sin olvidar el layout (organización espacial de los 
        #      elementos visualizados -> Nodos, aristas, etc.)
        cyto.Cytoscape(
            id='reticulo-cytoscape',
            elements=[],

            # (Para evitar interacciones por defecto)
            # Por medio de sendas banderas especiales, se puede sobreescribir el comportamiento por
            # defecto de Cytoscape, como permitir tomar un nodo y arrastrarlo/cambiar su posición en 
            # el grafo visualizado, así como hacer zoom con la rueda del ratón (esto último se ha bloqueado
            # para que el usuario no confunda el zoom lógico con el físico - propiamente hacer zoom dentro de una 
            # misma vista local, para inspeccionar mejor los nodos que allí aparecen), o mover la 
            # cámara (haciendo "Panning" - i.e. seleccionar el fondo del lienzo y arrastrarlo)
            #
            autoungrabify=True,       # Evita que el usuario pueda hacer clic y modificar la posición de los nodos
            userZoomingEnabled=False, # Bloquea el uso de la rueda del ratón (scroll) para hacer zoom "físico"
            userPanningEnabled=False, # Bloquea también la pantalla, no permitiendo mover la cámara (y perder la vista local)

            # El "layout" de cytoscape esencialmente es el algoritmo de ordenación espacial de los
            # elementos que se vayan a visualizar con él.
            # Al haber optado por una representación espacial en forma de grid, y haber calculado
            # ya explicitamente las coordenadas de cada nodo, se hace uso del layout "preset" (i.e. 
            # sin algoritmo predefinido, simplemente dibujando los elementos a partir de su atributo 
            # "position" -> Las coordenadas absolutas que se calcularon en la sección 3.3.)
            # NOTA: Cytoscape ya hace los cálculos correspondientes al autoencuadre de la región
            # a visualizar en cada momento (las diferentes vistas locales) a partir de las coordenadas
            # absolutas de los nodos (aplicando la transformación lineal oportuna en cada caso) de 
            # forma automática.
            layout={
                'name': 'preset',
                'fit': True,       # Fuerza a la cámara a hacer zoom/pan para encuadrar todos los nodos visibles
                'padding': 50      # Deja un margen de 50 píxeles para que los nodos no se peguen a los bordes
            }, 
                
            # Aquí se define el estilo global (el color del fondo, el ancho, así como la altura, la cual se ha
            # escogido como "80vh", para que así la aplicación sea "responsiva", en el sentido de que 
            # empleará siempre el 80% del alto de la ventana del navegador, sean cuales sean sus dimensiones)
            style={'width': '100%', 'height': '80vh', 'backgroundColor': '#f9f9f9', 'border': '1px solid #ccc'},
            
            # Estilo (tamaño, relleno, etiquetas, colores, fuente, etc.) de cada elemento visualizado 
            stylesheet=[
                # a) Nodos (Los conceptos formales)
                {
                    # (Por defecto) Nodos no-seleccionados, ni tampoco sub/super-conceptos 
                    # directos del seleccionado (en color gris)
                    'selector': '.nodo',
                    'style': {
                        'shape': 'round-rectangle', 
                        'min-width': '30px', 
                        'min-height': '30px',
                        'width': 'label', 
                        'height': 'label',
                        'padding': '10px',
                        'background-color': '#d3d3d3', 'border-color': 'black', 'border-width': 1,
                        'label': 'data(label)', 'text-wrap': 'wrap', 'text-valign': 'center', 
                        'text-halign': 'center', 'color': 'black', 'font-size': '12px', 'font-family': 'monospace'
                    }
                },
                {
                    # Nodo seleccionado (Verde) - sobre el que está centrada la vista
                    'selector': '.nodo[rol = "centro"]',
                    'style': {
                        'background-color': '#a1e3a1', 'border-color': '#2e7d32', 'border-width': 2,
                        'font-weight': 'bold'
                    }
                },
                {
                    # Superconceptos directos (Azul)
                    'selector': '.nodo[rol = "super"]',
                    'style': {
                        'background-color': '#BBDEFB', 'border-color': '#1976D2', 'border-width': 2
                    }
                },
                {
                    # Subconceptos directos (Magenta)
                    'selector': '.nodo[rol = "sub"]',
                    'style': {
                        'background-color': '#F8BBD0', 'border-color': '#C2185B', 'border-width': 2
                    }
                },
                # b) Aristas (arcos entre los nodos -> Líneas de color gris)
                {
                    'selector': '.arista',
                    'style': {
                        'width': 1.5, 'line-color': '#888', 'curve-style': 'bezier'
                    }
                },
                # c) Indicadores/Indicios visuales de que hay más nodos (ocultos) en ciertas direcciones,
                #    que no se pueden visualizar para el nivel de zoom considerado en cada momento
                {
                    # Clase base para la forma del indicador
                    'selector': '.indicador',
                    'style': {
                        'background-opacity': 0, 
                        'border-width': 0,       
                        'font-size': '24px',
                        'font-weight': 'bold',
                        'label': 'data(label)',
                        'text-halign': 'center',
                        'text-valign': 'center',
                        'text-wrap': 'wrap', # Esto permite los saltos de línea (para los indicadores verticales)
                    }
                },
                {
                    # Color si hay un Superconcepto oculto (Azul)
                    'selector': '.indicador-super',
                    'style': {'color': '#1976D2'} 
                },
                {
                    # Color si hay un Subconcepto oculto (Magenta)
                    'selector': '.indicador-sub',
                    'style': {'color': '#C2185B'}
                },
                {
                    # Color (por defecto) si solo hay nodos normales ocultos (Gris)
                    'selector': '.indicador-nada',
                    'style': {'color': '#999999'}
                },
                # d) Estilo visual de las aristas que salen de nodos de dentro de la vista
                #    local hacia nodos (ocultos) que se quedan fuera, y de los nodos auxiliares
                #    que hacen de puente, en el borde de la vista local, haciendo posible esta 
                #    representación.
                {
                    # Nodo auxiliar en el borde (totalmente invisible - 1x1 pixels)
                    'selector': '.nodo-corte',
                    'style': {
                        'width': '1px', 'height': '1px',
                        'background-opacity': 0, 'border-width': 0,
                        'label': ''
                    }
                },
                {
                    # Arista que sale de la vista (línea discontinua, con 'dashed')
                    'selector': '.arista-corte',
                    'style': {
                        'width': 1.5, 'line-color': '#bbb', 'line-style': 'dashed',
                        'curve-style': 'bezier'
                    }
                }
            ]
        ),

        # v) Panel desplegable para localizar mediante derivación (situado en el 
        #    borde derecho de la pantalla) a partir de un subconjunto de atributos/objetos, 
        #    que permite obtener el concepto formal asociado, re-centrándose automáticamente 
        #    además la vista local en dicho nodo)
        html.Div([
            # a) Pestaña que asoma para abrir/cerrar (implementado como un Botón)
            html.Button(
                "Derivador", 
                id="btn-abrir-cerrar-derivador",
                style={
                    "position": "absolute", 
                    "top": "50%", 
                    "left": "-40px",
                    "transform": "translateY(-50%) rotate(180deg)", 
                    "width": "40px", 
                    "height": "120px",
                    "writingMode": "vertical-rl",
                    "backgroundColor": "#512DA8", 
                    "color": "white", 
                    "border": "none",
                    "borderRadius": "0 10px 10px 0", 
                    "cursor": "pointer", 
                    "fontSize": "16px", 
                    "fontWeight": "bold", 
                    "letterSpacing": "2px",
                    "boxShadow": "2px 0 5px rgba(0,0,0,0.2)",
                    "outline": "none"
                }
            ),
            # b) Contenido del panel

            # Su título
            html.H3("Localizar por Derivación", style={"marginTop": "0", "fontFamily": "sans-serif"}),
                
            # La primera pregunta (seleccionar si se van a considerar objetos o atributos)
            html.Label("1. Tipo de elementos", style={"fontWeight": "bold", "fontFamily": "sans-serif"}),
            # El componente "RadioItems" de dash se compone de varios botones redondos de 
            # "selección exclusiva" (i.e. si se marca una opción, se desmarca automáticamente 
            # la que hubiera antes). Aquí, hay dos opciones: Objetos y Atributos
            dcc.RadioItems(
                id="derivador-tipo",
                options=[
                    {'label': ' Objetos', 'value': 'obj'},
                    {'label': ' Atributos', 'value': 'attr'}
                ],
                value='obj', # Selecciona los objetos por defecto
                style={'marginBottom': '15px', 'fontFamily': "sans-serif"}
            ),
                
            # La segunda pregunta (seleccionar el subconjunto concreto, de entre el total de  
            # atributos u objetos del contexto, a partir de un menú desplegable o "dropdown")
            html.Label("2. Seleccionar elementos:", style={"fontWeight": "bold", "fontFamily": "sans-serif"}),
            dcc.Dropdown(
                id="derivador-seleccion", 
                multi=True, 
                placeholder="Seleccione...", 
                style={'marginBottom': '15px'}
            ),
                
            # Finalmente, un botón para ejecutar la localización, una vez se han seleccionado
            # las opciones correspondientes en las anteriores tres preguntas.
            html.Button("Localizar", id="btn-ejecutar-derivador", style={
                "width": "100%", "padding": "10px", "backgroundColor": "#E64A19", 
                "color": "white", "border": "none", "borderRadius": "5px", "cursor": "pointer",
                "fontWeight": "bold", "fontSize": "14px"
            }),
                
            # Barra horizontal que separa el botón anterior de los resultados
            html.Hr(),
                
            # Caja de resultados (donde se mostrarán los resultados de la localización)
            html.Div(id="derivador-resultados", style={
                "marginTop": "15px", "whiteSpace": "pre-wrap", 
                "fontFamily": "monospace", "backgroundColor": "#EDE7F6",
                "padding": "10px", "borderRadius": "5px", "minHeight": "100px"
            })
                
        ], id="panel-lateral-derivador", style={ # Por defecto (al inicio) el panel está oculto ("right": "-350px")
            "position": "fixed", "right": "-350px", "top": "0", "width": "350px", "height": "100vh",
            "backgroundColor": "#F8F9FA", "boxShadow": "-2px 0 10px rgba(0,0,0,0.3)", 
            "zIndex": "1000", "transition": "right 0.3s ease-in-out", 
            "padding": "20px", "boxSizing": "border-box"
        }),

        # vi) Panel desplegable para Búsquedas (situado en el borde izquierdo de la pantalla)
        #    (a partir de un subconjunto de atributos/objetos, permite obtener la lista de
        #    conceptos formales que lo contienen en su intensión/extensión, respectivamente,
        #    y mostrarlos con diferentes criterios de ordenación (en orden ascendente o descendente   
        #    del número de objetos en la extensión, o de atributos en la intensión).
        html.Div([
            # a) Pestaña que asoma para abrir/cerrar (análogo al panel de localizar)
            html.Button(
                "Buscador", 
                id="btn-abrir-cerrar-buscador",
                style={
                    "position": "absolute", 
                    "top": "50%", 
                    "right": "-40px",
                    "transform": "translateY(-50%) rotate(180deg)", 
                    "width": "40px", 
                    "height": "120px", 
                    "writingMode": "vertical-rl",
                    "backgroundColor": "#512DA8", 
                    "color": "white", 
                    "border": "none",
                    "borderRadius": "10px 0 0 10px", 
                    "cursor": "pointer", 
                    "fontSize": "16px", 
                    "fontWeight": "bold", 
                    "letterSpacing": "2px",
                    "boxShadow": "0px 2px 5px rgba(0,0,0,0.2)"
                }
            ),
            # b) Contenido del panel

            # Su título 
            html.H3("Búsqueda de Conceptos", style={"marginTop": "0", "fontFamily": "sans-serif"}),
                
            # La primera pregunta (seleccionar si se van a considerar objetos o atributos)
            # (Análogo al panel de localizar)
            html.Label("1. Tipo de elementos", style={"fontWeight": "bold", "fontFamily": "sans-serif"}),
            dcc.RadioItems(
                id="buscador-tipo",
                options=[
                    {'label': ' Objetos', 'value': 'obj'},
                    {'label': ' Atributos', 'value': 'attr'}
                ],
                value='obj', # Selecciona los objetos por defecto
                style={'marginBottom': '15px', 'fontFamily': "sans-serif"}
            ),

            # La segunda pregunta (seleccionar el subconjunto concreto, de entre el total de  
            # atributos u objetos del contexto, a partir de un menú desplegable o "dropdown")
            # (Análogo al panel de localizar)
            html.Label("2. Seleccionar elementos:", style={"fontWeight": "bold", "fontFamily": "sans-serif"}),
            dcc.Dropdown(
                id="buscador-seleccion", 
                multi=True, 
                placeholder="Seleccione..."
            ),
                
            # La tercera pregunta (seleccionar el criterio de ordenación por el que se desea
            # que se presenten los conceptos formales resultantes)
            html.Label("3. Criterio de ordenación:", 
                       style={'marginTop': '15px', 'fontWeight': 'bold', 'fontFamily': 'sans-serif', 'display': 'block'}),
            dcc.Dropdown(
                id="buscador-orden",
                clearable=False,
                style={'fontFamily': "sans-serif", 'marginBottom': '15px'} 
            ),
                
            # Finalmente, un botón para ejecutar la búsqueda, una vez se han seleccionado
            # las opciones correspondientes en las anteriores tres preguntas.
            html.Button("Buscar", id="btn-ejecutar-buscador", style={
                "width": "100%", "padding": "10px", "backgroundColor": "#E64A19", 
                "color": "white", "border": "none", "borderRadius": "5px", "cursor": "pointer",
                "fontWeight": "bold", "fontSize": "14px"
            }),
                
            # Barra horizontal que separa el botón anterior de los resultados
            html.Hr(),

            # Caja de resultados (donde se mostrarán los resultados de la busqueda)
            html.Div(id="buscador-resultados", style={
                "marginTop": "15px", "whiteSpace": "pre-wrap", 
                "fontFamily": "monospace", "backgroundColor": "#EDE7F6",
                "padding": "10px", "borderRadius": "5px", "minHeight": "100px",
                "maxHeight": "calc(100vh - 400px)", 
                "overflowY": "auto"
            })
                
        ], id="panel-lateral-buscador", style={ # Por defecto (al inicio) el panel está oculto ("left": "-350px")
            "position": "fixed", "left": "-350px", "top": "0", "width": "350px", "height": "100vh",
            "backgroundColor": "#F8F9FA", "boxShadow": "2px 0 10px rgba(0,0,0,0.3)", 
            "zIndex": "1000", "transition": "left 0.3s ease-in-out", "padding": "20px", "boxSizing": "border-box"
        }),

        # vii) Panel inferior de inspección (donde se muestran la Extensión e Intensión del concepto formal
        #    seleccionado o localizado, y sobre el que está centrada la vista local en cada momento)
        html.Div(
            id="panel-inferior-info-conceptos",
            style={
                "position": "fixed", "bottom": "0", "left": "0", "width": "100%", # Ocupa todo el ancho del borde inferior de la pantalla
                "backgroundColor": "#F8F9FA",  # Fondo: Púrpura claro 
                "borderTop": "3px solid #512DA8", # Borde: Púrpura oscuro 
                "padding": "10px 20px", "boxSizing": "border-box",
                "zIndex": "1000", "fontFamily": "monospace", "fontSize": "14px",
                "display": "flex", "justifyContent": "space-between",
                "boxShadow": "0 -4px 10px rgba(0,0,0,0.05)"
            }
        )
    ])