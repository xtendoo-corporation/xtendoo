# Xtendoo - V 12  
###Este repositorio contiene todos los módulos mas generales de xtendoo.  
###Lista:  
# account_invoice_margin --> Añade margen en facturas.  
# account_triple_discount_fix --> Repara un bug de account_triple discount y depende del mismo.  
# account_triple_discount_zoopet --> Personalización del modulo account_triple_discount para zoopet.  
# account_payment_filter_today --> Filtro para los pagos de hoy.  
# account_payment_pivot_view --> Modifica la vista pivot de pagos.  
# add_invoice_comment --> Añade comentario en factura.  
# avaible_user_create_invoice --> Limita la creación de facturas directas ( no vienen de pedidos) a un grupo de usuarios.  
# base_avaible_pricelist --> Añade un señector en usuarios para indicar que tarifas puede ver ese usuario.  
# category_pricelist_percentaje --> Añade un % al precio de coste por cada tarifa y lo fija como precio de esa tarifa.  
# choose_invoice_journal --> Permite editar el diario de facturación en clientes.  
# create_contact_address_without_client_check --> Al crear un contacto con parent_id ( dirección de envío, facturación, etc) dejara el check de customer(es cliente) a False.  
# customer_invoice_delivery_address --> Añade un filtrado en el selector de direcciones de envio y factruación, para que solo salgan las de cliente seleccionado.   
# d_hr_administration --> Módulo con particularidades de administración para HUELVA REGALOS y DISCAFE.  
# document_format_bramah --> Formatos de impresión de BRAMAH.  
# document_format_ch --> Formatos de impresión de LA CASA DEL HOSTELERO.  
# document_format_dis --> Formatos de impresión de DISCAFE.  
# document_format_hr --> Formatos de impresión de HUELVA REGALOS.  
# document_format_xtendoo --> Formatos de impresión de XTENDOO.  
# hide_purchase_cost_in_so_and_invoice --> Oculta el precio de coste en ventas y facturas.  
# infortisa_product_import --> Importador de INFORTISA.  
# l10n_es_igic --> Añade los IGIC de Canarias.  
# lch_administration --> Módulo con particularidades de administración para LA CASA DEL HOSTELERO.  
# locked_payment_date --> Bloquea la fecha de pago para que no sea editable. 
# muk_autovacuum, muk_utils, muk_web_client, muk_web_client_refresh y muk_web_utils --> Herramientas de MUK para la interfaz web.  
# partner_delivery_zone --> Añade la funcionalidad de 'Zona de Entrega'.  
# partner_visit -->  
# pricelist_constraint_unique --> Evita que se dupliquen las tarifas en un mismo producto.  
# product_form_move_waiting_link --> Añade un link en productos que te lleva hasta sus movimientos en 'espera' de enviar.  
# product_form_move_waiting_purchase_link -->  Añade un link en productos que te lleva hasta sus movimientos en 'espera' de recibir.  
# product_hide_fields --> Oculta el campo 'list_price'.  
# product_next_coming --> Muestra la cantidad que se espera recibir de un producto.  
# product_pricelist_margin_base-->  
# product_show_pricelist --> Añade las tarifas la la vista tree de productos.  
# product_template_show_tax --> Muestra los impuestos en el producto.  
# purchase_order_cost_price --> Al comprar, carga automaticamente el precio de coste.  
# purchase_order_lot_selection --> Permite seleccionar el lote en una compra.  
# purchase_order_picking_all_done --> Añade los botones 'confirmar y entragar' y 'confirmar y facturar' en compras.  
# purchase_sale_bar --> Permite comprar y vender por barras (h7i).  
# res_partner_commercial_name --> Añade el campo 'nombre comercial' a clientes.  
# res_partner_hide_internal_notes --> Oculta las notas de clientes.  
# res_partner_ref_in_treeview --> Añade la referencia interna en la listView de clientes.  
# res_partner_show_ref --> Quita la refencia de la pestaña 'Ventas y Compras' y la añade a la ficha principal del cliente.  
# res_partner_vat_search --> Permite buscar or el CIF.  
# res_users_default_location -->  
# sale_campaign -->  
# sale_order_date_front -->  
# sale_order_date_update --> Permite actualizar la fecha de un pedido.  
# sale_order_general_discount_and_dpp --> Añade descuento global y por pronto pago (estaba hecho para zoopet, ya no sirve).  
# sale_order_lot_required --> Convierte el lote en obligatorio en ventas.  
# sale_order_lot_validation --> Validación de lotes.  
# sale_order_move_detail_info -->  
# sale_order_only_comercial_clients --> Filtro en ventas, para que solo aparezcan los clientes asociados al usuario actual.  
# sale_order_picking_all_done --> Añade los botones 'confirmar y entragar' y 'confirmar y facturar' en ventas.  
# sale_order_pricelist_auto_update --> Actualiza los precios de tarifas al hacer una venta.  
# sale_order_pricelist_line --> Añade la tarifa actual a la linea del pedido.  
# sale_order_triple_discount_fix --> Repara un bug de sale_order_triple discount y depende del mismo.  
# sale_order_triple_discount_zoopet --> Personalización del modulo sale_order_triple_discount para zoopet.  
# select_customer_warehouse --> Permite seleccionar un almacén para el usuario.  
# show_product_supplier_ref_in_po --> Muestra la referencia del pedido en ordenes de compra.  
# show_supplier_ref_in_purchase_order_view -->Muestra la referencia del pedido en la lista de ordenes de compra.  
# stock_barcodes_internal_transfer -->  
# stock_landed_costs_avco -->  
# stock_move_line_label --> Añade etiqueta en la linea de albarán.  
# stock_picking_and_sale_order_pallets_and_lumps --> Añade campo bultos y palets en ventas, albarán y factura.  
# stock_picking_batch_delivery --> Añade varios campos tanto en picking batch como en picking bacth line.  
# stock_picking_codebar_gs1 --> Generar codigos de barras.  
# stock_picking_done_to_draft --> Permite convertir albaranes marcados como hecho a borrador.  
# stock_picking_landed_cost_with_button -->  
# stock_picking_product_barcode_report --> Añade la impresión de códigos de barras en el picking.  
# stock_picking_product_label_with_barcode_128 -->  
# stock_picking_return_lot_qty -->  
# stock_picking_send_mail_remove_restriction -->  
# stock_picking_update_price --> Permite actualizar el precio desde el picking.  
# tutorial_create_classes_widgets -->  
# update_standar_price_where_bum --> Actualiza el precio de coste de un producto fabricado en función del coste de sus materiales.  
# web_digital_sign --> Permite firmar documentos.  
# website_product_multiwebsite -->  
# xtendoo_auto_backup --> Crear backups automatizados.  
# xtendoo_base_gs1_barcode -->  
# xtendoo_customer_invoice_delivery_address -->  
# xtendoo_product_code_unique --> Código de producto unico.  
# xtendoo_product_hide_cost --> Oculta el precio de coste.  
# xtendoo_sale_order_tag --> Añade etiquetas en pedidos de venta.  
# xtendoo_stock_cost_method_last -->  
# xtendoo_stock_lock_lot --> Impide que se pueda modificar el lote una vez validado.  
# xtendoo_stock_picking_barcodes -->  
# xtendoo_stock_picking_barcodes_gs1 -->  
# xtendoo_stock_picking_barcodes_qr -->  
# xtendoo_stock_picking_product_barcode_report -->  
# xtendoo_web_notify -->  
# xtendoo_web_sound -->  
# xtendoo_web_widget_digitized_signature -->
