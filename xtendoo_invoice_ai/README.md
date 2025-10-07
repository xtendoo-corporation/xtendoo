# Invoice AI - OpenAI Integration

Módulo de Odoo 18 que permite importar facturas de proveedor automáticamente usando OpenAI (ChatGPT).

## Características principales

- 🤖 Extracción inteligente con IA (GPT-4o)
- 📄 Soporte multi-formato (PDF, JPG, PNG)
- 🌍 Multi-divisa y multi-empresa
- 🤝 Creación automática de proveedores
- 💰 Mapeo inteligente de impuestos
- ✅ Validación de totales
- 📊 Histórico con métricas

## Instalación rápida

```bash
pip install openai pdf2image jsonschema
sudo apt-get install poppler-utils  # Linux
```

Configura tu API key en: **Ajustes → General → Integraciones → OpenAI**

## Uso

1. **Facturación → Proveedores → Importar factura con IA**
2. Sube tu PDF/imagen
3. ¡Listo! Factura creada en borrador

## Documentación completa

Ver [README.rst](README.rst)

## Licencia

AGPL-3.0

## Autor

**Xtendoo** - https://www.xtendoo.es
icon.png
*.pyc
*.pyo
__pycache__/
.pytest_cache/
*.egg-info/

