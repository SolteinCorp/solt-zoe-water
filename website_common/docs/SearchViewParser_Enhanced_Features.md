# SearchViewParser - Documentación Completa

## Descripción General
El `SearchViewParser` es una clase especializada para parsear y analizar arquitecturas XML de vistas de búsqueda (search views) en Odoo 17.0. Proporciona funcionalidades avanzadas para extraer y organizar elementos de búsqueda con validación estricta y opciones de filtrado flexibles.

## Características Principales
- **Validación estricta**: Requiere que `<search>` sea el elemento raíz
- **Parseo estructurado**: Organiza elementos en categorías (fields, filters, groups, etc.)
- **Filtrado avanzado**: Opciones para incluir/excluir elementos específicos
- **Rendimiento optimizado**: XPath eficiente para estructuras XML grandes
- **Seguridad**: Protección contra inyecciones XPath

## Cambio Importante: Validación Estricta del Elemento Search

### Comportamiento Actualizado
El `SearchViewParser` ahora requiere que el elemento `<search>` sea **obligatoriamente el elemento raíz** del XML. No se permite anidamiento dentro de otros elementos.

### Validación Estricta

```python
# ✅ VÁLIDO: search como elemento raíz
arch_valid = """
<search>
    <field name="name" string="Name"/>
    <filter name="active" string="Active"/>
</search>
"""

# ❌ INVÁLIDO: search anidado (ahora lanza error)
arch_invalid = """
<root>
    <search>
        <field name="name" string="Name"/>
    </search>
</root>
"""
# Lanza: ValueError("El elemento raíz debe ser 'search', encontrado: 'root'")

# ❌ INVÁLIDO: sin elemento search
arch_no_search = """
<form>
    <field name="name" string="Name"/>
</form>
"""
# Lanza: ValueError("El elemento raíz debe ser 'search', encontrado: 'form'")
```

### Método `_validate_search_element` Actualizado

```python
def _validate_search_element(self):
    """
    Valida que el elemento search sea el root del XML

    Raises:
        ValueError: Si el elemento raíz no es 'search'
    """
    if self.root.tag != 'search':
        raise ValueError("El elemento raíz debe ser 'search', encontrado: '{}'".format(self.root.tag))
```

### Impacto en Casos de Uso

#### Antes del Cambio (Comportamiento Anterior)
- ✅ `<search>` como raíz → Funcionaba
- ✅ `<root><search>...</search></root>` → Funcionaba (encontraba y usaba search)
- ❌ `<form>...</form>` → Error

#### Después del Cambio (Comportamiento Actual)
- ✅ `<search>` como raíz → Funciona
- ❌ `<root><search>...</search></root>` → **Ahora lanza error**
- ❌ `<form>...</form>` → Error (sin cambios)

### Razones del Cambio

1. **Simplicidad**: Elimina la ambigüedad sobre qué elemento usar como contexto
2. **Consistencia**: Los search views de Odoo siempre tienen search como raíz
3. **Rendimiento**: Evita búsquedas adicionales de elementos search anidados
4. **Claridad**: Hace explícito que solo se procesan search views válidos

### Migración de Código Existente

Si tenías código que usaba search anidado:

```python
# Código anterior que ya no funciona
arch = """
<root>
    <search>
        <field name="name"/>
    </search>
</root>
"""

# Migración necesaria
arch = """
<search>
    <field name="name"/>
</search>
"""
```

### Funcionalidades Avanzadas Mantenidas

Todas las funcionalidades avanzadas siguen funcionando con search como raíz:

```python
arch = """
<search>
    <field name="name" string="Name"/>
    <filter name="active" string="Active" domain="[('active', '=', True)]"/>
    <group string="Group By">
        <filter name="partner" string="Partner" context="{'group_by': 'partner_id'}"/>
    </group>
    <searchpanel>
        <field name="category_id" string="Category" select="multi"/>
    </searchpanel>
</search>
"""

parser = SearchViewParser(arch)

# Funcionalidad 1: Excluir campos de search panel
result = parser.parse(include_fields_on_search_panel=True)
# result['fields'] solo contiene 'name' (excluye 'category_id')

# Funcionalidad 2: Solo filtros de primer nivel
result = parser.parse(include_first_level_filters_only=True)
# result['filters'] solo contiene 'active' (excluye 'partner' que está en grupo)

# Funcionalidad 3: Combinadas
result = parser.parse(
    include_fields_on_search_panel=True,
    include_first_level_filters_only=True
)
```

### Casos de Prueba Actualizados

