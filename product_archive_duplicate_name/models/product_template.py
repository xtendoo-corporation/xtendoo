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
            # Excluir nombres vacíos o None
            # En Odoo 18, el campo name puede ser JSONB, necesitamos convertir a texto
            self.env.cr.execute("""
                SELECT
                    COALESCE(name::text, '') as name_text,
                    COUNT(*) as count,
                    array_agg(id ORDER BY id) as ids
                FROM product_template
                WHERE active = true
                  AND name IS NOT NULL
                  AND COALESCE(name::text, '') != ''
                  AND COALESCE(name::text, '') NOT LIKE '[%%]%%'
                GROUP BY name
                HAVING COUNT(*) > 1
                ORDER BY count DESC, COALESCE(name::text, '')
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
                    # Search for all active products with this name, ordered by ID
                    products = self.search(
                        [('name', '=', name), ('active', '=', True)],
                        order='id asc'
                    )

                    if not products:
                        _logger.warning(f"No products found for name '{name}' (unexpected)")
                        continue

                    if len(products) <= 1:
                        _logger.warning(
                            f"Only 1 product found for '{name}', skipping (expected {count})"
                        )
                        continue

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

