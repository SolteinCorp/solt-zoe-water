# Casos de Prueba para `get_n_years_date_range`

## Análisis del Método

### Descripción
El método `get_n_years_date_range()` genera un diccionario que mapea años (como strings) a tuplas de fechas de inicio y fin en UTC. Incluye el año de referencia y retrocede N años adicionales.

**Firma:**
```python
def get_n_years_date_range(reference_date: datetime, count: int = 1) -> dict
```

**Lógica del método:**
1. Asegura que `count` sea al menos 1 usando `max(count, 1)`
2. Incluye el año de la fecha de referencia
3. Incluye los N años previos al año de referencia
4. Cada año mapea a una tupla: (1 enero 00:00:00 UTC, 31 diciembre 23:59:59 UTC)

---

## Matriz Completa de Casos de Prueba

### 1. Casos Positivos (Entradas Válidas)

| ID | Caso de Prueba | Entrada `reference_date` | Entrada `count` | Años Esperados | Comportamiento Esperado |
|----|----------------|-------------------------|-----------------|----------------|------------------------|
| P1 | Valor por defecto | 2024-06-15 12:30:45 UTC | (default=1) | ['2024', '2023'] | Incluye año actual + 1 año previo |
| P2 | Count explícito 1 | 2024-06-15 12:30:45 UTC | 1 | ['2024', '2023'] | Igual que P1 |
| P3 | Count = 2 | 2024-06-15 12:30:45 UTC | 2 | ['2024', '2023', '2022'] | Año actual + 2 años previos |
| P4 | Count = 5 | 2024-06-15 12:30:45 UTC | 5 | ['2024', '2023', '2022', '2021', '2020', '2019'] | Año actual + 5 años previos |
| P5 | Count = 10 | 2024-06-15 12:30:45 UTC | 10 | 2024 a 2014 (11 años) | Año actual + 10 años previos |
| P6 | Count grande (50) | 2024-06-15 12:30:45 UTC | 50 | 2024 a 1974 (51 años) | Manejo eficiente de rangos grandes |

### 2. Casos Límite (Edge Cases)

| ID | Caso de Prueba | Entrada `reference_date` | Entrada `count` | Años Esperados | Comportamiento Esperado |
|----|----------------|-------------------------|-----------------|----------------|------------------------|
| E1 | Count = 0 | 2024-06-15 12:30:45 UTC | 0 | ['2024', '2023'] | Se trata como count=1 (max(count, 1)) |
| E2 | Count negativo | 2024-06-15 12:30:45 UTC | -5 | ['2024', '2023'] | Se trata como count=1 (max(count, 1)) |
| E3 | Inicio de año | 2025-01-01 00:00:00 UTC | 2 | ['2025', '2024', '2023'] | Manejo correcto de límites de año |
| E4 | Fin de año | 2024-12-31 23:59:59 UTC | 1 | ['2024', '2023'] | Sin afectar por hora específica |
| E5 | Año bisiesto ref | 2024-02-29 10:00:00 UTC | 1 | ['2024', '2023'] | Límites correctos independiente de día bisiesto |
| E6 | Múltiples bisiestos | 2024-01-01 00:00:00 UTC | 8 | 2024 a 2016 | Incluye 2024, 2020, 2016 (años bisiestos) |

### 3. Casos de Precisión y Formato

| ID | Caso de Prueba | Validación | Comportamiento Esperado |
|----|----------------|------------|------------------------|
| F1 | Zona horaria | Todas las fechas | Siempre UTC (tzinfo=timezone.utc) |
| F2 | Precisión inicio | Fecha inicio de cada año | 1 enero 00:00:00.000000 UTC |
| F3 | Precisión fin | Fecha fin de cada año | 31 diciembre 23:59:59.000000 UTC |
| F4 | Estructura retorno | Tipo de datos | dict con claves str y valores tuple(datetime, datetime) |
| F5 | Orden cronológico | Relación entre años | Años consecutivos decrecientes (2024, 2023, 2022...) |
| F6 | Inmutabilidad | Múltiples llamadas | Objetos datetime separados en cada llamada |

### 4. Casos de Independencia de Entrada

| ID | Caso de Prueba | Entrada `reference_date` | Entrada `count` | Validación |
|----|----------------|-------------------------|-----------------|------------|
| I1 | Independencia hora | 2024-06-15 08:00:00 vs 20:00:00 vs 00:00:00 | 2 | Resultados idénticos |
| I2 | Independencia mes/día | 2024-01-01 vs 2024-06-15 vs 2024-12-31 | 2 | Resultados idénticos |
| I3 | Count como float | 2024-06-15 12:30:45 UTC | 2.5 | Se trata como int(2), retorna 3 años |

### 5. Casos Negativos (Manejo de Errores)

