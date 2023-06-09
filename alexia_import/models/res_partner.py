import requests
import xml.etree.ElementTree as ET

from odoo import _, api, fields, models
# from odoo.exceptions import UserError, AccessError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def import_alexa(self):
        # msg_result = ""
        if self["vat"]:
            url = "https://ws2.alexiaedu.com/ACWebService/WSIntegracion.asmx/GetAlumnos"
            data = {
                'codigo': 'HbFYcML4Ti0%3d',
                'idInstitucion': '1587',
                'idCentro': '2343',
                'ejercicio': '2022',
                'check': 'B24BA-023E6-B1B93-B24A4-0863B6D1-2057',
            }
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            response = requests.post(url, headers=headers, data=data)
            # # Puedes procesar la respuesta según tus necesidades
            if response.status_code == 200:
                # La solicitud fue exitosa
                tree = ET.ElementTree(ET.fromstring(response.text))
                root = tree.getroot()

                for datos in root.findall('datos'):
                    for alumno in datos.findall('alumno'):
                        if alumno.find('NIF').text == self["vat"]:
                            print("********************************************************************************")
                            print("Partner encontrado: " + self["name"] + " con DNI " + self["vat"])
                            print("********************************************************************************")
                            # msg_result = msg_result + "Partner encontrado: " + self["name"] + " con DNI " + self["vat"] + "\n"
                            return self

                return self.addPartner()
            else:
                print("********************************************************************************")
                print("SOLICITUD FALLIDA")
                print("********************************************************************************")
                # msg_result = msg_result + "Solicitud con Alexia fallida.\n"
                # La solicitud falló
                # Manejar el error de alguna manera
        else:
            print("********************************************************************************")
            print("Contacto desestimado: " + self["name"])
            print("¡¡Campo D.N.I. obligatorio!!")
            print("********************************************************************************")

        # raise UserError(msg_result)

    def addPartner(self):
        print("********************************************************************************")
        print("Creo el partner: " + self["name"] + " con DNI " + self["vat"])
        print("********************************************************************************")

