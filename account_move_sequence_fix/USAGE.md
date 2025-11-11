# Casos de Uso y Ejemplos

## 🎯 Casos Comunes

### Caso 1: Error al Validar Factura

**Síntoma:**
```
RPC_ERROR Odoo Server Error
psycopg2.errors.UndefinedFunction: operator does not exist: integer = boolean
LINE 1: SELECT number_next FROM ir_sequence WHERE id=false FOR UPDAT...
```

**Causa:**
El diario tiene `secure_sequence_id = false` en lugar de un ID válido.

**Solución Rápida:**
```bash
cd /home/xtendoo/Documentos/odoo/17
./odoo/custom/src/xtendoo/account_move_sequence_fix/fix_sequences.sh
# Seleccionar opción 3 (Diagnóstico + Corrección)
```

**Solución Manual:**
```sql
UPDATE account_journal
SET secure_sequence_id = NULL
WHERE secure_sequence_id NOT IN (SELECT id FROM ir_sequence);
```

### Caso 2: Después de Restaurar un Backup

**Problema:**
Después de restaurar un backup, las secuencias pueden quedar desincronizadas.

**Solución:**
1. Ejecutar el diagnóstico:
   ```bash
   cd /home/xtendoo/Documentos/odoo/17
   docker-compose exec db psql -U odoo -d nombre_bd
   ```

2. Verificar secuencias:
   ```sql
   SELECT aj.id, aj.name, aj.secure_sequence_id, seq.id as real_seq_id
   FROM account_journal aj
   LEFT JOIN ir_sequence seq ON seq.id = aj.secure_sequence_id
   WHERE aj.secure_sequence_id IS NOT NULL;
   ```

3. Aplicar corrección si es necesario

### Caso 3: Error en Múltiples Diarios

**Síntoma:**
El error aparece en diferentes diarios.

**Diagnóstico:**
```sql
SELECT
    COUNT(*) as total_afectados,
    STRING_AGG(name, ', ') as diarios_afectados
FROM account_journal
WHERE secure_sequence_id IS NOT NULL
  AND secure_sequence_id NOT IN (SELECT id FROM ir_sequence);
```

**Solución:**
Aplicar la corrección general que afecta a todos los diarios.

### Caso 4: Prevención con el Módulo

**Instalación del Módulo:**

1. El módulo ya está en el repositorio xtendoo
2. Reiniciar Odoo:
   ```bash
   cd /home/xtendoo/Documentos/odoo/17
   docker-compose restart odoo
   ```

3. Actualizar lista de aplicaciones en Odoo

4. Buscar e instalar "Account Move Sequence Fix"

**Beneficios:**
- ✅ Detecta el problema antes de que falle
- ✅ Muestra mensajes de error claros
- ✅ Registra todos los intentos en logs
- ✅ Intenta recuperación automática

## 🔧 Comandos Útiles

### Diagnóstico Rápido

```bash
# Ver estado de todos los diarios
docker-compose exec db psql -U odoo -d nombre_bd -c "
SELECT
    aj.name,
    aj.type,
    CASE
        WHEN aj.secure_sequence_id IS NULL THEN 'Sin secuencia'
        WHEN aj.secure_sequence_id IN (SELECT id FROM ir_sequence) THEN 'OK'
        ELSE 'PROBLEMA'
    END as estado
FROM account_journal aj
ORDER BY estado DESC, aj.name;
"
```

### Corrección Selectiva

```bash
# Solo corregir diarios de tipo venta
docker-compose exec db psql -U odoo -d nombre_bd -c "
UPDATE account_journal
SET secure_sequence_id = NULL
WHERE type = 'sale'
  AND secure_sequence_id NOT IN (SELECT id FROM ir_sequence);
"
```

### Backup Antes de Corregir

```bash
# Crear backup
cd /home/xtendoo/Documentos/odoo/17
docker-compose exec db pg_dump -U odoo nombre_bd > backups/backup_antes_fix_$(date +%Y%m%d_%H%M%S).sql

# Aplicar corrección
./odoo/custom/src/xtendoo/account_move_sequence_fix/fix_sequences.sh

# Si algo sale mal, restaurar:
docker-compose exec -T db psql -U odoo nombre_bd < backups/backup_antes_fix_YYYYMMDD_HHMMSS.sql
```