| ID | Caso de Prueba | Entrada `reference_date` | Entrada `count` | Excepción Esperada | Descripción |
|----|----------------|-------------------------|-----------------|-------------------|-------------|
| N1 | reference_date string | "not a date" | 1 | TypeError/AttributeError | Tipo inválido para reference_date |
| N2 | reference_date None | None | 1 | TypeError/AttributeError | reference_date nulo |
| N3 | count string | 2024-06-15 12:30:45 UTC | "invalid" | TypeError | Tipo inválido para count |

### 6. Casos de Rendimiento

| ID | Caso de Prueba | Entrada | Criterio de Éxito |
|----|----------------|---------|------------------|
| R1 | Count grande (100) | count=100 | Ejecución < 1 segundo |
| R2 | Consistencia | Múltiples llamadas idénticas | Resultados iguales |
| R3 | Memoria | 50 llamadas consecutivas | Sin crecimiento excesivo de memoria |

### 7. Casos de Años Extremos

| ID | Caso de Prueba | Entrada `reference_date` | Entrada `count` | Años Esperados | |
|----|----------------|-------------------------|-----------------|----------------|-------------|
| X1 | Pasado lejano | 1900-01-01 00:00:00 UTC | 5 | ['1900', '1899', '1898', '1897', '1896', '1895'] | Manejo de años históricos |
| X2 | Futuro lejano | 3000-01-01 00:00:00 UTC | 2 | ['3000', '2999', '2998'] | Manejo de años futuros |

---

## Implementación con pytest y Odoo

### Configuración de pytest.ini
```ini
[tool:pytest]
testpaths = website_common/tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = -v --tb=short
markers =
    get_n_years_date_range: Tests for get_n_years_date_range function
    slow: Marks tests as slow
```

### Ejemplo de Ejecución con pytest

```bash
# Ejecutar todas las pruebas del método
pytest website_common/tests/test_get_n_years_date_range.py -v

# Ejecutar casos específicos
pytest website_common/tests/test_get_n_years_date_range.py::TestGetNYearsDateRange::test_count_five_years -v

# Ejecutar con marcadores
pytest -m "get_n_years_date_range" -v

# Con cobertura
pytest website_common/tests/test_get_n_years_date_range.py --cov=website_common.controllers.portal --cov-report=html
```

### Ejemplo de Ejecución con Odoo

```bash
# Ejecutar con el runner de Odoo
./odoo-bin -d test_db -i website_common --test-tags=get_n_years_date_range --stop-after-init

# Con logging detallado
./odoo-bin -d test_db -i website_common --test-tags=get_n_years_date_range --log-level=test --stop-after-init
```

### Casos de Prueba Parametrizados con pytest

```python
import pytest
from datetime import datetime, timezone
from odoo.addons.website_common.controllers.portal import get_n_years_date_range

@pytest.mark.parametrize("count,expected_length", [
    (1, 2),    # Año actual + 1 previo
    (2, 3),    # Año actual + 2 previos
    (5, 6),    # Año actual + 5 previos
    (10, 11),  # Año actual + 10 previos
])
def test_count_variations(count, expected_length):
    """Test various count values produce correct number of years."""
    ref_date = datetime(2024, 6, 15, tzinfo=timezone.utc)
    result = get_n_years_date_range(ref_date, count)
    assert len(result) == expected_length

@pytest.mark.parametrize("ref_date", [
    datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),      # Inicio año
    datetime(2024, 6, 15, 12, 30, 45, tzinfo=timezone.utc),  # Medio año
    datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc), # Fin año
])
def test_reference_date_independence(ref_date):
    """Test that different times within same year produce identical results."""
    result = get_n_years_date_range(ref_date, count=2)
    expected_years = {'2024', '2023', '2022'}
    assert set(result.keys()) == expected_years

@pytest.mark.parametrize("count,expected_count", [
    (0, 1),     # 0 se trata como 1
    (-1, 1),    # Negativo se trata como 1
    (-10, 1),   # Negativo grande se trata como 1
])
def test_count_edge_cases(count, expected_count):
    """Test edge cases for count parameter."""
    ref_date = datetime(2024, 6, 15, tzinfo=timezone.utc)
    result = get_n_years_date_range(ref_date, count)
    assert len(result) == expected_count + 1  # +1 por el año actual
```

---

## Validaciones de Calidad

### Cobertura de Código Esperada
- **Líneas**: 100%
- **Ramas**: 100%
- **Funciones**: 100%

### Métricas de Rendimiento
- **100 años**: < 1 segundo
- **Memoria**: Sin crecimiento significativo en múltiples llamadas
- **Consistencia**: Mismos inputs = mismos outputs

### Validaciones de Salida
1. **Estructura**: `dict[str, tuple[datetime, datetime]]`
2. **Claves**: Strings de 4 dígitos (años)
3. **Valores**: Tuplas con 2 datetime objects
4. **Timezone**: Siempre UTC
5. **Precisión**: Sin microsegundos
6. **Orden**: Cronológico decreciente

Este conjunto de casos de prueba asegura que el método `get_n_years_date_range` es robusto, eficiente y maneja correctamente todos los escenarios posibles en un entorno de producción de Odoo 17.0.
