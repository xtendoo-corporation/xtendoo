# Xtendoo Sale Barcode Scanner

Módulo custom para Odoo 19.0 que permite añadir productos a `sale.order`
mediante lector de códigos de barras usando el servicio nativo `barcode` de
Odoo y componentes OWL.

## Comportamiento

- Captura escaneos dentro del formulario de `sale.order`, aunque el foco esté
  en inputs editables del formulario.
- Busca `product.product` por `barcode` filtrando `sale_ok = True`.
- Si existe una línea del producto, incrementa `product_uom_qty` en 1.
- Si no existe, crea una nueva línea con cantidad 1 usando el flujo estándar
  de Odoo.
- Si hay ambigüedad, no hay producto, la UoM no coincide o el pedido no es
  editable, muestra un aviso y registra el evento en log.

## Validación recomendada

```bash
cd /home/xtendoo/Documentos/odoo/19
# Ajusta la base de datos según tu entorno
# docker compose run --rm -T odoo bash -c "odoo -d <db> --test-enable --stop-after-init -i xtendoo_sale_barcode_scanner --test-tags /xtendoo_sale_barcode_scanner"
```