## 📊 Monitoreo

### Ver Logs del Módulo

```bash
# Logs en tiempo real
docker-compose logs -f odoo | grep "account_move_sequence_fix"

# Últimos 100 errores
docker-compose logs odoo | grep -i "error\|sequence" | tail -100

# Buscar problemas específicos
docker-compose logs odoo | grep "secure_sequence_id"
```

### Verificar Estado Post-Corrección

```sql
-- No debe devolver ninguna fila
SELECT aj.id, aj.name, aj.secure_sequence_id
FROM account_journal aj
WHERE aj.secure_sequence_id IS NOT NULL
  AND aj.secure_sequence_id NOT IN (SELECT id FROM ir_sequence);

-- Debe devolver "OK" para todos
SELECT
    COUNT(*) as total_journals,
    COUNT(CASE WHEN secure_sequence_id IS NOT NULL
               AND secure_sequence_id IN (SELECT id FROM ir_sequence) THEN 1 END) as journals_ok,
    COUNT(CASE WHEN secure_sequence_id IS NULL THEN 1 END) as journals_sin_secuencia
FROM account_journal;
```

## 🚨 Troubleshooting

### Problema: El error persiste después de la corrección

**Posibles causas:**
1. Cache de Odoo no actualizado
2. Sesión de usuario no refrescada
3. Transacciones pendientes en BD

**Solución:**
```bash
# 1. Limpiar cache y reiniciar
docker-compose restart odoo

# 2. En Odoo, cerrar sesión y volver a entrar

# 3. Verificar que no hay transacciones bloqueadas
docker-compose exec db psql -U odoo -d nombre_bd -c "
SELECT * FROM pg_stat_activity WHERE state = 'active';
"
```

### Problema: Secuencias se recrean con números incorrectos

**Solución:**
```sql
-- Ajustar el próximo número de secuencia
UPDATE ir_sequence
SET number_next = (
    SELECT COALESCE(MAX(CAST(SUBSTRING(name FROM '[0-9]+') AS INTEGER)), 0) + 1
    FROM account_move
    WHERE journal_id = (
        SELECT id FROM account_journal WHERE secure_sequence_id = ir_sequence.id LIMIT 1
    )
)
WHERE code LIKE 'account.move%';
```

### Problema: Módulo no aparece en lista de aplicaciones

**Solución:**
```bash
# 1. Verificar que el módulo está en el lugar correcto
ls -la /home/xtendoo/Documentos/odoo/17/odoo/custom/src/xtendoo/account_move_sequence_fix/

# 2. Verificar permisos
chmod -R 755 /home/xtendoo/Documentos/odoo/17/odoo/custom/src/xtendoo/account_move_sequence_fix/

# 3. Reiniciar Odoo en modo actualización
docker-compose restart odoo

# 4. Actualizar lista de aplicaciones en Odoo con modo desarrollador activo
# Configuración > Activar modo desarrollador
# Aplicaciones > Actualizar lista de aplicaciones
```

## 📚 Referencias

- [Documentación Odoo - Sequences](https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html#sequences)
- [PostgreSQL - Type Casting](https://www.postgresql.org/docs/current/typeconv.html)
- [Odoo - Journal Configuration](https://www.odoo.com/documentation/17.0/applications/finance/accounting/getting_started/setup.html)

## 💡 Tips

1. **Siempre hacer backup** antes de modificar secuencias
2. **Usar el script de ayuda** para diagnóstico automatizado
3. **Instalar el módulo** para prevención a futuro
4. **Monitorear logs** después de aplicar correcciones
5. **Documentar** cualquier cambio realizado

---

**¿Necesitas más ayuda?**
- Revisa el archivo `INSTALL.md` para instrucciones detalladas
- Consulta `README.md` para documentación del módulo
- Ejecuta `fix_sequences.sh` para solución guiada

