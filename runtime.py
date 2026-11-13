# -*- coding: utf-8 -*-
# runtime.py (VERSION CON INTERFAZ GRAFICA USANDO Tkinter y caracteres ASCII unicamente)
# Adaptado para Python 3

import sys
import json
import time
import random
# tkinter es la libreria GUI estandar de Python
import tkinter as tk
from tkinter import messagebox as tkMessageBox

class Juego:
    def __init__(self, datos_juego):
        self.datos_juego = datos_juego
        self.tipo_juego = self.datos_juego.get('tipo_juego', 'TETRIS')
        config = self.datos_juego.get('config', {})
        self.ancho = config.get('grid_size', [10, 20])[0]
        self.alto = config.get('grid_size', [10, 20])[1]
        self.grid = [[0 for _ in range(self.ancho)] for _ in range(self.alto)]
        self.puntuacion = 0
        self.juego_terminado = False
        self.colores_piezas = config.get('colores_piezas', {
                    'I': '#00FFFF', 'J': '#0000FF', 'L': '#FFA500',
                    'O': '#FFFF00', 'S': '#00FF00', 'T': '#800080', 'Z': '#FF0000'})
        self.nombre_pieza_actual = None # sirve para guardar la letra de la pieza que está cayendo

        # --- NUEVO: Power-ups ---
        self.powerups = self.datos_juego.get('powerups', {})
        self.stats = {
            'rotaciones_totales': 0,
            'rotaciones_por_pieza': {},
            'piezas_colocadas': 0,
            'comida_devorada': 0
        }
        self.tiempo_slow = 0.0     # segundos restantes de gravedad lenta
        self.ultimo_powerup = ""
        self.tiempo_invencible = 0.0 # segundos invencible

        # Identificar si es Snake y si es la version evolucionada
        self.es_snake = self.tipo_juego in ('SNAKE', 'SNAKE_EVOLVED')
        self.es_snake_evolved = (self.tipo_juego == 'SNAKE_EVOLVED' or bool(self.powerups) or 
                                 'ON_EAT_POISON' in self.datos_juego.get('events', {}) or 
                                 'CLOUD' in self.datos_juego.get('shapes', {}) or
                                 bool(self.datos_juego.get('nivel')) or
                                 bool(self.datos_juego.get('config', {}).get('nivel')))

        # --- Configuracion de la GUI ---
        self.root = tk.Tk()
        self.root.title("BrickScript - " + self.tipo_juego)
        # Configurar la accion al cerrar la ventana ('X' de la barra de titulo)
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        
        self.taman_celda = 25 # Pixeles por celda
        self.ancho_canvas = self.ancho * self.taman_celda
        self.alto_canvas = self.alto * self.taman_celda
        
        # Canvas para dibujar el juego
        self.canvas = tk.Canvas(self.root, width=self.ancho_canvas, height=self.alto_canvas, bg='#111111')
        self.canvas.pack(side=tk.LEFT, padx=10, pady=10)

        # Marco lateral para la puntuacion y controles
        self.marco_score = tk.Frame(self.root, width=170, height=self.alto_canvas, bg='#222222')
        self.marco_score.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        self.label_score = tk.Label(self.marco_score, text="PUNTUACION\n0", bg='#222222', fg='white', font=('Consolas', 16, 'bold'))
        self.label_score.pack(pady=(30, 10), padx=10)

        # --- NUEVO: etiqueta para el ultimo power-up / estado del slow ---
        self.label_powerup = tk.Label(self.marco_score, text="", bg='#222222', fg='#FFD700',
                                      font=('Consolas', 10, 'bold'),
                                      wraplength=150, justify='center')
        self.label_powerup.pack(pady=10, padx=10)
        
        # Nota: Se ha eliminado 'Q: Salir' de los controles en pantalla
        self.label_controles = tk.Label(self.marco_score, text="CONTROLES\nFlechas: Mover/Rotar", bg='#222222', fg='gray', font=('Consolas', 10))
        if self.tipo_juego == 'TANKS':
            self.label_controles.config(text="CONTROLES\nFlechas: Mover/Rotar\nEspacio: Disparar")
        if self.es_snake:
            if self.es_snake_evolved:
                self.label_controles.config(text="CONTROLES Y REGLAS\nFlechas: Mover\nComida (+10 puntos): Azul\nVeneno (-10 puntos): Rojo\nNube (Perder todos los puntos): Gris\n Invencible (5 segundos): Fucsia")
            else:
                self.label_controles.config(text="CONTROLES\nFlechas: Mover\nComida (+10 puntos): Azul")
        self.label_controles.pack(pady=20, padx=10)

        # Configurar eventos de teclado. Usamos <Key> para capturar cualquier tecla
        self.root.bind('<Key>', self.manejar_input_gui)
        
        if self.tipo_juego == 'TETRIS':
            self.pieza_actual = None
            self.pieza_x, self.pieza_y, self.pieza_rotacion = 0, 0, 0
            self.velocidad_gravedad = 0.4
       
        if self.es_snake:
            self.serpiente_cuerpo = []
            self.serpiente_direccion = (1, 0)
            self.posicion_comida = None
            self.posicion_veneno = None
            self.posicion_nube = None
            if self.es_snake_evolved:
                nivel_cfg = self.datos_juego.get('nivel') or self.datos_juego.get('config', {}).get('nivel')
                self.nivel = nivel_cfg if nivel_cfg in ('BABY', 'ENTUSIASTA', 'NYAN_CAT') else 'BABY'
                velocidades = {'BABY': 0.15, 'ENTUSIASTA': 0.12, 'NYAN_CAT': 0.10}
                self.velocidad_gravedad = velocidades.get(self.nivel, 0.15)
            else:
                self.nivel = None
                self.velocidad_gravedad = 0.15

        self.timer_gravedad = 0
        self.timer_id = None

        if self.tipo_juego == 'TANKS':
            shape_tank = self.datos_juego.get('shapes', {}).get('PLAYER_TANK', {})
            self.jugador_posicion = [self.ancho - 3, self.alto - 3]
            self.jugador_spawn_pos = [self.ancho - 3, self.alto - 3]
            self.tank_direccion = (0, -1)  # Inicialmente apuntando hacia arriba
            self.tank_rotacion = 0          # 0: Arriba, 1: Derecha, 2: Abajo, 3: Izquierda
            self.jugador_vidas = 3
            self.jugador_salud_max = shape_tank.get('HEALTH', 100)
            self.jugador_salud = self.jugador_salud_max
            self.tiempo_invencible_jugador = 0
            self.balas_max_jugador = 5
            self.balas_restantes_jugador = 5
            self.cooldown_recarga_jugador = 0.0
            self.martillo_activo = False
            self.posicion_martillo = None
            self.intervalo_spawn_martillo = 15.0
            self.timer_spawn_martillo = 15.0
            self.timer_vida_martillo = 0.0
            self.duracion_vida_martillo = 12.0
            self.enemigos = []
            self.balas_jugador = []
            self.balas_enemigos = []
            self.muros = []
            self.muros_posiciones = {}
            self.velocidad_gravedad = 0.3
            self.tiempo_ultimo_disparo_jugador = 0
            
        
        # --- Control del menú: Solo para Snake Evolved ---
        self.en_menu = True if (self.es_snake and self.es_snake_evolved) else False
        if not self.en_menu:
            self.ejecutar_evento('ON_START')
            if self.tipo_juego == 'TANKS' and len(self.muros) == 0 and 'WALL' in self.datos_juego.get('shapes', {}):
                self.tank_generar_mapa_muros()

    def run(self):
        if self.en_menu:
            self.dibujar_menu()
        else:
            self.root.after(50, self.game_loop) 
        self.root.mainloop()

    def dibujar_menu(self):
        self.canvas.delete("all")
        # Dibuja el texto centrado en la pantalla
        cx, cy = self.ancho_canvas / 2, self.alto_canvas / 2
        self.canvas.create_text(cx, cy - 60, text="SELECCIONA DIFICULTAD", fill="white", font=('Consolas', 14, 'bold'))
        self.canvas.create_text(cx, cy - 10, text="1. BABY (Fácil)", fill="#00FF00", font=('Consolas', 12, 'bold'))
        self.canvas.create_text(cx, cy + 20, text="2. ENTUSIASTA (Medio)", fill="#FFFF00", font=('Consolas', 12, 'bold'))
        self.canvas.create_text(cx, cy + 50, text="3. NYAN CAT (Extremo)", fill="#FFB6C1", font=('Consolas', 12, 'bold'))
        texto_iniciar = "Presiona 1, 2 o 3 para iniciar"
        if getattr(self, 'nivel', None):
            texto_iniciar += "\n(Nivel predeterminado: " + str(self.nivel) + " - Presiona ESPACIO o ENTER)"
        self.canvas.create_text(cx, cy + 100, text=texto_iniciar, fill="gray", font=('Consolas', 10), justify='center')

    def iniciar_juego_snake(self, nivel, velocidad):
        self.nivel = nivel
        self.velocidad_gravedad = velocidad
        self.en_menu = False
        self.ejecutar_evento('ON_START') # Spawnea al jugador y obstáculos
        self.root.after(50, self.game_loop) #despues de presionar se inicia el juego

    def game_loop(self):
        if self.juego_terminado:
            self.mostrar_game_over()
            return

        # Logica de TICK/Gravedad
        # El loop se ejecuta cada 50ms (0.05 segundos)
        # --- NUEVO: respetar el slow si hay un power-up activo ---
        velocidad_efectiva = self.velocidad_gravedad
        if self.tiempo_slow > 0:
            velocidad_efectiva *= 2.5
            self.tiempo_slow -= 0.05
            if self.tiempo_slow < 0:
                self.tiempo_slow = 0

        self.timer_gravedad += 0.05 

        if self.tiempo_invencible > 0:
            self.tiempo_invencible -= 0.05
            self.label_powerup.config(text="INVENCIBLE: %.1fs" % self.tiempo_invencible)

        if self.tipo_juego == 'TANKS':
            self.tank_actualizar()
            if self.timer_gravedad >= velocidad_efectiva:
                self.timer_gravedad = 0
                self.ejecutar_evento('ON_TICK')
        elif self.timer_gravedad >= velocidad_efectiva:
            self.timer_gravedad = 0
            self.ejecutar_evento('ON_TICK')

        self.dibujar()

        # Programa el siguiente ciclo de juego
        self.timer_id = self.root.after(50, self.game_loop)
        
    def cerrar_ventana(self):
        # Detiene el loop de juego de forma segura
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.root.destroy()
        sys.exit(0)


    def manejar_input_gui(self, event):
        key = event.keysym.upper()

        #el mapeo de las teclas en el menu inicial
        if self.en_menu:
            if key == '1': self.iniciar_juego_snake('BABY', 0.15)
            elif key == '2': self.iniciar_juego_snake('ENTUSIASTA', 0.12)
            elif key == '3': self.iniciar_juego_snake('NYAN_CAT', 0.10)
            elif key in ('SPACE', 'RETURN'):
                vel = {'BABY': 0.15, 'ENTUSIASTA': 0.12, 'NYAN_CAT': 0.10}.get(self.nivel, 0.15)
                self.iniciar_juego_snake(self.nivel, vel)
            return
        
        # Mapeo de teclas de flecha
        if self.tipo_juego == 'TETRIS':
            if key == 'UP': self.ejecutar_evento('ON_KEY_UP')
            elif key == 'DOWN': self.ejecutar_evento('ON_KEY_DOWN')
            elif key == 'LEFT': self.ejecutar_evento('ON_KEY_LEFT')
            elif key == 'RIGHT': self.ejecutar_evento('ON_KEY_RIGHT')
        elif self.es_snake:
            # Llamamos a las funciones internas para Snake
            if key == 'UP': self.snake_cambiar_direccion('UP')
            elif key == 'DOWN': self.snake_cambiar_direccion('DOWN')
            elif key == 'LEFT': self.snake_cambiar_direccion('LEFT')
            elif key == 'RIGHT': self.snake_cambiar_direccion('RIGHT')

        elif self.tipo_juego == 'TANKS':
            if key == 'UP': self.tank_cambiar_direccion('ON_KEY_UP')
            elif key == 'DOWN': self.tank_cambiar_direccion('ON_KEY_DOWN')
            elif key == 'LEFT': self.tank_cambiar_direccion('ON_KEY_LEFT')
            elif key == 'RIGHT': self.tank_cambiar_direccion('ON_KEY_RIGHT')
            elif key == 'SPACE': self.tank_disparar(es_jugador=True)


    def dibujar(self):
    
        #print("Nombre pieza actual:", self.nombre_pieza_actual)
        #print("Colores disponibles:", list(self.colores_piezas.keys()))
        
        self.canvas.delete("all")
        self.label_score.config(text="PUNTUACION\n" + str(self.puntuacion))

        # --- NUEVO: actualizar la etiqueta del power-up ---
        if self.tipo_juego == 'TANKS':
            lineas = [
                "VIDAS: %s" % ("❤️ " * max(0, getattr(self, 'jugador_vidas', 1))),
                "HP: %d" % self.jugador_salud
            ]
            if getattr(self, 'cooldown_recarga_jugador', 0.0) > 0.0:
                lineas.append("COOLDOWN: %.1fs" % self.cooldown_recarga_jugador)
                self.label_powerup.config(fg='#FF4444')
            else:
                lineas.append("BALAS: %d/5" % getattr(self, 'balas_restantes_jugador', 5))
                self.label_powerup.config(fg='#FFD700')
            if getattr(self, 'martillo_activo', False):
                lineas.append("🔨 CURA: ACTIVO")
            else:
                lineas.append("🔨 CURA: %.0fs" % max(0, getattr(self, 'timer_spawn_martillo', 15.0)))
            lineas.append("---")
            for e in self.enemigos:
                nombre = e['tipo'].replace('ENEMY_TANK_', '')
                estado = ("%d HP" % e['salud']) if e.get('vivo', True) else "REVIVE"
                lineas.append("%s: %s" % (nombre, estado))
            self.label_powerup.config(text="\n".join(lineas))
        elif self.tiempo_slow > 0:
            self.label_powerup.config(text="SLOW: %.1fs" % self.tiempo_slow)
        elif self.tiempo_invencible > 0:
            self.label_powerup.config(text="INVENCIBLE: %.1fs" % self.tiempo_invencible)
        elif self.ultimo_powerup:
            self.label_powerup.config(text="Ultimo usado: " + self.ultimo_powerup)
        
        # Colores fijos para Snake
        COLOR_SNAKE_CABEZA = '#00FF00'
        COLOR_SNAKE_CUERPO = '#33CC33'
        COLOR_FOOD = "#2600FF"
        COLOR_POISON = "#ff0000"
        COLOR_CLOUD = "#AAAAAA"
        # 1. Dibujar la cuadrícula estática (piezas ya fijadas)
        for y in range(self.alto):
            for x in range(self.ancho):
                celda = self.grid[y][x]
                if celda == 0:
                    continue
                # --- NUEVO: si la celda tiene un power-up lo dibujamos distinto ---
                if isinstance(celda, str) and celda in self.powerups:
                    color_pu = self.powerups[celda].get('color', '#FFD700')
                    self.dibujar_celda_powerup(x, y, color_pu)
                else:
                    # Buscamos su color en el diccionario. Si no existe, usamos gris.
                    color_fijo = self.colores_piezas.get(celda, '#343434')
                    self.dibujar_celda(x, y, color_fijo)

        # 2. Dibujar la pieza actual de Tetris
        if self.tipo_juego == 'TETRIS' and self.pieza_actual:
            # Buscamos el color de la pieza que está cayendo
            color_actual = self.colores_piezas.get(self.nombre_pieza_actual, '#00FFFF')
            
            matriz_pieza = self.pieza_actual[self.pieza_rotacion]
            for y_offset, fila in enumerate(matriz_pieza):
                for x_offset, celda in enumerate(fila):
                    if celda == 1:
                        self.dibujar_celda(self.pieza_x + x_offset, self.pieza_y + y_offset, color_actual)
        
    # 3. Dibujar Snake, comida y obstáculos
        if self.es_snake:
            if self.posicion_comida:
                x, y = self.posicion_comida
                self.dibujar_celda(x, y, COLOR_FOOD)

            if self.es_snake_evolved and self.posicion_veneno:
                x, y = self.posicion_veneno
                self.dibujar_celda_circular(x, y, COLOR_POISON)

            if self.es_snake_evolved and self.posicion_nube:
                x, y = self.posicion_nube
                self.dibujar_celda_triangular(x, y, COLOR_CLOUD)

            forma = self.datos_juego.get('shapes', {}).get('PIXEL', {}).get('tipo_forma', 'RECTANGLE')

            #Cuerpo de la serpiente
            colores_arcoiris = ['#FF0000', '#FF7F00', '#FFFF00', '#00FF00', '#0000FF', '#4B0082', '#9400D3']
            
            for i, segmento in enumerate(self.serpiente_cuerpo):
                x, y = segmento
                
                # Color y efecto Nyan Cat
                if self.es_snake_evolved and self.nivel == 'NYAN_CAT':
                    color = '#FFB6C1' if i == 0 else colores_arcoiris[i % len(colores_arcoiris)]
                else:
                    color = COLOR_SNAKE_CABEZA if i == 0 else COLOR_SNAKE_CUERPO
                if self.es_snake_evolved and self.nivel == 'NYAN_CAT' and i == 0:
                    self.dibujar_celda_gato(x, y, color) # Usamos la nueva cabeza con rasgos de gato
                elif forma == 'CIRCLE':
                    self.dibujar_celda_circular(x, y, color)
                elif forma == 'TRIANGLE':
                    self.dibujar_celda_triangular(x, y, color)
                else:
                    self.dibujar_celda(x, y, color)

    # 4. Dibujar el jugador y enemigos (Tank)
        if self.tipo_juego == 'TANKS':
            # Dibujar muros destructibles
            shape_wall = self.datos_juego.get('shapes', {}).get('WALL', {})
            color_base = shape_wall.get('COLOR') or shape_wall.get('color') or '#B85D19'
            for muro in getattr(self, 'muros', []):
                salud = muro['salud']
                salud_max = muro.get('salud_max', 50)
                pct = salud / salud_max if salud_max > 0 else 1.0
                if pct > 0.6:
                    c_muro = color_base
                elif pct > 0.3:
                    c_muro = '#8B3E1B'
                else:
                    c_muro = '#5A210A'
                self.dibujar_celda_muro(muro['x'], muro['y'], c_muro, pct)

            if self.jugador_posicion:
                shape_tank = self.datos_juego.get('shapes', {}).get('PLAYER_TANK', {})
                estados = shape_tank.get('states', [
                    [[0, 1, 0],
                     [1, 1, 1],
                     [1, 1, 1]]
                ])
                color_tank = shape_tank.get('color', '#025a06')
                matriz_tanque = estados[self.tank_rotacion % len(estados)]

                base_x, base_y = self.jugador_posicion
                for y_offset, fila in enumerate(matriz_tanque):
                    for x_offset, celda in enumerate(fila):
                        if celda == 1:
                            self.dibujar_celda(base_x + x_offset, base_y + y_offset, color_tank)

            # Dibujar todos los tanques enemigos
            for enemigo in self.enemigos:
                if not enemigo.get('vivo', True):
                    continue
                tipo = enemigo['tipo']
                shape_enemy = self.datos_juego.get('shapes', {}).get(tipo, {})
                estados_enemy = shape_enemy.get('states', [
                    [[0, 1, 0],
                     [1, 1, 1],
                     [1, 1, 1]]
                ])
                color_enemy = enemigo.get('color', shape_enemy.get('COLOR', '#FF0000'))
                rot = enemigo.get('rotacion', 2)
                matriz_enemy = estados_enemy[rot % len(estados_enemy)]

                base_x, base_y = enemigo['posicion']
                for y_offset, fila in enumerate(matriz_enemy):
                    for x_offset, celda in enumerate(fila):
                        if celda == 1:
                            self.dibujar_celda(base_x + x_offset, base_y + y_offset, color_enemy)

            # Dibujar balas del jugador y enemigos
            for bala in self.balas_jugador:
                self.dibujar_celda_circular(bala['x'], bala['y'], bala.get('color', '#00FF00'))

            for bala in self.balas_enemigos:
                self.dibujar_celda_circular(bala['x'], bala['y'], bala.get('color', '#FF4444'))

            # Dibujar martillo de curación si está activo
            if getattr(self, 'martillo_activo', False) and getattr(self, 'posicion_martillo', None):
                shape_hammer = self.datos_juego.get('shapes', {}).get('HAMMER', {})
                estados_hammer = shape_hammer.get('states', [
                    [[1, 1, 1],
                     [0, 1, 0],
                     [0, 1, 0]]
                ])
                color_hammer = shape_hammer.get('COLOR') or shape_hammer.get('color') or '#ffffff'
                matriz_hammer = estados_hammer[0]
                hx, hy = self.posicion_martillo
                for y_offset, fila in enumerate(matriz_hammer):
                    for x_offset, celda in enumerate(fila):
                        if celda == 1:
                            self.dibujar_celda(hx + x_offset, hy + y_offset, color_hammer)


    def dibujar_celda(self, x, y, color):
        ts = self.taman_celda # Alias para taman de celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#000000')


    def dibujar_celda_circular(self, x, y, color):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline='#000000')

    def dibujar_celda_triangular(self, x, y, color):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        # esto dibuja un triangulo apuntando hacia arriba
        self.canvas.create_polygon(x1, y2, (x1+x2)/2, y1, x2, y2, fill=color, outline='#000000')
    
    def dibujar_celda_gato(self, x, y, color):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        
        # 1. Dibujar orejas (polígonos por detrás de la cabeza)
        self.canvas.create_polygon(x1 + ts*0.1, y1 + ts*0.3, x1 + ts*0.2, y1 - ts*0.1, x1 + ts*0.4, y1 + ts*0.1, fill=color, outline='#000000')
        self.canvas.create_polygon(x2 - ts*0.1, y1 + ts*0.3, x2 - ts*0.2, y1 - ts*0.1, x2 - ts*0.4, y1 + ts*0.1, fill=color, outline='#000000')
        
        # 2. Dibujar la cabeza (círculo base)
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline='#000000')
        
        # 3. Dibujar ojos
        self.canvas.create_oval(x1 + ts*0.2, y1 + ts*0.3, x1 + ts*0.4, y1 + ts*0.5, fill='black')
        self.canvas.create_oval(x1 + ts*0.6, y1 + ts*0.3, x1 + ts*0.8, y1 + ts*0.5, fill='black')
        
        # 4. Dibujar bigotes
        # Lado izquierdo
        self.canvas.create_line(x1 - ts*0.3, y1 + ts*0.5, x1 + ts*0.1, y1 + ts*0.6, fill='black')
        self.canvas.create_line(x1 - ts*0.3, y1 + ts*0.7, x1 + ts*0.1, y1 + ts*0.65, fill='black')
        # Lado derecho
        self.canvas.create_line(x2 + ts*0.3, y1 + ts*0.5, x2 - ts*0.1, y1 + ts*0.6, fill='black')
        self.canvas.create_line(x2 + ts*0.3, y1 + ts*0.7, x2 - ts*0.1, y1 + ts*0.65, fill='black')
    
    # --- NUEVO: dibujo especial para los power-ups (un circulo brillante) ---
    def dibujar_celda_powerup(self, x, y, color):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        self.canvas.create_rectangle(x1, y1, x2, y2, fill='#111111', outline='#333333')
        m = 3
        self.canvas.create_oval(x1 + m, y1 + m, x2 - m, y2 - m, fill=color, outline='#FFFFFF', width=2)

    def dibujar_celda_muro(self, x, y, color, pct_salud):
        ts = self.taman_celda
        x1, y1 = x * ts, y * ts
        x2, y2 = x1 + ts, y1 + ts
        # Fondo del ladrillo
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#200c02')
        # Textura de ladrillos con líneas de mortero
        mid_y = y1 + ts // 2
        self.canvas.create_line(x1, mid_y, x2, mid_y, fill='#3b1604', width=1)
        self.canvas.create_line(x1 + ts // 2, y1, x1 + ts // 2, mid_y, fill='#3b1604', width=1)
        self.canvas.create_line(x1 + ts // 4, mid_y, x1 + ts // 4, y2, fill='#3b1604', width=1)
        self.canvas.create_line(x1 + 3 * ts // 4, mid_y, x1 + 3 * ts // 4, y2, fill='#3b1604', width=1)
        # Grietas si el ladrillo ha recibido disparos
        if pct_salud <= 0.65:
            self.canvas.create_line(x1 + 4, y1 + 3, x1 + 11, y1 + 13, fill='#111111', width=1)
        if pct_salud <= 0.35:
            self.canvas.create_line(x1 + 14, y1 + 4, x1 + 8, y1 + 16, fill='#111111', width=2)


    def ejecutar_evento(self, nombre_evento):
        if nombre_evento in self.datos_juego['events']:
            for accion in self.datos_juego['events'][nombre_evento]:
                verbo, objeto = accion.get('accion'), accion.get('objeto')
                
                if verbo == 'INCREASE_SCORE': self.puntuacion += int(objeto)
                if verbo == 'DECREASE_SCORE':
                    self.puntuacion -= int(objeto)
                    # Si la puntuación baja de 0, forzamos el Game Over
                    if self.puntuacion < 0:
                        self.juego_terminado = True
                if verbo == 'GAME_OVER': self.juego_terminado = True
                if verbo == 'HEAL':
                    curacion = int(objeto) if objeto else 25
                    salud_max = getattr(self, 'jugador_salud_max', 100)
                    self.jugador_salud = min(salud_max, self.jugador_salud + curacion)

                if self.tipo_juego == 'TETRIS':
                    if verbo == 'SPAWN': self.tetris_spawn_pieza()
                    if verbo == 'MOVE': self.tetris_mover_pieza(accion['params'][0])
                    if verbo == 'ROTATE': self.tetris_rotar_pieza()
                
                if self.es_snake:
                    if verbo == 'SPAWN' and objeto == 'PLAYER': self.snake_spawn_jugador(accion)
                    if verbo == 'SPAWN' and objeto == 'FOOD': self.snake_spawn_comida()
                    if verbo == 'SPAWN' and objeto == 'POISON': self.snake_spawn_veneno()
                    if verbo == 'SPAWN' and objeto == 'CLOUD': self.snake_spawn_cloud()
                    if verbo == 'MOVE' and objeto == 'PLAYER': self.snake_mover_jugador()
                    if verbo == 'GROW': 
                        self.snake_crecer()
                        if self.es_snake_evolved:
                            self.stats['comida_devorada'] += 1
                            self.verificar_condiciones_powerup(evento='EAT_FOOD')
                    if verbo == 'SHRINK': self.snake_encoger(accion)
                    if verbo == 'FULL_SHRINK': 
                        if self.nivel == 'NYAN_CAT':
                            if self.puntuacion <= 0:
                                self.juego_terminado = True
                            else:
                                self.puntuacion = 0
                        else:
                            self.puntuacion = 0
                        self.snake_encoger_todo(accion)
                if self.tipo_juego == 'TANKS':
                    if verbo == 'SPAWN' and objeto == 'PLAYER':
                        self.tank_spawnear_jugador(accion)
                    elif verbo == 'SPAWN' and objeto == 'HAMMER':
                        self.tank_spawnear_martillo(accion)
                    elif verbo == 'SPAWN' and objeto == 'WALL':
                        self.tank_spawnear_muro(accion)
                    elif verbo == 'SPAWN' and objeto:
                        self.tank_spawnear_enemigo(objeto, accion)

    # METODOS DE LOGICA DE JUEGO (MANTENIDOS DEL ARCHIVO ORIGINAL)
    # ---------------------------------------------------------------------

    def tetris_spawn_pieza(self):
        shapes = self.datos_juego['shapes']

        nombres = list(shapes.keys())
        pesos = []

        for nombre in nombres:
            pesos.append(shapes[nombre].get('CHANCE', 1))

        total = sum(pesos)

        numero = random.uniform(0, total)
        acumulado = 0

        for i in range(len(nombres)):
            acumulado += pesos[i]

            if numero <= acumulado:
                nombre_pieza = nombres[i]
                break

        self.pieza_actual = shapes[nombre_pieza]['states']
        self.nombre_pieza_actual = nombre_pieza
        self.pieza_x, self.pieza_y, self.pieza_rotacion = self.ancho // 2 - 2, 0, 0

        if self.tetris_verificar_colision(
            self.pieza_x, self.pieza_y, self.pieza_rotacion):
            self.juego_terminado = True
    
    def tetris_mover_pieza(self, direccion):
        if not self.pieza_actual: return
        dx, dy = 0, 0
        if direccion == 'LEFT': dx = -1
        elif direccion == 'RIGHT': dx = 1
        elif direccion == 'DOWN': dy = 1
        if not self.tetris_verificar_colision(self.pieza_x + dx, self.pieza_y + dy, self.pieza_rotacion):
            self.pieza_x += dx
            self.pieza_y += dy
        elif dy > 0:
            self.tetris_fijar_pieza()

    def tetris_rotar_pieza(self):
        if not self.pieza_actual: return
        nueva_rotacion = (self.pieza_rotacion + 1) % len(self.pieza_actual)
        if not self.tetris_verificar_colision(self.pieza_x, self.pieza_y, nueva_rotacion):
            self.pieza_rotacion = nueva_rotacion
            # --- NUEVO: contar rotaciones ---
            self.stats['rotaciones_totales'] += 1
            if self.nombre_pieza_actual:
                p = self.nombre_pieza_actual
                self.stats['rotaciones_por_pieza'][p] = \
                    self.stats['rotaciones_por_pieza'].get(p, 0) + 1
            self.verificar_condiciones_powerup(evento='ROTATION')

    def tetris_fijar_pieza(self):
        matriz_pieza = self.pieza_actual[self.pieza_rotacion]
        # --- NUEVO: guardar los power-ups que esta pieza pise ---
        recogidos = []
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    if 0 <= self.pieza_y + y_offset < self.alto and 0 <= self.pieza_x + x_offset < self.ancho:
                        gy = self.pieza_y + y_offset
                        gx = self.pieza_x + x_offset
                        celda_prev = self.grid[gy][gx]
                        if isinstance(celda_prev, str) and celda_prev in self.powerups:
                            recogidos.append((gx, gy, celda_prev))
                        self.grid[gy][gx] = self.nombre_pieza_actual
        self.pieza_actual = None
        self.nombre_pieza_actual = None

        # --- NUEVO: aplicar efectos de los power-ups recogidos ---
        for gx, gy, pname in recogidos:
            self.aplicar_efecto_powerup(pname, gx, gy)

        # --- NUEVO: contar piezas colocadas y chequear spawn ---
        self.stats['piezas_colocadas'] += 1

        self.tetris_limpiar_lineas()
        self.verificar_condiciones_powerup(evento='PIECE_DROPPED')
        self.ejecutar_evento('ON_START')

    # --- NUEVO: dice si una celda bloquea o no (los power-ups no bloquean) ---
    def _celda_bloqueada(self, x, y):
        if not (0 <= x < self.ancho and 0 <= y < self.alto):
            return True
        val = self.grid[y][x]
        if val == 0:
            return False
        if isinstance(val, str) and val in self.powerups:
            return False
        return True

    def tetris_verificar_colision(self, x, y, rotacion):
        if not self.pieza_actual: return False
        matriz_pieza = self.pieza_actual[rotacion]
        for y_offset, fila in enumerate(matriz_pieza):
            for x_offset, celda in enumerate(fila):
                if celda == 1:
                    if self._celda_bloqueada(x + x_offset, y + y_offset):
                        return True
        return False

    def tetris_limpiar_lineas(self):
        nuevo_grid = [fila for fila in self.grid if 0 in fila]
        lineas_limpias = self.alto - len(nuevo_grid)
        if lineas_limpias > 0:
            self.grid = [[0] * self.ancho for _ in range(lineas_limpias)] + nuevo_grid
            for _ in range(lineas_limpias): self.ejecutar_evento('ON_LINE_CLEAR')
            # --- NUEVO: pasar cuantas lineas se limpiaron de una sola vez ---
            self.verificar_condiciones_powerup(evento='LINES_CLEARED', valor=lineas_limpias)

    # ============== NUEVO: Sistema de Power-Ups ==============
    def verificar_condiciones_powerup(self, evento=None, valor=0):
        """Recorre los power-ups definidos y comprueba sus condiciones."""
        for nombre, pdata in self.powerups.items():
            for cond in pdata.get('condiciones', []):
                tipo = cond.get('tipo')
                umbral = cond.get('valor', 1)
                disparado = False

                if tipo == 'LINES_CLEARED' and evento == 'LINES_CLEARED':
                    if valor >= umbral:
                        disparado = True

                elif tipo == 'ROTATIONS' and evento == 'ROTATION':
                    if self.stats['rotaciones_totales'] >= umbral:
                        disparado = True
                        self.stats['rotaciones_totales'] -= umbral

                elif tipo == 'ROTATIONS_PIECE' and evento == 'ROTATION':
                    pname = cond.get('pieza')
                    if pname and self.stats['rotaciones_por_pieza'].get(pname, 0) >= umbral:
                        disparado = True
                        self.stats['rotaciones_por_pieza'][pname] -= umbral

                elif tipo == 'PIECES_DROPPED' and evento == 'PIECE_DROPPED':
                    if self.stats['piezas_colocadas'] >= umbral:
                        disparado = True
                        self.stats['piezas_colocadas'] -= umbral

                elif tipo == 'FOOD_EATEN' and evento == 'EAT_FOOD':
                    if self.stats['comida_devorada'] >= umbral:
                        disparado = True
                        self.stats['comida_devorada'] -= umbral

                if disparado:
                    self.spawn_powerup(nombre)
                    return   # solo un spawn por comprobacion

    def _celdas_alcanzables(self):
        """Devuelve las celdas vacias a las que una pieza puede llegar
        cayendo desde arriba (evita huecos cerrados)."""
        from collections import deque
        alcanzables = set()
        cola = deque()

        # Arrancar desde las celdas vacias de la fila superior
        for x in range(self.ancho):
            if self.grid[0][x] == 0:
                alcanzables.add((x, 0))
                cola.append((x, 0))

        # Propagarse solo por celdas vacias
        while cola:
            cx, cy = cola.popleft()
            for dx, dy in ((-1, 0), (1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < self.ancho and 0 <= ny < self.alto
                        and (nx, ny) not in alcanzables
                        and self.grid[ny][nx] == 0):
                    alcanzables.add((nx, ny))
                    cola.append((nx, ny))

        return alcanzables

    def spawn_powerup(self, nombre):
        """Coloca el power-up en una celda vacia Y alcanzable al azar."""
        if nombre not in self.powerups:
            return

        alcanzables = list(self._celdas_alcanzables())
        if self.tipo_juego in ('SNAKE', 'SNAKE_EVOLVED'):
            alcanzables = [c for c in alcanzables if c not in getattr(self, 'serpiente_cuerpo', []) and c != getattr(self, 'posicion_comida', None) and c != getattr(self, 'posicion_veneno', None) and c != getattr(self, 'posicion_nube', None)]
        if not alcanzables:
            return   # tablero lleno o sin espacio util, no se spawnea nada

        x, y = random.choice(alcanzables)
        self.grid[y][x] = nombre

    def aplicar_efecto_powerup(self, nombre, gx, gy):
        """Ejecuta el efecto del power-up recogido en (gx, gy)."""
        if nombre not in self.powerups:
            return
        efecto = self.powerups[nombre].get('efecto', 'CLEAR_AREA')
        self.ultimo_powerup = nombre + " (" + efecto + ")"

        if efecto == 'CLEAR_AREA':
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.ancho and 0 <= ny < self.alto:
                        if not (isinstance(self.grid[ny][nx], str) and
                                self.grid[ny][nx] in self.powerups):
                            self.grid[ny][nx] = 0

        elif efecto == 'CLEAR_ROW':
            for x in range(self.ancho):
                if not (isinstance(self.grid[gy][x], str) and
                        self.grid[gy][x] in self.powerups):
                    self.grid[gy][x] = 0

        elif efecto == 'SLOW_GRAVITY':
            self.tiempo_slow = 5.0
        elif efecto == 'INVINCIBLE':
            self.tiempo_invencible = 5.0

    def snake_spawn_jugador(self, accion):
        coords = accion['params'][0] if accion['params'] else [self.ancho // 2, self.alto // 2]
        self.serpiente_cuerpo = [(coords[0], coords[1])]
        self.serpiente_direccion = (1, 0)
        
    def snake_spawn_comida(self):
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) != getattr(self, 'posicion_veneno', None) and (x, y) != getattr(self, 'posicion_nube', None):
                self.posicion_comida = (x, y)
                break

    def snake_spawn_veneno(self):
        if not self.es_snake_evolved or self.nivel == 'BABY': return # En Baby no hay veneno
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) != getattr(self, 'posicion_comida', None):
                self.posicion_veneno = (x, y)
                break

    def snake_spawn_cloud(self):
        if not self.es_snake_evolved or self.nivel in ['BABY', 'ENTUSIASTA']: return # Solo en Nyan Cat
        while True:
            x, y = random.randint(0, self.ancho - 1), random.randint(0, self.alto - 1)
            if (x, y) not in self.serpiente_cuerpo and (x, y) != getattr(self, 'posicion_comida', None) and (x, y) != getattr(self, 'posicion_veneno', None):
                self.posicion_nube = (x, y)
                break

    def snake_mover_jugador(self):
        if not self.serpiente_cuerpo: return
        cabeza_x, cabeza_y = self.serpiente_cuerpo[0]
        dir_x, dir_y = self.serpiente_direccion
        nueva_cabeza = (cabeza_x + dir_x, cabeza_y + dir_y)

        # 1. Choque con pared (con Invencibilidad tipo Pac-Man en Evolved)
        if not (0 <= nueva_cabeza[0] < self.ancho and 0 <= nueva_cabeza[1] < self.alto):
            if self.es_snake_evolved and getattr(self, 'tiempo_invencible', 0) > 0:
                # Efecto Pac-Man: Atraviesa la pared y sale por el otro lado
                nueva_cabeza = (nueva_cabeza[0] % self.ancho, nueva_cabeza[1] % self.alto)
            else:
                self.ejecutar_evento('ON_COLLISION_WALL')
                return
            
        # 2. Recoger Power-Ups de la cuadrícula (solo en Evolved)
        if self.es_snake_evolved:
            celda = self.grid[nueva_cabeza[1]][nueva_cabeza[0]]
            if isinstance(celda, str) and celda in self.powerups:
                self.aplicar_efecto_powerup(celda, nueva_cabeza[0], nueva_cabeza[1])
                self.grid[nueva_cabeza[1]][nueva_cabeza[0]] = 0 # Borrar power-up del mapa
            
        # 3. Choque con su propio cuerpo (inmune si hay invencibilidad en Evolved)
        if nueva_cabeza in self.serpiente_cuerpo[:-1]:
            if not (self.es_snake_evolved and getattr(self, 'tiempo_invencible', 0) > 0):
                self.ejecutar_evento('ON_COLLISION_SELF')
                return

        self.serpiente_cuerpo.insert(0, nueva_cabeza)
        
        # 4. Comer entidades de Snake (Comida, Veneno y Nube)
        if nueva_cabeza == getattr(self, 'posicion_comida', None):
            self.ejecutar_evento('ON_EAT_FOOD')
            
        elif self.es_snake_evolved and nueva_cabeza == getattr(self, 'posicion_veneno', None):
            if getattr(self, 'tiempo_invencible', 0) > 0:
                self.serpiente_cuerpo.pop() # Eres invencible: Ignoras el veneno (pasas de largo)
            else:
                self.ejecutar_evento('ON_EAT_POISON')
                
        elif self.es_snake_evolved and nueva_cabeza == getattr(self, 'posicion_nube', None):
            if getattr(self, 'tiempo_invencible', 0) > 0:
                self.serpiente_cuerpo.pop() # Eres invencible: Ignoras la nube (pasas de largo)
            else:
                self.ejecutar_evento('ON_CLOUD_COLLISION') 
                self.snake_spawn_cloud() 
                
        else:
            self.serpiente_cuerpo.pop()
 
    def snake_cambiar_direccion(self, direccion):
        if direccion == 'UP' and self.serpiente_direccion[1] != 1:
            self.serpiente_direccion = (0, -1)
        elif direccion == 'DOWN' and self.serpiente_direccion[1] != -1:
            self.serpiente_direccion = (0, 1)
        elif direccion == 'LEFT' and self.serpiente_direccion[0] != 1:
            self.serpiente_direccion = (-1, 0)
        elif direccion == 'RIGHT' and self.serpiente_direccion[0] != -1:
            self.serpiente_direccion = (1, 0)

    def snake_crecer(self):
        pass

    def snake_encoger(self, accion=None):
        # Lee cuánto debe encoger según la regla (por defecto 1)
        cantidad = int(accion['params'][0]) if (accion and accion.get('params')) else 1
        
        # Eliminamos (cantidad + 1) elementos del cuerpo
        for _ in range(cantidad + 1):
            if len(self.serpiente_cuerpo) > 1:
                self.serpiente_cuerpo.pop()

    def snake_encoger_todo(self, accion=None):
        # Eliminamos todo el cuerpo excepto la cabeza
        while len(self.serpiente_cuerpo) > 1:
            self.serpiente_cuerpo.pop()
    # ------------------- LOGICA DE TANKS -------------------
    def tank_cambiar_direccion(self, direccion):
        if not self.jugador_posicion or self.juego_terminado:
            return

        nueva_pos = list(self.jugador_posicion)

        if direccion == 'ON_KEY_UP':
            self.tank_rotacion = 0
            self.tank_direccion = (0, -1)
            nueva_pos[1] -= 1
        elif direccion == 'ON_KEY_DOWN':
            self.tank_rotacion = 2
            self.tank_direccion = (0, 1)
            nueva_pos[1] += 1
        elif direccion == 'ON_KEY_LEFT':
            self.tank_rotacion = 3
            self.tank_direccion = (-1, 0)
            nueva_pos[0] -= 1
        elif direccion == 'ON_KEY_RIGHT':
            self.tank_rotacion = 1
            self.tank_direccion = (1, 0)
            nueva_pos[0] += 1
        elif direccion == 'ON_KEY_SPACE':
            self.tank_disparar(es_jugador=True)
            return

        # Evitar que la matriz 3x3 se salga del canvas
        nueva_pos[0] = max(0, min(self.ancho - 3, nueva_pos[0]))
        nueva_pos[1] = max(0, min(self.alto - 3, nueva_pos[1]))

        # Comprobar colisión con tanques enemigos vivos (no atravesar otros tanques)
        nx, ny = nueva_pos
        colision = False
        for enemigo in self.enemigos:
            if enemigo.get('vivo', True):
                ex, ey = enemigo['posicion']
                if abs(nx - ex) < 3 and abs(ny - ey) < 3:
                    colision = True
                    break

        # Comprobar colisión con muros
        if not colision and hasattr(self, 'muros_posiciones'):
            for ox in range(3):
                for oy in range(3):
                    if (nx + ox, ny + oy) in self.muros_posiciones:
                        colision = True
                        break
                if colision:
                    break

        if not colision:
            self.jugador_posicion = nueva_pos
            self.tank_verificar_recogida_martillo()

    @property
    def generic_enemy_posicion(self):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                return e['posicion']
        if self.enemigos:
            return self.enemigos[0]['posicion']
        return [0, 0]

    @generic_enemy_posicion.setter
    def generic_enemy_posicion(self, pos):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                e['posicion'] = pos
                return
        if self.enemigos:
            self.enemigos[0]['posicion'] = pos

    @property
    def enemy_tank_rotacion(self):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                return e['rotacion']
        return 2

    @enemy_tank_rotacion.setter
    def enemy_tank_rotacion(self, rot):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                e['rotacion'] = rot
                return

    @property
    def enemy_tank_direccion(self):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                return e['direccion']
        return (0, 1)

    @enemy_tank_direccion.setter
    def enemy_tank_direccion(self, d):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                e['direccion'] = d
                return

    @property
    def enemy_vivo(self):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                return e['vivo']
        return any(e['vivo'] for e in self.enemigos) if self.enemigos else True

    @enemy_vivo.setter
    def enemy_vivo(self, v):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                e['vivo'] = v
                return

    @property
    def enemy_salud(self):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                return e['salud']
        return 100

    @enemy_salud.setter
    def enemy_salud(self, s):
        for e in self.enemigos:
            if e['tipo'] == 'ENEMY_TANK_GENERIC':
                e['salud'] = s
                return

    def tank_disparar(self, es_jugador=True, enemigo=None):
        if es_jugador:
            if not self.jugador_posicion or self.juego_terminado:
                return
            # Si está en cooldown de recarga de 4 segundos
            if getattr(self, 'cooldown_recarga_jugador', 0.0) > 0.0:
                return
            # Si no le quedan balas
            if getattr(self, 'balas_restantes_jugador', 0) <= 0:
                self.cooldown_recarga_jugador = 4.0
                return
            ahora = time.time()
            if ahora - getattr(self, 'tiempo_ultimo_disparo_jugador', 0) < 0.15:
                return
            self.tiempo_ultimo_disparo_jugador = ahora

            base_x, base_y = self.jugador_posicion
            dx, dy = self.tank_direccion
            shape_tank = self.datos_juego.get('shapes', {}).get('PLAYER_TANK', {})
            damage = shape_tank.get('DAMAGE', 25)

            bx = base_x + 1 + dx
            by = base_y + 1 + dy
            self.balas_jugador.append({
                'x': bx,
                'y': by,
                'dx': dx,
                'dy': dy,
                'damage': damage,
                'color': '#00FF00'
            })

            # Reducir balas disponibles (máximo 5)
            self.balas_restantes_jugador -= 1
            if self.balas_restantes_jugador <= 0:
                self.cooldown_recarga_jugador = 4.0 # Inicia cooldown de 4 segundos
        else:
            if self.juego_terminado:
                return
            if enemigo is None:
                for e in self.enemigos:
                    if e.get('vivo', True):
                        enemigo = e
                        break
            if not enemigo or not enemigo.get('vivo', True):
                return

            base_x, base_y = enemigo['posicion']
            dx, dy = enemigo['direccion']
            damage = enemigo.get('damage', 20)
            color_bala = enemigo.get('color', '#FF4444')

            bx = base_x + 1 + dx
            by = base_y + 1 + dy
            self.balas_enemigos.append({
                'x': bx,
                'y': by,
                'dx': dx,
                'dy': dy,
                'damage': damage,
                'color': color_bala,
                'tipo_enemigo': enemigo['tipo'],
                'tirador': enemigo
            })

    def tank_mover_y_disparar_enemigo(self):
        if not self.jugador_posicion:
            return

        px, py = self.jugador_posicion

        for enemigo in self.enemigos:
            if not enemigo.get('vivo', True):
                if enemigo.get('tiempo_respawn', 0) > 0:
                    enemigo['tiempo_respawn'] -= 0.05
                    if enemigo['tiempo_respawn'] <= 0:
                        sp_x, sp_y = enemigo['spawn_pos']
                        bloqueado = False
                        if abs(sp_x - px) < 3 and abs(sp_y - py) < 3:
                            bloqueado = True
                        for otro in self.enemigos:
                            if otro is not enemigo and otro.get('vivo', True):
                                ox, oy = otro['posicion']
                                if abs(sp_x - ox) < 3 and abs(sp_y - oy) < 3:
                                    bloqueado = True
                                    break
                        if bloqueado:
                            enemigo['tiempo_respawn'] = 1.0
                            continue

                        enemigo['posicion'] = list(enemigo['spawn_pos'])
                        enemigo['rotacion'] = 2
                        enemigo['direccion'] = (0, 1)
                        enemigo['vivo'] = True
                        enemigo['salud'] = enemigo['salud_max']
                continue

            ex, ey = enemigo['posicion']

            # Movimiento acorde a su velocidad (SPEED)
            enemigo['timer_movimiento'] += 0.05
            # SPEED 20 -> 0.30s, SPEED 40 -> 0.15s
            intervalo = max(0.10, 6.0 / max(1, enemigo.get('speed', 20)))
            if enemigo['timer_movimiento'] >= intervalo:
                enemigo['timer_movimiento'] = 0
                dx = px - ex
                dy = py - ey

                opciones = []
                if abs(dx) > abs(dy):
                    opciones.append((1 if dx > 0 else -1, 0, 1 if dx > 0 else 3))
                    opciones.append((0, 1 if dy > 0 else -1, 2 if dy > 0 else 0))
                else:
                    opciones.append((0, 1 if dy > 0 else -1, 2 if dy > 0 else 0))
                    opciones.append((1 if dx > 0 else -1, 0, 1 if dx > 0 else 3))

                todas = [(0, -1, 0), (1, 0, 1), (0, 1, 2), (-1, 0, 3)]
                random.shuffle(todas)
                for o in todas:
                    if o not in opciones:
                        opciones.append(o)

                for mdx, mdy, mrot in opciones:
                    nx = ex + mdx
                    ny = ey + mdy

                    if not (0 <= nx <= self.ancho - 3 and 0 <= ny <= self.alto - 3):
                        continue

                    if abs(nx - px) < 3 and abs(ny - py) < 3:
                        continue

                    choca_otro = False
                    for otro in self.enemigos:
                        if otro is not enemigo and otro.get('vivo', True):
                            ox, oy = otro['posicion']
                            if abs(nx - ox) < 3 and abs(ny - oy) < 3:
                                choca_otro = True
                                break
                    if choca_otro:
                        continue

                    # Comprobar colisión con muros
                    choca_muro = False
                    if hasattr(self, 'muros_posiciones'):
                        for ox in range(3):
                            for oy in range(3):
                                if (nx + ox, ny + oy) in self.muros_posiciones:
                                    choca_muro = True
                                    break
                            if choca_muro:
                                break
                    if choca_muro:
                        continue

                    enemigo['posicion'] = [nx, ny]
                    enemigo['direccion'] = (mdx, mdy)
                    enemigo['rotacion'] = mrot
                    ex, ey = nx, ny
                    break

            # Disparo según alineación o cadencia
            enemigo['tiempo_ultimo_disparo'] += 0.05
            alineado = False
            edx, edy = enemigo['direccion']
            if abs(ex - px) <= 1:
                if py > ey and edy > 0:
                    alineado = True
                elif py < ey and edy < 0:
                    alineado = True
            elif abs(ey - py) <= 1:
                if px > ex and edx > 0:
                    alineado = True
                elif px < ex and edx < 0:
                    alineado = True

            cooldown_alineado = enemigo.get('cooldown_alineado', 0.8)
            if alineado and enemigo['tiempo_ultimo_disparo'] >= cooldown_alineado:
                self.tank_disparar(es_jugador=False, enemigo=enemigo)
                enemigo['tiempo_ultimo_disparo'] = 0
            elif enemigo['tiempo_ultimo_disparo'] >= enemigo.get('tiempo_entre_disparos', 1.5):
                self.tank_disparar(es_jugador=False, enemigo=enemigo)
                enemigo['tiempo_ultimo_disparo'] = 0

    def tank_actualizar_balas(self):
        # 1. Balas del jugador
        balas_j = []
        for bala in self.balas_jugador:
            bala['x'] += bala['dx']
            bala['y'] += bala['dy']
            bx, by = bala['x'], bala['y']

            if bx < 0 or bx >= self.ancho or by < 0 or by >= self.alto:
                continue

            # Impacto en cualquiera de los tanques enemigos vivos
            impacto = False
            for enemigo in self.enemigos:
                if not enemigo.get('vivo', True):
                    continue
                ex, ey = enemigo['posicion']
                if ex <= bx < ex + 3 and ey <= by < ey + 3:
                    enemigo['salud'] -= bala.get('damage', 25)
                    self.puntuacion += 10
                    if enemigo['salud'] <= 0:
                        enemigo['salud'] = 0
                        enemigo['vivo'] = False
                        # Puntuación según tipo: Strong (más) > Generic > Fast (menos)
                        if enemigo['tipo'] == 'ENEMY_TANK_STRONG':
                            self.puntuacion += 400
                        elif enemigo['tipo'] == 'ENEMY_TANK_GENERIC':
                            self.puntuacion += 200
                        elif enemigo['tipo'] == 'ENEMY_TANK_FAST':
                            self.puntuacion += 100
                        else:
                            self.puntuacion += 150
                        enemigo['tiempo_respawn'] = 4.0
                    impacto = True
                    break

            # Impacto en muros
            if not impacto and hasattr(self, 'muros_posiciones') and (bx, by) in self.muros_posiciones:
                muro = self.muros_posiciones[(bx, by)]
                muro['salud'] -= bala.get('damage', 25)
                if muro['salud'] <= 0:
                    self.destruir_muro(muro)
                    self.puntuacion += 5
                impacto = True

            if not impacto:
                balas_j.append(bala)

        self.balas_jugador = balas_j

        # 2. Balas enemigas
        balas_e = []
        for bala in self.balas_enemigos:
            bala['x'] += bala['dx']
            bala['y'] += bala['dy']
            bx, by = bala['x'], bala['y']

            if bx < 0 or bx >= self.ancho or by < 0 or by >= self.alto:
                continue

            impacto = False

            # Impacto en el jugador
            if self.jugador_posicion:
                px, py = self.jugador_posicion
                if px <= bx < px + 3 and py <= by < py + 3:
                    if getattr(self, 'tiempo_invencible_jugador', 0) <= 0:
                        self.jugador_salud -= bala.get('damage', 20)
                        if self.jugador_salud <= 0:
                            self.jugador_vidas -= 1
                            if self.jugador_vidas > 0:
                                # Reaparece en su esquina de origen con salud completa y 2s de gracia
                                self.jugador_salud = getattr(self, 'jugador_salud_max', 100)
                                self.jugador_posicion = list(getattr(self, 'jugador_spawn_pos', [self.ancho - 3, self.alto - 3]))
                                self.tank_direccion = (0, -1)
                                self.tank_rotacion = 0
                                self.tiempo_invencible_jugador = 2.0
                                self.balas_restantes_jugador = getattr(self, 'balas_max_jugador', 5)
                                self.cooldown_recarga_jugador = 0.0
                            else:
                                self.jugador_salud = 0
                                self.ejecutar_evento('ON_ZERO_HEALTH')
                                self.juego_terminado = True
                    impacto = True

            # Impacto en otros tanques enemigos (fuego cruzado: se pueden hacer daño entre ellos)
            if not impacto:
                tirador = bala.get('tirador')
                for otro in self.enemigos:
                    if otro is not tirador and otro.get('vivo', True):
                        ox, oy = otro['posicion']
                        if ox <= bx < ox + 3 and oy <= by < oy + 3:
                            otro['salud'] -= bala.get('damage', 20)
                            if otro['salud'] <= 0:
                                otro['salud'] = 0
                                otro['vivo'] = False
                                otro['tiempo_respawn'] = 4.0
                            impacto = True
                            break

            # Impacto en muros
            if not impacto and hasattr(self, 'muros_posiciones') and (bx, by) in self.muros_posiciones:
                muro = self.muros_posiciones[(bx, by)]
                muro['salud'] -= bala.get('damage', 20)
                if muro['salud'] <= 0:
                    self.destruir_muro(muro)
                impacto = True

            if not impacto:
                balas_e.append(bala)
        self.balas_enemigos = balas_e

        # 3. Colisión entre balas
        if self.balas_jugador and self.balas_enemigos:
            pos_e = {(b['x'], b['y']) for b in self.balas_enemigos}
            nuevas_j = []
            destruidas_e = set()
            for b in self.balas_jugador:
                pos = (b['x'], b['y'])
                if pos in pos_e:
                    destruidas_e.add(pos)
                else:
                    nuevas_j.append(b)
            self.balas_jugador = nuevas_j
            self.balas_enemigos = [b for b in self.balas_enemigos if (b['x'], b['y']) not in destruidas_e]

    def tank_actualizar(self):
        if getattr(self, 'tiempo_invencible_jugador', 0) > 0:
            self.tiempo_invencible_jugador -= 0.05
        if getattr(self, 'cooldown_recarga_jugador', 0.0) > 0.0:
            self.cooldown_recarga_jugador -= 0.05
            if self.cooldown_recarga_jugador <= 0.0:
                self.cooldown_recarga_jugador = 0.0
                self.balas_restantes_jugador = getattr(self, 'balas_max_jugador', 5)

        # Manejo del spawn y duración del martillo de curación
        if getattr(self, 'martillo_activo', False):
            self.timer_vida_martillo -= 0.05
            if self.timer_vida_martillo <= 0.0:
                self.martillo_activo = False
                self.posicion_martillo = None
                self.timer_spawn_martillo = getattr(self, 'intervalo_spawn_martillo', 15.0)
            else:
                self.tank_verificar_recogida_martillo()
        else:
            self.timer_spawn_martillo -= 0.05
            if self.timer_spawn_martillo <= 0.0:
                self.tank_spawnear_martillo()

        self.tank_mover_y_disparar_enemigo()
        self.tank_actualizar_balas()

    def tank_spawnear_jugador(self, accion):
        coords = accion['params'][0] if accion.get('params') else [self.ancho - 3, self.alto - 3]
        self.jugador_posicion = [coords[0], coords[1]]

        # Limitar al área de juego considerando el tamaño 3x3
        self.jugador_posicion[0] = max(0, min(self.ancho - 3, self.jugador_posicion[0]))
        self.jugador_posicion[1] = max(0, min(self.alto - 3, self.jugador_posicion[1]))
        self.jugador_spawn_pos = list(self.jugador_posicion)
        shape_tank = self.datos_juego.get('shapes', {}).get('PLAYER_TANK', {})
        self.jugador_salud_max = shape_tank.get('HEALTH', 100)
        self.jugador_salud = self.jugador_salud_max
        self.balas_max_jugador = 5
        self.balas_restantes_jugador = 5
        self.cooldown_recarga_jugador = 0.0

    def tank_spawnear_enemigo(self, tipo_enemigo, accion):
        coords = accion['params'][0] if accion.get('params') else [0, 0]
        if coords == 'RANDOM':
            coords = [random.randint(0, self.ancho - 3), random.randint(0, self.alto - 3)]
        else:
            coords = [max(0, min(self.ancho - 3, coords[0])), max(0, min(self.alto - 3, coords[1]))]

        shape_data = self.datos_juego.get('shapes', {}).get(tipo_enemigo, {})
        salud = shape_data.get('HEALTH', 100)
        damage = shape_data.get('DAMAGE', 20)
        speed = shape_data.get('SPEED', 20)
        color = shape_data.get('COLOR', '#ff0000')

        # Cadencia de tiro: speed tiene menor cadencia (dispara menos frecuente)
        if tipo_enemigo == 'ENEMY_TANK_FAST':
            cadencia = 2.8
            cooldown_alineado = 1.4
        elif tipo_enemigo == 'ENEMY_TANK_STRONG':
            cadencia = 2.0
            cooldown_alineado = 1.0
        else: # ENEMY_TANK_GENERIC
            cadencia = 1.5
            cooldown_alineado = 0.8

        enemigo_existente = None
        for e in self.enemigos:
            if e['tipo'] == tipo_enemigo:
                enemigo_existente = e
                break

        if enemigo_existente:
            enemigo_existente['posicion'] = list(coords)
            enemigo_existente['spawn_pos'] = list(coords)
            enemigo_existente['salud'] = salud
            enemigo_existente['salud_max'] = salud
            enemigo_existente['damage'] = damage
            enemigo_existente['speed'] = speed
            enemigo_existente['color'] = color
            enemigo_existente['vivo'] = True
            enemigo_existente['rotacion'] = 2
            enemigo_existente['direccion'] = (0, 1)
            enemigo_existente['tiempo_entre_disparos'] = cadencia
            enemigo_existente['cooldown_alineado'] = cooldown_alineado
        else:
            nuevo_enemigo = {
                'tipo': tipo_enemigo,
                'posicion': list(coords),
                'spawn_pos': list(coords),
                'direccion': (0, 1),
                'rotacion': 2,
                'salud': salud,
                'salud_max': salud,
                'damage': damage,
                'speed': speed,
                'color': color,
                'vivo': True,
                'tiempo_respawn': 0,
                'timer_movimiento': random.uniform(0, 0.1),
                'tiempo_ultimo_disparo': random.uniform(0, 1.0),
                'tiempo_entre_disparos': cadencia,
                'cooldown_alineado': cooldown_alineado
            }
            self.enemigos.append(nuevo_enemigo)

    def tank_spawnear_generic_tank(self, accion):
        self.tank_spawnear_enemigo('ENEMY_TANK_GENERIC', accion)

    def tank_spawnear_martillo(self, accion=None):
        coords = None
        if accion and accion.get('params') and accion['params'][0] != 'RANDOM':
            coords = list(accion['params'][0])
            coords[0] = max(0, min(self.ancho - 3, coords[0]))
            coords[1] = max(0, min(self.alto - 3, coords[1]))
        else:
            # Generar posición aleatoria que no solape con jugador ni enemigos vivos
            posibles = []
            for _ in range(50):
                rx = random.randint(1, max(1, self.ancho - 4))
                ry = random.randint(1, max(1, self.alto - 4))
                # Distancia mínima con el jugador
                if self.jugador_posicion:
                    if abs(rx - self.jugador_posicion[0]) < 4 and abs(ry - self.jugador_posicion[1]) < 4:
                        continue
                # Distancia mínima con enemigos vivos
                solapa_enemigo = False
                for e in getattr(self, 'enemigos', []):
                    if e.get('vivo', True):
                        ex, ey = e['posicion']
                        if abs(rx - ex) < 4 and abs(ry - ey) < 4:
                            solapa_enemigo = True
                            break
                if solapa_enemigo:
                    continue
                # Que no solape con muros
                solapa_muro = False
                if hasattr(self, 'muros_posiciones'):
                    for ox in range(3):
                        for oy in range(3):
                            if (rx + ox, ry + oy) in self.muros_posiciones:
                                solapa_muro = True
                                break
                        if solapa_muro:
                            break
                if solapa_muro:
                    continue
                posibles.append([rx, ry])
                break

            if posibles:
                coords = posibles[0]
            else:
                coords = [random.randint(1, max(1, self.ancho - 4)), random.randint(1, max(1, self.alto - 4))]

        self.posicion_martillo = coords
        self.martillo_activo = True
        self.timer_vida_martillo = getattr(self, 'duracion_vida_martillo', 12.0)

    def tank_verificar_recogida_martillo(self):
        if not getattr(self, 'martillo_activo', False) or not self.posicion_martillo or not self.jugador_posicion:
            return
        px, py = self.jugador_posicion
        hx, hy = self.posicion_martillo
        # Comprobar solapamiento 3x3 entre jugador y martillo
        if abs(px - hx) < 3 and abs(py - hy) < 3:
            self.martillo_activo = False
            self.posicion_martillo = None
            self.timer_spawn_martillo = getattr(self, 'intervalo_spawn_martillo', 15.0)
            self.timer_vida_martillo = 0.0
            salud_antes = self.jugador_salud
            self.ejecutar_evento('ON_GRAB_HAMMER')
            if self.jugador_salud == salud_antes and self.jugador_salud < getattr(self, 'jugador_salud_max', 100):
                self.jugador_salud = min(getattr(self, 'jugador_salud_max', 100), self.jugador_salud + 25)

    def agregar_muro(self, x, y, salud=50, color='#B85D19'):
        pos = (x, y)
        if pos in self.muros_posiciones:
            return
        muro = {
            'x': x,
            'y': y,
            'salud': salud,
            'salud_max': salud,
            'color': color
        }
        self.muros.append(muro)
        self.muros_posiciones[pos] = muro

    def destruir_muro(self, muro):
        pos = (muro['x'], muro['y'])
        if pos in self.muros_posiciones:
            del self.muros_posiciones[pos]
        if muro in self.muros:
            self.muros.remove(muro)

    def tank_spawnear_muro(self, accion=None):
        shape_wall = self.datos_juego.get('shapes', {}).get('WALL', {})
        salud = shape_wall.get('HEALTH', 50)
        color = shape_wall.get('COLOR') or shape_wall.get('color') or '#B85D19'

        if accion and accion.get('params') and accion['params']:
            coords = accion['params'][0]
            if coords != 'RANDOM':
                wx = max(0, min(self.ancho - 1, coords[0]))
                wy = max(0, min(self.alto - 1, coords[1]))
                self.agregar_muro(wx, wy, salud, color)
                return

        # Si no se especificaron coordenadas, generar mapa táctico de muros
        self.tank_generar_mapa_muros()

    def tank_generar_mapa_muros(self):
        shape_wall = self.datos_juego.get('shapes', {}).get('WALL', {})
        salud = shape_wall.get('HEALTH', 50)
        color = shape_wall.get('COLOR') or shape_wall.get('color') or '#B85D19'

        coords = set()

        # 1. Columnas defensivas en la izquierda (x=8, 9)
        for y in range(4, 9):
            coords.add((8, y))
            coords.add((9, y))
        for y in range(16, 21):
            coords.add((8, y))
            coords.add((9, y))

        # 2. Columnas defensivas en la derecha (x=30, 31)
        for y in range(4, 9):
            coords.add((30, y))
            coords.add((31, y))
        for y in range(16, 21):
            coords.add((30, y))
            coords.add((31, y))

        # 3. Barreras medias (x=14, 15 y x=24, 25)
        for y in range(7, 12):
            coords.add((14, y))
            coords.add((15, y))
            coords.add((24, y))
            coords.add((25, y))
        for y in range(13, 18):
            coords.add((14, y))
            coords.add((15, y))
            coords.add((24, y))
            coords.add((25, y))

        # 4. Búnker e islas centrales (x=19, 20)
        for y in range(4, 7):
            coords.add((19, y))
            coords.add((20, y))
        for y in range(10, 15):
            coords.add((19, y))
            coords.add((20, y))
        for y in range(18, 21):
            coords.add((19, y))
            coords.add((20, y))

        # 5. Muros protectores de cruce
        for x in range(3, 7):
            coords.add((x, 12))
            coords.add((39 - x, 12))

        for wx, wy in coords:
            self.agregar_muro(wx, wy, salud, color)




    # METODOS DE SALIDA (ADAPTADOS A GUI)
    # -----------------------------------

    def mostrar_game_over(self):
        # Muestra una ventana de mensaje de Tkinter
        tkMessageBox.showinfo("Juego Terminado", "Puntuacion Final: " + str(self.puntuacion))
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 runtime.py <archivo_juego.json>")
        sys.exit(1)
    archivo_juego = sys.argv[1]
    try:
        with open(archivo_juego, 'r') as f:
            datos_juego = json.load(f)
    except IOError:
        print("Error: No se pudo encontrar el archivo " + archivo_juego)
        sys.exit(1)
    juego = Juego(datos_juego)
    juego.run()
