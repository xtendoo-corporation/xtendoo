# Copyright 2025 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def archive_duplicate_names(self):
        """
        Archive all products with duplicate names in product.template.
        For each set of duplicates, keeps the first one active and archives the rest.

        Returns:
            dict: A dictionary with information about the operation:
                - 'duplicate_names': list of names that were found duplicated
                - 'archived_count': number of products that were archived
                - 'errors': list of any errors encountered
        """
        _logger.info("=" * 80)
        _logger.info("Starting archive_duplicate_names process")
        _logger.info("=" * 80)

        archived_count = 0
        duplicate_names = []
        errors = []

        try:
            # Find all duplicate names in active products
            # En Odoo 18, el campo name puede ser JSONB (traducible)
            # Extraemos el valor de cualquier idioma para comparar
            # Si es un JSON con traducciones, tomamos el primer valor
            # Si es texto simple, lo usamos directamente
            self.env.cr.execute("""
                WITH name_values AS (
                    SELECT
                        id,
                        CASE
                            WHEN jsonb_typeof(name) = 'object' THEN
                                -- Es un JSON con traducciones, extraer primer valor
                                (SELECT value FROM jsonb_each_text(name) LIMIT 1)
                            ELSE
                                -- Es texto simple, convertir a texto
                                COALESCE(name::text, '')
                        END as name_text
                    FROM product_template
                    WHERE active = true
                      AND name IS NOT NULL
                )
                SELECT
                    name_text,
                    COUNT(*) as count,
                    array_agg(id ORDER BY id) as ids
                FROM name_values
                WHERE name_text != ''
                  AND name_text NOT LIKE '[%%]%%'
                GROUP BY name_text
                HAVING COUNT(*) > 1
                ORDER BY count DESC, name_text
            """)

            duplicate_data = self.env.cr.fetchall()

            _logger.info(f"Found {len(duplicate_data)} duplicate name(s)")

            if not duplicate_data:
                _logger.warning("No duplicate names found in active products")
                return {
                    'duplicate_names': [],
                    'archived_count': 0,
                    'errors': [],
                }

            for row in duplicate_data:
                name = row[0]
                count = row[1]
                ids = row[2] if len(row) > 2 else []

                duplicate_names.append(name)

                _logger.info(f"Processing: '{name}' ({count} products, IDs: {ids})")

                try:
                    # Buscar productos por IDs directamente (evita problemas con campos traducibles)
                    # Los IDs ya vienen de la consulta SQL que detectó los duplicados
                    if not ids or len(ids) <= 1:
                        _logger.warning(f"No IDs or only 1 ID for name '{name}', skipping")
                        continue

                    # Buscar productos por sus IDs (más confiable que por nombre)
                    products = self.browse(ids).filtered(lambda p: p.active)

                    if not products:
                        _logger.warning(f"No active products found for IDs {ids}")
                        continue

                    if len(products) <= 1:
                        _logger.warning(
                            f"Only {len(products)} active product(s) found for IDs {ids}, skipping"
                        )
                        continue

                    # Los productos ya están ordenados por ID (viene del array_agg ORDER BY id)
                    # Keep the first one active, archive the rest
                    first_product = products[0]
                    products_to_archive = products[1:]

                    _logger.info(
                        f"  → Keeping product ID {first_product.id} ('{first_product.name}')"
                    )
                    _logger.info(
                        f"  → Archiving {len(products_to_archive)} duplicate(s): "
                        f"IDs {[p.id for p in products_to_archive]}"
                    )

                    # Archive duplicates one by one to catch individual errors
                    for product in products_to_archive:
                        try:
                            product.write({'active': False})
                            archived_count += 1
                            _logger.info(f"    ✓ Archived product ID {product.id}")
                        except Exception as e:
                            error_msg = f"Error archiving product ID {product.id}: {str(e)}"
                            _logger.error(error_msg)
                            errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Error processing name '{name}': {str(e)}"
                    _logger.error(error_msg)
                    errors.append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"Critical error in archive_duplicate_names: {str(e)}"
            _logger.error(error_msg)
            errors.append(error_msg)

        result = {
            'duplicate_names': duplicate_names,
            'archived_count': archived_count,
            'errors': errors,
        }

        _logger.info("=" * 80)
        _logger.info(
            f"Archive process completed. Archived {archived_count} product(s), "
            f"found {len(duplicate_names)} duplicate name(s), "
            f"{len(errors)} error(s)"
        )
        _logger.info("=" * 80)

        return result

