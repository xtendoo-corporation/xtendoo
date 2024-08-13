# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
from ..wordpress_xmlrpc import base
from ..wordpress_xmlrpc import compat
from ..wordpress_xmlrpc import media
from odoo.exceptions import UserError


def upload_image(instance, image_data, image_name, mime_type):
    """
    This method is used to upload image to WooCommerce via XMLRPC.
    It will return like data as:
    {'id': 6, 'file': 'picture.jpg',
    'url': 'http://www.example.com/wp-content/uploads/2012/04/16/picture.jpg',
   'type': 'image/jpeg'}
    @param instance: Record of WooCommerce Instance.
    @param image_data: Binary data of image.
    @param image_name: Name of the image.
    @param mime_type: Mimetype of image.
    @return: Response from WooCommerce.
    Migrated by Maulik Barad on Date 07-Oct-2021.
    """
    try:
        if not image_data or not image_name or not instance.woo_admin_username or not instance.woo_admin_password:
            return {}
        client = base.Client('%s/xmlrpc.php' % instance.woo_host, instance.woo_admin_username,
                             instance.woo_admin_password)
        binary_data = base64.decodebytes(image_data)
        data = {
            'name': '%s_%s.%s' % (image_name, instance.id, mime_type.split("/")[1]),
            'type': mime_type,
            'bits': compat.xmlrpc_client.Binary(binary_data)
        }

        res = client.call(media.UploadFile(data))
        return res
    except Exception as e:
        raise UserError(
            "It seems there is a configuration problem in your WooCommerce store."
            "Please check the user guide to enable XML-RPC in your WooCommerce store.\n\n "f"Error: {str(e)}")
