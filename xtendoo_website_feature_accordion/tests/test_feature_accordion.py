# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestFeatureAccordionSnippet(HttpCase):
    """Verify that the Feature Accordion snippet loads correctly
    on the website frontend and that its JS interaction is registered."""

    def test_snippet_template_exists(self):
        """The QWeb template for the snippet must be loadable."""
        template = self.env.ref(
            "xtendoo_website_feature_accordion.s_feature_accordion",
            raise_if_not_found=False,
        )
        self.assertTrue(
            template,
            "The s_feature_accordion QWeb template should exist after install.",
        )

    def test_snippet_registered_in_panel(self):
        """The snippet registration template (snippets.xml) must exist."""
        template = self.env.ref(
            "xtendoo_website_feature_accordion.snippets",
            raise_if_not_found=False,
        )
        self.assertTrue(
            template,
            "The snippets panel registration template should exist.",
        )

    def test_homepage_loads(self):
        """Verify the website homepage still loads without errors
        after installing the module (no broken assets)."""
        response = self.url_open("/")
        self.assertEqual(
            response.status_code,
            200,
            "The website homepage should return HTTP 200 after module install.",
        )
