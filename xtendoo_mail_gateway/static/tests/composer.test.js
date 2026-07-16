import "@xtendoo_mail_gateway/components/composer/composer";

import { Composer } from "@mail/core/common/composer";
import { expect, test } from "@odoo/hoot";

test("gateway composer forwards the focus event", () => {
    const composer = {};
    let propagationStopped = false;
    const event = {
        stopPropagation() {
            propagationStopped = true;
        },
    };
    const component = {
        props: { composer, type: false },
        thread: undefined,
    };

    Composer.prototype.onFocusin.call(component, event);

    expect(propagationStopped).toBe(true);
    expect(composer.isFocused).toBe(true);
});
