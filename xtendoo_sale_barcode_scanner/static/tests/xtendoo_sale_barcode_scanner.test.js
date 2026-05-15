import { beforeEach, destroy, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, defineModels, fields, models, mountView, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { barcodeService } from "@barcodes/barcode_service";

class SaleOrder extends models.Model {
    name = fields.Char({ string: "Reference" });
    partner_name = fields.Char({ string: "Customer" });
    _barcode_scanned = fields.Char({ string: "Barcode Scanned" });

    _records = [{ id: 1, name: "S0001", partner_name: "Azure Interior", _barcode_scanned: "" }];
}

defineModels([SaleOrder]);

beforeEach(() => {
    patchWithCleanup(barcodeService, {
        maxTimeBetweenKeysInMs: 0,
    });
});

test("scanner widget enables barcode capture on regular editable fields inside the sale order form", async () => {
    const view = await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner_name"/>
                <field name="_barcode_scanned" widget="xtendoo_sale_barcode_scanner"/>
            </form>
        `,
    });

    const onBarcodeScanned = (event) => {
        expect.step(event.detail.barcode);
    };
    view.env.services.barcode.bus.addEventListener("barcode_scanned", onBarcodeScanned);

    const internalInput = document.querySelector(".o_field_widget[name=partner_name] input");

    expect(".o_field_widget[name=partner_name] input").toHaveAttribute("barcode_events", "true");

    await contains(".o_field_widget[name=partner_name] input").focus();
    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "SCAN001",
        target: internalInput,
    });
    await animationFrame();

    expect.verifySteps(["SCAN001"]);
    expect(".o_field_widget[name=partner_name] input").toBeFocused();

    view.env.services.barcode.bus.removeEventListener("barcode_scanned", onBarcodeScanned);
});

test("scanner widget only updates the record for events coming from its form", async () => {
    const view = await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner_name"/>
                <field name="_barcode_scanned" widget="xtendoo_sale_barcode_scanner"/>
            </form>
        `,
    });

    const internalInput = document.querySelector(".o_field_widget[name=partner_name] input");
    const externalInput = document.createElement("input");
    document.body.append(externalInput);

    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "OUTSIDE",
        target: externalInput,
    });
    await animationFrame();
    expect(view.model.root.data._barcode_scanned).toBe("");

    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "DIRECT001",
        target: internalInput,
    });
    await animationFrame();
    expect(view.model.root.data._barcode_scanned).toBe("DIRECT001");

    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "",
        target: internalInput,
    });
    await animationFrame();
    expect(view.model.root.data._barcode_scanned).toBe("DIRECT001");

    externalInput.remove();
});

test("scanner widget restores managed barcode_events attributes on unmount", async () => {
    const view = await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner_name"/>
                <field name="_barcode_scanned" widget="xtendoo_sale_barcode_scanner"/>
            </form>
        `,
    });

    const formElement = document.querySelector(".o_form_view, .o_form_renderer");
    const managedInput = document.querySelector(".o_field_widget[name=partner_name] input");
    const preconfiguredInput = document.createElement("input");
    preconfiguredInput.setAttribute("barcode_events", "false");
    formElement.append(preconfiguredInput);
    await animationFrame();

    expect(managedInput.getAttribute("barcode_events")).toBe("true");
    expect(preconfiguredInput.getAttribute("barcode_events")).toBe("true");

    destroy(view);
    await animationFrame();

    expect(managedInput.getAttribute("barcode_events")).toBe(null);
    expect(preconfiguredInput.getAttribute("barcode_events")).toBe("false");
});

test("scanner widget keeps the original field value while the barcode is processed", async () => {
    const view = await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner_name"/>
                <field name="_barcode_scanned" widget="xtendoo_sale_barcode_scanner"/>
            </form>
        `,
    });

    const internalInput = document.querySelector(".o_field_widget[name=partner_name] input");
    internalInput.value = "Azure Interior";

    for (const key of ["S", "C", "A", "N", "0", "0", "1", "Enter"]) {
        const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key });
        internalInput.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(true);
    }
    expect(internalInput.value).toBe("Azure Interior");

    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "SCAN001",
        target: internalInput,
    });
    await animationFrame();

    expect(internalInput.value).toBe("Azure Interior");
    expect(view.model.root.data._barcode_scanned).toBe("SCAN001");
});

test("scanner widget does not require cleanBarcode on the started barcode service", async () => {
    const view = await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="partner_name"/>
                <field name="_barcode_scanned" widget="xtendoo_sale_barcode_scanner"/>
            </form>
        `,
    });

    const internalInput = document.querySelector(".o_field_widget[name=partner_name] input");

    expect(view.env.services.barcode.cleanBarcode).toBe(undefined);

    for (const key of ["1", "2", "3"]) {
        const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key });
        internalInput.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(true);
    }

    view.env.services.barcode.bus.trigger("barcode_scanned", {
        barcode: "123",
        target: internalInput,
    });
    await animationFrame();

    expect(view.model.root.data._barcode_scanned).toBe("123");
});

