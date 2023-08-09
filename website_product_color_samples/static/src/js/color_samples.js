odoo.define('color_samples', function (require) {
    'use strict';
    $(function () {
        $(".color_sample_input").click(function () {
            const product_id = $(this).data('product_id')
            const $img = $(this).closest("form").find(".oe_product_image").find('img')
            $img.attr("src", "/web/image/product.product/" + product_id + "/image_variant_128")
            // Remove active class from all color labels
            $(".css_attribute_color").removeClass("active");
            // Add active class to selected color label
            $(this).closest(".css_attribute_color").addClass("active");
        })
    });
});