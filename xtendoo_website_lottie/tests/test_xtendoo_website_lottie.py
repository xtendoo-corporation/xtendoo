from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestXtendooWebsiteLottie(TransactionCase):

    def test_frontend_assets_are_registered(self):
        asset_paths = self.env['ir.asset']._get_asset_paths('web.assets_frontend', {})
        available_paths = {path[0] for path in asset_paths}

        self.assertIn(
            '/xtendoo_website_lottie/static/lib/lottie/lottie.min.js',
            available_paths,
        )
        self.assertIn(
            '/xtendoo_website_lottie/static/src/js/lottie_init.js',
            available_paths,
        )
        self.assertIn(
            '/xtendoo_website_lottie/static/src/scss/lottie.scss',
            available_paths,
        )

    def test_snippet_template_is_available(self):
        snippet = self.env.ref('xtendoo_website_lottie.s_xtd_lottie')
        self.assertTrue(snippet, 'La plantilla del snippet debe existir')
        self.assertIn('xtd-lottie', snippet.arch_db)
        self.assertIn('/xtendoo_website_lottie/static/src/lottie/example.json', snippet.arch_db)