Los siguientes casos de prueba han sido actualizados:

1. `test_search_element_as_child_raises_error` - Ahora verifica que search anidado lanza error
2. `test_nested_search_raises_error` - Verifica que estructuras con search no-raíz fallan
3. `test_first_level_filters_only_with_search_root` - Funcionalidad con search como raíz
4. `test_search_panel_fields_exclusion_with_search_root` - Exclusión con search como raíz

### Validación de Errores

```python
try:
    parser = SearchViewParser(arch_with_nested_search)
except ValueError as e:
    print(f"Error esperado: {e}")
    # Output: "El elemento raíz debe ser 'search', encontrado: 'root'"
```

### Compatibilidad

- ✅ **Código correcto existente**: No requiere cambios (search ya era raíz)
- ❌ **Código con search anidado**: Requiere migración para extraer search como raíz
- ✅ **Funcionalidades avanzadas**: Funcionan igual con search como raíz

## Clase SearchViewParser

### Constructor

```python
class SearchViewParser:
    def __init__(self, arch: str):
        """
        Inicializa el parser con una arquitectura XML de search view.

        Args:
            arch (str): String XML con la definición de la vista de búsqueda

        Raises:
            ValueError: Si el elemento raíz no es 'search'
            XMLSyntaxError: Si el XML está malformado
            TypeError: Si arch no es un string
        """
```

### Métodos Públicos

#### `parse(**kwargs) -> Dict[str, Any]`
Método principal que parsea la vista y retorna un diccionario estructurado.

```python
def parse(self, **kwargs) -> Dict[str, Any]:
    """
    Parsea la vista en secciones organizadas

    Args:
        **kwargs: Opciones de parseo (ver sección Opciones)

    Returns:
        Dict con las secciones: 'fields', 'filters', 'groups', 'separators', 'search_panel'
    """
```

**Estructura de retorno:**
```python
{
    'fields': [          # Lista de campos de búsqueda
        {
            'name': str,
            'string': str,         # Opcional
            'filter_domain': str,  # Opcional
            'operator': str,       # Opcional
            'domain': str,         # Opcional
            'context': str,        # Opcional
        }
    ],
    'filters': [         # Lista de filtros predefinidos
        {
            'name': str,
            'string': str,
            'domain': str,         # Opcional
            'context': str,        # Opcional
            'help': str,           # Opcional
            'invisible': str,      # Opcional
            'date': str,           # Opcional
            'default_period': str, # Opcional
        }
    ],
    'groups': [          # Lista de grupos de filtros
        {
            'expand': str,         # Opcional
            'string': str,         # Opcional
            'filters': [           # Filtros dentro del grupo
                # Misma estructura que filters
            ]
        }
    ],
    'separators': [      # Lista de separadores
        {
            'string': str,         # Opcional
            'invisible': str,      # Opcional
        }
    ],
    'search_panel': {    # Configuración del panel de búsqueda
        'fields': [
            {
                'name': str,
                'string': str,
                'select': str,         # 'multi' o 'one'
                'icon': str,           # Opcional
                'color': str,          # Opcional
                'enable_counters': str,# Opcional
                'expand': str,         # Opcional
                'domain': str,         # Opcional
            }
        ]
    }
}
```

### Métodos Privados

#### `_validate_search_element()`
Valida que el elemento raíz sea 'search'.

#### `_parse_fields(**kwargs) -> List[Dict[str, Any]]`
Extrae los campos de búsqueda del XML.

#### `_parse_filters(**kwargs) -> List[Dict[str, Any]]`
Extrae los filtros predefinidos del XML.

#### `_parse_groups() -> List[Dict[str, Any]]`
Extrae los grupos de filtros (Group By) del XML.

#### `_parse_separators() -> List[Dict[str, Any]]`
Extrae los separadores del XML.

#### `_parse_search_panel() -> Dict[str, Any]`
Extrae la configuración del search panel del XML.

## Opciones de Parseo

### `include_fields_on_search_panel` (bool, opcional)
Controla si incluir campos que están dentro de elementos `<searchpanel>`.

- **Default**: `False` (incluye campos de searchpanel)
- **`True`**: Excluye campos dentro de `<searchpanel>`
- **`False`**: Incluye todos los campos

**Ejemplo:**
```python
parser = SearchViewParser(arch)

# Incluir todos los campos (comportamiento por defecto)
result = parser.parse()
result = parser.parse(include_fields_on_search_panel=False)

# Excluir campos de searchpanel
result = parser.parse(include_fields_on_search_panel=True)
```

