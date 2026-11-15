# compiler.py
# Compilador universal para BrickScript (Version Final y Depurada - Adaptado para Python 3)
# Uso: python3 compiler.py <archivo_entrada.brick>

import sys
import re
import json


def lexer(codigo_fuente):
    codigo_fuente = re.sub(r'//.*', '', codigo_fuente)
    codigo_fuente = re.sub(r'#(?![0-9A-Fa-f]{3,6}\b).*', '', codigo_fuente)
    token_regex = r'\b[A-Z_]+\b|\d+|[\[\](),:{}]|#[0-9A-Fa-f]{3,6}'
    tokens = re.findall(token_regex, codigo_fuente)
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.ast = {"tipo_juego": None, "config": {}, "shapes": {},
                    "boss": {}, "powerups": {}, "events": {}}

    def parse(self):
        while self.posicion < len(self.tokens):
            token_actual = self.tokens[self.posicion]
            if token_actual == 'GAME_TYPE':
                self.parsear_tipo_juego()
            elif token_actual == 'LEVEL':
                self.parsear_nivel()
            elif token_actual == 'GAME_GRID':
                self.parsear_grid()
            elif token_actual == 'BOSS':
                self.parsear_boss()
            elif token_actual == 'DEFINE':
                # Diferenciar entre DEFINE SHAPE, DEFINE POWERUP y DEFINE BOSS
                if (self.posicion + 1 < len(self.tokens) and
                        self.tokens[self.posicion + 1] == 'POWERUP'):
                    self.parsear_powerup()
                elif (self.posicion + 1 < len(self.tokens) and
                        self.tokens[self.posicion + 1] == 'BOSS'):
                    self.parsear_boss()
                else:
                    self.parsear_shape()
            elif token_actual == 'ON':
                self.parsear_evento()
            elif token_actual == 'COLORES' or token_actual == 'COLOR':
                self.parsear_colores()
            else:
                self.posicion += 1
        return self.ast

    def consumir(self, token_esperado=None):
        if self.posicion < len(self.tokens):
            token = self.tokens[self.posicion]
            if token_esperado and token != token_esperado:
                raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se encontro '" + token + "'")
            self.posicion += 1
            return token
        if token_esperado:
            raise Exception("Error de sintaxis: Se esperaba '" + token_esperado + "' pero se llego al final del archivo.")
        return None

    def parsear_tipo_juego(self):

        self.consumir('GAME_TYPE')
        self.ast['tipo_juego'] = self.consumir()

    def parsear_nivel(self):
        self.consumir('LEVEL')
        nivel_token = self.consumir()
        if nivel_token == 'NYAN':
            if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'CAT':
                self.consumir('CAT')
            nivel = 'NYAN_CAT'
        elif nivel_token == 'NYAN_CAT':
            nivel = 'NYAN_CAT'
        else:
            nivel = nivel_token
        self.ast['nivel'] = nivel
        self.ast['config']['nivel'] = nivel

    def parsear_grid(self):
        self.consumir('GAME_GRID')
        self.consumir('(')
        ancho = int(self.consumir())
        self.consumir(',')
        alto = int(self.consumir())
        self.consumir(')')
        self.ast['config']['grid_size'] = [ancho, alto]

    def parsear_colores(self):
        if self.tokens[self.posicion] in ('COLORES', 'COLOR'):
            self.consumir(self.tokens[self.posicion])
        self.consumir('{')
        colores = {}

        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != '}':
            nombre_pieza = self.consumir()  #Teclas  I, J, L, O, S, T, Z
            self.consumir(':')
            color_hex = self.consumir()     # un ejemplo: #00FFFF
            colores[nombre_pieza] = color_hex
            # Si el usuario puso comas entre los colores, se consumen para evitar errores de interpretacion
            if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ',':
                self.consumir(',')
                        
        self.consumir('}') # Cuando toque la barra de cierre deja de leer
                
        # Guardar en la configuración del AST
        self.ast['config']['colores_piezas'] = colores
    def parsear_shape(self):
        self.consumir('DEFINE')
        self.consumir('SHAPE')
        nombre_shape = self.consumir()
        self.consumir(':')
        
        # Valores por defecto para los atributos de la forma
        shape_data = {
            'tipo_forma': 'RECTANGLE',
            'tipo': 'ENEMY',
            'CHANCE': 1,
            'SPEED': 1,
            'HEAL': 1,
            'DAMAGE': 1,
            'HEALTH': 1,
            'HP': 1,
            'COLOR': '#FFFFFF',
            'states': []
        }
        
        if 'colores_piezas' not in self.ast['config']:
            self.ast['config']['colores_piezas'] = {}

        # Loop to parse attributes and states in any order until END
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            token = self.tokens[self.posicion]
            
            if token == 'TYPE':
                self.consumir('TYPE')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                tipo_val = self.consumir()
                shape_data['tipo_forma'] = tipo_val
                shape_data['tipo'] = tipo_val
            elif token == 'CHANCE':
                self.consumir('CHANCE')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                shape_data['CHANCE'] = int(self.consumir())
            elif token == 'SPEED':
                self.consumir('SPEED')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                shape_data['SPEED'] = int(self.consumir())
            elif token == 'HEAL':
                self.consumir('HEAL')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                shape_data['HEAL'] = int(self.consumir())
            elif token == 'DAMAGE':
                self.consumir('DAMAGE')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                shape_data['DAMAGE'] = int(self.consumir())
            elif token in ('HEALTH', 'HP'):
                self.consumir(token)
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                val = int(self.consumir())
                shape_data['HEALTH'] = val
                shape_data['HP'] = val
            elif token == 'COLOR':
                self.consumir('COLOR')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                color = self.consumir()
                shape_data['COLOR'] = color
                self.ast['config']['colores_piezas'][nombre_shape] = color
            elif token == 'STATE':
                self.consumir('STATE')
                self.consumir() # Consume el número del estado
                self.consumir(':')
                matriz = []
                while self.posicion < len(self.tokens) and self.tokens[self.posicion] == '[':
                    fila = []
                    self.consumir('[')
                    while self.tokens[self.posicion] != ']':
                        fila.append(int(self.consumir()))
                        if self.tokens[self.posicion] == ',': self.consumir(',')
                    self.consumir(']')
                    matriz.append(fila)
                shape_data['states'].append(matriz)
            else:
                raise Exception("Token inesperado en DEFINE SHAPE: " + token)

        self.consumir('END')
        self.ast['shapes'][nombre_shape] = shape_data

    def parsear_boss(self):
        if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'DEFINE':
            self.consumir('DEFINE')
        self.consumir('BOSS')
        if self.posicion < len(self.tokens) and self.tokens[self.posicion] != ':':
            nombre_boss = self.consumir()
        else:
            nombre_boss = 'FINAL_BOSS'
        self.consumir(':')

        boss_data = {
            'tipo': 'BOSS',
            'tipo_forma': 'RECTANGLE',
            'CHANCE': 1,
            'SPEED': 0,
            'HEAL': 0,
            'DAMAGE': 50,
            'HEALTH': 500,
            'HP': 500,
            'COLOR': '#FF0055',
            'states': []
        }

        if 'colores_piezas' not in self.ast['config']:
            self.ast['config']['colores_piezas'] = {}

        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            token = self.tokens[self.posicion]

            if token == 'TYPE':
                self.consumir('TYPE')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                boss_data['tipo_forma'] = self.consumir()
            elif token == 'COLOR':
                self.consumir('COLOR')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                color = self.consumir()
                boss_data['COLOR'] = color
                self.ast['config']['colores_piezas'][nombre_boss] = color
                self.ast['config']['colores_piezas']['BOSS'] = color
            elif token in ('HP', 'HEALTH'):
                self.consumir(token)
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                val = int(self.consumir())
                boss_data['HEALTH'] = val
                boss_data['HP'] = val
            elif token == 'DAMAGE':
                self.consumir('DAMAGE')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                boss_data['DAMAGE'] = int(self.consumir())
            elif token == 'SPEED':
                self.consumir('SPEED')
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == ':':
                    self.consumir(':')
                boss_data['SPEED'] = int(self.consumir())
            elif token == 'STATE':
                self.consumir('STATE')
                self.consumir()
                self.consumir(':')
                matriz = []
                while self.posicion < len(self.tokens) and self.tokens[self.posicion] == '[':
                    fila = []
                    self.consumir('[')
                    while self.tokens[self.posicion] != ']':
                        fila.append(int(self.consumir()))
                        if self.tokens[self.posicion] == ',': self.consumir(',')
                    self.consumir(']')
                    matriz.append(fila)
                boss_data['states'].append(matriz)
            else:
                self.posicion += 1

        self.consumir('END')
        if 'boss' not in self.ast:
            self.ast['boss'] = {}
        self.ast['boss'][nombre_boss] = boss_data
        self.ast['shapes'][nombre_boss] = boss_data
        self.ast['shapes']['BOSS'] = boss_data

    def parsear_powerup(self):
        self.consumir('DEFINE')
        self.consumir('POWERUP')
        nombre = self.consumir()
        self.consumir(':')

        powerup = {
            'nombre': nombre,
            'estados': [],
            'efecto': 'CLEAR_AREA',   # efecto por defecto
            'color': '#FFD700',       # dorado por defecto
            'condiciones': []
        }

        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            token = self.tokens[self.posicion]

            if token == 'STATE':
                self.consumir('STATE')
                self.consumir()                # numero de estado
                self.consumir(':')
                matriz = []
                while self.posicion < len(self.tokens) and self.tokens[self.posicion] == '[':
                    fila = []
                    self.consumir('[')
                    while self.tokens[self.posicion] != ']':
                        fila.append(int(self.consumir()))
                        if self.tokens[self.posicion] == ',':
                            self.consumir(',')
                    self.consumir(']')
                    matriz.append(fila)
                powerup['estados'].append(matriz)

            elif token == 'EFFECT':
                self.consumir('EFFECT')
                powerup['efecto'] = self.consumir()

            elif token == 'COLOR':
                self.consumir('COLOR')
                powerup['color'] = self.consumir()

            elif token == 'CONDITION':
                self.consumir('CONDITION')
                tipo = self.consumir()
                cond = {'tipo': tipo}
                # Condiciones que necesitan un nombre de pieza
                if tipo in ('ROTATIONS_PIECE',):
                    cond['pieza'] = self.consumir()
                cond['valor'] = int(self.consumir())
                powerup['condiciones'].append(cond)

            else:
                self.posicion += 1

        self.consumir('END')
        self.ast['powerups'][nombre] = powerup


    # --- FUNCION CORREGIDA ---
    def parsear_evento(self):
        self.consumir('ON')
        nombre_evento = 'ON_' + self.consumir()
        params_evento = []
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != ':':
            params_evento.append(self.consumir())
        self.consumir(':')
        acciones = []
        palabras_reservadas = [
            'END', 'ON', 'DEFINE', 'SPAWN', 'MOVE', 'ROTATE', 'INCREASE_SCORE',
            'SET_DIRECTION', 'GROW', 'COLOR', 'GAME_OVER', 'SHRINK', 'DECREASE_SCORE',
            'CLOUD_COLLISION', 'FULL_SHRINK', 'POWERUP', 'HEAL', 'DAMAGE', 'SPEED',
            'HEALTH', 'HP', 'BOSS', 'TARGET_SCORE'
        ]
        while self.posicion < len(self.tokens) and self.tokens[self.posicion] != 'END':
            verbo = self.consumir()
            
            # Si el comando es de una sola palabra, lo anadimos y continuamos
            if verbo == 'GAME_OVER':
                acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue

            if verbo == 'FULL_SHRINK':
                if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'PLAYER':
                    objeto = self.consumir('PLAYER')
                    params = []
                    if self.posicion < len(self.tokens) and self.tokens[self.posicion] not in palabras_reservadas:
                        params.append(self.consumir())
                    acciones.append({'accion': verbo, 'objeto': objeto, 'params': params})
                else:
                    acciones.append({'accion': verbo, 'objeto': None, 'params': []})
                continue
            
            # Si no, parseamos el resto de la accion
            objeto = self.consumir()
            params = []
            if self.posicion < len(self.tokens) and self.tokens[self.posicion] == 'AT':
                self.consumir('AT')
                if self.tokens[self.posicion] == 'RANDOM':
                    params.append(self.consumir())
                else:
                    self.consumir('(')
                    x = int(self.consumir())
                    self.consumir(',')
                    y = int(self.consumir())
                    self.consumir(')')
                    params.append([x, y])
            elif self.posicion < len(self.tokens) and self.tokens[self.posicion] not in palabras_reservadas:
                params.append(self.consumir())
            acciones.append({'accion': verbo, 'objeto': objeto, 'params': params})
        self.consumir('END')
        self.ast['events'][nombre_evento] = acciones
        if params_evento and nombre_evento == 'ON_TARGET_SCORE':
            try:
                self.ast['config']['target_score'] = int(params_evento[0])
            except ValueError:
                pass

def generar_codigo(ast, archivo_salida):
    with open(archivo_salida, 'w') as f:
        json.dump(ast, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 compiler.py <archivo_entrada.brick>")
        sys.exit(1)
    archivo_entrada = sys.argv[1]
    archivo_salida = archivo_entrada.replace('.brick', '.json')
    print("Compilando " + archivo_entrada + "...")
    try:
        with open(archivo_entrada, 'r') as f:
            codigo = f.read()
        tokens = lexer(codigo)
        parser = Parser(tokens)
        ast = parser.parse()
        generar_codigo(ast, archivo_salida)
        print("Compilacion exitosa! Archivo de juego creado en " + archivo_salida)
    except Exception as e:
        print("\n!!! ERROR DE COMPILACION !!!")
        print(str(e))
        sys.exit(1)

