"""Base de conocimiento vectorial — CODEFEST AD ASTRA 2026, Etapa 1.

Este módulo se ejecuta antes que cualquier otro del paquete, y por eso aquí se
resuelve el conflicto de OpenMP entre faiss y torch (ver abajo). No añadir
imports pesados: `generador.py` depende de que esto corra primero.
"""

import os

# faiss-cpu y torch empaquetan cada uno su propia copia de libomp.dylib. Al
# cargar las dos en el mismo proceso, la segunda aborta el intérprete con
# "OMP: Error #15", sin importar el orden de importación. Como generador.py
# codifica las consultas con torch y luego busca con faiss, se topa con esto
# de lleno: el arreglo tiene que viajar dentro de la entrega y no depender del
# entorno de quien la ejecute.
#
# La variable permite que convivan las dos copias, pero por sí sola NO basta:
# solo silencia el aviso, y los dos runtimes siguen levantando cada uno su pool
# de hilos hasta que el segundo aborta el proceso con SIGSEGV. La otra mitad del
# arreglo está en `index_build.limitar_hilos_openmp()`, que deja a faiss y a
# torch con un hilo cada uno. Hacen falta las dos.
# Verificado contra numpy puro sobre los 91.088 vectores de e5_large: los IDs
# recuperados coinciden salvo empates con diferencia de puntuación <= 1e-4, y
# las puntuaciones ordenadas coinciden a 1e-5.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
