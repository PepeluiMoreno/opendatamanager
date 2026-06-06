# El modelo, en una cara

*Mapa fijo para cuando la conversación corra más que nosotros. Cinco conceptos,
cinco párrafos.*

**Especie** (en el UI, *Fetcher*). Una tecnología de obtención de datos y su
vocabulario completo de parámetros: qué huecos existen, de qué tipo es cada
uno, cuáles son obligatorios y qué valor tienen por defecto. La especie no
sabe de fuentes concretas: "API REST" sabe pedir JSON y recorrer paginaciones,
no sabe qué es Aragón. Las definiciones de los parámetros pertenecen a la
especie y **nadie más las toca**.

**Variante**. Una implementación concreta de la tecnología de su especie, con
nombre: CKAN, Socrata, PLACSP CODICE. La variante **no añade ni cambia
parámetros: solo les pone valor** a algunos del vocabulario de su especie
(cabeceras, estrategia de paginación, mapa de campos). Ese valor actúa como
*default con autoridad*: rige si nadie lo pisa.

**Recurso**. Una fuente concreta: especie + variante (o "Genérico" si no hay
dialecto) + lo que falte por rellenar — típicamente la URL. La cadena de
resolución de cada parámetro es siempre la misma:
`default de la especie → valor de la variante → valor del recurso → ejecución`,
y cada capa pisa a la anterior. Un requerido no exige relleno al recurso si la
variante ya lo cubre: *requerido* describe el hueco, no quién lo llena.

**El árbol de decisiones**. Algunos parámetros son *controladores* (¿qué
paginación? ¿qué extracción?) y sus elecciones abren o cierran ramas de
parámetros dependientes. El árbol se ve **entero** al definir la especie
(modo Genérico, ramas anidadas bajo su controlador), **podado** al ver una
variante (solo las ramas que sus decisiones abren — por eso cambian los
contadores), y **recorrido** al crear el recurso (los parámetros se despliegan
según lo ya decidido, sin anotaciones de mecánica).

**El candado** (🔒). Por defecto, todo valor de variante es pisable por el
recurso mediante un gesto deliberado (*Sobrescribir*). Pero la variante puede
marcar parámetros como **inviolables** cuando son la esencia del dialecto y no
un ajuste: el `field_map` de PLACSP CODICE es el primero. Un valor con candado
no muestra botón de sobrescribir y la ejecución ignora cualquier intento de
pisarlo. Regla mnemotécnica: *ajustes pisables, esencias con candado*.
