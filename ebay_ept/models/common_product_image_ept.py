#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""
Describes methods to store images in eBay.
"""
import base64
import logging
import io
from PIL import Image


from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class CommonProductImageEpt(models.Model):
    """storage_image_in_ebay
    Upload product images to ebay
    """
    _inherit = 'common.product.image.ept'

    ebay_image_ids = fields.One2many(
        "ebay.product.image.ept", "odoo_image_id", string='eBay Product Images', help="eBay Product Images")

    def create_picture_url(self, instance):
        """
        Upload product image to ebay
        :return: Full URL of uploaded product image
        """
        api = instance.get_trading_api_object()
        is_good_image = self.is_good_images()
        url = ''
        if is_good_image:
            image = io.BytesIO(base64.standard_b64decode(self.image))
            picture_data = {
                "WarningLevel": "High",
                "PictureName": self.name
            }
            files = {'file': ('EbayImage', image)}
            try:
                response = api.execute('UploadSiteHostedPictures', picture_data, files=files)
            except Exception as error:
                errors = error.response.dict()['Errors']
                if not isinstance(errors, list):
                    errors = [errors]
                error_message = ''
                for error in errors:
                    if error['SeverityCode'] == 'Error':
                        error_message += error['LongMessage'] + '(' + error['ErrorCode'] + ')'
                    if error['ErrorCode'] == '21916884':
                        error_message += _('Or the condition is not compatible with the category.')
                    if error['ErrorCode'] == '10007' or error['ErrorCode'] == '21916803':
                        error_message = _('eBay is unreachable. Please try again later.')
                    if error['ErrorCode'] == '21916635':
                        error_message = _(
                            'Impossible to revise a listing into a multi-variations listing.\n Create a new listing.')
                    if error['ErrorCode'] == '942':
                        error_message += _(
                            " If you want to set quantity to 0, the Out Of Stock option should be enabled"
                            " and the listing duration should set to Good 'Til Canceled")
                    if error['ErrorCode'] == '21916626':
                        error_message = _(
                            " You need to have at least 2 variations selected for a multi-variations listing.\n"
                            " Or if you try to delete a variation, you cannot do it by unselecting it."
                            " Setting the quantity to 0 is the safest method to make a variation unavailable.")
                    raise UserError(_("Error Encountered.\n'%s'") % (error_message,))
            site_hosted_picture_details = response.dict().get('SiteHostedPictureDetails', {})
            url = response and response.dict() and site_hosted_picture_details.get('FullURL', '')
        return url

    def is_good_images(self):
        """Images need to follow some guidelines to be accepted on ebay, otherwise they may generate errors
           https://developer.ebay.com/DevZone/guides/features-guide/default.html#development/Pictures-Intro.html
           https://developer.ebay.com/devzone/xml/docs/Reference/eBay/types/PictureDetailsType.html
        :return: all attachments that are images satisfying ebay requirements
        """
        try:
            data = io.BytesIO(base64.standard_b64decode(self.image))
            img = Image.open(data)
            good_image = (max(img.size) >= 500 and
                          sum(img.size) <= 12000 and
                          data.getbuffer().nbytes <= 12e6 and
                          (not img.format == 'JPEG' or img.mode == 'RGB'))
            return good_image
        except Exception as error:
            _logger.error(error)
            return False
