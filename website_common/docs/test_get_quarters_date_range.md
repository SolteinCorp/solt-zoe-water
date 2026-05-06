# Casos de Prueba para `get_quarters_date_range`

## Descripción del Método

El método `get_quarters_date_range()` retorna un diccionario que mapea nombres de trimestres localizados a sus respectivos rangos de fechas de inicio y fin para el año actual en UTC.

**Firma del método:**
```python
def get_quarters_date_range() -> dict
```

**Retorna:**
```python
{
    _('Q1'): (start_datetime, end_datetime),
    _('Q2'): (start_datetime, end_datetime),
    _('Q3'): (start_datetime, end_datetime),
    _('Q4'): (start_datetime, end_datetime)
}
```

## Categorías de Casos de Prueba

### 1. Casos de Estructura y Validación Básica

| Caso de Prueba | Descripción | Objetivo |
|----------------|-------------|----------|
| `test_quarters_date_range_structure` | Verifica la estructura correcta del diccionario retornado | Validar que retorna dict con 4 trimestres, cada uno con tupla de 2 datetime |
| `test_quarters_return_type_consistency` | Verifica consistencia de tipos de retorno | Asegurar que siempre retorna tipos consistentes |

### 2. Casos de Años Específicos

| Caso de Prueba | Descripción | Entradas | Salidas Esperadas |
|----------------|-------------|----------|------------------|
| `test_quarters_date_range_normal_year_2023` | Prueba año normal (no bisiesto) | Mock year=2023 | Rangos correctos para 2023 |
| `test_quarters_date_range_leap_year_2024` | Prueba año bisiesto | Mock year=2024 | Q1 termina en Marzo 31 (no afectado por Feb 29) |
| `test_quarters_date_range_future_year_2030` | Prueba año futuro | Mock year=2030 | Todas las fechas en 2030 |
| `test_quarters_extreme_years` | Prueba años extremos | Mock years=[1900, 2100, 2200, 3000] | Manejo correcto de años extremos |

### 3. Casos de Años Bisiestos

| Caso de Prueba | Descripción | Objetivo |
|----------------|-------------|----------|
| `test_quarters_leap_year_february_impact` | Verifica que Feb bisiesto no afecte límites de trimestres | Q1 debe terminar en Mar 31 independientemente |
| `test_quarters_century_leap_years` | Prueba años centenarios no bisiestos (1900, 2100) | Validar manejo correcto de reglas bisiestas |
| `test_quarters_leap_year_date_arithmetic` | Aritmética de fechas en año bisiesto | Verificar días correctos: Q1=91, Q2=91, Q3=92, Q4=92 |

### 4. Casos de Límites y Precisión de Fechas

| Caso de Prueba | Descripción | Validaciones |
|----------------|-------------|-------------|
| `test_quarters_date_boundaries` | Límites exactos de trimestres | Q1: Ene 1-Mar 31, Q2: Abr 1-Jun 30, etc. |
| `test_quarters_no_gaps_or_overlaps` | Sin gaps entre trimestres | Fin de Q1 + 1 segundo = Inicio de Q2 |
| `test_quarters_datetime_precision` | Precisión de fechas | Inicio: 00:00:00.000, Fin: 23:59:59.000 |
| `test_quarters_microseconds_handling` | Manejo de microsegundos | Todos los microsegundos = 0 |
| `test_quarters_boundary_precision` | Precisión de límites de trimestre | Primer día del mes, último día correcto |

### 5. Casos de Zona Horaria

| Caso de Prueba | Descripción | Objetivo |
|----------------|-------------|----------|
| `test_quarters_timezone_consistency` | Consistencia de timezone UTC | Todos los datetime deben ser UTC |
| `test_quarters_different_timezones_mock` | Función retorna UTC independiente del sistema | Siempre UTC sin importar timezone local |
| `test_quarters_string_representation` | Representación string incluye timezone | Strings deben contener '+00:00' |

### 6. Casos de Cobertura Temporal

| Caso de Prueba | Descripción | Validaciones |
|----------------|-------------|-------------|
| `test_quarters_total_year_coverage` | Cobertura completa del año | Ene 1 - Dec 31, sin gaps |
| `test_quarters_year_boundary_edge_cases` | Casos límite de año | Q1 inicia Ene 1 00:00:00, Q4 termina Dec 31 23:59:59 |
| `test_quarters_february_handling` | Manejo correcto de Febrero | Feb no incluido en límites de trimestre |

### 7. Casos de Aritmética de Fechas

| Caso de Prueba | Descripción | Días Esperados |
|----------------|-------------|----------------|
| `test_quarters_date_arithmetic_validation` | Días por trimestre año normal | Q1=90, Q2=91, Q3=92, Q4=92 |
| `test_quarters_leap_year_date_arithmetic` | Días por trimestre año bisiesto | Q1=91, Q2=91, Q3=92, Q4=92 |

### 8. Casos de Lógica de Negocio

