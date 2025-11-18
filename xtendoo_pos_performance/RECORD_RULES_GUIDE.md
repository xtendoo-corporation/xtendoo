# Record Rule para res.partner - Multi-compañía en Odoo 19.0

## Explicación de la lógica

Esta regla de registro permite que un usuario vea:
1. **Contactos sin compañía asignada** (`company_id` vacío/False)
2. **Contactos de sus propias compañías** (compañías a las que tiene acceso el usuario)

Esto es útil en entornos multi-compañía donde quieres que:
- Los contactos "globales" (sin company_id) sean visibles para todos
- Cada usuario solo vea los contactos de su(s) compañía(s)
- Los usuarios no vean contactos de otras compañías

---

## Dominio de la regla

```python
['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
```

**Explicación del dominio:**
- `|` = Operador OR (uno u otro)
- `('company_id', '=', False)` = Contactos sin compañía
- `('company_id', 'in', company_ids)` = Contactos de las compañías del usuario

`company_ids` es una variable especial que Odoo resuelve automáticamente con las compañías del usuario actual.

---

## XML de ejemplo para ir.rule

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- Regla de registro para res.partner multi-compañía -->
        <record id="res_partner_company_rule" model="ir.rule">
            <field name="name">Contactos: multi-compañía</field>
            <field name="model_id" ref="base.model_res_partner"/>
            <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
            <field name="groups" eval="[(4, ref('base.group_user'))]"/>
            <field name="perm_read" eval="True"/>
            <field name="perm_write" eval="True"/>
            <field name="perm_create" eval="True"/>
            <field name="perm_unlink" eval="True"/>
        </record>

    </data>
</odoo>
```

**Explicación de los campos:**

- `id`: Identificador único del registro
- `name`: Nombre descriptivo de la regla
- `model_id`: Referencia al modelo (res.partner)
- `domain_force`: Dominio que se aplica automáticamente
- `groups`: Grupos a los que aplica (base.group_user = usuarios internos)
- `perm_read/write/create/unlink`: Permisos afectados por la regla

---

## Crear desde la interfaz gráfica

1. **Ir a**: Ajustes → Técnico → Seguridad → Reglas de registro
2. **Clic en**: Crear
3. **Rellenar**:
   - **Nombre**: Contactos: multi-compañía
   - **Modelo**: res.partner
   - **Dominio**: `['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]`
   - **Grupos**: Seleccionar "Usuario interno" (base.group_user)
   - **Permisos**: Marcar los que necesites (Leer, Escribir, Crear, Eliminar)

4. **Guardar**

---

## Notas y buenas prácticas en Odoo 19.0

### 1. Usar `noupdate="1"` en datos sensibles
```xml
<data noupdate="1">
```
Esto evita que se sobrescriba la regla si el usuario la modifica manualmente.

### 2. Variables disponibles en dominios de record rules

- `user.id` - ID del usuario actual
- `company_id` - Compañía actual del usuario
- `company_ids` - Lista de compañías del usuario
- `time.strftime('%Y-%m-%d')` - Fecha actual

### 3. Operadores OR/AND en dominios

```python
# OR (uno u otro)
['|', condicion1, condicion2]

# AND (ambos) - implícito por defecto
[condicion1, condicion2]

# OR con múltiples condiciones
['|', '|', condicion1, condicion2, condicion3]

# Combinación AND/OR
['&', condicion1, '|', condicion2, condicion3]
```

### 4. Probar record rules

**Desde Python (consola Odoo):**
```python
# Verificar qué contactos ve un usuario
user = env['res.users'].browse(USER_ID)
partners = env['res.partner'].with_user(user).search([])
print(f"Usuario {user.name} ve {len(partners)} contactos")
```

### 5. Orden de evaluación de record rules

- Si hay múltiples reglas para el mismo modelo y grupo: **se evalúan con OR**
- Si hay reglas en diferentes grupos: **se evalúan con AND** entre grupos
- Si un modelo no tiene reglas: **acceso completo** (según permisos de acceso)

### 6. Record rules vs Access Rights

- **Access Rights (ir.model.access)**: Definen SI un grupo puede acceder a un modelo
- **Record Rules (ir.rule)**: Definen QUÉ registros puede ver dentro de ese modelo

Ambos deben permitir el acceso para que funcione.

### 7. Debugging record rules

**Activar logs de seguridad:**
```python
# En archivo de configuración de Odoo
log_level = debug_rpc
log_db = True
```

**Ver reglas aplicadas:**
```python
# En shell de Odoo
model = env['res.partner']
rules = env['ir.rule']._compute_domain(model._name, 'read')
print(rules)
```

### 8. Rendimiento de record rules

- ⚠️ Record rules se aplican en CADA búsqueda
- ⚠️ Dominios complejos pueden ralentizar las consultas
- ✅ Crear índices en campos usados en dominios:
  ```python
  company_id = fields.Many2one('res.company', index=True)
  ```

### 9. Excepciones comunes

**Error: "El campo 'company_ids' no existe"**
- Solución: Usar `user.company_ids.ids` en lugar de `company_ids` en algunos casos

**La regla no se aplica:**
- Verificar que el grupo está bien asociado
- Verificar que no hay reglas conflictivas
- Limpiar caché: `odoo.sh -c config.conf -d database --stop-after-init`

### 10. Ejemplo avanzado: con usuario específico

```xml
<record id="res_partner_own_contacts_rule" model="ir.rule">
    <field name="name">Contactos: solo los propios del usuario</field>
    <field name="model_id" ref="base.model_res_partner"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

---

## Resumen

Para implementar la regla multi-compañía en res.partner:

1. **Crear un módulo** o añadir a uno existente
2. **Añadir el XML** con la definición del ir.rule
3. **Instalar/actualizar** el módulo
4. **Probar** con usuarios de diferentes compañías
5. **Verificar** que los contactos se filtran correctamente

**La regla garantiza que:**
- ✅ Contactos globales (sin company_id) son visibles para todos
- ✅ Cada usuario ve solo contactos de sus compañías
- ✅ Multi-compañía funciona correctamente
- ✅ No hay fugas de información entre compañías

---

**Documento creado para Odoo 19.0**
**Xtendoo Software S.L.U.**

