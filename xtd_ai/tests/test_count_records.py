from odoo.tests import tagged

from .common import XtdAiCase


@tagged("post_install", "-at_install")
class TestCountRecords(XtdAiCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spain = cls.env.ref("base.es")
        # names are shown in the user's language: tests must not assume English
        cls.spain_name = cls.spain.with_context(lang=cls.user.lang).name
        Partner = cls.env["res.partner"]
        cls.partners = Partner.create(
            [
                {
                    "name": "Cuenta Uno SL",
                    "is_company": True,
                    "country_id": cls.spain.id,
                },
                {
                    "name": "Cuenta Dos SL",
                    "is_company": True,
                    "country_id": cls.spain.id,
                },
                {"name": "Cuenta Tres", "is_company": False},
            ]
        )

    def setUp(self):
        super().setUp()
        self.run, _token = self.start_run(self.user)

    def partners_of_user(self):
        """Partners as the agent sees them: the user's rights and language."""
        return (
            self.env["res.partner"]
            .with_user(self.user)
            .with_context(lang=self.user.lang)
        )

    def count(self, args):
        return self.call(self.user, self.run, "count_records", args)[
            "structuredContent"
        ]

    def test_total_and_groups_match_the_orm(self):
        result = self.count({"model": "res.partner"})
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(
            result["data"]["total"],
            self.env["res.partner"].with_user(self.user).search_count([]),
        )
        result = self.count(
            {
                "model": "res.partner",
                "group_by": "country_id",
                "filters": [{"field": "is_company", "operator": "=", "value": "true"}],
            }
        )
        groups = {
            g["group"] and g["group"]["untrusted_text"]: g["count"]
            for g in result["data"]["groups"]
        }
        expected = self.partners_of_user().search_count(
            [("is_company", "=", True), ("country_id", "=", self.spain.id)]
        )
        self.assertEqual(groups[self.spain_name], expected)
        self.assertNotIn("items", result["data"])  # figures only, never records

    def test_filter_by_name_of_a_related_record(self):
        result = self.count(
            {
                "model": "res.partner",
                "filters": [
                    {"field": "country_id", "operator": "=", "value": self.spain_name}
                ],
            }
        )
        self.assertEqual(
            result["data"]["total"],
            self.partners_of_user().search_count(
                [("country_id", "ilike", self.spain_name)]
            ),
        )

    def test_only_whitelisted_fields(self):
        for args in (
            {"model": "res.partner", "group_by": "email"},
            {"model": "res.partner", "group_by": "vat"},
            {
                "model": "res.partner",
                "filters": [{"field": "email", "operator": "ilike", "value": "@"}],
            },
            {"model": "res.partner", "measure": "credit_limit"},
            {"model": "product.template", "group_by": "month"},
        ):
            result = self.count(args)
            self.assertIn(result["error"]["code"], ("validation", "not_found"), args)
        # a model outside the list is refused by the schema itself
        status, response = self.rpc(
            self.user,
            self.run,
            "tools/call",
            {"name": "count_records", "arguments": {"model": "res.users"}},
        )
        self.assertEqual(status, 200)
        error = response.get("error") or response["result"]["structuredContent"]
        self.assertTrue(error)

    def test_record_rules_apply(self):
        self.env["res.partner"].create(
            {"name": "Contar Oculto", "company_id": self.company2.id}
        )
        self.user.company_ids = self.company
        filters = [
            {"field": "company_id", "operator": "=", "value": str(self.company2.id)}
        ]
        result = self.count({"model": "res.partner", "filters": filters})
        self.assertEqual(result["data"]["total"], 0)  # not visible to the user
        self.assertTrue(
            self.env["res.partner"].search_count(
                [("company_id", "=", self.company2.id)]
            )
        )

    def test_search_partners_without_query_lists_all_with_total(self):
        result = self.call(self.user, self.run, "search_partners", {"limit": 1})[
            "structuredContent"
        ]
        self.assertEqual(result["status"], "ok", result)
        self.assertEqual(len(result["data"]["items"]), 1)
        self.assertEqual(
            result["data"]["total"],
            self.env["res.partner"].with_user(self.user).search_count([]),
        )