| Caso de Prueba | Descripción | Validación |
|----------------|-------------|------------|
| `test_quarters_business_logic_validation` | Trimestres fiscales estándar | Q1:Ene-Mar, Q2:Abr-Jun, Q3:Jul-Sep, Q4:Oct-Dec |
| `test_quarters_data_integrity` | Integridad entre múltiples llamadas | Orden cronológico consistente |

### 9. Casos de Rendimiento y Eficiencia

| Caso de Prueba | Descripción | Criterio de Éxito |
|----------------|-------------|------------------|
| `test_quarters_performance_multiple_calls` | Rendimiento de múltiples llamadas | 100 llamadas < 1 segundo |
| `test_quarters_memory_efficiency` | Eficiencia de memoria | No crecimiento significativo de objetos |
| `test_quarters_thread_safety` | Seguridad en concurrencia | Resultados consistentes en 10 threads |

### 10. Casos de Inmutabilidad y Pureza

| Caso de Prueba | Descripción | Objetivo |
|----------------|-------------|----------|
| `test_quarters_immutability` | Inmutabilidad de objetos datetime | Objetos separados en cada llamada |
| `test_quarters_datetime_immutability` | Modificaciones no afectan futuras llamadas | Función pura sin efectos secundarios |
| `test_quarters_function_purity` | Función pura | Múltiples llamadas dan resultados idénticos |

### 11. Casos de Consistencia y Estabilidad

| Caso de Prueba | Descripción | Validación |
|----------------|-------------|------------|
| `test_quarters_date_range_consistency_across_calls` | Consistencia entre llamadas | Mismo año produce mismo resultado |
| `test_quarters_iso_format_compliance` | Cumplimiento formato ISO | Conversión y parsing ISO exitoso |

### 12. Casos de Traducción e Internacionalización

| Caso de Prueba | Descripción | Validación |
|----------------|-------------|------------|
| `test_quarters_translation_keys` | Uso de claves de traducción | 4 claves válidas, no nulas |
| `test_quarters_translation_integration` | Integración con sistema de traducción Odoo | Claves no vacías |

### 13. Casos de Manejo de Errores

| Caso de Prueba | Descripción | Comportamiento Esperado |
|----------------|-------------|------------------------|
| `test_quarters_error_handling_invalid_year` | Años inválidos extremos | Manejo graceful o excepción controlada |

## Matriz de Cobertura de Escenarios

### Entradas Válidas
- ✅ Años normales (2023, 2025)
- ✅ Años bisiestos (2024, 2020)
- ✅ Años centenarios no bisiestos (1900, 2100)
- ✅ Años extremos (1, 3000)
- ✅ Años futuros (2030)

### Casos Límite
- ✅ Límites de trimestres
- ✅ Transiciones de mes
- ✅ Límites de año
- ✅ Precisión de tiempo (microsegundos)

### Casos Negativos/Edge Cases
- ✅ Años extremadamente tempranos
- ✅ Concurrencia
- ✅ Múltiples llamadas consecutivas
- ✅ Eficiencia de memoria

### Aspectos de Calidad
- ✅ Rendimiento
- ✅ Inmutabilidad
- ✅ Pureza funcional
- ✅ Consistencia de tipos
- ✅ Formato estándar (ISO)

## Instrucciones de Ejecución

### Con pytest (recomendado)
```bash
# Ejecutar todas las pruebas
python -m pytest website_common/tests/test_portal_controller.py -v

# Ejecutar prueba específica
python -m pytest website_common/tests/test_portal_controller.py::TestGetQuartersDateRange::test_quarters_date_range_structure -v

# Con cobertura
python -m pytest website_common/tests/test_portal_controller.py --cov=website_common.controllers.portal --cov-report=html
```

### Con unittest
```bash
# Ejecutar todas las pruebas
python -m unittest website_common.tests.test_portal_controller.TestGetQuartersDateRange

# Ejecutar prueba específica
python -m unittest website_common.tests.test_portal_controller.TestGetQuartersDateRange.test_quarters_date_range_structure
```

### En Odoo
```bash
# Ejecutar las pruebas en el contexto de Odoo
./odoo-bin -d test_db -i website_common --test-tags=TestGetQuartersDateRange --stop-after-init
```

## Métricas de Cobertura Esperadas

- **Cobertura de líneas**: 100%
- **Cobertura de ramas**: 100%
- **Cobertura de condiciones**: 100%
- **Casos de prueba**: 32
- **Tiempo de ejecución estimado**: < 2 segundos

## Dependencias de Pruebas

```python
# Dependencias requeridas
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
import threading
import queue
import time
import sys
```

## Configuración del Entorno de Pruebas

```python
def setUp(self):
    """Set up test fixtures."""
    super().setUp()
    self.maxDiff = None  # Para comparaciones detalladas
```

Este conjunto de pruebas garantiza que el método `get_quarters_date_range` funcione correctamente en todos los escenarios posibles, desde casos normales hasta situaciones extremas, manteniendo la calidad y confiabilidad del código en producción.