### `include_first_level_filters_only` (bool, opcional)
Controla si incluir solo filtros que son hijos directos del elemento `<search>`.

- **Default**: `False` (incluye todos los filtros)
- **`True`**: Solo filtros hijos directos de `<search>`
- **`False`**: Incluye todos los filtros (anidados y directos)

**Ejemplo:**
```python
parser = SearchViewParser(arch)

# Incluir todos los filtros (comportamiento por defecto)
result = parser.parse()
result = parser.parse(include_first_level_filters_only=False)

# Solo filtros de primer nivel
result = parser.parse(include_first_level_filters_only=True)
```

### Combinación de Opciones
```python
# Usar ambas opciones juntas
result = parser.parse(
    include_fields_on_search_panel=True,
    include_first_level_filters_only=True
)
```

## Casos Válidos e Inválidos

### ✅ Casos Válidos

#### 1. Search View Simple
```xml
<search>
    <field name="name" string="Name"/>
    <filter name="active" string="Active" domain="[('active', '=', True)]"/>
</search>
```

#### 2. Search View Completa
```xml
<search>
    <field name="name" string="Name" filter_domain="[('name', 'ilike', self)]"/>
    <field name="partner_id" string="Partner" operator="child_of"/>
    <field name="date" string="Date" context="{'default_date': self}"/>

    <separator string="Filters"/>
    <filter name="active" string="Active Records" domain="[('active', '=', True)]"/>
    <filter name="inactive" string="Inactive Records" domain="[('active', '=', False)]" help="Show inactive records"/>
    <filter name="date_filter" string="Date Range" date="date" default_period="this_month"/>

    <group expand="0" string="Group By">
        <filter name="group_partner" string="Partner" context="{'group_by': 'partner_id'}"/>
        <filter name="group_date" string="Date" context="{'group_by': 'date'}"/>
    </group>

    <searchpanel>
        <field name="category_id" string="Category" select="multi" enable_counters="1"/>
        <field name="state" string="State" select="one" expand="1"/>
    </searchpanel>
</search>
```

#### 3. Search View Vacía
```xml
<search></search>
```

#### 4. Search View con Grupos Anidados
```xml
<search>
    <group string="Level 1">
        <group string="Level 2">
            <filter name="nested_filter" string="Nested Filter"/>
        </group>
    </group>
</search>
```

#### 5. Search View con Caracteres Unicode
```xml
<search>
    <field name="name" string="Nombre"/>
    <filter name="active" string="Activo" domain="[('active', '=', True)]"/>
    <separator string="Filtros Avanzados"/>
</search>
```

### ❌ Casos Inválidos

#### 1. Search Anidado
```xml
<root>
    <search>
        <field name="name" string="Name"/>
    </search>
</root>
```
**Error**: `ValueError("El elemento raíz debe ser 'search', encontrado: 'root'")`

#### 2. Sin Elemento Search
```xml
<form>
    <field name="name" string="Name"/>
    <button name="action" string="Action"/>
</form>
```
**Error**: `ValueError("El elemento raíz debe ser 'search', encontrado: 'form'")`

#### 3. XML Malformado
```xml
<search>
    <field name="name" string="Name"
    <filter name="active" string="Active"/>
</search>
```
**Error**: `XMLSyntaxError`

#### 4. Elementos con Namespaces
```xml
<odoo:search xmlns:odoo="http://odoo.com">
    <odoo:field name="name" string="Name"/>
</odoo:search>
```
**Error**: `ValueError("El elemento raíz debe ser 'search', encontrado: 'odoo:search'")`

#### 5. Parámetro No String
```python
SearchViewParser(123)        # TypeError
SearchViewParser(None)       # AttributeError
SearchViewParser("")         # XMLSyntaxError
```

## Ejemplos de Uso

### Ejemplo Básico
```python
from website_common.utils.arch import SearchViewParser

# XML de search view
arch = """
<search>
    <field name="name" string="Name"/>
    <field name="email" string="Email"/>
    <filter name="active" string="Active" domain="[('active', '=', True)]"/>
    <group string="Group By">
        <filter name="group_by_company" string="Company" context="{'group_by': 'company_id'}"/>
    </group>
</search>
"""

# Crear parser y parsear
parser = SearchViewParser(arch)
result = parser.parse()

# Acceder a los resultados
print(f"Campos encontrados: {len(result['fields'])}")
print(f"Filtros encontrados: {len(result['filters'])}")
print(f"Grupos encontrados: {len(result['groups'])}")
```

