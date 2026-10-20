import logging
import odoo.tools.pdf as odoo_pdf

_logger = logging.getLogger(__name__)


def safe_fill_form_fields_pdf(writer, form_fields=None):
    if not form_fields:
        return

    try:
        root = getattr(writer, "_root_object", None)
        acroform = root.get("/AcroForm") if root else None
        has_fields = (
            acroform and acroform.get("/Fields") and len(acroform.get("/Fields")) > 0
        )
    except Exception:
        has_fields = False

    if not has_fields:
        _logger.debug("Skipping PDF form fill: no AcroForm fields present.")
        return

    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, form_fields)
        except Exception:
            # DO NOT depend on pypdf import
            _logger.warning(
                "Error while updating form fields. Skipping.",
                exc_info=True,
            )
            return


# Monkey patch
odoo_pdf.fill_form_fields_pdf = safe_fill_form_fields_pdf
