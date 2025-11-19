#!/bin/bash
# Script de verificación rápida del módulo xtendoo_pos_order
# Uso: bash check_module.sh

set -e

MODULE_PATH="/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_order"

echo "=========================================="
echo "  VERIFICACIÓN XTENDOO_POS_ORDER"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contador de errores
ERRORS=0

# Función para verificar archivo
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
    else
        echo -e "${RED}✗${NC} $1 - NO ENCONTRADO"
        ERRORS=$((ERRORS + 1))
    fi
}

# Función para verificar sintaxis Python
check_python() {
    if python3 -m py_compile "$1" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} Sintaxis Python: $1"
    else
        echo -e "${RED}✗${NC} Error de sintaxis en: $1"
        ERRORS=$((ERRORS + 1))
    fi
}

# Función para verificar sintaxis XML
check_xml() {
    if command -v xmllint &> /dev/null; then
        if xmllint --noout "$1" 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Sintaxis XML: $1"
        else
            echo -e "${RED}✗${NC} Error de sintaxis en: $1"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${YELLOW}⚠${NC} xmllint no disponible, omitiendo verificación XML"
    fi
}

cd "$MODULE_PATH"

echo "1. VERIFICANDO ESTRUCTURA DE ARCHIVOS"
echo "--------------------------------------"

# Archivos principales
check_file "__init__.py"
check_file "__manifest__.py"
check_file "hooks.py"
check_file "README.md"
check_file "LICENSE"

# Modelos
check_file "models/__init__.py"
check_file "models/pos_config.py"
check_file "models/pos_order.py"
check_file "models/pos_order_line.py"

# Vistas
check_file "views/pos_config_view.xml"
check_file "views/pos_order_view.xml"

# Seguridad
check_file "security/ir.model.access.csv"

# Tests
check_file "tests/__init__.py"
check_file "tests/test_pos_order_backend.py"

# Demo
check_file "demo/pos_config_demo.xml"

# Documentación
check_file "INSTALL.md"
check_file "QUICKSTART.md"
check_file "SUMMARY.md"
check_file "CHANGELOG.md"
check_file "VERIFICATION.md"

echo ""
echo "2. VERIFICANDO SINTAXIS PYTHON"
echo "--------------------------------------"

check_python "__init__.py"
check_python "hooks.py"
check_python "models/__init__.py"
check_python "models/pos_config.py"
check_python "models/pos_order.py"
check_python "models/pos_order_line.py"
check_python "tests/__init__.py"
check_python "tests/test_pos_order_backend.py"

echo ""
echo "3. VERIFICANDO SINTAXIS XML"
echo "--------------------------------------"

check_xml "views/pos_config_view.xml"
check_xml "views/pos_order_view.xml"
check_xml "demo/pos_config_demo.xml"

echo ""
echo "4. VERIFICANDO CONTENIDO DEL MANIFEST"
echo "--------------------------------------"

if grep -q "xtendoo_pos_order" "__manifest__.py"; then
    echo -e "${GREEN}✓${NC} Nombre del módulo correcto"
else
    echo -e "${RED}✗${NC} Error en nombre del módulo"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "19.0" "__manifest__.py"; then
    echo -e "${GREEN}✓${NC} Versión Odoo correcta (19.0)"
else
    echo -e "${RED}✗${NC} Error en versión de Odoo"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "point_of_sale" "__manifest__.py"; then
    echo -e "${GREEN}✓${NC} Dependencia point_of_sale declarada"
else
    echo -e "${RED}✗${NC} Falta dependencia point_of_sale"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "post_init_hook" "__manifest__.py"; then
    echo -e "${GREEN}✓${NC} Hook post_init_hook declarado"
else
    echo -e "${YELLOW}⚠${NC} Hook post_init_hook no declarado"
fi

echo ""
echo "5. ESTADÍSTICAS DEL MÓDULO"
echo "--------------------------------------"

PY_FILES=$(find . -name "*.py" -not -path "./__pycache__/*" | wc -l)
XML_FILES=$(find . -name "*.xml" | wc -l)
MD_FILES=$(find . -name "*.md" | wc -l)

echo "Archivos Python: $PY_FILES"
echo "Archivos XML: $XML_FILES"
echo "Archivos Markdown: $MD_FILES"

PY_LINES=$(find . -name "*.py" -not -path "./__pycache__/*" -exec cat {} \; | wc -l)
XML_LINES=$(find . -name "*.xml" -exec cat {} \; | wc -l)
MD_LINES=$(find . -name "*.md" -exec cat {} \; | wc -l)

echo "Líneas Python: $PY_LINES"
echo "Líneas XML: $XML_LINES"
echo "Líneas Markdown: $MD_LINES"
echo "Total líneas: $((PY_LINES + XML_LINES + MD_LINES))"

echo ""
echo "=========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ VERIFICACIÓN COMPLETADA SIN ERRORES${NC}"
    echo "=========================================="
    echo ""
    echo "El módulo está listo para instalar."
    echo ""
    echo "Siguiente paso:"
    echo "  1. Instalar en Odoo: Aplicaciones → xtendoo_pos_order"
    echo "  2. Ver guía: cat QUICKSTART.md"
    exit 0
else
    echo -e "${RED}❌ VERIFICACIÓN COMPLETADA CON $ERRORS ERROR(ES)${NC}"
    echo "=========================================="
    echo ""
    echo "Por favor, corrija los errores antes de instalar."
    exit 1
fi