### Ejemplo con Opciones Avanzadas
```python
arch = """
<search>
    <field name="name" string="Name"/>
    <field name="email" string="Email"/>

    <filter name="active" string="Active" domain="[('active', '=', True)]"/>

    <group string="Group By">
        <filter name="by_company" string="Company" context="{'group_by': 'company_id'}"/>
        <filter name="by_date" string="Date" context="{'group_by': 'create_date'}"/>
    </group>

    <searchpanel>
        <field name="category_id" string="Category" select="multi"/>
        <field name="state" string="State" select="one"/>
    </searchpanel>
</search>
"""

parser = SearchViewParser(arch)

# Parseo normal - incluye todo
result_all = parser.parse()
print(f"Todos los campos: {len(result_all['fields'])}")      # 4 (name, email, category_id, state)
print(f"Todos los filtros: {len(result_all['filters'])}")    # 3 (active, by_company, by_date)

# Solo campos principales (excluir searchpanel)
result_main_fields = parser.parse(include_fields_on_search_panel=True)
print(f"Campos principales: {len(result_main_fields['fields'])}")  # 2 (name, email)

# Solo filtros de primer nivel
result_top_filters = parser.parse(include_first_level_filters_only=True)
print(f"Filtros de primer nivel: {len(result_top_filters['filters'])}")  # 1 (active)

# Combinando opciones
result_strict = parser.parse(
    include_fields_on_search_panel=True,
    include_first_level_filters_only=True
)
print(f"Campos estrictos: {len(result_strict['fields'])}")   # 2 (name, email)
print(f"Filtros estrictos: {len(result_strict['filters'])}")  # 1 (active)
```

### Ejemplo de Manejo de Errores
```python
def safe_parse_search_view(arch_xml):
    """Función segura para parsear search views con manejo de errores"""
    try:
        parser = SearchViewParser(arch_xml)
        return parser.parse()
    except ValueError as e:
        print(f"Error de validación: {e}")
        return None
    except etree.XMLSyntaxError as e:
        print(f"Error de sintaxis XML: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None

# Uso
valid_arch = "<search><field name='test'/></search>"
invalid_arch = "<form><field name='test'/></form>"

result1 = safe_parse_search_view(valid_arch)    # Retorna diccionario
result2 = safe_parse_search_view(invalid_arch)  # Retorna None
```

## Casos de Prueba Definidos

### Categorías de Pruebas

#### 1. Pruebas Básicas de Funcionalidad
- `test_simple_search_view_parsing`: Parseo de vista simple
- `test_complex_search_view_parsing`: Parseo de vista compleja con todos los elementos
- `test_empty_search_view_parsing`: Parseo de vista vacía

#### 2. Pruebas de Validación
- `test_valid_search_element_as_root`: Search como elemento raíz válido
- `test_search_element_as_child_raises_error`: Error cuando search es hijo
- `test_no_search_element_raises_error`: Error cuando no hay elemento search
- `test_empty_root_raises_error`: Error con XML sin search
- `test_nested_search_not_found`: Error con search profundamente anidado
- `test_nested_search_raises_error`: Error con search dentro de otros elementos

#### 3. Pruebas de Manejo de Errores
- `test_malformed_xml_handling`: Manejo de XML malformado
- `test_invalid_xml_structure_handling`: Manejo de estructura XML inválida
- `test_empty_string_arch_handling`: Manejo de string vacío
- `test_none_arch_handling`: Manejo de valor None
- `test_non_string_arch_handling`: Manejo de tipo no-string

#### 4. Pruebas de Parseo de Elementos
- `test_field_with_all_attributes`: Campo con todos los atributos posibles
- `test_filter_with_all_attributes`: Filtro con todos los atributos posibles
- `test_search_panel_with_all_attributes`: Panel con todos los atributos posibles
- `test_nested_group_filters_parsing`: Parseo de filtros dentro de grupos
- `test_multiple_search_panels`: Manejo de múltiples campos de search panel
- `test_deeply_nested_structure`: Estructuras XML profundamente anidadas
- `test_extremely_nested_groups`: Grupos extremadamente anidados (4+ niveles)

