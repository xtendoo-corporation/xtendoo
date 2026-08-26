from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPortalNoEconomics(HttpCase):
    """Validate that the "no economics" portal profile cannot reach economic data.

    The tests cover:
    - A portal user WITHOUT the group keeps standard access (control case).
    - A portal user WITH the group is redirected away from every economic route.
    - The portal home hides the economic cards for the restricted user.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_no_eco = cls.env.ref(
            "cdv_portal_no_economics.group_portal_no_economics"
        )
        portal_group = cls.env.ref("base.group_portal")

        cls.standard_user = cls.env["res.users"].create(
            {
                "name": "Portal Standard",
                "login": "portal_standard",
                "password": "portal_standard",
                "group_ids": [(6, 0, [portal_group.id])],
            }
        )
        cls.restricted_user = cls.env["res.users"].create(
            {
                "name": "Portal Restricted",
                "login": "portal_restricted",
                "password": "portal_restricted",
                "group_ids": [(6, 0, [portal_group.id, cls.group_no_eco.id])],
            }
        )

        cls.economic_routes = [
            "/my/quotes",
            "/my/orders",
            "/my/invoices",
            "/my/invoices/overdue",
            "/my/payment_method",
        ]

    def _assert_redirected_to_my(self, url):
        response = self.url_open(url, allow_redirects=False)
        self.assertIn(
            response.status_code,
            (301, 302, 303),
            f"{url} should redirect for the restricted user",
        )
        self.assertTrue(
            response.headers.get("Location", "").endswith("/my"),
            f"{url} should redirect to /my, got {response.headers.get('Location')}",
        )

    def test_restricted_user_is_redirected(self):
        self.authenticate("portal_restricted", "portal_restricted")
        for url in self.economic_routes:
            self._assert_redirected_to_my(url)

    def test_restricted_home_hides_economic_cards(self):
        self.authenticate("portal_restricted", "portal_restricted")
        response = self.url_open("/my")
        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertNotIn("/my/quotes", body)
        self.assertNotIn("/my/orders", body)
        self.assertNotIn("/my/invoices", body)
        self.assertNotIn("/my/payment_method", body)

    def test_standard_user_keeps_access(self):
        self.authenticate("portal_standard", "portal_standard")
        for url in ["/my/quotes", "/my/orders", "/my/invoices"]:
            response = self.url_open(url, allow_redirects=False)
            self.assertEqual(
                response.status_code,
                200,
                f"{url} should stay accessible for a standard portal user",
            )

    def test_standard_home_shows_economic_cards(self):
        self.authenticate("portal_standard", "portal_standard")
        response = self.url_open("/my")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/my/orders", response.text)
        self.assertIn("/my/invoices", response.text)
