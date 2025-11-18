#!/bin/bash
# Script de instalación y verificación del módulo xtendoo_pos_performance
# Xtendoo Software S.L.U. - 2025

set -e

echo "================================================"
echo "  Xtendoo POS Performance - Verificación"
echo "================================================"
echo ""

MODULE_PATH="/home/xtendoo/Documentos/odoo/19/odoo/custom/src/xtendoo/xtendoo_pos_performance"
PROJECT_PATH="/home/xtendoo/Documentos/odoo/19"

echo "✓ Verificando estructura del módulo..."
if [ -d "$MODULE_PATH" ]; then
    echo "  ✓ Módulo encontrado en: $MODULE_PATH"
else
    echo "  ✗ ERROR: Módulo no encontrado en: $MODULE_PATH"
    exit 1
fi

echo ""
echo "✓ Verificando archivos principales..."
files=(
    "__init__.py"
    "__manifest__.py"
    "README.md"
    "models/__init__.py"
    "models/res_config_settings.py"
    "data/ir_config_parameter_data.xml"
    "views/res_config_settings_views.xml"
)

for file in "${files[@]}"; do
    if [ -f "$MODULE_PATH/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ ERROR: Falta archivo $file"
        exit 1
    fi
done

echo ""
echo "✓ Verificando sintaxis Python..."
python3 -m py_compile "$MODULE_PATH/__init__.py" && echo "  ✓ __init__.py"
python3 -m py_compile "$MODULE_PATH/__manifest__.py" && echo "  ✓ __manifest__.py"
python3 -m py_compile "$MODULE_PATH/models/__init__.py" && echo "  ✓ models/__init__.py"
python3 -m py_compile "$MODULE_PATH/models/res_config_settings.py" && echo "  ✓ models/res_config_settings.py"

echo ""
echo "✓ Verificando sintaxis XML..."
xmllint --noout "$MODULE_PATH/data/ir_config_parameter_data.xml" 2>/dev/null && echo "  ✓ data/ir_config_parameter_data.xml"
xmllint --noout "$MODULE_PATH/views/res_config_settings_views.xml" 2>/dev/null && echo "  ✓ views/res_config_settings_views.xml"

echo ""
echo "================================================"
echo "  ✓ Módulo verificado correctamente"
echo "================================================"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. Reiniciar Odoo:"
echo "   cd $PROJECT_PATH"
echo "   docker-compose restart odoo"
echo ""
echo "2. Acceder a Odoo: http://localhost:19069"
echo ""
echo "3. Actualizar lista de aplicaciones:"
echo "   Aplicaciones → (⋮) → Actualizar lista de aplicaciones"
echo ""
echo "4. Buscar e instalar:"
echo "   Buscar: 'Xtendoo POS Performance'"
echo "   Clic en: Instalar"
echo ""
echo "5. Configurar en:"
echo "   Ajustes → Punto de venta → Rendimiento"
echo ""
echo "================================================"

