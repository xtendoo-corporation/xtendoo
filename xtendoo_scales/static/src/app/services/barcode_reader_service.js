/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/services/barcode_reader_service";

console.log('%c[Xtendoo Scales] 🔧 Módulo cargado - Iniciando patch del BarcodeReader', 'background: #875A7B; color: white; padding: 2px 5px; border-radius: 3px;');
console.log('[Xtendoo Scales] BarcodeReader disponible:', BarcodeReader);
console.log('[Xtendoo Scales] BarcodeReader.prototype:', BarcodeReader.prototype);

// Parchea la clase BarcodeReader para interceptar el método scan
// y evitar que las entradas numéricas de básculas USB se interpreten como códigos de barras
patch(BarcodeReader.prototype, {
    scan(code) {
        console.log('%c[Xtendoo Scales] 🎯 SCAN interceptado', 'background: #2ECC71; color: white; font-weight: bold; padding: 3px 6px;');
        console.log('[Xtendoo Scales] 📥 Código recibido:', code);
        return super.scan(code);
    },
    async _scan(code) {
        // Expresión regular mejorada para detectar números con punto O coma decimal
        // Acepta SOLO de 1 a 3 decimales: 123, 1.5, 1,5, 0.385, 0,385, 1,234
        // Rechaza más de 3 decimales: 0.3804, 1.23456 (se procesarán como código de barras)
        const isNumericOnly = /^\d+([.,]\d{1,3})?$/.test(code);

        // Validar que no tenga más de 5 dígitos en la parte entera
        const parts = code.split(/[.,]/);
        const integerPart = parts[0];
        const hasMoreThan5Digits = integerPart.length > 5;

        console.log('[Xtendoo Scales] 📊 _scan interceptado:', {
            code: code,
            type: typeof code,
            isNumeric: isNumericOnly,
            regex_test: /^\d+([.,]\d{1,3})?$/.test(code),
            decimals: code.includes(',') || code.includes('.') ? code.split(/[.,]/)[1]?.length || 0 : 0,
            integerDigits: integerPart.length,
            hasMoreThan5Digits: hasMoreThan5Digits
        });

        if (!code) {
            console.log('[Xtendoo Scales] ⚠️ Código vacío, ignorando');
            return;
        }

        // Verificar si es solo un número (posiblemente peso de báscula)
        // Debe cumplir: ser numérico Y tener máximo 5 dígitos enteros
        const isValidScale = isNumericOnly && !hasMoreThan5Digits;

        if (isNumericOnly && hasMoreThan5Digits) {
            console.log('%c[Xtendoo Scales] 📦 Número con más de 5 dígitos detectado', 'background: #9B59B6; color: white; font-weight: bold; padding: 2px 5px;');
            console.log('[Xtendoo Scales] 📏 Dígitos enteros:', integerPart.length);
            console.log('[Xtendoo Scales] ➡️ Procesando como código de barras (no como cantidad)');
            // Continuar al flujo normal de código de barras
        }

        if (isValidScale) {
            const hasComma = code.includes(',');
            const hasDot = code.includes('.');
            console.log('%c[Xtendoo Scales] 🔢 Entrada numérica detectada', 'background: #3498DB; color: white; font-weight: bold; padding: 2px 5px;');
            console.log('[Xtendoo Scales] 📏 Valor:', code);
            console.log('[Xtendoo Scales] 🌍 Formato:', hasComma ? 'Europeo (coma decimal)' : hasDot ? 'Anglosajón (punto decimal)' : 'Entero');

            // Obtener el elemento activo (con foco)
            const activeElement = document.activeElement;
            console.log('[Xtendoo Scales] 🎯 Elemento activo:', {
                tagName: activeElement?.tagName,
                type: activeElement?.type,
                name: activeElement?.name,
                className: activeElement?.className,
                id: activeElement?.id
            });

            // Lista de selectores para campos de cantidad
            const quantityFieldSelectors = [
                'input[name="quantity"]',
                '.numpad-input',
                '.product-list input',
                '.orderline-quantity input',
                'input[type="number"]',
                '.pos-input-quantity',
                '.quantity-input',
                'input.o_input[type="text"]',
                '.o_field_widget input',
                '[name*="qty"] input',
                '[name*="quantity"] input',
            ];

            // Verificar si el foco está en un campo de cantidad
            const isQuantityField = activeElement &&
                quantityFieldSelectors.some(selector => {
                    const matches = activeElement.matches(selector);
                    if (matches) {
                        console.log('[Xtendoo Scales] ✅ Coincide con selector:', selector);
                    }
                    return matches;
                });

            if (isQuantityField) {
                console.log('[Xtendoo Scales] 🚫 IGNORANDO - Campo de cantidad con foco');
                console.log('[Xtendoo Scales] 📝 Dejando que el valor se ingrese normalmente');
                return;
            }

            // Verificar si hay una línea de pedido seleccionada
            const orderlineSelectors = [
                '.orderline.selected',
                '.order-line.selected',
                '[class*="orderline"][class*="selected"]',
                '.o-selected',
                '[data-selected="true"]'
            ];

            let hasSelectedOrderline = false;
            for (const selector of orderlineSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    hasSelectedOrderline = true;
                    console.log('[Xtendoo Scales] ✅ Línea de pedido seleccionada encontrada:', selector);
                    break;
                }
            }

            if (hasSelectedOrderline) {
                console.log('%c[Xtendoo Scales] ⚖️ ESTABLECIENDO CANTIDAD', 'background: #E67E22; color: white; font-weight: bold; padding: 2px 5px;');
                console.log('[Xtendoo Scales] 💡 Línea de pedido seleccionada detectada');
                console.log('[Xtendoo Scales] 🔢 Estableciendo cantidad:', code);
                console.log('%c[Xtendoo Scales] 🛑 DETENIENDO procesamiento como código de barras', 'background: #E74C3C; color: white; font-weight: bold; padding: 2px 5px;');

                // Intentar establecer la cantidad en la línea seleccionada
                try {
                    // Convertir coma a punto para JavaScript (formato europeo -> anglosajón)
                    const numericValue = code.replace(',', '.');

                    console.log('[Xtendoo Scales] 🔢 Valor original recibido:', code);
                    console.log('[Xtendoo Scales] 🔢 Valor convertido (sin aproximar):', numericValue);
                    console.log('[Xtendoo Scales] 🔢 Tipo de dato:', typeof numericValue);
                    console.log('[Xtendoo Scales] 🔢 Longitud del string:', numericValue.length);

                    // ESTRATEGIA 1: Buscar cualquier elemento clickeable en la línea para activar edición
                    const selectedOrderline = document.querySelector('.orderline.selected, .order-line.selected');
                    console.log('[Xtendoo Scales] 🔍 Línea seleccionada encontrada:', selectedOrderline);

                    if (selectedOrderline) {
                        // Mostrar estructura del elemento para debug
                        console.log('[Xtendoo Scales] 📋 Clases de la línea:', selectedOrderline.className);
                        console.log('[Xtendoo Scales] 📋 HTML interno:', selectedOrderline.innerHTML.substring(0, 200) + '...');

                        // ESTRATEGIA 2: Buscar el botón "Qty" del numpad inferior
                        // El botón tiene la clase específica: numpad-qty
                        let numpadQtyButton = document.querySelector('button.numpad-qty');

                        if (!numpadQtyButton) {
                            // Fallback: buscar por otras clases
                            numpadQtyButton = document.querySelector('.numpad-button.numpad-qty');
                        }

                        if (!numpadQtyButton) {
                            // Fallback adicional: buscar por texto
                            const allButtons = document.querySelectorAll('button');
                            for (const btn of allButtons) {
                                const text = btn.textContent?.trim().toLowerCase();
                                if (text === 'qty' || text === 'ctd.' || text === 'ctd' || text === 'cantidad') {
                                    numpadQtyButton = btn;
                                    break;
                                }
                            }
                        }

                        if (numpadQtyButton) {
                            console.log('[Xtendoo Scales] 🎯 Botón Qty del numpad encontrado:', numpadQtyButton);
                            console.log('[Xtendoo Scales] 🎯 Clases del botón:', numpadQtyButton.className);
                            console.log('[Xtendoo Scales] 🎯 Texto del botón:', numpadQtyButton.textContent);
                        }

                        if (numpadQtyButton) {
                            numpadQtyButton.click();
                            console.log('[Xtendoo Scales] 🖱️ Click en botón Qty del numpad');
                        } else {
                            console.log('[Xtendoo Scales] ⚠️ No se encontró botón Qty del numpad, intentando con elemento de la línea');
                            const qtyElement = selectedOrderline.querySelector('.qty, span.qty, .quantity, [class*="qty"]');
                            if (qtyElement) {
                                qtyElement.click();
                                console.log('[Xtendoo Scales] 🖱️ Click en elemento Qty de la línea');
                            } else {
                                selectedOrderline.click();
                                console.log('[Xtendoo Scales] 🖱️ Click en línea de pedido');
                            }
                        }

                        // ESTRATEGIA 3: Usar eventos de teclado globales (no buscar input)
                        // En Odoo POS, después de hacer click en Qty, el sistema espera entrada de teclado directa
                        console.log('[Xtendoo Scales] ⌨️ Usando numpad virtual del POS');

                        // Usar Promise para esperar de forma asíncrona
                        await new Promise((resolve) => {
                            setTimeout(() => {
                                // Simular eventos de teclado globales para cada dígito
                                const chars = numericValue.split('');
                                console.log('[Xtendoo Scales] ⌨️ Simulando pulsaciones de teclas:', chars);
                                console.log('[Xtendoo Scales] ⌨️ Total de caracteres a enviar:', chars.length);
                                console.log('[Xtendoo Scales] ⌨️ Valor exacto sin aproximar:', numericValue);

                                // Simular cada pulsación de tecla con un pequeño delay entre ellas
                                chars.forEach((char, index) => {
                                    setTimeout(() => {
                                        // Crear eventos de teclado realistas
                                        const keydownEvent = new KeyboardEvent('keydown', {
                                            key: char,
                                            code: char === '.' ? 'Period' : char === ',' ? 'Comma' : 'Digit' + char,
                                            keyCode: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            which: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            bubbles: true,
                                            cancelable: true,
                                            composed: true
                                        });

                                        const keypressEvent = new KeyboardEvent('keypress', {
                                            key: char,
                                            code: char === '.' ? 'Period' : char === ',' ? 'Comma' : 'Digit' + char,
                                            keyCode: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            which: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            charCode: char.charCodeAt(0),
                                            bubbles: true,
                                            cancelable: true,
                                            composed: true
                                        });

                                        const keyupEvent = new KeyboardEvent('keyup', {
                                            key: char,
                                            code: char === '.' ? 'Period' : char === ',' ? 'Comma' : 'Digit' + char,
                                            keyCode: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            which: char === '.' ? 190 : char === ',' ? 188 : 48 + parseInt(char),
                                            bubbles: true,
                                            cancelable: true,
                                            composed: true
                                        });

                                        // Disparar eventos en el documento (global)
                                        document.dispatchEvent(keydownEvent);
                                        document.dispatchEvent(keypressEvent);
                                        document.dispatchEvent(keyupEvent);

                                        // También disparar en window por si Odoo escucha ahí
                                        window.dispatchEvent(keydownEvent);

                                        console.log('[Xtendoo Scales] 🔤 Tecla disparada:', char, `(posición ${index + 1}/${chars.length})`);

                                        // Si es el último carácter, resolver la promise
                                        if (index === chars.length - 1) {
                                            setTimeout(() => {
                                                console.log('[Xtendoo Scales] ✅ Todas las teclas simuladas');
                                                console.log('[Xtendoo Scales] ✅ Valor completo enviado:', chars.join(''));

                                                // IMPORTANTE: Simular Enter para confirmar la cantidad
                                                setTimeout(() => {
                                                    const enterEvent = new KeyboardEvent('keydown', {
                                                        key: 'Enter',
                                                        code: 'Enter',
                                                        keyCode: 13,
                                                        which: 13,
                                                        bubbles: true,
                                                        cancelable: true,
                                                        composed: true
                                                    });
                                                    document.dispatchEvent(enterEvent);
                                                    window.dispatchEvent(enterEvent);
                                                    console.log('[Xtendoo Scales] ⏎ Enter disparado para confirmar cantidad');

                                                    // Esperar un momento y verificar la cantidad
                                                    setTimeout(() => {
                                                        const orderlineElement = document.querySelector('.orderline.selected, .order-line.selected');
                                                        if (orderlineElement) {
                                                            const qtyElement = orderlineElement.querySelector('.qty, span.qty');
                                                            const displayedQty = qtyElement?.textContent?.trim();
                                                            const expectedQty = numericValue;

                                                            console.log('[Xtendoo Scales] 📊 Cantidad mostrada en UI:', displayedQty);
                                                            console.log('[Xtendoo Scales] 📊 Cantidad esperada:', expectedQty);

                                                            // Comparar valores como números para detectar aproximación
                                                            const displayedNum = parseFloat(displayedQty);
                                                            const expectedNum = parseFloat(expectedQty);

                                                            if (!isNaN(displayedNum) && !isNaN(expectedNum) && Math.abs(displayedNum - expectedNum) > 0.0001) {
                                                                console.warn('%c[Xtendoo Scales] ⚠️ ADVERTENCIA: La cantidad fue aproximada por Odoo', 'background: #E74C3C; color: white; font-weight: bold; padding: 3px 6px;');
                                                                console.warn('[Xtendoo Scales] ⚠️ Valor enviado:', expectedQty, '→ Valor mostrado:', displayedQty);
                                                                console.warn('[Xtendoo Scales] ⚠️ Diferencia:', Math.abs(displayedNum - expectedNum));
                                                                console.warn('%c[Xtendoo Scales] 🔧 SOLUCIÓN:', 'background: #3498DB; color: white; font-weight: bold; padding: 3px 6px;');
                                                                console.warn('[Xtendoo Scales] 📍 Ir a: Inventario → Configuración → Unidades de Medida');
                                                                console.warn('[Xtendoo Scales] 📍 Buscar la unidad: "Unidades" o "kg"');
                                                                console.warn('[Xtendoo Scales] 📍 Campo "Precision de Redondeo" debe ser: 0.001');
                                                                console.warn('[Xtendoo Scales] 📍 Actualmente podría ser: 0.01 (redondea a 2 decimales)');
                                                                console.warn('[Xtendoo Scales] 📍 Con 0.001 permitirá 3 decimales sin aproximar');
                                                            } else if (displayedQty === expectedQty || Math.abs(displayedNum - expectedNum) <= 0.0001) {
                                                                console.log('%c[Xtendoo Scales] ✅ PERFECTO: Cantidad establecida correctamente sin aproximación', 'background: #27AE60; color: white; font-weight: bold; padding: 3px 6px;');
                                                            }
                                                        }
                                                        resolve();
                                                    }, 100);
                                                }, 50);
                                            }, 50);
                                        }
                                    }, index * 50); // 50ms entre cada tecla
                                });

                                // Si no hay caracteres (no debería pasar), resolver inmediatamente
                                if (chars.length === 0) {
                                    resolve();
                                }

                            }, 200); // Esperar 200ms después del click en Qty
                        });
                    }

                    // NO llamar al super._scan() - RETORNAR AQUÍ
                    console.log('%c[Xtendoo Scales] ✅ CANTIDAD ESTABLECIDA - No se procesará como código de barras', 'background: #27AE60; color: white; font-weight: bold; padding: 2px 5px;');
                    return; // IMPORTANTE: Salir aquí sin procesar como barcode
                } catch (error) {
                    console.error('[Xtendoo Scales] ❌ Error al establecer cantidad:', error);
                    console.error(error.stack);
                    // Si hay error, continuar con el flujo normal
                }
            }

            // Verificar si el popup de cantidad está visible
            const popupSelectors = [
                '.popup.number-popup',
                '.modal-dialog .numpad',
                '[class*="NumberPopup"]',
                '.o_dialog .numpad',
                '.modal-open'
            ];

            let isPopupVisible = false;
            for (const selector of popupSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    isPopupVisible = true;
                    console.log('[Xtendoo Scales] ✅ Popup detectado:', selector);
                    break;
                }
            }

            if (isPopupVisible) {
                console.log('[Xtendoo Scales] 🚫 IGNORANDO - Popup de cantidad visible');
                return;
            }

            console.log('[Xtendoo Scales] ⚠️ No se encontró contexto de cantidad');
            console.log('[Xtendoo Scales] ➡️ Procesando como código de barras normal');
        } else {
            console.log('[Xtendoo Scales] 📦 No es numérico, procesando como código de barras:', code);
        }

        // Llamar al método original
        console.log('[Xtendoo Scales] 🔄 Llamando al método _scan original');
        return super._scan(code);
    }
});

console.log('%c[Xtendoo Scales] ✅ Patch aplicado correctamente', 'background: #27AE60; color: white; font-weight: bold; padding: 3px 6px;');
console.log('[Xtendoo Scales] ✓ scan() patcheado');
console.log('[Xtendoo Scales] ✓ _scan() patcheado');
console.log('[Xtendoo Scales] 🎉 Módulo listo para interceptar códigos de barras numéricos');