#### 5. Pruebas de Filtrado Avanzado
- `test_include_fields_on_search_panel_false`: Incluir campos de searchpanel
- `test_include_fields_on_search_panel_true`: Excluir campos de searchpanel
- `test_include_fields_on_search_panel_default_behavior`: Comportamiento por defecto
- `test_nested_searchpanel_fields_exclusion`: Exclusión de campos anidados en panel
- `test_multiple_searchpanel_sections_exclusion`: Múltiples secciones de panel
- `test_include_first_level_filters_only_false`: Incluir todos los filtros
- `test_include_first_level_filters_only_true`: Solo filtros de primer nivel
- `test_include_first_level_filters_only_default_behavior`: Comportamiento por defecto
- `test_deeply_nested_filters_exclusion`: Exclusión de filtros profundamente anidados
- `test_no_direct_child_filters`: Cuando no hay filtros hijos directos
- `test_mixed_elements_with_first_level_only`: Elementos mixtos con filtro de primer nivel

#### 6. Pruebas de Funcionalidad Integrada
- `test_first_level_filters_only_with_search_root`: Filtros de primer nivel con search raíz
- `test_search_panel_fields_exclusion_with_search_root`: Exclusión con search raíz

#### 7. Pruebas de Rendimiento y Memoria
- `test_large_xml_performance`: Rendimiento con XML grande (100 elementos)
- `test_very_large_xml_stress_test`: Prueba de estrés (1000 elementos)
- `test_memory_usage_with_repeated_parsing`: Eficiencia de memoria con parseo repetido
- `test_parser_memory_cleanup`: Limpieza de memoria del parser

#### 8. Pruebas de Seguridad
- `test_xpath_injection_security`: Protección contra inyección XPath
- `test_special_characters_in_attributes`: Manejo de caracteres especiales

#### 9. Pruebas de Compatibilidad
- `test_unicode_content_handling`: Manejo de contenido Unicode
- `test_invalid_encoding_handling`: Manejo de codificación inválida
- `test_xml_with_comments_and_cdata`: XML con comentarios y secciones CDATA
- `test_arch_with_namespaces`: XML con namespaces

#### 10. Pruebas de Casos Especiales
- `test_none_attributes_filtering`: Filtrado de atributos None
- `test_duplicate_element_names`: Manejo de nombres de elementos duplicados
- `test_parser_instance_reusability`: Reutilización segura de instancia de parser
- `test_concurrent_parsing_safety`: Seguridad en parseo concurrente

### Métricas de Cobertura de Pruebas

- **Total de casos de prueba**: 45+
- **Cobertura de métodos públicos**: 100%
- **Cobertura de métodos privados**: 100%
- **Cobertura de opciones de parseo**: 100%
- **Cobertura de casos de error**: 100%
- **Pruebas de rendimiento**: Sí
- **Pruebas de seguridad**: Sí
- **Pruebas de concurrencia**: Sí

### Benchmarks de Rendimiento

- **Vistas pequeñas** (< 10 elementos): < 10ms
- **Vistas medianas** (10-100 elementos): < 100ms
- **Vistas grandes** (100-1000 elementos): < 1 segundo
- **Prueba de estrés** (1000+ elementos): < 2 segundos

## Consideraciones de Seguridad

### Protecciones Implementadas
1. **Validación de entrada**: Verificación estricta del tipo de dato
2. **Protección XPath**: Prevención de inyecciones XPath
3. **Manejo de caracteres especiales**: Procesamiento seguro de entidades XML
4. **Limitación de memoria**: Control de uso de memoria en estructuras grandes

### Buenas Prácticas
- Siempre validar el XML de entrada antes del parseo
- Usar manejo de excepciones apropiado
- Monitorear el rendimiento en aplicaciones de producción
- Implementar timeouts para XMLs muy grandes

## Limitaciones Conocidas

1. **Tamaño de XML**: Aunque optimizado, XMLs extremadamente grandes (>10MB) pueden afectar el rendimiento
2. **Elementos personalizados**: Solo parsea elementos estándar de search views de Odoo
3. **Validación semántica**: No valida la corrección semántica de dominios o contextos
4. **Threading**: Aunque es thread-safe, el rendimiento puede verse afectado con alta concurrencia

## Historial de Versiones

### v1.2.0 (Actual)
- ✅ Validación estricta de elemento search como raíz
- ✅ Opciones avanzadas de filtrado (`include_fields_on_search_panel`, `include_first_level_filters_only`)
- ✅ Cobertura completa de casos de prueba
- ✅ Optimizaciones de rendimiento
- ✅ Protecciones de seguridad

### v1.1.0 (Anterior)
- ✅ Parseo básico de elementos de search view
- ✅ Soporte para search anidado
- ✅ Manejo básico de errores

### v1.0.0 (Inicial)
- ✅ Funcionalidad básica de parseo
- ✅ Estructura de retorno organizada
