from email.policy import default

from odoo import fields, models


class AppccRegistration(models.Model):
    _name = "appcc.registration"
    _description = "Verificacion Global del Sistema APPCC"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Referencia", required=True, copy=False, readonly=True, default="Nuevo")
    date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today, tracking=True)
    frequency = fields.Selection(
        [("annual", "Anual")],
        string="Frecuencia",
        required=True,
        default="annual",
        tracking=True,
    )
    responsible_id = fields.Many2one(
        "res.users", string="Responsable", required=True, default=lambda self: self.env.user, tracking=True
    )

    method_text = fields.Text(
        string="Metodo",
        default=(
            "Una vez al ano el responsable de la verificacion hace un analisis de toda la documentacion generada "
            "a lo largo de ese ano y procede a contestar a las preguntas que se exponen a continuacion para "
            "concluir si el sistema implantado esta funcionando correctamente con el fin de minimizar o eliminar "
            "los potenciales peligros que puedan aparecer en el desarrollo de nuestra actividad de cara a la "
            "salubridad de nuestros productos y por tanto desde el punto de vista de la seguridad alimentaria."
        ),
        readonly=True,
    )

    result_selection = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado de la Verificacion",
        required=True,
        default= "favorable"
    )

    p1_q1 = fields.Boolean(string="Agua suministrada por gestor autorizado", required=True)
    p1_q2 = fields.Boolean(string="Otra fuente de abastecimiento complementaria", required=True)
    p1_q3 = fields.Boolean(string="Analitica inicial de control de agua de grifo", required=True)
    p1_q4 = fields.Boolean(string="Resultados de analiticas ajustados a norma", required=True)
    p1_q5 = fields.Boolean(string="Medicion de desinfectante residual y organoleptico", required=True)
    p1_q6 = fields.Boolean(string="Incidencia relacionada con este plan", required=True)
    p1_q7 = fields.Boolean(string="Incidencias registradas en el parte", required=True)
    p1_q8 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p1_q9 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p1_q10 = fields.Boolean(string="Cambio de red interna de tuberias en el ultimo ano", required=True)
    p1_q11 = fields.Boolean(string="Vigilancia segun directrices teoricas", required=True)
    p1_q12 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p1_q13 = fields.Boolean(string="Fruto de esta verificacion hay cambios", required=True)
    p1_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p1_incident_count = fields.Integer(string="Numero de incidencias")
    p1_changes = fields.Text(string="Cambios efectuados o incidencias")

    p2_q1 = fields.Boolean(string="Almacen especifico para productos de limpieza", required=True)
    p2_q2 = fields.Boolean(string="Productos especificos para superficies de contacto", required=True)
    p2_q3 = fields.Boolean(string="Fichas tecnicas y de seguridad archivadas", required=True)
    p2_q4 = fields.Boolean(string="Fichas tecnicas y de seguridad actualizadas", required=True)
    p2_q5 = fields.Boolean(string="Frecuencias de limpieza respetadas", required=True)
    p2_q6 = fields.Boolean(string="Vigilancia segun directrices teoricas", required=True)
    p2_q7 = fields.Boolean(string="Analitica programada sobre superficies realizada", required=True)
    p2_q8 = fields.Boolean(string="Resultados satisfactorios", required=True)
    p2_q9 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p2_q10 = fields.Boolean(string="Incidencia relacionada con este plan", required=True)
    p2_q11 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p2_q12 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p2_q13 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p2_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p2_incident_count = fields.Integer(string="Numero de incidencias")
    p2_changes = fields.Text(string="Cambios efectuados o incidencias")

    p3_q1 = fields.Boolean(string="Barreras fisicas contra animales", required=True)
    p3_q2 = fields.Boolean(string="Contrato con empresa autorizada ROESBA", required=True)
    p3_q3 = fields.Boolean(string="Frecuencias de accion respetadas", required=True)
    p3_q4 = fields.Boolean(string="Sustancias para detectar o eliminar plagas", required=True)
    p3_q5 = fields.Boolean(string="Documentacion del plan facilitada", required=True)
    p3_q6 = fields.Boolean(string="Frecuencia de vigilancia respetada", required=True)
    p3_q7 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p3_q8 = fields.Boolean(string="Incidencia relacionada en este periodo", required=True)
    p3_q9 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p3_q10 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p3_q11 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p3_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p3_incident_count = fields.Integer(string="Numero de incidencias")
    p3_changes = fields.Text(string="Cambios efectuados o incidencias")

    p4_q1 = fields.Boolean(string="Nueva maquinaria o instalacion este ano", required=True)
    p4_q2 = fields.Boolean(string="Condiciones para contacto con materias primas y productos", required=True)
    p4_q3 = fields.Boolean(string="Empresa de mantenimiento contratada este ano", required=True)
    p4_q4 = fields.Boolean(string="Parte de trabajo generado por mantenimiento", required=True)
    p4_q5 = fields.Boolean(string="Anomalia que afecte a la salubridad", required=True)
    p4_q6 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p4_q7 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p4_q8 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p4_q9 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p4_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p4_incident_count = fields.Integer(string="Numero de incidencias")
    p4_changes = fields.Text(string="Cambios efectuados o incidencias")

    p5_q1 = fields.Boolean(string="Nuevo equipo de frio este ano", required=True)
    p5_q2 = fields.Boolean(string="Condiciones para contacto con materias primas", required=True)
    p5_q3 = fields.Boolean(string="Anomalia con perdida de cadena de frio", required=True)
    p5_q4 = fields.Boolean(string="Intervencion de empresa para subsanar anomalia", required=True)
    p5_q5 = fields.Boolean(string="Parte de trabajo generado", required=True)
    p5_q6 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p5_q7 = fields.Boolean(string="Registro diario de temperatura", required=True)
    p5_q8 = fields.Boolean(string="Contraste semestral con termometro externo", required=True)
    p5_q9 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p5_q10 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p5_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p5_incident_count = fields.Integer(string="Numero de incidencias")
    p5_changes = fields.Text(string="Cambios efectuados o incidencias")

    p6_q1 = fields.Boolean(string="Control correcto de entrada de materias primas y envases", required=True)
    p6_q2 = fields.Boolean(string="Control correcto de producciones", required=True)
    p6_q3 = fields.Boolean(string="Control correcto de salidas", required=True)
    p6_q4 = fields.Boolean(string="Incidencia con perdida de informacion de trazabilidad", required=True)
    p6_q5 = fields.Boolean(string="Registro y medidas correctoras aplicadas", required=True)
    p6_q6 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p6_q7 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p6_q8 = fields.Boolean(string="Loteados correctos para seguimiento interno", required=True)
    p6_q9 = fields.Boolean(string="Trazar producto final a lote de materia prima", required=True)
    p6_q10 = fields.Boolean(string="Seguir materia prima hasta entrega de producto", required=True)
    p6_q11 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p6_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p6_incident_count = fields.Integer(string="Numero de incidencias")
    p6_changes = fields.Text(string="Cambios efectuados o incidencias")

    p7_q1 = fields.Boolean(string="Formacion en manipulacion de alimentos", required=True)
    p7_q2 = fields.Boolean(string="Soporte documental de la formacion", required=True)
    p7_q3 = fields.Boolean(string="Incidencia que afecte a la salubridad", required=True)
    p7_q4 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p7_q5 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p7_q6 = fields.Boolean(string="Incorporacion de nuevos manipuladores", required=True)
    p7_q7 = fields.Boolean(string="Acreditacion de formacion de nuevos manipuladores", required=True)
    p7_q8 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p7_q9 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p7_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p7_incident_count = fields.Integer(string="Numero de incidencias")
    p7_changes = fields.Text(string="Cambios efectuados o incidencias")

    p8_q1 = fields.Boolean(string="Eliminacion de residuos segun procedimiento", required=True)
    p8_q2 = fields.Boolean(string="Respeto de pautas de tiempo minimo de residuos", required=True)
    p8_q3 = fields.Boolean(string="Numero suficiente de contenedores", required=True)
    p8_q4 = fields.Boolean(string="Anomalia que afecte a materias primas o productos", required=True)
    p8_q5 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p8_q6 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p8_q7 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p8_q8 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p8_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p8_incident_count = fields.Integer(string="Numero de incidencias")
    p8_changes = fields.Text(string="Cambios efectuados o incidencias")

    p9_q1 = fields.Boolean(string="Proveedores con garantia sanitaria contrastada", required=True)
    p9_q2 = fields.Boolean(string="Listado de proveedores habituales actualizado", required=True)
    p9_q3 = fields.Boolean(string="Autorizaciones sanitarias y fichas tecnicas guardadas", required=True)
    p9_q4 = fields.Boolean(string="Anomalia relacionada con este plan", required=True)
    p9_q5 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p9_q6 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p9_q7 = fields.Boolean(string="Nuevos proveedores incorporados este ano", required=True)
    p9_q8 = fields.Boolean(string="Solvencia sanitaria acreditada de nuevos proveedores", required=True)
    p9_q9 = fields.Boolean(string="Cumplimiento del programa de registros", required=True)
    p9_q10 = fields.Boolean(string="Fruto de esta verificacion se cambia algun aspecto", required=True)
    p9_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p9_incident_count = fields.Integer(string="Numero de incidencias")
    p9_changes = fields.Text(string="Cambios efectuados o incidencias")

    p10_q1 = fields.Boolean(string="Analiticas realizadas con la frecuencia estipulada", required=True)
    p10_q2 = fields.Boolean(string="Analiticas realizadas por laboratorios autorizados", required=True)
    p10_q3 = fields.Boolean(string="Desviacion sobre la norma en resultados", required=True)
    p10_q4 = fields.Boolean(string="Aplicacion de medidas correctoras", required=True)
    p10_q5 = fields.Boolean(string="Resultados correctores satisfactorios", required=True)
    p10_q6 = fields.Boolean(string="Cambio de actuaciones, frecuencia o laboratorio", required=True)
    p10_result = fields.Selection(
        [("favorable", "Favorable"), ("desfavorable", "Desfavorable")],
        string="Resultado del Plan",
        required=True,
        default="favorable"
    )
    p10_incident_count = fields.Integer(string="Numero de incidencias")
    p10_changes = fields.Text(string="Cambios efectuados o incidencias")

    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get("name", "Nuevo") == "Nuevo":
                vals["name"] = self.env["ir.sequence"].next_by_code("appcc.registration") or "Nuevo"
        return super().create(vals_list)

    def action_accept_all(self):
        """Marca todos los campos booleanos a True y todos los results a 'favorable'."""
        for record in self:
            vals = {"result_selection": "favorable"}
            for field_name, field in record._fields.items():
                if field.type == "boolean" and any(
                    field_name.startswith(f"p{i}_") for i in range(1, 11)
                ):
                    vals[field_name] = True
                elif field.type == "selection" and field_name.endswith("_result"):
                    vals[field_name] = "favorable"
            record.write(vals)

    def action_print_report(self):
        """Genera el PDF del informe APPCC."""
        self.ensure_one()
        return self.env.ref(
            "appcc_registration_system.action_report_appcc_registration"
        ).report_action(self)

    def action_send_email(self):
        """Abre el wizard de envio de email con el reporte PDF adjunto."""
        self.ensure_one()
        template = self.env.ref(
            "appcc_registration_system.email_template_appcc_registration",
            raise_if_not_found=False,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_composition_mode": "comment",
                "default_template_id": template.id if template else False,
                "default_use_template": True,
                "force_email": True,
            },
        }

