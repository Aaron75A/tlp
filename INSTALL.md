=============================================================
      BrickScript: Requisitos de Instalación y Ejecución
=============================================================

Este documento describe el software necesario y los pasos para compilar y ejecutar los juegos creados con el lenguaje BrickScript.

-------------------------------------------------------------
## 1. Requisitos de Software
-------------------------------------------------------------

Este proyecto fue refactorizado para ejecutarse en entornos Linux (específicamente distribuciones basadas en Debian/Ubuntu) utilizando herramientas modernas, abandonando el soporte heredado de Python 2.

* **Sistema Operativo:** Ubuntu 20.04 o superior (y derivados).
* **Intérprete de Python:** Se requiere **Python 3**.
* **Dependencias de Sistema:** Es indispensable instalar la librería de interfaz gráfica nativa para Python 3.
  * Para instalarla, ejecuta en la terminal:
    sudo apt update
    sudo apt install python3-tk

-------------------------------------------------------------
## 2. Estructura de Archivos del Proyecto
-------------------------------------------------------------

Para que los scripts funcionen correctamente, los archivos deben estar organizados de la siguiente manera:

    ~/brickscript_project/
    |
    +--- compiler.py         (El compilador en Python 3 que traduce .brick a .json)
    +--- runtime.py          (El motor en Python 3 que ejecuta los juegos .json)
    +--- jugar.sh            (El script Bash para compilar y jugar fácilmente)
    +--- README.txt          (Información general del lenguaje)
    +--- INSTALL.txt         (Este archivo)
    |
    \--- games/
         +--- tetris.brick    (Código fuente del juego Tetris)
         +--- snake.brick     (Código fuente del juego Snake)
         \--- (Aquí se generarán los archivos .json)

-------------------------------------------------------------
## 3. Cómo Compilar y Ejecutar un Juego
-------------------------------------------------------------

La forma más sencilla de jugar en Linux es utilizando el script bash `jugar.sh`.

1.  **Abre la Terminal:**
    * Navega hasta la carpeta del proyecto. Por ejemplo:
      cd ~/Downloads/tlp

2.  **Otorga Permisos de Ejecución (Solo la primera vez):**
    * Ejecuta el siguiente comando para hacer el script ejecutable:
      chmod +x jugar.sh

3.  **Ejecuta el Script `jugar.sh`:**
    * Escribe `./jugar.sh` seguido del nombre del juego que deseas probar (sin la extensión `.brick`).

    * **Para jugar Snake:**
        ./jugar.sh snake

    * **Para jugar Tetris:**
        ./jugar.sh tetris

El script se encargará de llamar al **compilador** (`compiler.py`) para traducir el código `.brick` a un archivo `.json`. Si la compilación es exitosa, automáticamente ejecutará el **motor de juego** (`runtime.py`) con el archivo `.json` recién creado y lanzará la interfaz gráfica.

-------------------------------------------------------------
## 4. Solución de Problemas Comunes
-------------------------------------------------------------

* **Error: `ModuleNotFoundError: No module named 'tkinter'`**
    * **Causa:** El entorno de Python 3 no tiene instaladas las librerías gráficas de Tcl/Tk.
    * **Solución:** Ejecuta en la terminal: `sudo apt install python3-tk`

* **Error: `Permission denied` al ejecutar `./jugar.sh`**
    * **Causa:** El script no tiene permisos de ejecución asignados en el sistema de archivos.
    * **Solución:** Ejecuta `chmod +x jugar.sh` y vuelve a intentarlo.

* **El juego no compila y muestra "ERROR DE COMPILACION"**
    * **Causa:** Hay un error de sintaxis en el archivo `.brick` que modificaste.
    * **Solución:** Revisa cuidadosamente tu código `.brick` y compáralo con los ejemplos de `tetris.brick` y `snake.brick`. Asegúrate de que todas las palabras clave estén bien escritas y que los paréntesis y dos puntos estén en su lugar.
